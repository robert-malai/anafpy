---
title: Declaration portal upload (WAS6DUS) — authenticated recon
service: declaratii
language: en
sources:
  - url: https://decl.anaf.mfinante.gov.ro/WAS6DUS/
    title: "Depunere declarații upload app (live recon 2026-07-16: unauthenticated choreography + one certificate login; live filing 2026-07-17: one D406T — the sanctioned no-effect test declaration — captured the success page)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/SAF_T_Ghidul_D406_1712021.pdf
    title: "Ghidul contribuabilului D406 — the D406T voluntary-testing programme (test filing with no legal/fiscal effect)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/saf_t.htm
    title: "ANAF SAF-T page (D406T references, validator support)"
    retrieved: 2026-07-17
compiled: 2026-07-16
compiled_by: claude-fable-5
last_verified: 2026-07-17
status: draft
---

# Declaration portal upload (`decl.anaf.mfinante.gov.ro/WAS6DUS/`)

The portal behind **anaf.ro → Depunere declarații → Transmitere declarații**:
where the signed declaration PDF is actually filed. There is no official API
documentation; this reference is compiled from live recon (2026-07-16, raw
captures under `_sources/decl-portal/`) — the unauthenticated choreography plus
**one real certificate login** that captured the authenticated app surface.
**No document was filed**; the successful-upload response (the page carrying
the upload index) is deliberately still unobserved — see §4.

This page records the **M2 recon facts**; the upload client itself is not
implemented yet.

## 1. Access model — F5 APM certificate wall (SPV's, with one extra step)

Same F5 BigIP APM cookie-session model as SPV (`webserviced.anaf.ro`, see the
[SPV reference](../spv/api.md) §1.1), with one difference: a **logon-form POST
precedes the certificate renegotiation**. The full login choreography
(live-proven, macOS `/usr/bin/curl` SecureTransport with a Keychain identity):

```
1. GET  /WAS6DUS/          -> 302 /my.policy   (Server: BigIP; sets MRHSession,
                                                LastMRH_Session)
2. GET  /my.policy         -> 200 APM logon page (customization
                              D112_HTTPS_Auth_v2_general_ui): certificate-only —
                              no user/password, one submit "Prezentare certificat"
3. POST /my.policy  vhost=standard
                           -> 302 /my.policy   (sets F5_ST + fresh MRHSession)
4. GET  /my.policy  (client certificate; TLS renegotiation -> token PIN / 2FA)
                           -> 302 /my.policy_nonce?nonce=<...>
                           -> 302 /WAS6DUS/
5. GET  /WAS6DUS/          -> 200 the upload app (sets WebSphere JSESSIONID)
```

Live facts:

- **`F5_ST` is timestamped and short-lived**: pausing minutes between step 3
  and step 4 gets the connection reset (`Send failure: Broken pipe`) before any
  renegotiation — run the chain promptly, in one go.
- Do **not** let curl `--location` carry the POST across step 3's redirect: it
  re-sends a POST over a downgraded HTTP/1.0 connection and the F5 resets it.
  Steps must be discrete (or the follow must be a GET).
- The final response often ends with **`SSLRead() error -9806` / curl exit 56**
  despite full success — the same no-`close_notify` F5 quirk as SPV's
  bootstrap; judge success by the body and cookies, not the exit code.
- The session cookie set is `MRHSession` + `LastMRH_Session` + `F5_ST` (APM)
  plus **`JSESSIONID`** (the WebSphere app; `X-Powered-By: Servlet/3.0`,
  IBM sample-code markup in the pages). A **plain, certificate-less client
  replaying the cookies is fully authenticated** — same bearer-cookie model as
  SPV, so the SPV pattern (curl bootstrap once, httpx rides the cookies) fits.
- Stated **10-minute inactivity timeout** (logon page) — much shorter than
  SPV's; treat sessions as disposable (login → upload → done).
- Certificate-less access to step 4 dead-ends at `/vdesk/hangup.php3`.
- Logout: `GET /exit` → 302 (APM teardown).

## 2. The upload app

The authenticated `/WAS6DUS/` page is a single multipart upload form:

```html
<form name="uf" method="POST" action="/WAS6DUS/displayFile.do"
      enctype="multipart/form-data">
  <input type="file" name="linkdoc" size="75" value="">
  <input type="submit" value="Trimite">
</form>
```

- **One file field, `linkdoc`** — the signed declaration PDF.
- `/WAS6DUS/welcome.do` renders the same form ("Pentru a depune o noua
  declaratie apasati aici" links there).
- The page itself points recipisa verification at
  **`https://www.anaf.ro/StareD112/`** (the service wrapped by
  [stared112.md](stared112.md)) and repeats its 200-declaration batching
  advice — ANAF's own statement that StareD112 is the post-filing
  confirmation channel.
- Notes on the page: pre-Nov/Dec-2011 reporting periods for D100/300/710/390
  are counter-only; a red banner (also on the logon page) warns that Adobe
  updates can break declaration signing — the portal's signature validation is
  sensitive to signer tooling.

## 3. Error page shape

A `GET` of `/WAS6DUS/displayFile.do` (no file) answers HTTP 200 with the app's
generic error page (captured, `upload-error-nofile.html`):

> `Ne cerem scuze, dar cererea dumneavoastra nu a putut fi indeplinita!` —
> `Motivul: <span style="color: red">…</span>`

with the reason in the red `span` (here: `Nu ati selectat fisierul ce urmeaza a
fi transmis`) and a link back to `/WAS6DUS/welcome.do`. Expect upload
rejections (wrong signature, malformed PDF) to ride this same shape.

## 4. Success page (live-captured 2026-07-17)

The successful-upload response — long deliberately unobserved, finally
captured by filing a **D406T** (§5; raw capture
`_sources/decl-portal/upload-response-d406t.html`). HTTP 200, the same
IBM-sample-markup style as the rest of the app:

- Header: *"Agentia Nationala de Administrare Fiscala — **Succes depunere**"*,
  plus the "depune o nouă declarație" link back to `/WAS6DUS/welcome.do`.
- The payload sentence, filename echoed and the **upload index** in a `<b>`:

  > Fişierul dumneavoastră cu numele "d406t.pdf" a fost depus cu succes.
  > Indexul este **1100000005**.

- An explicit caveat that this page is **not** the registration confirmation:
  *"Acest mesaj nu constituie confirmarea inregistrării documentului.
  Confirmarea depunerii va fi afisată in recipisă."* — followed by a pointer
  to `https://www.anaf.ro/StareD112/` ("Vizualizare stare"), hidden by an
  inline script on the `extranet` hostname.

**StareD112 tracks the filing immediately**: a status query with the returned
index listed the document (form `D406T`, state `In prelucrare`) within a
minute of the upload — see [stared112.md](stared112.md).

There is still **no separate TEST environment for declaration filing** — the
D406T on the production portal (§5) is the sanctioned no-effect exercise.

## 5. D406T — the sanctioned no-effect test filing

ANAF's SAF-T **voluntary testing programme** (verified online 2026-07-17)
accepts **D406T**, the test variant of the D406 informative declaration,
through the **normal production filing channel** — signed smart-PDF with the
SAF-T XML attached, qualified certificate, uploaded via "Depunere declarații"
— explicitly **without legal or fiscal effect**: the transmitted data is not
processed, stored, or used in ANAF's risk analyses, and is deleted from
ANAF's systems after the verification report is issued. ANAF states the
programme is a **permanent** assistance service (it continued past
2022-01-01) and is open to taxpayers **and** software vendors (ERP /
financial-accounting application suppliers) alike. `D406T` **is its own DUK
form** (proven locally 2026-07-17): namespace
`mfp:anaf:dgti:d406t:declaratie:v1`, jars only in the dedicated `duk_SAFT`
distribution — sourcing, compatibility, and the minimal-file structure
gotchas are in the [DUK reference](duk.md) §1 ("The SAF-T module").

M2 status: the upload client **landed and is live-verified** —
`anafpy.declaratii.upload.DeclarationUploadClient` +
`PortalCurlBootstrapper` implement §1's choreography and §2's multipart
POST, with the known §3 rejection page returned as a business outcome and
the §4 success page yielding the upload index. The live test
`tests/test_declaratii_upload_live.py` runs the full pipeline (validate →
render → sign → file → StareD112) on a committed minimal D406T
(`tests/fixtures/declaratii/d406t-minimal.xml`, validates `ok` under both
D406T and D406), gated on `ANAFPY_LIVE_FILE_D406T=1` because it fires the
certificate 2FA twice. Its first run (2026-07-17, upload index 1100000005)
settled all three open questions in one pass:

- the **successful-upload response** is captured and documented (§4);
- the portal **accepts the pyHanko CMS signature** (the open question from
  the [DUK reference](duk.md) §5 — the AIA-completed chain was accepted);
- **StareD112 tracks a D406T upload index** (form `D406T`,
  `In prelucrare` within a minute of filing).
