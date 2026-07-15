---
title: SPV Web Services — inbox messages, document download, report requests (webserviced.anaf.ro)
service: spv
language: en
sources:
  - url: https://github.com/MfpAnaf/ClientSPV/blob/master/README.md
    title: "ClientSPV — Client Java apelare servicii web Spatiul Privat Virtual (README)"
    source_revision: "commit 949ea92c2b4abe99d531a5a094af288e6f662c26 (2019-05-07, repo head as of retrieval)"
    retrieved: 2026-07-12
    local_copy: ../_sources/clientspv/README.md
  - url: https://github.com/MfpAnaf/ClientSPV/blob/master/src/main/java/sqw/apelspv/ApelSPV.java
    title: "ClientSPV — ApelSPV.java (reference client: PKCS#11 mTLS setup + listaMesaje call)"
    source_revision: "commit 949ea92c2b4abe99d531a5a094af288e6f662c26"
    retrieved: 2026-07-12
    local_copy: ../_sources/clientspv/src/ApelSPV.java
compiled: 2026-07-12
compiled_by: claude-fable-5
last_verified: 2026-07-15
status: draft
---

# SPV Web Services (Spațiul Privat Virtual)

Read-side web services over a taxpayer's **SPV** mailbox on
`https://webserviced.anaf.ro/SPVWS2/rest/` — list inbox messages
(`listaMesaje`), download message documents as PDF (`descarcare`), and request
official reports/documents that are later delivered into the same inbox
(`cerere`). The only official documentation is ANAF's example Java client
repository **MfpAnaf/ClientSPV** (vendored verbatim under
[`_sources/clientspv/`](../_sources/clientspv/README.md)); there is no PDF,
no swagger presentation, and no OpenAPI spec. The upstream repo was last
touched 2019-05-07 — treat every shape here as "documented 2018/2019, verify
live" until confirmed against the current service.

This family is separate from both the OAuth-protected e-Factura / e-Transport
APIs on `api.anaf.ro` (see [efactura/api.md](../efactura/api.md),
[etransport/api.md](../etransport/api.md)) and the public no-auth lookups on
`webservicesp.anaf.ro` (see [public/api.md](../public/api.md)): **different
host, different authentication** (TLS client certificate, §1).

## 1. Authentication — mutual TLS with a qualified certificate

*Source: README lines 2, 10, 15–17; ApelSPV.java (whole file).*

Every endpoint requires a TLS handshake authenticated with the taxpayer's
**qualified digital certificate** ("certificatul digital calificat cu care se
face autentificarea"). There are no tokens, API keys, or auth headers — the
identity is established entirely at the TLS layer, and every JSON response
echoes it back:

- `cnp` — the certificate holder's personal identifier;
- `serial` — the certificate's serial number ("SN-ul certificatului");
- `cui` — comma-separated list of CUIs/CNPs the certificate holder has SPV
  rights for. This doubles as an **authorization inventory**: any `cif` you
  query outside this list yields a rights error (§5).

The reference client (`ApelSPV.java`) reads the private key from a **PKCS#11
USB token** (SafeNet/Aladdin config file borrowed from DUKIntegrator), builds
a client-cert `SSLContext`, and calls the REST URLs over
`HttpsURLConnection`. Two implementation details worth noting:

- it installs a `CookieManager` before connecting — the service (or the
  fronting infrastructure) may set session cookies; a client that preserves
  cookies across calls can keep one authenticated session rather than
  re-handshaking per request;
- the 2019-era protocol pins (`https.protocols=TLSv1`, `SSLv3` context) are
  historical artifacts, not requirements — do not replicate.

The README's roadmap (line 260) mentions possible future username/password
authentication for natural persons; as documented, certificate mTLS is the
only mechanism.

### 1.1 Live-confirmed auth choreography (production, 2026-07-12)

The mTLS is fronted by an **F5 BIG-IP APM cookie session**, observed live
with a certSIGN qualified certificate (macOS system curl, SecureTransport
backend, Keychain identity):

1. `GET` on any API URL with no session → `302` to `/my.policy` plus fresh
   `MRHSession` / `LastMRH_Session` / `F5_ST` cookies (`Server: BigIP`).
2. `GET /my.policy` (cookies attached) → the server initiates a
   **mid-connection TLS renegotiation** (`HelloRequest` → `CertificateRequest`)
   — this is the only point where the client certificate is used; the
   private-key operation (and any token PIN / cloud-2FA authorization)
   happens here. Without a certificate the session is terminated via
   `302 /vdesk/hangup.php3`.
3. With a valid certificate → `302 /my.policy_nonce?nonce=...` → the
   `MRHSession` cookie is rewritten to an authenticated value → `302` back
   to the originally requested URL → `200` with JSON.
4. **Subsequent requests need only the cookie jar** — confirmed with a plain
   no-certificate client. Mid-session the APM occasionally answers with a
   `302 /my.policy_nonce?...` revalidation hop that just needs following
   (cookies intact); only a redirect to bare `/my.policy` means the
   certificate is required again.

TLS session resumption (session IDs) was honored across connections, so the
signing operation ran once even though the redirect chain used
`Connection: close` per hop. Practical upshot: one certificate/PIN operation
establishes an APM session; polling loops ride the cookies.

Bootstrap behavior with a **cloud-HSM key** (certSIGN Paperless webSIGN,
vToken 2FA), observed over repeated fresh bootstraps:

- the 2FA authorization is requested on **every** fresh session bootstrap —
  the middleware caches an authorization only briefly (minutes), so there is
  no silent re-login across processes or runs;
- the bootstrap is **intermittently flaky**: with the prompt answered
  promptly, most handshakes complete in seconds but some hang indefinitely
  (no error surfaced by either side) — a client must bound the bootstrap
  with a timeout and offer a retry (which re-fires the 2FA), not assume
  determinism;
- the resulting APM cookie session is a plain bearer credential: it worked
  from a **different process** with no certificate configured, minutes
  later. Treat the cookie jar as a secret with the same care as a token
  store.

The same live run confirmed the §2 no-results shape verbatim
(`{"titlu":"Lista Mesaje","eroare":"Nu exista mesaje in ultimele 5 zile"}`)
and the full with-results shape including `cnp`/`cui`/`serial`; observed
`tip` values beyond the README's `RECIPISA`: `PLATA`, `RASPUNS SOLICITARE`,
`ADEVERINTA VENIT`, and `DECLARATIE ` — the last with a **trailing space on
the wire**, confirming `tip` must be modeled as an open string (and compared
trimmed). Apple's NSURLSession/Network framework **hangs on step 2's
renegotiation** (challenge answered, handshake never completes) — a
SecureTransport-backed client (system curl `--cert <keychain name>`) is the
macOS path that works.

**Windows on ARM caveat** (observed 2026-07-13, Windows 11 ARM64 in a
Parallels VM, same certSIGN Paperless vToken identity): certSIGN's
middleware — the `certSIGN Paperless vToken Key Storage Provider` KSP — is
**x64-only**, and KSP DLLs load in-process, so every ARM64-native consumer
fails *locally, before any network I/O*: System32's ARM64 `curl.exe`
(Schannel) errors `AcquireCredentialsHandle … SEC_E_UNKNOWN_CREDENTIALS`,
`certutil -csplist` reports the provider as `NTE_PROVIDER_DLL_FAIL`, and
ARM64 Chrome *lists* the certificate in its picker (the store entry and its
key-container reference look healthy — `HasPrivateKey` is true) but
completes the handshake with no certificate, so ANAF answers its
"Certificatul nu a fost prezentat" page. certSIGN's own guidance for ARM
computers is to use **Opera** — an x64 build running under Windows' x64
emulation, which can load the x64 KSP; confirmed working live. Practical
upshot for a Windows bootstrapper: on ARM64 Windows the certificate step
must run in an **x64 process** until certSIGN ships ARM64 middleware; the
store-and-thumbprint discovery itself works fine from ARM64 processes.

Validated live the same day with an **x64 Schannel curl under emulation**
(`curl --cert "CurrentUser\MY\<thumbprint>"` + `-L` + a cookie jar): the
full APM bootstrap returned `200` + JSON (~27 s wall including the vToken
phone approval, 0.5 s TLS), and a follow-up request with the **cookie jar
only, no certificate** answered in 0.13 s — the §1.1 cookie-session model
holds identically on Windows. Sourcing caveat: stock ARM64 Windows has no
x64 Schannel curl — System32's build is ARM64, and the curl.se win64
packages are **LibreSSL-only** (the CertStore `--cert` syntax is a Schannel
feature; on a single-backend build it is read as a file path and fails
instantly with code `000`, and `CURL_SSL_BACKEND` is silently ignored).
Git for Windows' x64 `mingw64\bin\curl.exe` is multi-backend — select
Schannel with `CURL_SSL_BACKEND=schannel`. Two wire quirks from the same
run: (1) the F5 closes without a TLS close_notify, so Schannel curl exits
**56** (`server closed abruptly`) *after* delivering the complete `200`
body — judge success by status + body, never by curl's exit code; (2) with
no certificate and no session, the APM's "Certificatul nu a fost prezentat"
logout page arrives as HTTP **200** — the login wall must be detected by
content/URL, never by status code.

**curl-version caveat** (observed 2026-07-15, Windows 11 x64): Schannel curl
versions **8.13.0–8.15.0** carry a regression
([curl#18029](https://github.com/curl/curl/issues/18029), commit `a1850ad`)
that breaks **TLS 1.2 renegotiation with a certificate-store client cert** —
exactly step 2's mid-connection renegotiation. The handshake fails mid-read
with `curl: (56) schannel: failed to read data from server:
SEC_E_CONTEXT_EXPIRED (0x80090317)` *before* any body arrives (distinct from
the benign exit-56 close_notify above, which lands *after* the full `200`).
This bites Windows' built-in `System32\curl.exe` when it is one of those
versions; a file-backed cert would sidestep it, but SPV's non-exportable
store key rules that out. Fix: use a Schannel curl **outside** that range —
current Git for Windows ships one (curl ≥ 8.16) — via `ANAFPY_SPV_CURL`.
Confirmed live that pointing the override at Git for Windows'
`mingw64\bin\curl.exe` (curl 8.21.0) completed the bootstrap where the
System32 8.13.0 curl failed.

## 2. `listaMesaje` — list available messages

*Source: README lines 7–30, 254–258.*

```
GET https://webserviced.anaf.ro/SPVWS2/rest/listaMesaje?zile=50[&cif=8000000000]
```

| Param | Required | Meaning |
|---|---|---|
| `zile` | yes | Look-back window in days — messages that *arrived* in the last N days. |
| `cif` | no | Restrict to one CUI/CNP (added 06.11.2018); default is all the certificate has rights for. |

Success response (README's example, values anonymized by ANAF):

```json
{"titlu":"Lista Mesaje disponibile din ultimele 50 zile",
 "mesaje":[{"id":"100000000",
            "detalii":"recipisa pentru CIF 8000000000, tip D112, numar_inregistrare INTERNT-130000000-2017/20-12-2017, perioada raportare 11.2017",
            "cif":"8000000000",
            "data_creare":"20.12.2017 12:00:00",
            "id_solicitare":null,
            "tip":"RECIPISA"}],
 "cnp":"1111111111118",
 "cui":"8000000000,8000000001,8000000002",
 "serial":"xxxxxxxxxxxxxxxxxxx"}
```

Per message: `id` is the **download index** (feed to `descarcare`), `detalii`
a free-text description, `cif` the CUI/CNP the message belongs to,
`data_creare` the arrival timestamp — format `dd.MM.yyyy HH:mm:ss` since the
06.11.2018 fix (before that, date only) — `id_solicitare` the request id the
message answers (non-null when the message is a report delivered for a
`cerere`, §4), and `tip` the message type. The README shows only
`tip: "RECIPISA"`; the type set is open (report deliveries, notifications,
"Anliza de risc" documents are mentioned in the changelog) — **model `tip` as
an open string**.

The "no results" case rides the **error key**, same overloading pattern as
the e-Factura message list:

```json
{"titlu":"Lista Mesaje","eroare":"Nu exista mesaje in ultimele 5 zile"}
```

`eroare` is "the error that occurred *or the reason no messages are
returned*" (README line 30) — a client must classify no-results notes apart
from genuine errors rather than raising on every `eroare`. The no-results
shape carries **only** `titlu` + `eroare` (live-confirmed 2026-07-12): the
identity fields `cnp`/`cui`/`serial` are omitted, so the certificate's
authorization inventory can only be read off a response that contains
messages.

## 3. `descarcare` — download a message document

*Source: README lines 32–36.*

```
GET https://webserviced.anaf.ro/SPVWS2/rest/descarcare?id=100000000
```

`id` is the download index from `listaMesaje`. Returns **PDF bytes** (the SPV
document) on success, or a JSON error:

```json
{"titlu":"Descarcare mesaj 100000000","eroare":"Nu aveti dreptul sa descarcati acest mesaj"}
```

The README documents no content-type contract — distinguish PDF from error by
sniffing (`%PDF` magic / JSON `eroare` key), not by trusting headers.

## 4. `cerere` — request a report/document (asynchronous)

*Source: README lines 38–252.*

```
GET https://webserviced.anaf.ro/SPVWS2/rest/cerere?tip=...&cui=...[&an=&luna=&motiv=&numar_inregistrare=&cui_pui=&lunai=&lunas=]
```

Requests are **asynchronous**: a successful call returns an `id_solicitare`;
the finished report later appears as a message in `listaMesaje` (matched on
its `id_solicitare` field) and is downloaded via `descarcare` as PDF.

Success response (README's example — shown there in relaxed/unquoted JSON):

```json
{"id_solicitare":260149,"parametri":"an=2017, cui=8000000000","serial":"20A0506B2450015C39C","cnp":"1111111111118","titlu":"Transmitere cerere tip D101"}
```

Parameters (README lines 192–199): `tip` = request type; `cui` = the CUI/CNP
the request is about; `an` = year; `luna` = month; `motiv` = reason (**only**
Adeverinte Venit); `numar_inregistrare` = the form's registration number
(**only** Duplicat Recipisa); `cui_pui` = the CUI of the branch/working point
(**only** Fisa Rol). The `NeconcordanteD394` example additionally uses
`lunai`/`lunas` (start/end month of the period) — parameters used by the
example URL (line 238) but absent from the parameter list.

### 4.1 Request types and their parameters

The README gives the type list with explanations (lines 42–151) and one
example URL per type (lines 201–238). The *explicit* statements of which
parameters are mandatory are only the server-side validation error (line 248:
"Pentru tip raport= D101 parametri cui si an sunt obligatorii") and the
"doar la ..." notes on `motiv`/`numar_inregistrare`/`cui_pui`; the per-type
groupings below are **inferred from the example URLs** — trust the server's
validation errors over this table on any discrepancy.

`tip` values are passed verbatim, spaces URL-encoded (`Bilant%20anual`);
casing follows the README exactly (`VECTOR FISCAL`, `DATE IDENTIFICARE`
uppercase; `D112Contrib`, `NeconcordanteD112CNP` camel-case).

**`cui` only:**

| `tip` | What it returns |
|---|---|
| `D112Contrib` | Social-contribution data as declared by employers in D112 |
| `Obligatii de plata` | Unpaid fiscal obligations at the end of the previous month |
| `Nota obligatiilor de plata` | Payment note usable at the treasury counter / for remote payment |
| `Istoric Spatiu Virtual` | SPV activity history — profile changes, downloads |
| `Registru intrari-iesiri` | SPV activity history — document ins and outs |
| `DATE IDENTIFICARE` | The legal person's identification data in ANAF's DB at generation time |
| `VECTOR FISCAL` | The legal person's fiscal vector at generation time |
| `Situatie Sintetica` | Debit situation; generated until the 10th of the month, for the previous month |
| `InterogariBanci` | Banks' queries to ANAF about the natural person's income |
| `Fisa Rol` | Taxpayer sheet from the local administration; optional `cui_pui` for a branch |
| `Istoric bilant` | History of filed financial statements + half-year reports (last valid) |
| `NeconcordanteD112CNP` | D112 ↔ REVISAL mismatch details |

**`cui` + `an`:**

| `tip` | What it returns |
|---|---|
| `Bilant anual` | Annual financial statements ("Luna se alege automat" — month auto-selected) |
| `Istoric declaratii` | Valid declarations filed for the selected year (covers D100, D101, D102, D103, D112, D120, D130, D300, D301, D390, D394, D710, D205) |
| `D205` | Withholding-tax informative declaration, per income beneficiary |
| `D120` | Excise-duty return |
| `D130` | Domestic-crude-oil tax return |
| `D101` | Corporate income tax declaration |
| `D392` | Informative declaration — goods deliveries and services |
| `D393` | Informative declaration — international road passenger transport ticket income |
| `D106` | Informative declaration — shareholder dividends |
| `Bilant semestrial` | Half-year financial reports |
| `D212` | Duplicate of the last filed natural-person single declarations (per chapter, latest rectifications) |

**`cui` + `an` + `luna`:**

| `tip` | What it returns |
|---|---|
| `D300` | VAT return (includes D305) |
| `D390` | Recapitulative statement — intra-community supplies/acquisitions |
| `D100` | State-budget payment obligations (includes valid D100 and D710) |
| `D112` | Social contributions / income tax / insured-persons declaration |
| `D208` | Real-estate-transfer withholding tax; **half-yearly** — `luna=6` for S1, `luna=12` for S2 |
| `D394` | Informative declaration — domestic supplies and acquisitions |
| `D301` | Special VAT return |
| `D180` | Certification note by an active fiscal consultant |
| `D311` | VAT owed by taxpayers whose VAT registration code was cancelled |

**Special parameter shapes:**

| `tip` | Parameters | Notes |
|---|---|---|
| `Duplicat Recipisa` | `cui`, `numar_inregistrare` | Duplicate of an e-filing receipt (e.g. `numar_inregistrare=INTERNT-140000000-2018`); generated at request time, not the original receipt |
| `Adeverinte Venit` | `cui`, `an`, `motiv` | Income certificate for a natural person; `motiv` from the fixed list below |
| `NeconcordanteD394` | `cui`, `an`, `lunai`, `lunas` | D394 mismatches for the period `lunai`..`lunas` (start/end month) |

Not yet available: **CAF** (certificat de atestare fiscala) — "Tip raport=
CAF inca nu poate fi solicitat prin WS" (README lines 154, 249).

### 4.2 `motiv` values for `Adeverinte Venit`

The README (lines 156–186) says the text is matched **exactly** ("se verifica
ca textul sa fie exact la fel"), then its own example uses lowercase
`motiv=altele` against list entry `Altele` — verify case-sensitivity live.
The accepted list, verbatim:

Sanatate; Cresa; Gradinita; Scoala; Liceu; Facultate; Alocatia pentru copiii
nou nascuti; Trusou nou nascuti; Alocatia de stat pentru copii; Indemnizatie
ajutor stimulent pentru cresterea copilului; Sprijin financiar acordat la
constituirea familiei; Alocatia pentru sustinerea familiei; Alocatia familiala
complementara; Somaj si stimularea fortei de munca; Ajutor social; Pensie;
Stimulent de insertie; Ajutoare pentru incalzirea locuintei; Ajutoare
financiare pentru persoane aflate in extrema dificultate; Cheltuieli cu
inmormantarea persoanelor din familiile beneficiare de ajutor social; Ajutoare
de urgenta in caz de calamitati naturale; Indemnizatia Bugetul personal
complementar pentru persoana cu handicap; Alocatia de plasament; Indemnizatia
pentru insotitor; Alocatia lunara de hrana pentru copiii cu handicap de tip
HIV SIDA; Ajutor anual pentru veteranii de razboi; Institutie financiar
bancara asigurare etc.; Executor judecatoresc; Autoritati straine; Altele

## 5. Error model

*Source: README lines 27–30, 35–36, 244–252.*

All endpoints report errors as JSON `{titlu, eroare}` with Romanian free
text. Documented categories (messages verbatim, including upstream typos):

- **rights** — `Nu veti drept sa solictati informatii despre CIF=8000000000`
  (the `cui` is outside the certificate's rights list, §1);
- **validation** — `CUI-ul introdus= 8000000001 nu este corect.`;
  `Pentru tip raport= D101 parametri cui si an sunt obligatorii`;
  `Tip raport= CAF inca nu poate fi solicitat prin WS`;
- **technical** — `Eroare transmitere cerere. Cod 057`; report the numeric
  code (plus the call, if possible) to `spv.webservice@mfinante.ro`;
- **no results** (listaMesaje only) — `Nu exista mesaje in ultimele 5 zile`
  is not a failure (§2).

## 6. Limits, SLAs, changelog

*Source: README lines 254–263.*

No rate limits, quotas, or SLAs are documented anywhere in the source. Known
service changes (06.11.2018): `data_creare` gained the time component;
"Anliza de risc" report downloads fixed (previously returned null); `cif`
filter parameter added to `listaMesaje`. The stated roadmap (username/password
auth, declaration submission, CAF requests, contact-form submissions, profile
changes) is from 2019 and none of it is part of the documented surface.
Contact: `spv.webservice@mfinante.ro`.
