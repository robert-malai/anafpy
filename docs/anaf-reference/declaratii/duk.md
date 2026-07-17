---
title: DUKIntegrator — headless declaration validation, PDF rendering, and signing
service: declaratii
language: en
sources:
  - url: https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip
    title: "DUKIntegrator distribution (dist/ + bundled 32-bit JRE 6; Instructiuni.txt)"
    retrieved: 2026-07-15
  - url: http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml
    title: "DUKIntegrator update feed (current core + per-form jar versions)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/d300_v12_11022026.xml
    title: "D300 v12 XSD (the .xml extension notwithstanding, it is the schema)"
    retrieved: 2026-07-15
  - url: https://github.com/nokeect/duk-integrator-macos
    title: "Community macOS DUKIntegrator setup (AXIOM ADVISORY): offLine=Y silent-exit fix, Java-8 pin, SafeNet PKCS#11 signing config"
    retrieved: 2026-07-16
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/duk_SAFT_20230216.zip
    title: "Dedicated SAF-T DUKIntegrator distribution — the only source of the D406T jars (D406TValidator.jar / D406TPdf.jar)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/RO_SAFT_SchemaDefCod_16.02.2026.xlsx
    title: "RO SAF-T schema definition & codes workbook (current element tables, ID-type prefixes, nomenclatures)"
    retrieved: 2026-07-17
compiled: 2026-07-15
compiled_by: claude-opus-4-8
last_verified: 2026-07-17
status: draft
---

# DUKIntegrator (declaration validation, rendering, signing)

DUKIntegrator is ANAF's Java desktop tool for tax declarations. Its per-form
**validator jars are ANAF's own validation code** — anafpy runs them and never
re-implements a rule. anafpy drives it headlessly ("mode B") for two operations,
`-v` (validate) and `-p` (render the official PDF); the qualified signature is
added separately (see §5) because DUK's signing path cannot reach a macOS
CryptoTokenKit key.

Everything below was live-proven on **2026-07-15** (macOS 26 / Oracle Java 26 /
certSIGN Paperless vToken).

## 1. Distribution and update feed

- **Distribution**:
  `https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip`.
  Extract `dist/`; **ignore the bundled 32-bit JRE 6** — a modern JVM (proven on
  Oracle Java 26, macOS arm64) runs `-v`/`-p` fine.
- **Update feed**: `http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml`
  lists the current core jars (`DUKIntegrator.jar`, `DecValidation.jar`,
  `DecPdf.jar`, `Validator.jar`) and per-form jars (e.g. D300 at
  `D300Validator.jar` + `D300Pdf.jar`, version `J12.0.1`/`P9.0.0`). Per-form jars
  go into `dist/lib/`. **The GUI mode auto-updates; the CLI mode does not** —
  staleness must be surfaced (anafpy's `declaratie_duk_status` /
  `DukIntegrator.feed_versions` compare installed against the feed).

  **Feed shape** (live-fetched 2026-07-17; no XML namespace): one `<integrator>`
  element for the core (its `<versiune>` is the DUKIntegrator core version, with
  `iJars`/`sJars`/`zJars` lists of bare `jarURL`s), then **one container element
  per form, named after the form**:

  ```xml
  <versiuni>
    <integrator>
      <versiune>1.4.18.3.3</versiune>
      ...
    </integrator>
    <D300>
      <versiuneJ>J12.0.1</versiuneJ>
      <versiuneP>P9.0.0</versiuneP>
      <JURL>http://static.anaf.ro/static/10/Anaf/update5/D300/D300Validator.jar</JURL>
      <PURL>http://static.anaf.ro/static/10/Anaf/update5/D300/D300Pdf.jar</PURL>
      <DURL>http://static.anaf.ro/static/10/Anaf/update5/D300/D300IstoriaVersiunilor.txt</DURL>
    </D300>
    ...
  </versiuni>
  ```

  `versiuneJ` is the validator jar's version and `versiuneP` the PDF jar's; the
  installed `<form>IstoriaVersiunilor.txt` (what `DURL` points at) leads with the
  same `J…` string, which is what makes installed-vs-feed comparison possible.

### The SAF-T module (D406/D406T) — jar sourcing and compatibility

Live-proven 2026-07-17 (macOS, Oracle Java 26); this is the module behind the
D406T no-effect test filing (portal-upload reference §5).

- **The 2018/2020-era core jars cannot run the D406 validators**: they fail
  with `NoClassDefFoundError: dec/DECTagStruct` (written to `validator.log`,
  stdout only says `cod eroare=-5` with an **empty err file**). Fix: update
  `DUKIntegrator.jar` (feed path `zz9/`) **and** `lib/DecValidation.jar`
  (feed path `ss8/`) to the feed's current versions.
- A dist without its `config/` folder makes the updated `DUKIntegrator.jar`
  **exit silently** (no output, exit 0) — carry `config/` over when assembling
  a fresh dist.
- **`D406` is in the update feed** (`D406_35/`, `J2.2.18`); **`D406T` is
  not** — its jars (`D406TValidator.jar`, `D406TPdf.jar`) ship only inside the
  dedicated `duk_SAFT` distribution
  (`duk_SAFT_20230216.zip` is the newest observed; jars dated 2023,
  `J2.0.6`), dropped into `lib/` like any per-form pair. Consequence: the
  staleness comparison (`feed_versions`) will never show D406T.
- **Form names and namespaces**: `-v D406` expects
  `mfp:anaf:dgti:d406:declaratie:v1`, `-v D406T` expects
  `mfp:anaf:dgti:d406t:declaratie:v1` (the T validator errors with the exact
  expected namespace). The same document content validates under both — only
  the namespace differs; the 2023 T-validator additionally requires an
  (empty) `AnalysisTypeTable` the current D406 no longer asks for.
- **SAF-T validators emit `F:`** (structure/fatal) finding lines besides
  `E:`/`W:`; parameters are **period-versioned** inside the jar (version table
  2019-01 → 2023-01 → 2024-01 → 2025-07), so structure rules shift with the
  reporting period, and several sections are vestigial in the current version:
  `MovementTypeTable` and `MovementOfGoods` must be **present but empty**
  (their children answer `maxOccurs=0`), `Products`/`Owners`/`Assets` may be
  empty, `SalesInvoices`/`PurchaseInvoices`/`Payments` may be omitted (a
  present `SalesInvoices` demands a full `Invoice`).
- **Structure gotchas** (from converging the minimal file, committed at
  `tests/fixtures/declaratii/d406t-minimal.xml`): partner identifiers
  (`CustomerID`/`SupplierID`/partner `RegistrationNumber`) need the 2-char
  **ID-type prefix** from the SAF-T nomenclature (`00` + CUI for Romanian
  companies, check-digit-verified; `080000000000000` is the generic
  no-ID person code); `Transaction` **and** each `TransactionLine` require
  both `CustomerID` and `SupplierID`; every `AmountStructure` requires
  `Amount` + `CurrencyCode` + `CurrencyAmount`; each line requires
  `TaxInformation`; `BaseRate` is a fraction (`1.00`, not `100.00`). A
  misplaced-but-known element is reported as *"ar fi trebuit sa apara de
  minimum 1 ori"* — check ordering before existence. The schema-definition
  workbook (`RO_SAFT_SchemaDefCod_*.xlsx`) is the current element table, but
  its `Line` naming is the newer schema's — the v1 wire element is
  `TransactionLine`.

### Silent-exit-on-update escape hatch (`offLine=Y`)

anafpy's `-v`/`-p` runs did not hit this, but it is worth knowing: DUK's startup
update check uses **hardcoded Windows paths**, and on a non-Windows host it can
make the app **silently exit** (exit `0`, no err file, no PDF). The fix, from the
community macOS setup ([nokeect/duk-integrator-macos]), is to disable the check by
setting `offLine=Y` in a `config/config.properties` and pointing DUK at it with the
CLI's `-c <configPath>` flag (see §2). If a CLI run ever exits cleanly but produces
nothing, this is the first thing to try.

[nokeect/duk-integrator-macos]: https://github.com/nokeect/duk-integrator-macos

## 2. CLI contract

Positional arguments; `$` means "use the default"; missing arguments produce the
single stdout message `linie comanda incompleta`.

```
java -jar DUKIntegrator.jar [-c configPath] -v <tip> <xml> [errFile] [valOption]
java -jar DUKIntegrator.jar [-c configPath] -p <tip> <xml> [errFile] [valOption] [zipFile] [pdfFile]
java -jar DUKIntegrator.jar [-c configPath] -s <tip> <xml> [errFile] [valOption] [zipFile] [pdfFile] <pin> <smartCard> [certSelector]
```

- `tip` — the form name exactly as the validator jar prefix (`D300`, `D112`, …).
- `errFile` — a clean run contains literally `ok`; otherwise, lines prefixed
  `E:` (errors) / `W:` (warnings) / `A:` (atentionare — informational notices)
  — the SAF-T validators (D406/D406T) also emit `F:` (structure/fatal) — each
  followed by indented detail lines (`eroare regula: R25: …`,
  `eroare atribut: …`). **Judgment**: `E:`/`F:` findings are blocking; a run
  whose only findings are `W:`/`A:` is a **pass** — some forms never write a
  bare `ok` (D700 always emits an `A:` "prelucrat la organul fiscal competent"
  notice on a valid document), so warnings-only must not be read as failure.
  An empty or unrecognized err file is a failure (a broken/mis-versioned dist
  leaves one behind) — never infer success from output you cannot parse. A
  clean-run success is **also** printed to stdout as
  `Validare fara erori fisier: <path>`.
- **The exit code is `0` either way** — judge success by the err-file content,
  never by the exit code, and never parse stdout except as debug info.
- `valOption` defaults to `0`; it is form-specific.
- `zipFile` — `0` when the form has no attachment (true for D300).
- `-p` writes the official multi-page PDF with the XML as an **embedded file**
  (`/EmbeddedFiles` present). Proven: a 4-page, ~25 KB D300.
- `-s` is **not** used on macOS (see §5); on Windows it is the candidate signer
  with `algorithm=mscapi` (deferred).

anafpy always fills every positional explicitly (it passes temp paths, so no `$`
is needed): `-v <form> <xml> <err> <option>` and
`-p <form> <xml> <err> <option> 0 <pdf>`.

## 3. D300 wire format and `nr_evid`

- **XSD**:
  `https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/d300_v12_11022026.xml`
  (despite the extension it is the XSD). Root `declaratie300`, namespace
  `mfp:anaf:dgti:d300:declaratie:v12`; **everything is an attribute** on the one
  element, no children. Per-form pages under
  `https://static.anaf.ro/static/10/Anaf/Declaratii_R/<nnn>.html` publish the XSD
  and the validation annex PDF.
- **The XSD is the authoring template.** DUKIntegrator does **not** generate
  templates or skeleton XML (verified against the jar, 2026-07-15; its surface is
  validate / render / sign only). Author the XML from the XSD.

### `nr_evid` layout

`nr_evid` ("numărul de evidență a plății") is a required 23-character field,
decoded from the validator bytecode (`D300Validator.jar` v10 = XSD v12) and
confirmed against the annex example `10301010111250211000020` and a live `-v`
acceptance (2026-07-15):

| positions | content |
|---|---|
| `[0:2]`   | fixed `10` |
| `[2:5]`   | `cod_imp`, correlated with `tip_decont`: `301`=L (monthly), `302`=T (quarterly), `303`=S, `304`=A |
| `[5:7]`   | fixed `01` |
| `[7:11]`  | reporting period `MMYY` (zero-padded `luna` + last 2 of `an`) |
| `[11:17]` | payment due date `25` + `MM` (`luna`+1, wrapping into the next year) + `YY` |
| `[17:21]` | fixed `0000` |
| `[21:23]` | check: the two-digit **sum of the first 21 digits** |

Example: 06/2026 monthly → `10` `301` `01` `0626` `250726` `0000` `42`. anafpy
computes this as a pure function (`declaratii.payment_evidence_number`); the model
never computes the check digit. Sums here are always < 100 (no modulo).

## 4. Iterating a document

Iterating a nil D300 with `-v` from scratch took five rounds in the spike; the
validator messages are precise enough (rule ids, attribute names) to converge a
model without any other documentation. A validated nil D300 (06/2026):

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

Notes: `Str_listaDaNuSType` admits `1|D|N`; `tip_decont` admits `1|L|T|S|A`; the
Romanian CUI check digit uses key `753217532` (sum of digit-products, ×10 mod 11,
10→0). The CUI comes from the user and DUK validates it, so anafpy needs no CUI
helper.

## 5. Signing on macOS — the CryptoTokenKit finding

- certSIGN Paperless vToken on macOS is a **CryptoTokenKit extension**
  (`ro.certsign.vtoken.ctke`; visible via `security list-smartcards`). There is
  **no PKCS#11 dylib**, so DUK's `sunpkcs11` path can never work on macOS, and
  `mscapi` is Windows-only. The key is reachable **only** through
  Security.framework, and CPython's `ssl` cannot present a non-exportable
  platform-store key.
- **Working pipeline** (proven end-to-end; signature validated `intact=True,
  valid=True`, coverage `ENTIRE_FILE`, `/EmbeddedFiles` preserved): DUK `-p`
  renders → **pyHanko** embeds a standard `adbe.pkcs7.detached` CMS as an
  incremental update, where the raw RSA PKCS#1 v1.5 SHA-256 operation is
  `SecKeyCreateSignature` on the Keychain identity. **Each raw signature fires the
  vToken phone approval** — that is the human gate; no PIN or secret passes
  through anafpy's code.
- Certificate chain: leaf via `SecIdentityCopyCertificate`; the intermediate via
  the leaf's AIA URL (live:
  `http://crl.certsign.ro/certsign-qualifiedca2023rsa.crt`).
- **The portal accepts this signature** (confirmed 2026-07-17): a D406T signed
  through this exact pipeline was filed on the WAS6DUS upload portal and
  answered with the success page + upload index — see the
  [portal-upload reference](portal-upload.md) §4/§5. (Acceptance of a
  **leaf-only** CMS — the AIA-fetch-failed fallback — remains unverified.)
- Windows follows in a later milestone (a `CngRawSigner` via CNG, or DUK `-s`
  with `mscapi`), over the same raw-signer seam.
- **Why not DUK's own `-s` on macOS?** The community setup
  ([nokeect/duk-integrator-macos]) does sign through DUK, by wiring `safeNet.cfg`'s
  `library=` at a **SafeNet** PKCS#11 dylib (`/usr/local/lib/libeTPkcs11.dylib`).
  anafpy deliberately does not: that path is **SafeNet-only** (it needs a vendor
  `.dylib` — the certSIGN vToken above ships none), **pins Java 8** (DUK's signing
  leans on removed `sun.security.pkcs11` internals, so Java 9+ breaks it — the
  reason that project pins Zulu 8), and would route the **PIN through DUK's
  process**. Our Security.framework path avoids all three and works for a
  CryptoTokenKit token that has no PKCS#11 module at all.

anafpy ports the raw-signing semantics to **ctypes against Security.framework**
(no build step, no new dependency) in `anafpy.declaratii.signing`. The proven
Swift reference program is preserved below as the semantic spec.

### Appendix A — proven raw-signer semantics (Swift reference)

Compiled and validated 2026-07-15 (`swiftc -O`; `sign` produced a 512-byte
RSA-4096 PKCS#1 v1.5 SHA-256 signature that `openssl dgst -verify` accepted; the
vToken phone approval fired per call).

```swift
// keychain-sign: raw RSA PKCS#1 v1.5 signing via a macOS Keychain/CTK identity.
//   keychain-sign list
//   keychain-sign cert <label>            -> DER certificate to stdout
//   keychain-sign sign <label> <sha256|sha1> < data-on-stdin -> raw signature
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
case "cert":
    let identity = findIdentity(label: args[2])
    var certRef: SecCertificate?
    guard SecIdentityCopyCertificate(identity, &certRef) == errSecSuccess,
          let cert = certRef else { fail("cannot copy certificate") }
    FileHandle.standardOutput.write(SecCertificateCopyData(cert) as Data)
case "sign":
    let identity = findIdentity(label: args[2])
    var keyRef: SecKey?
    guard SecIdentityCopyPrivateKey(identity, &keyRef) == errSecSuccess,
          let key = keyRef else { fail("cannot copy private key") }
    let algorithm: SecKeyAlgorithm = args[3] == "sha1"
        ? .rsaSignatureMessagePKCS1v15SHA1 : .rsaSignatureMessagePKCS1v15SHA256
    let data = FileHandle.standardInput.readDataToEndOfFile()
    var error: Unmanaged<CFError>?
    guard let sig = SecKeyCreateSignature(key, algorithm, data as CFData, &error)
    else { fail("sign failed: \(error!.takeRetainedValue())") }
    FileHandle.standardOutput.write(sig as Data)
default:
    fail("unknown command \(args[1])")
}
```

### pyHanko API notes (0.35.x)

- `SimpleCertificateStore` lives in `pyhanko_certvalidator.registry` (not
  `pyhanko.sign.general`).
- A custom signer subclasses `pyhanko.sign.signers.Signer` and implements
  `async_sign_raw(data, digest_algorithm, dry_run)`; on `dry_run=True` return
  zero-bytes of the signature size (RSA key size / 8 — read it from the cert's
  public key, do not hardcode 512).
- `validate_pdf_signature` calls `asyncio.run` internally; use
  `async_validate_pdf_signature` from inside an event loop.
