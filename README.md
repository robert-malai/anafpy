# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing) and **e-Transport** (goods transport) — plus a local
MCP server that exposes them as [Claude Cowork](https://claude.com) skills.

anafpy is a **thin transport client**, not invoicing software: you bring invoice XML that
your own invoicing system produced, and anafpy validates it, files it with ANAF, tracks
status, and pulls documents back — wrapping the XML you read back (your filings and
invoices suppliers issued to you) in a friendly **flat read view** for easy display.
(e-Factura is a filing endpoint; Romanian law presumes you already run an invoicing
system.)

> Status: **early / alpha** (`0.x`), not yet published to PyPI. The OAuth2 auth layer,
> both async clients (with an easy-to-read flat view of downloaded documents), local
> Schematron pre-validation, and the MCP server (XML pass-through filing + read-only
> inbox) are implemented and tested. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of ANAF's
> APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## What works today

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx.Auth` integration for the clients.
- **`EFacturaClient`** (async) — `upload`, `get_status`, `download`, `to_pdf`, the
  `upload_and_wait` poll-until-terminal helper, and `list_messages` — a single async
  iterator that pages the message list under the hood (window by `days` or `start`/`end`;
  empty window → empty iterator, real ANAF errors → raise). `download` exposes three read
  tiers: raw signed bytes, the full UBL model, and an easy-to-read `FlatInvoice` **view**.
- **`ETransportClient`** (async) — `upload`, `get_status`, `info`, `upload_and_wait`, and
  `list_notifications` (same async-iterator shape).
- **Flat read views** — `read_flat_invoice` / `read_flat_transport` project UBL /
  e-Transport documents into small, easy-to-read shapes (lossy, with a `complete` flag);
  anafpy reads documents into these, it never composes documents from them.
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **Local Schematron pre-validation** (`anafpy[validation]`) — EN 16931 + CIUS-RO and
  e-Transport rules via `saxonche`, returning structured BR-RO findings.
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

The distribution offers extras: `anafpy[validation]` (local Schematron via saxonche),
`anafpy[mcp]` (the MCP server), and `anafpy[cli]`.

## Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**. The
one-time, interactive bootstrap runs on your machine (the cert lives there):

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback
anafpy auth status        # show stored token validity
```

This opens your browser for the certificate step, captures the authorization code on a
local callback listener, exchanges it for tokens, and stores them under
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
/ `etransport_get_status` / `etransport_lookup`; and `*_validate`) plus **two-step gated
filing**: `*_prepare*` validates the supplied XML locally and returns a preview + a
confirmation token bound to the document and the CIF being filed for; `*_submit*` files
only when given that token (same document, same CIF) and `confirm=True`, and each token
is single-use — filing again requires a fresh prepare. Filing is **XML pass-through** — you hand it the complete UBL /
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
```

Models under `efactura/ubl/` and `etransport/schema/` are **generated** (via
`scripts/generate_*.py` from vendored XSDs in `schemas/`) and must not be hand-edited.
See [`CLAUDE.md`](CLAUDE.md) for repository conventions.

## License

[Apache-2.0](LICENSE). Independent / unofficial — not affiliated with ANAF.
