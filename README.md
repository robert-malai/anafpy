# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing) and **e-Transport** (goods transport) — plus an
MCP server that exposes the functionality as
[Claude Cowork](https://claude.com) skills.

> Status: **early / alpha** (`0.x`), not yet published to PyPI. The OAuth2 auth layer,
> both async clients, local Schematron pre-validation, and the MCP server are
> implemented and tested. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of
> ANAF's APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## What works today

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx.Auth` integration for the clients.
- **`EFacturaClient`** (async) — `upload`, `get_status`, `download`, `list_messages` /
  `list_messages_paged`, `to_pdf`, and the `upload_and_wait` poll-until-terminal helper.
- **`ETransportClient`** (async) — `upload`, `get_status`, `list_notifications`, `info`,
  and `upload_and_wait`.
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **Local Schematron pre-validation** (`anafpy[validation]`) — EN 16931 + CIUS-RO and
  e-Transport rules via `saxonche`, returning structured BR-RO findings.
- **MCP server** (`anafpy[mcp]`) — a local stdio connector exposing the operations as
  Cowork skills, with read-first, two-step gated filing (see below).

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

It exposes **read-only** tools (`auth_status`, `efactura_list_messages` /
`efactura_get_status` / `efactura_download`, `etransport_list` / `etransport_get_status`
/ `etransport_lookup`, and `*_validate`) plus **two-step gated filing**: `*_prepare*`
validates locally and returns a preview + a confirmation token; `*_submit*` files only
when given that token (for the same document) and `confirm=True`. The compiled ANAF
reference is surfaced as read-only resources. Invoices/declarations are authored with
small **flat** models, or passed through as existing UBL / e-Transport XML. Auth stays
the host-side CLI — the server only reads and refreshes the token store. Configuration
is environment-only; see [`CLAUDE.md`](CLAUDE.md).

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
