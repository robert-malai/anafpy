# Tax declarations (authoring, validation, signing)

`anafpy.declaratii` prepares Romanian tax declarations (D300 VAT return first;
the design is per-form generic) entirely **locally**: it validates with ANAF's
own DUKIntegrator, renders the official PDF, and signs it with the taxpayer's
qualified certificate. It has **no transport client, no ANAF host, no session** —
it is subprocess + crypto + files. Filing the signed PDF with ANAF (portal
upload) is a later milestone; for now you file the signed PDF manually on the
portal.

The pipeline: unstructured info → author the XML → DUKIntegrator `-v` (validate
in a loop until `ok`) → DUKIntegrator `-p` (official PDF) → pyHanko + the
platform raw signer (qualified signature) → signed PDF on disk.

## Prerequisites

- **DUKIntegrator** — download
  [`dist_javaInclus20200203.zip`](https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip),
  extract it, and drop the per-form validator jars (e.g. `D300Validator.jar`,
  `D300Pdf.jar` from ANAF's update feed) into `dist/lib/`. Ignore the bundled
  32-bit JRE 6 — any modern JVM works.
- **A JRE/JDK** (Java 8+) on `PATH`, or set `ANAFPY_DUK_JAVA`.
- **The `declaratii` extra** for signing: `pip install 'anafpy[declaratii]'`
  (pyHanko). Validation and rendering do not need it.

See the [DUKIntegrator reference](../anaf-reference/declaratii/duk.md) for the
CLI contract, the err-file format, and the `nr_evid` layout.

## Validate and render

```python
from pathlib import Path
from anafpy.declaratii import DukIntegrator

duk = DukIntegrator(Path("~/DUKIntegrator/dist").expanduser())

xml = Path("d300.xml").read_bytes()
result = await duk.validate("D300", xml)
if not result.ok:
    for finding in result.findings:      # DUK's own messages, verbatim
        print(finding.severity, finding.message)

# Render the official PDF (validates first; writes nothing on failure).
rendered = await duk.render("D300", xml, Path("d300.pdf"))
assert rendered.ok
```

`validate`/`render` judge success by the err-file content, never by the exit
code (DUK exits `0` on a validation failure). `installed_forms()` and
`feed_versions()` power a staleness check — CLI-mode DUK does not auto-update, so
an installed validator can lag ANAF's current one.

## The `nr_evid` helper

D300 requires `nr_evid`, a 23-character payment-evidence number with a check
digit. Compute it — never by hand:

```python
from anafpy.declaratii import payment_evidence_number

payment_evidence_number(tip_decont="L", luna=6, an=2026)
# '10301010626250726000042'
```

## Signing (macOS)

anafpy never touches key material: the raw RSA signature is delegated to the OS,
and the token middleware owns the PIN/2FA. On macOS the qualified certificate
lives behind a CryptoTokenKit extension (no PKCS#11 dylib), so the key is reached
through Security.framework via `KeychainRawSigner`; **each signature fires the
token's approval prompt**.

```python
from anafpy.declaratii import KeychainRawSigner
from anafpy.declaratii.signing import resolve_signing_label
from anafpy.declaratii.pdfsign import sign_pdf

label = resolve_signing_label()          # ANAFPY_SIGN_IDENTITY / persisted SPV cert
signer = KeychainRawSigner(label)        # same qualified certificate as SPV
result = await sign_pdf(Path("d300.pdf").read_bytes(), signer)
Path("d300-semnat.pdf").write_bytes(result.pdf)
```

`sign_pdf` embeds a standard `adbe.pkcs7.detached` CMS as an incremental update,
so a rendered PDF's embedded XML (`/EmbeddedFiles`) survives and the signature
covers the whole file. The issuer certificate is fetched best-effort from the
leaf's AIA URL; if that fetch fails the CMS is leaf-only and
`result.chain_complete` is `False` (portal acceptance of a leaf-only chain is
unverified). The identity defaults to the persisted SPV certificate selection
(`anafpy spv select`) — the same qualified certificate — or set
`ANAFPY_SIGN_IDENTITY`.

**Windows signing is not in this release**; the `RawSigner` protocol is the seam
a `CngRawSigner` will slot into.

## CLI

```bash
anafpy declaratii validate D300 d300.xml --duk-dir ~/DUKIntegrator/dist
anafpy declaratii render   D300 d300.xml -o d300.pdf --duk-dir ~/DUKIntegrator/dist
anafpy declaratii sign     d300.pdf -o d300-semnat.pdf   # fires the PIN/2FA prompt
```

`--duk-dir` defaults to `ANAFPY_DUK_DIR`, `--java` to `ANAFPY_DUK_JAVA`. `sign`
resolves the certificate from `--identity`, then `ANAFPY_SIGN_IDENTITY`, then the
persisted SPV selection.

## Using it through Claude (MCP)

The same operations are MCP tools (`declaratie_validate`, `declaratie_render`,
`declaratie_sign`, `declaratie_nr_evid`, `declaratie_duk_status`) and a
`declaratie-compose` skill — see the [MCP tools](../mcp/tools.md) and
[setup](../mcp/setup.md) pages.
