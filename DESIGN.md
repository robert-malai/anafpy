# anafpy — Design

> Canonical design reference for **anafpy**, a Python package for Romania's ANAF
> tax-authority services (e-Factura + e-Transport), with a later MCP server that
> exposes the functionality as Cowork skills.
>
> Status: design agreed 2026-06-28. This document is the spec we build from.
> PyPI/import name: **`anafpy`** (the working label "pyanaf" was already taken on PyPI).

## 1. Goals & scope

- **Phase 1 — typed clients** for **e-Factura** and **e-Transport** (both use ANAF
  OAuth2 + a qualified digital certificate, XML payloads).
- **Phase 2 — a local MCP server** wrapping the clients, exposing operations as
  skills/tools for Claude Cowork. *(Implemented — see §7.)*
- **Local ANAF API reference docs**, compiled from ANAF's scattered online sources.
- General requirements: **Python 3.12+**, **httpx**, **Pydantic v2**.

Out of scope (for now): the public CUI/VAT lookup web service; SPV; e-TVA; CII syntax;
e-Transport API v1.

## 2. Cross-cutting architecture

- **Async is the source of truth; a sync facade is generated via `unasync`.**
  The MCP server (async) drives the async core; batch/script users get sync.
- **Single distribution** `anafpy` with optional extras (not a multi-package repo):
  - runtime: `httpx`, `pydantic`, `xsdata-pydantic`, `tenacity`
  - `anafpy[validation]` → `saxonche` (local Schematron)
  - `anafpy[mcp]` → MCP SDK
  - `anafpy[cli]`
- **`src/` layout** (ships generated code + vendored XSD/Schematron as package data).

```
src/anafpy/
  _transport/      # shared httpx layer; per-service base URL; env (test/prod)
  auth/            # TokenProvider, TokenStore, OAuth bootstrap, callback listener
  efactura/
    ubl/           # generated UBL models (Invoice + CreditNote closure)
    client.py
    schematron/    # vendored CIUS-RO .sch/.xsl (versioned)
  etransport/
    schema/        # generated models from ANAF e-Transport XSD (v2)
    client.py
    schematron/    # vendored e-Transport .sch (versioned)
  cli/             # `anafpy auth login`, etc.
  mcp/             # MCP server (extra: anafpy[mcp])
    models.py      # curated flat skill models
    mapping.py     # curated <-> UBL converters
docs/anaf-reference/   # agent-compiled local reference (+ _sources/)
```

## 3. Authentication (shared)

ANAF OAuth2, Authorization Code grant. Endpoints:
`https://logincert.anaf.ro/anaf-oauth2/v1/{authorize,token,revoke}`.

- The **`authorize`** step happens in the **user's browser**, authenticating with a
  **qualified digital certificate (USB/PKCS#11)** over mutual TLS. This step is
  inherently host-side and human-driven; no library can drive it.
- Token lifetimes: **access ~90 days, refresh ~365 days**. The certificate is only
  needed for the interactive browser `authorize` step — **not** for code exchange,
  refresh, or routine API calls. Verified 2026-06-28: the `/token` endpoint accepts a
  plain HTTPS POST with no client cert and returns a standard OAuth error
  (`invalid_client`), i.e. no mutual-TLS there. Consequence: an unattended runtime
  (incl. the Docker container) can refresh for the full ~365-day refresh window
  without the cert; re-bootstrap is needed only ~once a year (or on revocation).
- **Callback URL does not need a public server**; `https://localhost:PORT/callback`
  is registered and works (only the user's browser hits it).

Design (layered):

- Core depends on an abstract **`TokenProvider`**.
- Ship a batteries-included bootstrap: authorize-URL builder, **localhost callback
  listener**, code→token exchange, file-backed **`TokenStore`**, **transparent
  refresh** (incl. refresh-on-401 — this stays in the client; it's credential
  management, not network retry).
- **`anafpy auth login`** runs host-side (browser + cert). The MCP server consumes
  the token store and auto-refreshes.

### Deployment

- The MCP server is a **local stdio connector**, launched host-side by Claude Desktop
  and bridged into Cowork. A remote/hosted server can't drive the USB cert and would
  make us custodian of users' ANAF tokens — avoid.
- **Docker is optional** (for dependency control). Token store mounts as a RW volume;
  the OAuth callback works in-container via `-p` port mapping. The server must also
  run as `python -m anafpy.mcp`.
- Cowork/Claude's built-in connector OAuth (Protected Resource Metadata → OAuth 2.1 +
  PKCE) **cannot** drive ANAF auth: it's remote-only and has no client-certificate
  mutual-TLS support. Confirms the host-side CLI approach.

## 4. e-Factura

- Format: **UBL 2.1 + CIUS-RO** (`CustomizationID =
  urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1`). **UBL
  only** (no CII).
- **Models**: generate Pydantic v2 from the **OASIS UBL 2.1 XSDs** with
  **`xsdata-pydantic`**, scoped to the **`UBL-Invoice` + `UBL-CreditNote` roots**
  (their transitive closure only — not the ~80 other UBL document types). Vendored
  XSDs + a regeneration script. The **client speaks these UBL models** internally and
  as its public surface.
- **Serialization**: no marshmallow. UBL ⇄ XML via `xsdata-pydantic`'s
  `XmlParser`/`XmlSerializer` (zero serializer code). The only hand-written piece is
  the curated⇄UBL mapping (MCP layer).

### Operations (option C: discrete primary + optional orchestration)

- Discrete 1:1 methods are the **primary** surface (and the future MCP tools):
  `upload`, `get_status`, `download`, `list_messages`, plus XML→PDF conversion.
- Optional `upload_and_wait(...)` convenience polls until terminal state.
- Flow: `upload` → `id_încărcare`; poll `stareMesaj` (`în prelucrare` → `ok`/`nok`);
  `descărcare` → ZIP (signed invoice + ANAF signature).

### Retries & errors

- **The client does no transport retry** — single transparent calls (avoids
  duplicate-`upload`, a non-idempotent POST). Consumers bring their own retry.
  On 429 the client raises `AnafRateLimitError` exposing `retry_after`.
- **`tenacity` is used in exactly one place**: the `upload_and_wait` poll loop
  (`AsyncRetrying` + `retry_if_result(still_processing)` + `wait_exponential_jitter` +
  `stop_after_delay(timeout)`).
- **Hybrid error model**: exceptions for transport/auth/programming errors
  (`AnafError` base → `AnafAuthError`, `AnafRateLimitError`, `AnafTransportError`, …);
  **business outcomes** (`nok` + BR-RO findings) are **typed return values**, sharing
  one `ValidationFinding` shape with the local validator.

### Download

- `download` returns a **raw-preserving `DownloadedMessage`**: raw ZIP bytes + raw
  signed-invoice XML bytes (the legally valid artifact, archived ~10 years) + a
  lazily-parsed `ubl.Invoice` + signature. Never parse-only.

### Validation

- **Local Schematron pre-validation from the start**, as opt-in `anafpy[validation]`.
- A `Validator` protocol in core; a `SchematronValidator` in the extra.
- **Vendor** ANAF's CIUS-RO artifacts (current **v1.0.9**, 2024-06-05) — EN 16931 +
  code lists + BR-RO — and bump per ANAF release.
- Runtime: EN 16931 Schematron is **XSLT 2.0**, so `lxml` won't do → **`saxonche`**.
  Apply XSLT → SVRL → structured findings (BR-RO id + message).
- **Local pass is never authoritative** — ANAF decides (drift risk). It's a fast
  pre-filter, especially valuable for the conversational MCP UX.

## 5. e-Transport

Mirrors e-Factura, with differences (some corrected after compiling the 29.07.2024 API
doc — see `docs/anaf-reference/etransport/api.md`):

- Same OAuth2; operations: `upload` (→ UIT + `index_incarcare`), `stareMesaj`,
  `lista` (days 1–60 + CIF), `info` (transporter lookup). Same discrete-methods +
  `upload_and_wait` + hybrid errors. Its own Schematron (currently **v2.0.2**).
- **Same OAuth host as e-Factura — `api.anaf.ro/{prod,test}`** (NOT a different host;
  `webserviceapl.anaf.ro` is only the cert-direct mode we don't use). The per-service
  difference is the **path prefix** (`/ETRANSPORT/ws/v1/` vs `/FCTEL/rest/`) → shared
  `_transport` varies the path prefix, not the host.
- **No `descarcare`/ZIP download** (unlike e-Factura): the UIT + signed content come
  back at upload, and state is read via `lista`/`stareMesaj`. So e-Transport does NOT
  reuse `DownloadedMessage`.
- Upload body is **`application/xml`** (e-Factura upload uses `text/plain`).
- Path segment `standard` = **`ETRANSP`**; data-schema **`versiune=2`** appended in the
  v2 upload form (`/upload/ETRANSP/{cif}/2`).
- **Proprietary ANAF XSD** (`schema_ETR_v2_20230126.xsd`, not UBL) → generate via
  `xsdata-pydantic` into `etransport/schema/`.

## 6. Local ANAF reference docs

- A version-pinned local reference *about ANAF*, mirrored from PDFs/HTML/XSD/Schematron.
- **Agent-driven (LLM) compilation** — reconcile scattered sources into coherent
  Markdown. Process: author now as committed, human-reviewed artifacts + capture a
  repeatable regeneration procedure; automate later if worth it.
- Guardrails (tax spec → correctness critical):
  - **Preserve raw sources verbatim** under `docs/anaf-reference/_sources/`; XSD/
    Schematron never LLM-rewritten.
  - **Per-section provenance** (cite the source per claim).
  - **Frontmatter** on every file: title, service, `sources[]` (url, title,
    source_revision, retrieved), compiled, compiled_by, last_verified,
    `status: draft|reviewed`.
  - Keep **original Romanian** (+ English index). Organize by service.

## 7. MCP server (phase 2)

> **Implemented** in `src/anafpy/mcp/` (extra `anafpy[mcp]`): `python -m anafpy.mcp`.
> 13 tools (`auth_status`, e-Factura/e-Transport read-only + two-step gated filing) and
> the compiled reference as resources. Common-case flat→UBL/e-Transport mapping +
> XML pass-through; advanced flat fields grow on demand.

- Local stdio connector built on the phase-1 clients. The MCP layer owns its own
  curated, flat, skill-friendly models (not in the client).
- **Safety: read-first, two-step gated mutations.** Read-only skills (status, list,
  download, **validate**) are freely callable. Mutating skills (`submit_invoice`,
  `create_transport`) are two-step: `prepare` returns a preview + local Schematron
  result + a **confirmation token**; `submit` requires that token + explicit human
  confirmation. Mutating tools annotated non-read-only so Cowork prompts.
- **Curated model (tiered)**: a flat `FlatInvoice` (seller, buyer, currency, dates,
  lines, + optional typed advanced fields) is the **LLM authoring surface**, grown on
  demand. **Escape hatch = UBL-XML pass-through** (`{kind:"ubl_xml", xml|path}`) for
  existing ERP/user UBL — not the structured model. The structured full UBL model is
  **library-only** (its JSON Schema is too large/awkward for an LLM to author).
- **ANAF reference exposed as MCP resources** (with draft/Romanian notes) so the skill
  can ground BR-RO explanations and code lists. Prompts deferred.
- **Auth handling**: server reads the token store + transparent refresh; interactive
  login stays the host-side CLI. Expose a read-only **`auth_status`**; all tools fail
  with a clear "run `anafpy auth login`" remediation when unauthenticated.

## 8. Tooling

- **uv** (deps + lockfile), **hatchling** (build), **ruff** (lint+format),
  **mypy `--strict`**, **pytest** + **pytest-asyncio** + **respx**, **pre-commit**.
- **SemVer**, pre-1.0 (`0.x`). Support + test **3.12 and 3.13**.
- **License: Apache-2.0** (explicit patent grant; ship `NOTICE`).
- **CI: GitHub Actions** (lint + type + test matrix; later publish-to-PyPI).
- **Testing (layered)**: respx mock suite as the credential-free CI gate + an opt-in
  `@pytest.mark.integration` live suite against ANAF's TEST env. Three tiers:
  1. golden round-trip on generated UBL models (catch regen/serialization regressions);
  2. Schematron validator corpus (known valid/invalid → expected BR-RO);
  3. client behavior via respx (upload→poll→download, `nok`, 401-refresh, 429).

## 9. Open / deferred items

1. ~~Verify: does `logincert.anaf.ro/token` require client-cert mTLS for
   refresh/exchange?~~ **RESOLVED 2026-06-28: no.** The `/token` endpoint accepts a
   cert-free HTTPS POST and returns a standard OAuth error; refresh/exchange are
   headless. The container runs unattended for the full ~365-day refresh window.
   (A single live refresh during implementation will confirm end-to-end.)
2. **Token-store-at-rest encryption** — default is a plain file on a volume; decide
   whether to encrypt vs rely on OS perms + Cowork keychain for `client_secret`.
3. **CLI surface beyond `auth login`** (e.g. `validate`, `submit`, `status`).
4. **Cowork local-stdio availability** — live ambiguity whether local connectors run
   directly in Cowork vs only Claude Desktop. ANAF's cert forces local execution
   regardless; affects only which surface hosts it. Verify at build time.
5. **Phase-2 MCP prompts** and in-session `begin_login` — deferred by design.
6. **Public CUI/VAT lookup, SPV, e-TVA, CII, e-Transport v1** — out of scope; revisit
   only if needed.
