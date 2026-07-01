# CLAUDE.md

Guidance for working in this repository. See [DESIGN.md](DESIGN.md) for the full
design rationale and [docs/anaf-reference/](docs/anaf-reference/) for a compiled local
reference of ANAF's APIs.

## What this is

`anafpy` — typed Python clients for Romania's **ANAF** tax-authority web services,
**e-Factura** (electronic invoicing) and **e-Transport** (goods transport). It is a
**thin, stateless transport client, not invoicing software**: callers bring complete
invoice XML their own system produced, and anafpy validates, files, tracks, and downloads.
Outbound is **XML pass-through** (no invoice composition); received UBL is wrapped in a
friendly **flat read view** (`FlatInvoice`, UBL→flat only) reused for the e-Factura inbox
and the outbound `prepare` preview. Phase 1 is the typed async clients; phase 2 is the
**MCP server** (`anafpy.mcp`, extra `anafpy[mcp]`) exposing the operations as Claude Cowork
skills. The client methods map 1:1 onto MCP tools — discrete operations,
serializable typed inputs/outputs, good docstrings.

Python **3.12+** (test 3.12 and 3.13). Built on **httpx** and **Pydantic v2**.

## Commands

```bash
uv sync --all-extras                 # set up env with all dev dependency groups
uv run pytest -q                     # tests (respx-mocked, credential-free)
uv run pytest tests/test_auth.py     # one file
uv run ruff check . && uv run ruff format --check .
uv run mypy                          # strict
```

Run the MCP server (host-side, where the `anafpy auth login` token store lives):

```bash
ANAFPY_CLIENT_ID=... ANAFPY_CLIENT_SECRET=... ANAFPY_CIF=... \
  uv run python -m anafpy.mcp        # stdio; or the `anafpy-mcp` console script
```

Config is env-only — `anafpy.mcp.config.ServerConfig` is a `pydantic-settings`
`BaseSettings` (use `ServerConfig.from_env()` for a friendly `AnafConfigError`):
`ANAFPY_CLIENT_ID`,
`ANAFPY_CLIENT_SECRET` (required), `ANAFPY_TOKEN_STORE` (default `~/.anafpy/tokens.json`),
`ANAFPY_ENV` (`test`/`prod`), `ANAFPY_CIF` (default fiscal code), `ANAFPY_DOCS_DIR`
(reference resources, defaults to the repo `docs/anaf-reference/`).

Codegen (only when re-vendoring XSDs — see below):

```bash
uv run python scripts/generate_ubl.py
uv run python scripts/generate_etransport.py
```

All three gates (pytest / ruff / mypy --strict) are currently green and must stay green.

## Layout

```
src/anafpy/
  exceptions.py          # AnafError hierarchy (see "Error model")
  _transport/base.py     # Environment, Service, service_base_url — shared host/path logic
  auth/                  # OAuth2 layer: models, store, oauth, provider, callback
  cli/main.py            # `anafpy auth login|status`
  efactura/
    ubl/                 # GENERATED UBL 2.1 models (xsdata-pydantic) — do not hand-edit
    client.py            # EFacturaClient (async)
    models.py            # value types (UploadResult, MessageStatus, ...) + FlatInvoice read view + UBL→flat reader
    __init__.py          # re-exports Invoice, CreditNote from ubl.maindoc
  etransport/
    schema/              # GENERATED e-Transport XSD models — do not hand-edit
    client.py            # ETransportClient (async)
    models.py            # value types + FlatTransport read view + reader
  mcp/                   # MCP server (extra: anafpy[mcp]) — phase 2
    config.py            # ServerConfig.from_env (creds, store path, env, default CIF)
    context.py           # AppContext: TokenProvider + lazy clients + token ledger; auth_status
    models.py            # XML pass-through inputs (no authoring); reuses the client flat read view
    documents.py         # resolve XML input -> bytes; parse bytes -> client flat read view
    tokens.py            # HMAC confirmation tokens for two-step gated mutations
    server.py            # FastMCP server: tools + resources; `create_server`, `main`
    __main__.py          # `python -m anafpy.mcp` (stdio)
schemas/                 # vendored XSDs (git-tracked, NOT shipped in the wheel)
scripts/                 # codegen scripts
docs/anaf-reference/     # compiled ANAF API reference (oauth/efactura/etransport/public)
tests/                   # respx-mocked unit tests
```

## Architecture & conventions

- **Both services share one host** `api.anaf.ro`, differing only by path prefix
  (`FCTEL/rest` vs `ETRANSPORT/ws/v1`) and `test`/`prod` segment. All of that lives in
  [_transport/base.py](src/anafpy/_transport/base.py); clients take an `environment`.
- **Auth is a separate layer.** Clients receive a `TokenProvider` and drive httpx via
  the `AnafAuth` (`httpx.Auth`) class, which handles transparent token refresh. The
  qualified-certificate step happens only in the interactive `anafpy auth login` browser
  flow; code-exchange and refresh are headless. Don't add cert/mTLS handling to clients.
- **Clients are async**, own their `httpx.AsyncClient` (unless one is injected), and are
  async context managers (`async with EFacturaClient(...) as c:`).
- **Discrete methods do NO transport retry** — one call, one result-or-raise — so the
  non-idempotent `upload` POST is never silently repeated. Consumers bring their own
  retry. `tenacity` is used in exactly one place: the `upload_and_wait` poll loop, which
  retries on the *business* processing state, not on transport errors.
- **Module style**: `from __future__ import annotations`, explicit `__all__`, module +
  class docstrings, Google-style docstring sections. Line length 88. Keep new code in the
  voice of the surrounding files.

## MCP server (`anafpy.mcp`)

- **Local stdio connector built on the phase-1 clients.** `create_server(config)`
  returns a `FastMCP`; `AppContext` owns one `TokenProvider` + lazily-built clients and
  closes them in the server lifespan. The server reads the existing token store and
  refreshes headlessly — it never drives the cert/browser step (that stays the CLI).
- **Outbound filing is XML pass-through only.** The tool input is the complete UBL /
  e-Transport XML the caller's invoicing software exported (`UblXmlInput` /
  `EtransportXmlInput` in `mcp/models.py`) — the MCP layer does **not** compose invoices,
  and must never reuse the generated UBL / e-Transport schema models as tool input.
  `prepare` parses the supplied XML with the shared client-layer **UBL→flat reader** into a
  `FlatInvoice` read view to build the preview; there is no flat→XML write mapping.
- **`FlatInvoice` / `FlatTransport` are a read view, not an authoring surface.** Defined at
  the **client layer** ([efactura/models.py](src/anafpy/efactura/models.py),
  [etransport/models.py](src/anafpy/etransport/models.py)) and produced *from* UBL by
  `read_flat_invoice` / `read_flat_transport` (UBL→flat only). They back three things:
  `DownloadedMessage.view` (`download` tier 3), the e-Factura inbox, and the `prepare`
  preview. The view is lossy by design — raw bytes + full UBL stay authoritative — and
  carries `complete` / `dropped_fields` when it can't represent something. There is no
  flat→UBL path; do not add one.
- **Read-first, two-step gated mutations.** Read-only tools (`*_list*`, `*_status`,
  `*_download`, `*_lookup`, `efactura_validate`, `auth_status`) are annotated
  `readOnlyHint` and freely callable. Filing is split `*_prepare*` → `*_submit*`: prepare
  parses the XML for a preview and returns an HMAC **confirmation token**
  (`mcp/tokens.py`) bound to the exact XML bytes, the CIF, and (e-Factura) the upload
  standard; submit requires that token (same document, same CIF) **and** `confirm=True`,
  and each token is **single-use** (`TokenLedger`) so a non-idempotent upload is never
  repeated on one approval. Don't collapse this into a `dry_run` bool.
- **Validation is ANAF's, not local.** `efactura_validate` calls the server-side
  `validare` endpoint via `EFacturaClient.validate_remote` (authoritative by
  definition); e-Transport has no standalone validator — ANAF validates on upload.
  There is deliberately **no local rule engine** (a Schematron/saxonche extra existed
  and was removed 2026-07-02); prepare never blocks on validation — the human review +
  ANAF's verdict are the gates. Don't reintroduce local validation.

## Error model (important)

Hybrid, per design — do not collapse it:

- **Exceptions** (`AnafError` → `AnafAuthError`, `AnafTransportError`/`AnafResponseError`,
  `AnafRateLimitError`, `AnafConfigError`) are for transport / auth / programming errors.
  HTTP 429 raises `AnafRateLimitError` exposing `retry_after`; the client does **not**
  auto-back-off.
- **Business outcomes** (e-Factura `nok`/`REJECTED`, upload rejections with BR-RO
  findings) are returned as **typed values** (e.g. `UploadResult.accepted is False`,
  `MessageStatus.state`), never raised.
- **Listing** (`list_messages` / `list_notifications`) is the one place a 200-with-error-note
  is split: ANAF overloads the note (e-Factura: `eroare`; e-Transport: `Errors[].errorMessage`)
  for both "no results" and real errors, so a no-results note yields an **empty iterator**
  while a genuine list error **raises `AnafResponseError`** (`status_code=200`). The
  classifier is `_transport.base.is_empty_result_message`.

## Generated code — do not hand-edit

`src/anafpy/efactura/ubl/` and `src/anafpy/etransport/schema/` are generated by the
`scripts/generate_*.py` scripts from vendored XSDs in `schemas/`. They are committed as
source but excluded from ruff and mypy (see `extend-exclude` / `exclude` in
[pyproject.toml](pyproject.toml)). To change them, edit the script / re-vendor the XSD
and regenerate; never edit the output by hand. Note: `xsdata[cli]` is pinned `<25` — the
`xsdata-pydantic` plugin targets the 24.x line and newer core emits invalid fields.

Public UBL entry points: `from anafpy.efactura import Invoice, CreditNote`.

## ANAF response formats

Response schemas come from ANAF's official per-endpoint **swagger presentations**
(vendored 2026-07-02 under `docs/anaf-reference/_sources/{efactura,etransport}-swagger/`
and folded into `docs/anaf-reference/*/api.md`) — the API PDFs cover URLs/params only.
Still not confirmed against a live TEST call. When touching parsing code, treat the doc
as the source of truth and prefer being explicit over silently returning empty results.

## Conventions for changes

- Keep `pytest`, `ruff`, and `mypy --strict` green; add/extend respx tests for client
  behavior changes (upload→poll→download, `nok` path, 401-refresh, 429 surfacing).
- **Keep the docs in sync with the change.** When a change alters the public surface,
  status, layout, or conventions, update the affected docs in the same change:
  [README.md](README.md) (what works / usage / install), this `CLAUDE.md` (layout,
  commands, conventions), [DESIGN.md](DESIGN.md) (design decisions), and
  `docs/anaf-reference/` (only when ANAF API facts change — keep its provenance
  frontmatter intact). Don't let docs drift behind the code.
- Don't commit, push, or create branches/PRs unless asked.
- There is no git remote yet and no CI workflow yet (both are planned, not done).
