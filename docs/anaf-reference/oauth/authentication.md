---
title: ANAF OAuth2 Authentication (e-Factura & e-Transport)
service: oauth
language: en
sources:
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/API/Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf
    title: "OAUTH — Procedură de înregistrare aplicații portal ANAF (official PDF, 35 pp)"
    source_revision: "Instrucțiuni de utilizare actualizate 23.06.2022"
    retrieved: 2026-06-28
    local_copy: ../_sources/Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf
  - url: https://www.anaf.ro/anaf/internet/ANAF/servicii_online/inreg_api
    title: "ANAF — Înregistrare pentru API-uri (developer enrollment)"
    retrieved: 2026-06-28
  - url: https://mfinante.gov.ro/ro/web/efactura/informatii-tehnice
    title: "MF — Informații tehnice e-Factura"
    retrieved: 2026-06-28
  - url: https://mfinante.gov.ro/ro/web/etransport/informatii-tehnice
    title: "MF — Informații tehnice e-Transport"
    retrieved: 2026-06-28
  - title: "Live endpoint probe (this project)"
    note: "Direct TLS/HTTP probe of logincert.anaf.ro/anaf-oauth2/v1/token"
    retrieved: 2026-06-28
compiled: 2026-06-28
compiled_by: claude-opus-4-8
last_verified: 2026-06-28
status: draft   # draft until human-reviewed
---

# ANAF OAuth2 Authentication

Shared authentication for both ANAF API services covered by `anafpy` (e-Factura and
e-Transport). This is an **OAuth 2.0 Authorization Code** flow whose interactive
authorization step is gated by a **qualified digital certificate**.

> **Status:** draft, compiled from the sources above. The endpoint behaviour facts
> in §3, §5, §6 were additionally verified by a live probe on 2026-06-28. Anything
> not so marked is from the 2022-dated official PDF and should be re-confirmed during
> implementation.

## 1. Prerequisites

1. **A qualified digital certificate** for electronic signature (USB/PKCS#11 token),
   registered in ANAF's SPV (Spațiul Privat Virtual) with the **SPV PJ** role. The
   certificate shown in the official flow is issued by *"Anaf Issue CA2"*.
2. **Developer enrollment** on the ANAF portal: *Servicii Online → Înregistrare
   utilizatori → Dezvoltatori aplicații → Înregistrare pentru API-uri*. Confirmed via
   a security code emailed to you.
3. **An OAuth application profile** (next section), yielding a `client_id` +
   `client_secret`.

> Provenance: official PDF pp. 16–22, 34; [ANAF Înregistrare pentru API-uri](https://www.anaf.ro/anaf/internet/ANAF/servicii_online/inreg_api).

## 2. Registering an OAuth application profile

In the *Profil Oauth* form you provide:

| Field | Notes |
|---|---|
| **Denumire aplicație** | Application name. |
| **Callback URL 1** | The redirect URI. **Must match exactly** at token time. Multiple callback URLs can be added (`+`). May be a localhost URL — it does **not** need a public server (only your browser hits it) — **but the scheme must be `https://`**: registering an `http://` callback fails with an HTTP 400 from the portal's F5 APM backend (`/mgmt/tm/apm/oauth/oauth-client-app`). Register `https://localhost:PORT/callback`; capture the code via anafpy's `auth login --paste` (no listener) or its TLS listener (`--tls-cert`). *(Both facts are this project's live verifications: `https://` registrable 2026-06-28; `http://` rejected 2026-07-02. The full authorize→exchange flow against an `https://localhost` callback was live-completed 2026-07-02 — observed token lifetimes match §5's 90d/365d. The PDF's example uses Postman's `oauth.pstmn.io` callback.)* |
| **Serviciu** | One or more of: **E-Factura**, **E-Transport**. |

Pressing **Generare Client ID** issues a **Client ID** and **Client Secret**. The
registered profile then displays its OAuth values:

- **Grant Type:** Authorization Code
- **Auth URL:** `https://logincert.anaf.ro/anaf-oauth2/v1/{authorize,token,revoke}`
- **Client ID / Client Secret**

The *Meniu* offers **Gestionare aplicații**, **Istoric**, and **Renunțare Oauth**
(deletes all apps + client_id/secret pairs and revokes their access — see §9).

> ⚠️ **Source discrepancy:** older screenshots in the PDF show the legacy host
> `https://loginapi.fiscnet.ro/f5-oauth2/v1/...`. The current, authoritative host is
> **`logincert.anaf.ro/anaf-oauth2/v1`** (used in the PDF body text and **verified
> live 2026-06-28**). Treat `fiscnet.ro` as historical.
>
> Provenance: official PDF pp. 16–23.

## 3. Endpoints

| Purpose | Method | URL |
|---|---|---|
| Authorize (interactive, cert) | GET (browser) | `https://logincert.anaf.ro/anaf-oauth2/v1/authorize` |
| Token (exchange + refresh) | POST | `https://logincert.anaf.ro/anaf-oauth2/v1/token` |
| Revoke | POST | `https://logincert.anaf.ro/anaf-oauth2/v1/revoke` |

The OAuth host is the **same for test and production** (the test/prod split applies to
the API hosts, not to OAuth). The server presents a `*.anaf.ro` certificate
(DigiCert/RapidSSL). **JWT signing:** `alg = RS512`, `kid` e.g. `anaf_2023_2024`,
`iss = https://logincert.anaf.ro`.

> ⚠️ `/revoke` on the `logincert` host appears only in the PDF's **legacy** `fiscnet`
> screenshots (host-migrated by pattern); the live probe verified `/token` only.
> Confirm `/revoke` before relying on it.

> Provenance: official PDF pp. 23–28; live TLS/HTTP probe 2026-06-28.

## 4. Step 1 — Authorization request (browser + certificate)

Open in a browser:

```
https://logincert.anaf.ro/anaf-oauth2/v1/authorize
  ?response_type=code
  &client_id=<CLIENT_ID>
  &redirect_uri=<EXACT_CALLBACK_URL>
  &token_content_type=jwt
```

- `scope` and `state` are **left empty** in ANAF's reference flow.
- The browser prompts the user to **select the digital certificate** (SPV PJ). This is
  the **only step that requires the certificate**.
- On success ANAF redirects to the callback URL with `?code=<AUTH_CODE>`.

> **Implementation note:** the cert handshake is a browser + USB/PKCS#11 operation that
> a library cannot drive. `anafpy auth login` opens this URL and runs a localhost
> callback listener to capture `code`.
>
> Provenance: official PDF pp. 23–27.

## 5. Step 2 — Token exchange

```
POST https://logincert.anaf.ro/anaf-oauth2/v1/token
Authorization: Basic base64(client_id:client_secret)      # "Send as Basic Auth header"
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=<AUTH_CODE>
&redirect_uri=<EXACT_CALLBACK_URL>
&token_content_type=jwt
```

- **Client authentication = HTTP Basic** (`client_id:client_secret`).
- `token_content_type=jwt` is sent **on the query for `/authorize` and in the body for
  `/token`**.
- **No client certificate is required for this call** — verified live 2026-06-28: a
  cert-free POST to `/token` reaches ANAF's OAuth logic and returns a standard OAuth
  JSON error (`{"error":"invalid_client", ...}`, HTTP 400) rather than a TLS failure.
- **Timing:** a valid token must be obtained **within 60 seconds**; after 60s the
  connection is reset. (Capture `code` and exchange promptly.)
- Response: **200 OK** with a JSON body containing `access_token` and `refresh_token`.

> Provenance: official PDF pp. 23–29, 33; live probe 2026-06-28.

## 6. Step 3 — Refreshing the access token

```
POST https://logincert.anaf.ro/anaf-oauth2/v1/token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=<REFRESH_TOKEN>
```

- **Headless** — Basic Auth with client_id/secret + the refresh token. **No
  certificate.** (Official PDF p. 29 *"Refresh Token JWT"*, corroborated by the live
  probe.)
- Returns **200 OK** with **new `access_token` *and* `refresh_token`** — i.e. the
  refresh token is **rotated**; **persist both** every time.

> **Implementation note:** because refresh needs no cert, an unattended/Dockerized
> `anafpy` MCP server can keep itself authenticated for the full ~365-day refresh
> window; the cert/browser bootstrap is needed only ~once a year (or after revocation).
>
> Provenance: official PDF p. 29; live probe 2026-06-28.

## 7. Token structure & lifetimes

The access token is a **digitally-signed JWT** (validate via signature; tampering
invalidates it). Decoded payload includes:

- `token_type`: `Bearer`
- `iss`: `https://logincert.anaf.ro`
- `iat`, `nbf`, `exp` (epoch seconds) — read `exp` locally to schedule refresh
- `scope`: `clientappid info issuer role serial`
- `role` / per-service claims listing granted services, e.g.
  `EFACTURA, ETRANSPORT, SRV_EFACTURA, HELLO`
- `clientappid`, `serial` (certificate serial)

| Token | Lifetime |
|---|---|
| **Access token (JWT)** | **129600 min = 90 days** |
| **Refresh token (JWT)** | **525600 min = 365 days** |

> Provenance: official PDF pp. 28–29, 33.

## 8. Using the token & calling the APIs

Send `Authorization: Bearer <access_token>` to the service APIs (e-Factura
`api.anaf.ro/{test,prod}/FCTEL/rest/...`; e-Transport — see the e-Transport doc).

**Status codes / behaviour:**

| Code | Meaning |
|---|---|
| **200 OK** | Authentication + authorization succeeded. The web service then returns its own success/error payload depending on the request, the certificate's rights, the CUIs it covers, and the data uploaded. |
| **403 Forbidden** | Unauthorized request to the service URL. |
| **429 Too Many Requests** | Rate limit exceeded. |

**Rate limit (`api.anaf.ro`):** **1000 requests / minute** (may be adjusted per service
in future). → `anafpy` raises `AnafRateLimitError` on 429; the client itself does not
auto-retry.

**Quick token test:** `GET https://api.anaf.ro/TestOauth/jaxrs/hello?name=<v>` echoes
the received request (including the `Authorization: Bearer …` header) — handy to confirm
a token is accepted.

> Provenance: official PDF pp. 31–33.

## 9. Revocation

- **`/anaf-oauth2/v1/revoke`** revokes a token.
- **Renunțare Oauth** (portal) deletes all of the account's app profiles and
  client_id/secret pairs and revokes access of clients using their tokens; to obtain
  new tokens you must re-register.
- If tokens are compromised, send them to ANAF to block their access.

> Provenance: official PDF pp. 20–22, 29.

## 10. `anafpy` implementation checklist

- [ ] `client_id`/`client_secret` via config (keychain-backed in Cowork); never logged.
- [ ] Authorize URL builder with `response_type=code`, `client_id`, exact
      `redirect_uri`, `token_content_type=jwt`.
- [ ] Localhost callback listener (host-side `auth login`); exchange `code` **within
      60 s**.
- [ ] Token + refresh calls use **HTTP Basic** auth; `token_content_type=jwt` in the
      token body.
- [ ] Persist **both** tokens after refresh (refresh-token rotation).
- [ ] Schedule refresh from the JWT `exp` (or refresh-on-401).
- [ ] Surface 403 / 429 distinctly; do not auto-retry in the client.
- [ ] **Verify end-to-end during implementation:** a real refresh round-trip (the live
      probe only confirmed cert-free transport + OAuth error handling, not a full
      refresh with valid credentials).

> ⚠️ **Stale e-Transport facts in this 2022 PDF** (p. 30) — resolved in the
> [e-Transport doc](../etransport/api.md), which is the current truth: the upload path
> is listed **without** the `versiune` segment and with `standard=ETRANSPORT` (now
> `ETRANSP` + `/{versiune}`), and a `…/ETRANSPORT/ws/v1/descarcare/{id}` endpoint is
> listed that has since been **removed** (informații-tehnice: *"Serviciul de Descărcare
> a fost eliminat de pe mediul de test și de producție"*).
