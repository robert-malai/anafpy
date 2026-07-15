# Plan: `anafpy.declaratii` — declaration authoring, validation, and signing (M1)

Status: **plan** (branch `feature/declaratii`). Scope of this milestone: **document
generation and signing only, exposed via MCP**. Filing the signed document with
ANAF (portal upload + recipisa tracking) is **milestone M2** and is deliberately
out of scope here — see §10 for the M2 sketch so nothing in M1 paints us into a
corner.

Everything in §2 was **live-proven on 2026-07-15** (macOS 26 / Oracle Java 26 /
certSIGN Paperless vToken). The appendices contain the working spike code and a
validated D300 XML; the implementer should not need to redo any research.

---

## 1. Goal and user story

Let Claude fill a Romanian tax declaration (D300 first; the design is per-form
generic) **from unstructured information**, validate it with **ANAF's own
validator**, render the **official PDF with embedded XML**, and **sign it with
the user's qualified certificate** — all locally via MCP tools, with the human
approving the signature out-of-band (vToken phone approval / token PIN). The
output of M1 is a signed PDF the user can file manually on the ANAF portal
(anaf.ro → Depunere declarații → Transmitere declarații); M2 automates that
upload.

Pipeline: unstructured info → Claude authors XML → DUKIntegrator `-v`
(validate-fix loop until `ok`) → DUKIntegrator `-p` (official PDF) → pyHanko +
platform raw-signer (qualified signature) → signed PDF on disk.

## 2. Facts established by the spikes (do not re-derive)

### 2.1 DUKIntegrator is headless-scriptable ("mode B")

- Distribution: `https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip`
  (extract `dist/`; **ignore the bundled 32-bit JRE 6**). Runs fine on modern
  JVMs for `-v` and `-p` (proven on Oracle Java 26, macOS arm64).
- Update feed: `http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml` —
  lists current core jars (`zz9/DUKIntegrator.jar`, `ss8/DecValidation.jar`,
  `ss8/DecPdf.jar`, `ss8/Validator.jar`) and per-form jars (e.g. D300 at
  `D300_27/D300Validator.jar` + `D300Pdf.jar`, version `J12.0.1`/`P9.0.0`).
  Per-form jars go into `dist/lib/`. **GUI mode auto-updates; CLI mode does
  not** — staleness must be surfaced (see `declaratie_duk_status`, §5).
- CLI contract (positional; `$` = "use default"; missing args → the only error
  message is `linie comanda incompleta` on stdout):

  ```
  java -jar DUKIntegrator.jar [-c configPath] -v <tip> <xml> [errFile] [valOption]
  java -jar DUKIntegrator.jar [-c configPath] -p <tip> <xml> [errFile] [valOption] [zipFile] [pdfFile]
  java -jar DUKIntegrator.jar [-c configPath] -s <tip> <xml> [errFile] [valOption] [zipFile] [pdfFile] <pin> <smartCard> [certSelector]
  ```

  - `tip` = form name exactly as the validator jar prefix (`D300`, `D112`, ...).
  - `errFile`: on success contains literally `ok`; on failure, lines prefixed
    `E:` (errors) / `W:` (warnings) followed by indented detail lines
    (`eroare regula: R25: ...`, `eroare atribut: ...`). Success is ALSO printed
    to stdout as `Validare fara erori fisier: <path>`; exit code is **0 either
    way** — judge by err-file content, never by exit code.
  - `valOption` defaults to 0; form-specific.
  - `zipFile`: `0` = form has no attachment (true for D300).
  - `-p` writes the official multi-page PDF with the XML as an embedded file
    (`/EmbeddedFiles` present). Proven: 4-page D300, 25 KB.
  - `-s` is NOT used on macOS (see 2.3); on Windows it is the candidate signer
    with `algorithm=mscapi` (see §8).

### 2.2 D300 wire format and the `nr_evid` field

- XSD: `https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/d300_v12_11022026.xml`
  (despite the extension it IS the XSD). Root `declaratie300`, namespace
  `mfp:anaf:dgti:d300:declaratie:v12`, **everything is attributes** on the one
  element, no children. Per-form pages under
  `https://static.anaf.ro/static/10/Anaf/Declaratii_R/<nnn>.html` publish the
  XSD + the validation annex PDF (`structura_D300_v12.0.0_10022026.pdf`).
- A validated nil D300 (June 2026) is in Appendix C. Iterating with `-v` from
  scratch took 5 rounds; the validator messages are precise enough to converge
  a model without any other documentation.
- `nr_evid` ("numărul de evidență a plății", required, 23 chars) is fully
  decoded from validator bytecode (v10 = XSD v12; confirmed against the annex
  example `10301010111250211000020` and accepted live by the validator):

  | positions | content |
  |---|---|
  | [0:2] | fixed `10` |
  | [2:5] | cod_imp, correlated with `tip_decont`: `301`=L (monthly), `302`=T (quarterly), `303`=S, `304`=A |
  | [5:7] | fixed `01` |
  | [7:11] | reporting period `MMYY` (zero-padded `luna` + last 2 of `an`) |
  | [11:17] | payment due date `25` + `MM` (luna+1, wrapping into the next year) + `YY` |
  | [17:21] | fixed `0000` |
  | [21:23] | check: the two-digit **sum of the first 21 digits** |

  Example: 06/2026 monthly → `10` `301` `01` `0626` `250726` `0000` `42`.
  Implement as a pure function; do not let the model compute the check digit.

### 2.3 Signing on macOS (SOLVED — this is the architecture)

- certSIGN Paperless vToken on macOS is a **CryptoTokenKit extension**
  (`ro.certsign.vtoken.ctke`; visible via `security list-smartcards`). There is
  **no PKCS#11 dylib**, so DUK's `sunpkcs11` path can never work on macOS, and
  `mscapi` is Windows-only. The key is reachable **only** through
  Security.framework.
- Working pipeline (proven end-to-end, signature validated
  `intact=True, valid=True`, coverage `ENTIRE_FILE`, `/EmbeddedFiles`
  preserved): DUK `-p` renders → **pyHanko** embeds a standard
  `adbe.pkcs7.detached` CMS as an incremental update, where the raw RSA
  PKCS#1 v1.5 SHA-256 op is `SecKeyCreateSignature` on the Keychain identity.
  Each raw signature fires the vToken **phone approval** — that is the human
  gate; **no PIN or secret ever passes through our code**.
- The proven raw-signing semantics are in Appendix A (Swift, 70 lines,
  compiled with stock `swiftc`); the pyHanko glue is Appendix B. The
  implementation should port the Swift semantics to **ctypes against
  Security.framework** (no build step, no new dependency) — see §4.3. Keep the
  Swift source in the reference docs as the semantic spec.
- Certificate chain: leaf via `SecIdentityCopyCertificate`; intermediate via
  the leaf's AIA URL (live: `http://crl.certsign.ro/certsign-qualifiedca2023rsa.crt`).
- pyHanko 0.35.x API notes: `SimpleCertificateStore` lives in
  `pyhanko_certvalidator.registry` (NOT `pyhanko.sign.general`); custom signer
  subclasses `pyhanko.sign.signers.Signer` and implements
  `async_sign_raw(data, digest_algorithm, dry_run)`; on `dry_run=True` return
  zero-bytes of the signature size (RSA key size / 8 — read it from the cert's
  public key, don't hardcode 512).

## 3. Design stance (must-keep invariants)

1. **anafpy never touches key material.** Raw signing is delegated to the OS
   (Security.framework / CNG / DUK+PKCS#11); PIN/2FA is owned by the
   middleware. **No MCP tool accepts a PIN parameter — ever** (it would enter
   model context).
2. **Validation authority is ANAF's.** DUK's per-form validators ARE ANAF's
   code; we run them, we never re-implement rules. (The `nr_evid` helper is
   composition, not validation.)
3. Signing is **consequential**: `declaratie_sign` is gated on `confirm=true`
   (model must relay the user's explicit ask), one attempt per call, failures
   return `signed=false` + guidance (mirror `spv_login`'s contract, not
   exceptions).
4. Binary artifacts go to **disk at caller-given paths** through the shared
   `write_artifact` collision guard (`overwrite=true` to replace) — never
   base64 into context. Same rules as e-Factura/SPV downloads.
5. User owns the DUK installation (like the OAuth app and the certificate):
   we point at it via env, we check staleness, we do not auto-install.
   (Follow-up may add an opt-in updater; not M1.)
6. Repo conventions apply unchanged: English identifiers (Romanian only in
   string literals/wire names; `D300`, `cui`, `luna` are domain terms), module
   style (`from __future__ import annotations`, `__all__`, Google docstrings,
   line length 88), async clients, pydantic models, no `@dataclass`.

## 4. Library layer — `src/anafpy/declaratii/`

New package, sibling of `spv/`. All async where subprocesses are involved
(`asyncio.create_subprocess_exec`, follow `spv/bootstrap.py` for style:
bounded timeouts, explicit env, tmp files in a `tempfile.TemporaryDirectory`).

### 4.1 `duk.py` — the DUKIntegrator wrapper

```python
class DukFinding(BaseModel):
    severity: Literal["error", "warning"]   # E: / W:
    message: str                            # the indented detail line(s), joined

class DukResult(BaseModel):
    ok: bool
    findings: list[DukFinding]
    raw: str                                # full err-file text, for debugging

class DukIntegrator:
    def __init__(self, duk_dir: Path, *, java: str | None = None,
                 timeout: float = 120.0) -> None: ...
    async def validate(self, form: str, xml: bytes,
                       *, option: int = 0) -> DukResult: ...
    async def render(self, form: str, xml: bytes, pdf_path: Path,
                     *, option: int = 0) -> DukResult: ...   # ok=True => pdf written
    def installed_forms(self) -> dict[str, str]: ...  # {"D300": "J12.0.1", ...}
    async def feed_versions(self) -> dict[str, str]: ...  # from versiuni.xml (httpx)
```

- `duk_dir` is the extracted `dist/` folder; validate its shape at construction
  (`DUKIntegrator.jar` exists, `lib/` exists) and raise `AnafConfigError` with
  the download URL in the message otherwise.
- Java discovery: explicit `java` arg > `ANAFPY_DUK_JAVA` > `shutil.which("java")`;
  missing java → `AnafConfigError`. Check it once (subprocess `java -version`)
  and cache.
- `installed_forms`: scan `lib/*Validator.jar`, read the version from the jar's
  manifest or the `<form>IstoriaVersiunilor.txt` if present; if neither, report
  `"unknown"`. Keep it cheap and non-fatal.
- Err-file parsing: `ok` (exact, stripped) → `ok=True, findings=[]`. Otherwise
  split on lines starting `E:`/`W:`; attach following indented lines to the
  current finding. Encoding: the err file is written in the platform default —
  decode with `errors="replace"` and try `utf-8` then `cp1250`.
- **Never trust the exit code** (0 on validation failure); never parse stdout
  except as debug info.
- Command shapes (note every positional filled explicitly — no `$` needed when
  we always pass temp paths):
  - validate: `-v <form> <xml_tmp> <err_tmp> <option>`
  - render: `-p <form> <xml_tmp> <err_tmp> <option> 0 <pdf_path>`
- The vendored XSDs are NOT needed at runtime; DUK owns schema validation.

### 4.2 `nr_evid.py` — payment evidence number

```python
def payment_evidence_number(*, tip_decont: str, luna: int, an: int) -> str
```

Pure function implementing §2.2 exactly (raise `ValueError` on unknown
`tip_decont`; document that `1` (special decont) has no known cod_imp mapping —
reject it for now with a clear message). Unit-test against BOTH known vectors:
the annex example (`tip_decont="L"`, 01/2011 → `10301010111250211000020`) and
the live-validated 06/2026 case (→ `10301010626250726000042`).
D300-specific for now; if another form needs it later, generalize by taking
`cod_imp` directly. Note: the check digit is `sum of first 21 digits` compared
for equality against `d21*10 + d22` — sums here are always < 100, no modulo.

### 4.3 `signing.py` — platform raw signer + identity

```python
class RawSigner(Protocol):
    """Raw PKCS#1 v1.5 signature over `data` (the signer hashes internally)."""
    def certificate(self) -> bytes: ...           # leaf, DER
    async def sign(self, data: bytes) -> bytes:   # SHA-256, raw signature bytes
```

macOS implementation `KeychainRawSigner(label: str)` via **ctypes** against
`/System/Library/Frameworks/Security.framework/Security` (+ CoreFoundation for
CFData/CFString/CFDictionary). Functions needed: `SecItemCopyMatching` (query:
`kSecClassIdentity`, `kSecMatchLimitAll`, return refs+attributes; match on
`kSecAttrLabel == label`), `SecIdentityCopyCertificate`,
`SecCertificateCopyData`, `SecIdentityCopyPrivateKey`, `SecKeyCreateSignature`
with algorithm constant `kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA256`
(load CFStringRef globals with `c_void_p.in_dll`). The **Swift program in
Appendix A is the proven reference semantics** — port it 1:1; if the ctypes
port fights back, shipping-and-compiling the Swift helper is NOT an acceptable
fallback (adds a toolchain dependency); instead fall back to `pyobjc-framework-Security`
as an optional dependency of the `declaratii` extra and keep the same class API.
- The `sign` call **blocks on the middleware approval** — run it in
  `asyncio.to_thread` with a generous timeout (110 s, mirroring the SPV
  bootstrap's bounded-wait stance) and surface timeout as a clean failure.
- Identity selection: default label comes from the **persisted SPV identity**
  (`ANAFPY_SPV_IDENTITY_FILE`, written by `anafpy spv select`) since it is the
  same qualified certificate; overridable via `ANAFPY_SIGN_IDENTITY`. If
  neither exists → `AnafConfigError` pointing at `anafpy spv certs` /
  `anafpy spv select`.
- Windows: **not in M1** (see §8). Keep the protocol seam clean so
  `CngRawSigner` / a DUK-`mscapi` runner slots in without touching callers.

### 4.4 `pdfsign.py` — pyHanko embedding

```python
async def sign_pdf(pdf: bytes, signer: RawSigner, *,
                   field_name: str = "Semnatura1") -> bytes
```

- Build the pyHanko `Signer` subclass over `RawSigner` (Appendix B is the
  working code; keep `md_algorithm="sha256"`).
- Chain: leaf from the signer; intermediate fetched from the leaf's AIA
  (`ca_issuers` URL) via httpx with a short timeout, **best-effort** — if the
  fetch fails, sign with leaf-only CMS and report a warning in the result
  (portal acceptance with leaf-only is unverified; the warning must say so).
  Cache the intermediate next to the session files (`~/.anafpy/`) keyed by URL.
- Dependency: `pyhanko` under a new optional extra `declaratii` in
  `pyproject.toml` (`anafpy[declaratii]`); the MCP extra does NOT pull it in
  automatically — the tools import-guard and raise `AnafConfigError` with
  "install anafpy[declaratii]" if missing (same pattern as the `mcp` extra).
- mypy: pyHanko ships typing but expect a few `# type: ignore[...]` at the
  subclass override; keep them narrow.

### 4.5 What M1 does NOT add to the library

No transport client, no ANAF host, no session — nothing under `_transport/`
changes. `declaratii` is a purely local module (subprocess + crypto + files).
This keeps M2's upload client (which WILL be a transport client behind the F5
APM wall) a clean, separate addition.

## 5. MCP layer — `src/anafpy/mcp/declaratii/`

New service package (`tools.py`, `models.py`), registered in `app.py` following
the existing per-service pattern. Tool titles use service name **`Declarations`**
(`Declarations: validate`, ...). Config additions in `mcp/config.py`:
`ANAFPY_DUK_DIR` (no default), `ANAFPY_DUK_JAVA` (optional),
`ANAFPY_SIGN_IDENTITY` (optional). Without `ANAFPY_DUK_DIR` the server still
starts; declaration tools raise a how-to-enable `AnafConfigError` (same
contract as missing OAuth credentials).

Tools (all lazy over one `DukIntegrator` held on `AppContext`):

| tool | annotations | contract |
|---|---|---|
| `declaratie_validate` | readOnly | input `{xml \| path}` (reuse the `XmlInput` base from `mcp/gate.py`) + `form` (e.g. `"D300"`) + optional `option`; returns `{ok, findings[]}`. This is the model's iteration loop — findings verbatim from DUK, no rephrasing. |
| `declaratie_render` | not readOnly, idempotent, non-destructive | `{xml \| path}`, `form`, `save_pdf_as`, `overwrite=false`; validates first (a failed validation returns findings and writes nothing), renders via `-p`, writes through `write_artifact`. Returns `{ok, findings[], pdf_path}`. |
| `declaratie_sign` | not readOnly, non-idempotent (fires a 2FA approval per call), **requires `confirm=true`** | `{pdf_path, save_as?, overwrite=false}`; signs `pdf_path` (default `save_as` = `<name>-semnat.pdf` next to it); returns `{signed, pdf_path?, chain_complete, guidance?}`. Timeout/dismissed approval → `signed=false` + retry guidance, never an exception. Description must tell the model to warn the user an approval prompt is about to fire on their device. |
| `declaratie_nr_evid` | readOnly | `{tip_decont, luna, an}` → the 23-char number. Errors list valid `tip_decont` values (self-healing, like the SPV `motiv` contract). |
| `declaratie_duk_status` | readOnly | DUK dir, java version, `installed_forms()` vs `feed_versions()` staleness table (feed fetch best-effort — offline returns installed-only with a note). |

Server `instructions` in `app.py` get a short paragraph: compose XML →
`declaratie_validate` loop → `declaratie_render` → user approval →
`declaratie_sign`; filing is manual in M1 (point at the portal page).

### Skill — `skills/declaratie-compose/SKILL.md`

Frontmatter `name: declaratie-compose`, `description`, optional `source`
argument (seed data). Body playbook:

1. Gather the facts from the user/source; state assumptions explicitly.
2. Check `declaratie_duk_status` (stale validator → tell the user, continue
   with a caveat).
3. Author the XML against the form's XSD conventions (attributes on a single
   root; the D300 v12 namespace and the Appendix C template are the worked
   example). Compute `nr_evid` via the tool, never by hand.
4. Loop `declaratie_validate` until `ok` — findings are ANAF's own messages;
   fix and retry (typical convergence: <6 rounds).
5. `declaratie_render` to the user's chosen path; show the summary (period,
   CUI, key amounts) and ask the user to review the PDF.
6. Only on the user's explicit go: `declaratie_sign` with `confirm=true`,
   telling them the approval prompt is coming.
7. Hand back: signed PDF path + "file it at anaf.ro → Depunere declarații"
   (until M2 lands).

## 6. CLI

`anafpy declaratii sign <pdf> [-o out.pdf]` in `cli/main.py` — same signer
stack, prints the identity label and waits for the approval. Exists so
non-MCP users get signing too and so the signer has a debug entry point.
(`validate`/`render` subcommands are cheap to add with the same wrapper —
include them: `anafpy declaratii validate|render <form> <xml>`.)

## 7. Tests (respx/mocked, credential-free — the gate)

- `tests/test_declaratii_duk.py`: command construction (every positional slot),
  err-file parser (ok / single error / multi-finding / cp1250 bytes), timeout
  path, `AnafConfigError` on bad `duk_dir`/missing java, `installed_forms` on a
  fixture tree, `feed_versions` over respx.
- `tests/test_declaratii_nr_evid.py`: both known vectors (§4.2), wrapping
  December→January due date, all four `tip_decont` mappings, rejects `"1"`.
- `tests/test_declaratii_pdfsign.py`: full sign+validate round trip with a
  **software fake `RawSigner`** (test RSA key via `cryptography`, which pyHanko
  already depends on transitively; sign PKCS1v15/SHA-256 in-process). Assert
  pyHanko validation `intact and valid`, coverage ENTIRE_FILE, and that a
  pre-existing `/EmbeddedFiles` tree survives (build the input PDF fixture with
  pyHanko/pdf utils embedding a dummy attachment). Leaf-only chain warning path.
- `tests/test_mcp_declaratii.py`: tool registration, config-missing errors,
  the `confirm=true` gate, artifact collision guard on `save_pdf_as`/`save_as`,
  `declaratie_sign` returning `signed=false` (mock signer timeout).
- Live opt-in (skipped by default): `tests/test_declaratii_live.py` behind
  `ANAFPY_LIVE=1` **and** `ANAFPY_DUK_DIR` set — real `-v`+`-p` on the
  Appendix C XML (no signature). Signing live test additionally behind
  `ANAFPY_LIVE_SIGN=1` (it fires a real 2FA approval — must never ride along
  with a normal live run) and `sys.platform == "darwin"`.
- Keep `pytest`, `ruff`, `mypy --strict`, `mkdocs build --strict` green. The
  ctypes module will need tight `type: ignore` discipline under strict mypy.

## 8. Windows (explicitly deferred within M1, seam prepared)

The `RawSigner` protocol is the seam. Two candidate implementations, decided by
a pending spike (runbook exists at the scratchpad `spike/RUNBOOK-windows.md`
from 2026-07-15, kit zipped at `~/Desktop/spike-mscapi.zip`):

- DUK `-s` with `algorithm=mscapi` cfg (dummy PIN ignored; KSP middleware owns
  the prompt) — needs Temurin ≥ 13 x64 most likely (SunMSCAPI CNG-key support);
  or
- a `CngRawSigner` via ctypes (`NCryptOpenKey`/`NCryptSignHash` on the
  CurrentUser\MY key) feeding the same pyHanko path as macOS — architecturally
  cleaner (one PDF-signing stack everywhere).

Document in the guide that M1 signing is macOS-only and Windows follows.

## 9. Docs (same change, not later)

- **`docs/anaf-reference/declaratii/duk.md`** — new compiled reference with
  provenance frontmatter: DUK CLI contract, err-file format, update feed
  schema, per-form page URL pattern, the `nr_evid` layout (provenance: decoded
  from `D300Validator.jar` v10 bytecode, confirmed against the annex example
  and live validation 2026-07-15), and a "live facts" section for the CTK
  findings (no PKCS#11 on macOS; CTK extension id; approval-per-signature).
  Vendor ANAF's `Instructiuni.txt` under `docs/anaf-reference/_sources/duk/`
  (source: the DUK distribution zip, retrieved 2026-07-15) and cite it.
  Appendix A (Swift reference semantics) lives here too.
- `docs/library/declaratii.md` — library guide (wrapper, signer, pdfsign;
  the macOS-only caveat; DUK install walkthrough incl. update-feed jars).
- `docs/mcp/tools.md` — the five tools; `docs/mcp/skills.md` — the skill;
  `docs/mcp/setup.md` — `ANAFPY_DUK_DIR` setup section (accountant audience:
  download zip, extract, point the env var; screenshot-level detail).
- `mkdocs.yml` nav entries for the new pages.
- `CLAUDE.md`: layout tree (+`declaratii/` in both `src/anafpy/` and
  `src/anafpy/mcp/`), commands (extras install), a short conventions paragraph
  (PIN-never-in-context; DUK validation authority).
- `DESIGN.md`: new §"Declarations (authoring + signing)" recording the
  decisions (§3 invariants, the CTK finding, pass-through stance for M2), and
  **fix the stale §1 out-of-scope list (line ~72) that still names SPV** —
  reword to reflect SPV shipped 2026-07-12 and declarations-authoring landing
  now, with filing (M2) still out of scope.
- `README.md`: one feature bullet + extras mention.

## 10. M2 sketch (do not implement now)

Portal upload of the signed PDF + recipisa tracking. Recon first (M0 of M2):
capture the real upload at `decl.anaf.mfinante.gov.ro` / e-guvernare.ro with
the certificate — expect the same F5 APM cookie wall as SPV (reuse
`CurlBootstrapper` machinery; its probe URL is the one hardcoded bit,
`spv/bootstrap.py:164`). Then `upload_declaration(pdf) -> registration number`,
`declaratie_prepare`/`declaratie_submit` over the `mcp/gate.py` two-step gate
(token bound to the signed PDF bytes), recipisa via the existing SPV reads
(`tip=RECIPISA`, match on registration number in `detalii`; `Duplicat
Recipisa` cerere as fallback). **No TEST environment exists for filing** — M2's
live verification files a real (nil/rectifiable) declaration. Also confirms
whether the portal accepts the pyHanko CMS (expected yes — same signature
class as DUK/Adobe with the same qualified cert; the §4.4 chain warning
matters here).

## 11. Suggested implementation order

1. `nr_evid.py` + tests (pure, instant win).
2. `duk.py` + tests (mock subprocess), then live-check against a local DUK.
3. `signing.py` ctypes port + `pdfsign.py` + fake-signer round-trip tests;
   live sign smoke on this Mac (`ANAFPY_LIVE_SIGN=1`).
4. MCP package + config + tests; skill.
5. CLI subcommands.
6. Docs sweep (§9), gates green, PR.

---

## Appendix A — proven raw-signer semantics (Swift, reference for the ctypes port)

Compiled and validated 2026-07-15 (`swiftc -O`; `list`/`cert` ran clean;
`sign` produced a 512-byte RSA-4096 PKCS#1v15-SHA256 signature that
`openssl dgst -verify` accepted; the vToken phone approval fired per call).

```swift
// keychain-sign: raw RSA PKCS#1 v1.5 signing via a macOS Keychain/CTK identity.
// Usage:
//   keychain-sign list
//   keychain-sign cert <label>            -> DER certificate to stdout
//   keychain-sign sign <label> <sha256|sha1> < data-on-stdin -> raw signature to stdout
import Foundation
import Security

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

func findIdentity(label: String) -> SecIdentity {
    let query: [String: Any] = [
        kSecClass as String: kSecClassIdentity,
        kSecMatchLimit as String: kSecMatchLimitAll,
        kSecReturnRef as String: true,
        kSecReturnAttributes as String: true,
    ]
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let items = result as? [[String: Any]] else {
        fail("identity query failed: \(status)")
    }
    for item in items {
        let lbl = item[kSecAttrLabel as String] as? String ?? ""
        if lbl == label {
            return item[kSecValueRef as String] as! SecIdentity
        }
    }
    fail("no identity labeled '\(label)'")
}

let args = CommandLine.arguments
guard args.count >= 2 else { fail("usage: keychain-sign list|cert|sign ...") }

switch args[1] {
case "list":
    let query: [String: Any] = [
        kSecClass as String: kSecClassIdentity,
        kSecMatchLimit as String: kSecMatchLimitAll,
        kSecReturnAttributes as String: true,
    ]
    var result: CFTypeRef?
    guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
          let items = result as? [[String: Any]] else { fail("query failed") }
    for item in items {
        let lbl = item[kSecAttrLabel as String] as? String ?? "?"
        let tkid = item[kSecAttrTokenID as String] as? String ?? "file-keychain"
        print("\(lbl)\t\(tkid)")
    }
case "cert":
    guard args.count == 3 else { fail("usage: keychain-sign cert <label>") }
    let identity = findIdentity(label: args[2])
    var certRef: SecCertificate?
    guard SecIdentityCopyCertificate(identity, &certRef) == errSecSuccess, let cert = certRef
    else { fail("cannot copy certificate") }
    FileHandle.standardOutput.write(SecCertificateCopyData(cert) as Data)
case "sign":
    guard args.count == 4 else { fail("usage: keychain-sign sign <label> <sha256|sha1>") }
    let identity = findIdentity(label: args[2])
    var keyRef: SecKey?
    guard SecIdentityCopyPrivateKey(identity, &keyRef) == errSecSuccess, let key = keyRef
    else { fail("cannot copy private key") }
    let algorithm: SecKeyAlgorithm = args[3] == "sha1"
        ? .rsaSignatureMessagePKCS1v15SHA1 : .rsaSignatureMessagePKCS1v15SHA256
    let data = FileHandle.standardInput.readDataToEndOfFile()
    var error: Unmanaged<CFError>?
    guard let sig = SecKeyCreateSignature(key, algorithm, data as CFData, &error) else {
        fail("sign failed: \(error!.takeRetainedValue())")
    }
    FileHandle.standardOutput.write(sig as Data)
default:
    fail("unknown command \(args[1])")
}
```

## Appendix B — proven pyHanko glue (0.35.2)

Signed the DUK-rendered D300 on 2026-07-15; validation `intact=True,
valid=True`, ENTIRE_FILE, embedded XML preserved. (Here the raw op shells to
the Appendix A helper; the real implementation calls the ctypes signer.)

```python
import asyncio
from pathlib import Path

from asn1crypto import x509
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore


class KeychainSigner(signers.Signer):
    def __init__(self, leaf_der: bytes, ca_der: bytes) -> None:
        leaf = x509.Certificate.load(leaf_der)
        registry = SimpleCertificateStore()
        registry.register(x509.Certificate.load(ca_der))
        super().__init__(signing_cert=leaf, cert_registry=registry)

    async def async_sign_raw(
        self, data: bytes, digest_algorithm: str, dry_run: bool = False
    ) -> bytes:
        if dry_run:
            return bytes(512)  # real impl: key size from the cert
        assert digest_algorithm.lower() == "sha256"
        return await raw_sign(data)  # -> SecKeyCreateSignature(...PKCS1v15SHA256)


async def sign(src: Path, dst: Path, signer: signers.Signer) -> None:
    with src.open("rb") as inf:
        writer = IncrementalPdfFileWriter(inf)
        meta = signers.PdfSignatureMetadata(
            field_name="Semnatura1", md_algorithm="sha256"
        )
        with dst.open("wb") as outf:
            await signers.async_sign_pdf(writer, meta, signer=signer, output=outf)
```

Validation used in the spike (for the round-trip test):

```python
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

vc = ValidationContext(extra_trust_roots=[ca_cert], allow_fetching=False)
sig = PdfFileReader(fh).embedded_signatures[0]
status = validate_pdf_signature(sig, vc)
assert status.intact and status.valid
```

## Appendix C — validated nil D300 (06/2026, XSD v12, validator J12.0.1)

`Validare fara erori` on 2026-07-15. Identification values are placeholders
(CUI `12345674` is check-digit-valid but fictitious); the skill fills real ones.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<declaratie300 xmlns="mfp:anaf:dgti:d300:declaratie:v12"
  luna="6" an="2026" depusReprezentant="0" bifa_interne="1" temei="0"
  nume_declar="Popescu" prenume_declar="Ion" functie_declar="Administrator"
  cui="12345674" den="TEST SPIKE SRL" adresa="Str. Exemplu nr. 1, Bucuresti"
  banca="-" cont="-" caen="6201" tip_decont="L" pro_rata="100.0"
  bifa_cereale="N" bifa_mob="N" bifa_disp="N" bifa_cons="N"
  solicit_ramb="N" nr_evid="10301010626250726000042" totalPlata_A="0"/>
```

Notes for the implementer: `Str_listaDaNuSType` admits `1|D|N`; `tip_decont`
admits `1|L|T|S|A`; the Romanian CUI check digit uses key `753217532`
(sum of digit-products, ×10 mod 11, 10→0) — no helper exists in the codebase
yet (the UIT check in `etransport/models.py` is a different algorithm), and M1
does not need one: the CUI comes from the user and DUK validates it.
