# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** and **e-Transport** — with a later MCP server that exposes the
functionality as [Claude Cowork](https://claude.com) skills.

> Status: **early / alpha** (`0.x`). The OAuth2 auth core is the first module under
> construction. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of
> ANAF's APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## Install

```bash
pip install anafpy                # clients + auth + CLI
pip install "anafpy[validation]"  # + local Schematron pre-validation (saxonche)
pip install "anafpy[mcp]"         # + the MCP server
```

## Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**.
The one-time, interactive bootstrap runs on your machine (the cert lives there):

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback
```

This opens your browser for the certificate step, captures the authorization code on a
local callback listener, exchanges it for tokens, and stores them locally. Tokens then
refresh **headlessly** for ~a year (access token 90 days, refresh token 365 days), so
the cert is needed only about once a year. See
[`docs/anaf-reference/oauth/authentication.md`](docs/anaf-reference/oauth/authentication.md).

## Development

```bash
uv sync --all-extras          # set up the env with dev groups
uv run pytest                 # tests
uv run ruff check . && uv run mypy
```

## License

[Apache-2.0](LICENSE). Independent / unofficial — not affiliated with ANAF.
