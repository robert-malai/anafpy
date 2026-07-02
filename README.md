# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), and the
**public no-auth registries** (VAT/taxpayer lookups, financial statements) — plus a
local MCP server that exposes them as [Claude Cowork](https://claude.com) skills.

anafpy is a **thin transport client**, not invoicing software: you bring invoice XML that
your own invoicing system produced, and anafpy validates it, files it with ANAF, tracks
status, and pulls documents back — wrapping the XML you read back (your filings and
invoices suppliers issued to you) in a friendly **flat read view** for easy display.
(e-Factura is a filing endpoint; Romanian law presumes you already run an invoicing
system.)

> Status: **early / alpha** (`0.x`), not yet published to PyPI. The OAuth2 auth layer,
> both async clients (with an easy-to-read flat view of downloaded documents), and the
> MCP server (XML pass-through filing + read-only inbox) are implemented and tested.
> Validation is ANAF's own server-side `validare` endpoint — there is no local rule
> engine. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of ANAF's
> APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## What works today

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx.Auth` integration for the clients.
- **`EFacturaClient`** (async) — `upload`, `get_status`, `download`, `to_pdf`,
  `validate_remote` (ANAF's authoritative server-side validation, no filing — uses the
  public no-auth production validator, so it works whatever environment the client
  targets), `validate_signature` (checks the MF signature over a downloaded invoice), the
  `upload_and_wait` poll-until-terminal helper, and `list_messages` — a single async
  iterator that pages the message list under the hood (window by `days` or `start`/`end`;
  empty window → empty iterator, real ANAF errors → raise). `download` exposes three read
  tiers: raw signed bytes, the full UBL model, and an easy-to-read `FlatInvoice` **view**.
- **`ETransportClient`** (async) — `upload`, `get_status`, `info`, `upload_and_wait`, and
  `list_notifications` (same async-iterator shape).
- **`PublicClient`** (async) — ANAF's **unauthenticated** public services on
  `webservicesp.anaf.ro`: `lookup_taxpayers` (VAT registration, VAT-on-collection,
  inactive, split-VAT, and RO e-Factura register membership in one call),
  `lookup_efactura_register`, `lookup_farmers`, `lookup_cult_entities`, and
  `get_financial_statement` (public bilanț indicators). No credentials, no test/prod
  split; requests are paced client-side at ANAF's stated 1 req/s rule.
- **Flat read views** — `read_flat_invoice` / `read_flat_transport` project UBL /
  e-Transport documents into small, easy-to-read shapes (lossy, with a `complete` flag);
  anafpy reads documents into these, it never composes documents from them.
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **MCP server** (`anafpy[mcp]`) — a local stdio connector exposing the operations as
  Cowork skills, with read-first, two-step gated filing and a read-only e-Factura inbox
  (see below).

Not yet built: a sync facade, CI, and PyPI publishing.

## Install

Not on PyPI yet — install from source:

```bash
git clone https://github.com/robertmalai/anafpy && cd anafpy
uv sync --all-extras
```

The distribution offers one extra: `anafpy[mcp]` (the MCP server).

## Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**. The
one-time, interactive bootstrap runs on your machine (the cert lives there):

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback --paste
anafpy auth status        # show stored token validity
```

Register the callback URL with the **`https://` scheme** — ANAF's developer portal
rejects `http://` callbacks (HTTP 400 at registration; verified 2026-07-02). The
callback still doesn't need a public server; pick how the code gets captured:

- **`--paste` (recommended default).** No listener runs. After the certificate step the
  browser shows a connection error — expected — and you paste the redirect URL from the
  address bar into the CLI. Paste promptly: ANAF's code expires in ~60 seconds.
- **`--tls-cert` / `--tls-key`.** The local listener serves TLS directly with a
  certificate you supply — a self-signed one works. Generate it once (browsers
  require a `subjectAltName`, not just the CN):

  ```bash
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -keyout ~/.anafpy/callback-key.pem -out ~/.anafpy/callback-cert.pem \
    -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  ```

  then pass `--tls-cert ~/.anafpy/callback-cert.pem --tls-key ~/.anafpy/callback-key.pem`
  instead of `--paste`. The browser shows a one-time "proceed to localhost" warning
  (click through — it's your own cert on your own loopback); trust the cert in the OS
  keychain, or use [mkcert](https://github.com/FiloSottile/mkcert), to remove the
  warning entirely. On **Windows** (no stock OpenSSL), prefer mkcert:
  `choco install mkcert` (or `scoop install mkcert`), then `mkcert -install` and
  `mkcert localhost 127.0.0.1` — the emitted PEM pair plugs into
  `--tls-cert`/`--tls-key` unchanged, with no browser warning at all.
- **Neither flag.** The listener speaks plain HTTP; put your own TLS terminator in
  front of it. If the listener can't start, the CLI falls back to paste mode.

This opens your browser for the certificate step, captures the authorization code,
exchanges it for tokens, and stores them under
`~/.anafpy/tokens.json`. Tokens then refresh **headlessly** for ~a year (access token
90 days, refresh token 365 days), so the cert is needed only about once a year. See
[`docs/anaf-reference/oauth/authentication.md`](docs/anaf-reference/oauth/authentication.md).

## Usage

The clients are async and used as context managers. Build a `TokenProvider` over your
stored tokens, then call discrete operations:

```python
from anafpy.auth import FileTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient

provider = TokenProvider(
    client_id="<ID>",
    client_secret="<SECRET>",
    store=FileTokenStore("~/.anafpy/tokens.json"),
)

async with EFacturaClient(provider) as efactura:
    result = await efactura.upload(invoice_xml, cif="RO12345678")
    status = await efactura.get_status(result.upload_id)
    # or, in one call: status = await efactura.upload_and_wait(invoice_xml, cif=...)
```

Discrete methods make a single call (no transport retry). HTTP/auth problems raise
`AnafError` subclasses; **business outcomes** (a `nok` rejection, BR-RO findings) come
back as typed values, not exceptions. On HTTP 429 the client raises `AnafRateLimitError`
exposing `retry_after` rather than backing off itself.

The public registries need no auth at all:

```python
from anafpy.public import PublicClient

async with PublicClient() as public:
    lookup = await public.lookup_taxpayers(["RO12345678"])
    if lookup.found:
        record = lookup.found[0]
        print(record.name, record.vat_registered, record.efactura_registered)
```

## MCP server

The `anafpy[mcp]` extra ships a **local stdio MCP server** that wraps the clients as
Cowork skills. Run it host-side, where the token store written by `anafpy auth login`
lives:

```bash
ANAFPY_CLIENT_ID=... ANAFPY_CLIENT_SECRET=... ANAFPY_CIF=... \
  python -m anafpy.mcp        # or the `anafpy-mcp` console script
```

It exposes **read-only** tools (`auth_status`; the e-Factura inbox via
`efactura_list_messages` / `efactura_get_status` / `efactura_download`; `etransport_list`
/ `etransport_get_status` / `etransport_lookup`; `efactura_validate`, which runs
ANAF's authoritative server-side validator without filing; and the `anaf_*` public
lookups — taxpayer/VAT registry, RO e-Factura register, farmers/cult registers, and
financial statements — which need **no login at all**) plus **two-step gated
filing**: `*_prepare*` parses the supplied XML and returns a preview + a confirmation
token bound to the document and the CIF being filed for; `*_submit*` files only when
given that token (same document, same CIF) and `confirm=True`, and each token is
single-use — filing again requires a fresh prepare. Filing is **XML pass-through** —
you hand it the complete UBL /
e-Transport XML your invoicing software exported; the server does not compose invoices.
Both the inbox and the `prepare` preview present invoices as a friendly **flat read view**
(`FlatInvoice`) parsed from the XML — easy to read, lossy by design (the raw bytes stay
authoritative). The compiled ANAF reference is surfaced as read-only resources. Auth stays
the host-side CLI — the server only reads and refreshes the token store. Configuration is
environment-only; see [`CLAUDE.md`](CLAUDE.md).

## Development

```bash
uv sync --all-extras
uv run pytest                              # respx-mocked, credential-free
uv run ruff check . && uv run ruff format --check .
uv run mypy                                # strict
ANAFPY_LIVE=1 uv run pytest -m live        # opt-in: live smoke against real ANAF
```

The `live` marker re-confirms wire shapes against real ANAF endpoints and is skipped
by default (not a gate). It covers the public services (no credentials needed) plus,
with `.env` credentials and an `anafpy auth login` token store, the authenticated
**TEST** environment: read-only shape checks and two roundtrips that actually file a
test document — a minimal CIUS-RO invoice (e-Factura) and a domestic transport
declaration (e-Transport). The roundtrips target TEST only, never production.

Models under `efactura/ubl/` and `etransport/schema/` are **generated** (via
`scripts/generate_*.py` from vendored XSDs in `schemas/`) and must not be hand-edited.
See [`CLAUDE.md`](CLAUDE.md) for repository conventions.

## License

[Apache-2.0](LICENSE). Independent / unofficial — not affiliated with ANAF.
