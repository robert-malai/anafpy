# Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**
— the same one used on ANAF's SPV portal. anafpy keeps that split cleanly in two:

- The **one-time, interactive bootstrap** (`anafpy auth login`) runs in a browser
  on the machine where the certificate lives. This is the only step that touches
  the certificate.
- Everything after — code exchange, token refresh — is **headless**. Clients
  receive a `TokenProvider` and drive httpx through the `AnafAuth` (`httpx.Auth`)
  integration, which refreshes tokens transparently. Tokens last ~90 days (access)
  / ~365 days (refresh), so the certificate is needed roughly **once a year**.

The clients themselves never handle certificates or mTLS — auth is a separate
layer by design.

## The CLI

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback --paste
anafpy auth status        # show stored token validity
anafpy auth logout        # remove the stored tokens (signs this machine out)
```

The Client ID / Secret come from the OAuth application you register on ANAF's
developer portal — the [MCP setup walkthrough](../mcp/setup.md) covers that
registration step by step (it is the same registration regardless of whether you
use the MCP server or the library).

## Capturing the authorization code

Register the callback URL with the **`https://` scheme** — ANAF's developer portal
rejects `http://` callbacks (HTTP 400 at registration; verified 2026-07-02). The
callback still doesn't need a public server; pick how the code gets captured:

- **`--paste` (recommended default).** No listener runs. After the certificate
  step the browser shows a connection error — expected — and you paste the
  redirect URL from the address bar into the CLI. Paste promptly: ANAF's code
  expires in ~60 seconds.
- **`--tls-cert` / `--tls-key`.** The local listener serves TLS directly with a
  certificate you supply — a self-signed one works. Generate it once (browsers
  require a `subjectAltName`, not just the CN):

  ```bash
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -keyout ~/.anafpy/callback-key.pem -out ~/.anafpy/callback-cert.pem \
    -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  ```

  then pass `--tls-cert ~/.anafpy/callback-cert.pem --tls-key
  ~/.anafpy/callback-key.pem` instead of `--paste`. The browser shows a one-time
  "proceed to localhost" warning (click through — it's your own cert on your own
  loopback); trust the cert in the OS keychain, or use
  [mkcert](https://github.com/FiloSottile/mkcert), to remove the warning entirely.
  On **Windows** (no stock OpenSSL), prefer mkcert: `choco install mkcert` (or
  `scoop install mkcert`), then `mkcert -install` and `mkcert localhost
  127.0.0.1` — the emitted PEM pair plugs into `--tls-cert`/`--tls-key` unchanged,
  with no browser warning at all.
- **Neither flag.** The listener speaks plain HTTP; put your own TLS terminator in
  front of it. If the listener can't start — or no callback arrives in time — the
  CLI falls back to paste mode.

Every login binds a random OAuth `state` (login-CSRF protection): the listener
rejects redirects that don't echo it, and the paste parser rejects a mismatching
URL — a pasted bare code is exempt.

## Token storage

The login stores tokens through the `TokenStore` protocol (`load`/`save`/`clear`):

- **`KeyringTokenStore`** — the **default** backend: the OS credential store
  (macOS Keychain, Windows Credential Manager, Linux Secret Service/KWallet). On
  Windows the token set is transparently split across vault entries (Credential
  Manager caps one entry at 2560 bytes, smaller than an ANAF JWT).
- **`FileTokenStore`** — a JSON file (default `~/.anafpy/tokens.json`), the
  opt-out for Docker/headless hosts without a credential store. Select it with
  `--store-backend file` on the CLI or `ANAFPY_TOKEN_STORE_BACKEND=file`
  (`--store` / `ANAFPY_TOKEN_STORE` moves the file).

## Using the tokens from code

```python
from anafpy.auth import KeyringTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient

provider = TokenProvider(
    client_id="<ID>",
    client_secret="<SECRET>",
    store=KeyringTokenStore(),
)

async with EFacturaClient(provider) as efactura:
    ...
```

The provider reads the stored token set, refreshes it headlessly when it nears
expiry, and writes the refreshed set back to the store.

## Signing out

`anafpy auth logout` deletes the stored tokens, which is what ends this machine's
access: without the refresh token it can no longer mint new access tokens. The
logout is **purely local** — ANAF documents a `/revoke` endpoint but it is not
reachable headlessly (live-verified 2026-07-05: ANAF's gateway answers with its
certificate login wall, same as for a nonexistent path), so server-side the tokens
simply expire. To hard-revoke them on ANAF's side, use **Renunțare Oauth** in
ANAF's developer portal (this deletes the app registration).

See the compiled [OAuth reference](../anaf-reference/oauth/authentication.md) for
the wire-level details of ANAF's flow.
