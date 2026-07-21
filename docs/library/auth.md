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
                  --redirect-uri https://localhost:9002/callback
anafpy auth status        # show stored token validity
anafpy auth logout        # remove the stored tokens (signs this machine out)
```

The Client ID / Secret come from the OAuth application you register on ANAF's
developer portal — the [MCP setup walkthrough](../mcp/setup.md) covers that
registration step by step (it is the same registration regardless of whether you
use the MCP server or the library).

## Capturing the authorization code

Register the callback URL with the **`https://` scheme** — ANAF's developer portal
rejects `http://` callbacks (HTTP 400 at registration; verified 2026-07-02). No
public CA may issue a certificate for `localhost` (CA/Browser Forum baseline
requirements), so a browser-trusted local listener can't exist out of the box —
the capture modes trade that constraint off differently:

- **No flags (the default).** The listener serves TLS with a **one-time
  self-signed certificate generated on the spot** — nothing to create, nothing
  installed, nothing persisted (the key pair lives only for the login attempt).
  After the certificate step the browser shows a single "connection is not
  private" warning — **expected**, and announced by the CLI beforehand: click
  "Advanced" and proceed to localhost, and the code is captured automatically.
  Since logins recur only ~yearly, that one click is the entire recurring cost.
- **`--tls-cert` / `--tls-key`.** The listener serves TLS with a certificate you
  supply — bring one your machine already trusts and the browser warning
  disappears entirely. [mkcert](https://github.com/FiloSottile/mkcert) is the
  easy way: `mkcert -install`, then `mkcert localhost 127.0.0.1` — the emitted
  PEM pair plugs into `--tls-cert`/`--tls-key` unchanged.
- **`--paste`.** No listener runs. The browser ends on a connection error —
  expected — and you paste the redirect URL from the address bar into the CLI.
  Paste promptly: ANAF's code expires in ~60 seconds. This is also the automatic
  fallback whenever the listener can't start or no callback arrives in time.
- **`--no-tls`.** The listener speaks plain HTTP; only useful with your own TLS
  terminator in front of it holding the real certificate.

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
