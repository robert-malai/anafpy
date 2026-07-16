---
title: Declaration portal upload (WAS6DUS) — authenticated recon
service: declaratii
language: en
sources:
  - url: https://decl.anaf.mfinante.gov.ro/WAS6DUS/
    title: "Depunere declarații upload app (live recon: unauthenticated choreography + one certificate login; no document was filed)"
    retrieved: 2026-07-16
compiled: 2026-07-16
compiled_by: claude-fable-5
last_verified: 2026-07-16
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

## 4. Deliberately unobserved

The **successful-upload response** — the page that returns the upload index
(the number `StareD112` and the recipisa are keyed by). Observing it requires
actually filing a declaration, and there is **no TEST environment for
declaration filing** — so it stays unknown until M2's live verification files
a real (nil/rectifiable) declaration. Everything else needed to build the M2
client is above.
