# Tax declarations (authoring, validation, signing, status)

`anafpy.declaratii` prepares Romanian tax declarations (D300 VAT return first;
the design is per-form generic) entirely **locally**: it validates with ANAF's
own DUKIntegrator, renders the official PDF, and signs it with the taxpayer's
qualified certificate. Filing the signed PDF works two ways: manually on the
portal, or through the
[upload client](#filing-on-the-portal) — live-verified end to end on
2026-07-17. Afterwards you **track it from here**:
[`DeclarationStatusClient`](#filing-status-and-recipisa)
checks the processing status and downloads the signed recipisa over ANAF's
public StareD112 service, with no login of any kind.

The pipeline: unstructured info → author the XML → DUKIntegrator `-v` (validate
in a loop until `ok`) → DUKIntegrator `-p` (official PDF) → pyHanko + the
platform raw signer (qualified signature) → signed PDF on disk → manual portal
upload → status/recipisa via StareD112.

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

## Filing on the portal

`DeclarationUploadClient` automates the "Depunere declarații" portal
(`decl.anaf.mfinante.gov.ro/WAS6DUS`): a certificate login — same
platform-keystore model as the [SPV client](../anaf-reference/spv/api.md),
**fires the token PIN / 2FA** — followed by the one multipart POST of the
signed PDF. Live-verified end to end (2026-07-17, a D406T filing): the success
page yields the **upload index**, the portal's known rejection page comes back
as `accepted=False` with the reason, and an unrecognised page returns
`accepted=None` with the raw `html` carried. Mind the portal's own caveat: the
success page is **not** the registration confirmation — that is the recipisa,
which you poll via StareD112 with the returned index. Sessions are disposable
(the portal enforces a ~10-minute inactivity timeout): log in, upload, done.

```python
from anafpy.declaratii import DeclarationUploadClient, PortalCurlBootstrapper

async with DeclarationUploadClient(
    bootstrapper=PortalCurlBootstrapper("MY CERT IDENTITY")  # Keychain name
) as client:
    await client.login()                      # fires the certificate 2FA
    result = await client.upload(signed_pdf, filename="d300.pdf")
    if result.accepted:
        print("upload index:", result.upload_index)   # feed it to StareD112
    elif result.accepted is False:
        print("rejected:", result.reason)
```

There is **no TEST environment** for declaration filing — every upload is a
production filing. The one sanctioned no-effect exercise is **D406T**, the
SAF-T voluntary-testing declaration (no legal or fiscal effect; see the
[portal-upload reference](../anaf-reference/declaratii/portal-upload.md)) —
which is exactly what anafpy's own gated live test files.

## Filing status and recipisa

After you upload the signed PDF on the portal, ANAF hands back an **upload
index** (also the recipisa number). ANAF's
[StareD112 service](../anaf-reference/declaratii/stared112.md) is **public and
unauthenticated** — the index + CUI pair is the access key — so checking the
processing status and fetching the signed recipisa needs no certificate, no
OAuth, nothing:

```python
from anafpy.declaratii import DeclarationStatusClient

async with DeclarationStatusClient() as client:
    status = await client.check_status(1100000001, "99999909")
    if status.found:
        for doc in status.documents:        # ALL the CUI's filings, last 3 months
            print(doc.index, doc.form, doc.state, doc.upload_date)
        mine = status.document(1100000001)  # the row for the queried index

    pdf = await client.download_receipt(1100000001)
    if pdf is not None:                     # None: unknown index or window lapsed
        Path("recipisa.pdf").write_bytes(pdf)
```

Each document's `state` is a `DeclarationState` — an enum whose **values are
ANAF's verbatim Romanian wording** (`"Documentul este valid"`,
`"In prelucrare"`, …) with a one-line English `description` per member, like
the SPV `ReportType` nomenclature. Compare by member
(`doc.state is DeclarationState.VALID`); the text as actually served stays in
`state_text`. Keep polling while a document is `DeclarationState.PROCESSING`.
For documents filed at an ANAF
counter, pass `filed_at_counter=True` and give the registration number as the
index. Service limits (ANAF's, not anafpy's): only the last **3 months** / last
**200 submissions** are queryable, and the recipisa PDF is available for
**~60 days** from filing (`receipt_available` per row) — archive it promptly;
it is the digitally signed proof of filing.

## CLI

```bash
anafpy declaratii validate D300 d300.xml --duk-dir ~/DUKIntegrator/dist
anafpy declaratii render   D300 d300.xml -o d300.pdf --duk-dir ~/DUKIntegrator/dist
anafpy declaratii sign     d300.pdf -o d300-semnat.pdf   # fires the PIN/2FA prompt
anafpy declaratii status   1100000001 99999909           # public — no login
anafpy declaratii recipisa 1100000001 -o recipisa.pdf    # public — no login
```

`--duk-dir` defaults to `ANAFPY_DUK_DIR`, `--java` to `ANAFPY_DUK_JAVA`. `sign`
resolves the certificate from `--identity`, then `ANAFPY_SIGN_IDENTITY`, then the
persisted SPV selection.

## Using it through Claude (MCP)

The same operations are MCP tools (`declaratie_validate`, `declaratie_render`,
`declaratie_sign`, `declaratie_nr_evid`, `declaratie_duk_status`,
`declaratie_status`, `declaratie_recipisa`) and a `declaratie-compose` skill —
see the [MCP tools](../mcp/tools.md) and [setup](../mcp/setup.md) pages.
