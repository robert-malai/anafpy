# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing) and **e-Transport** (goods transport) — with a
later MCP server that will expose the functionality as
[Claude Cowork](https://claude.com) skills.

> Status: **early / alpha** (`0.x`), not yet published to PyPI. The OAuth2 auth layer
> and both async clients are implemented and tested; local Schematron validation and the
> MCP server are designed but not built. See [`DESIGN.md`](DESIGN.md) for the full design
> and [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of
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

Not yet built: local Schematron pre-validation (`[validation]` extra), the MCP server
(`[mcp]` extra), a sync facade, CI, and PyPI publishing.

## Install

Not on PyPI yet — install from source:

```bash
git clone https://github.com/robertmalai/anafpy && cd anafpy
uv sync --all-extras
```

The published distribution will offer extras: `anafpy[validation]` (local Schematron via
saxonche) and `anafpy[mcp]` (the MCP server).

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
