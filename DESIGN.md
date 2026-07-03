# anafpy — Design

> Canonical design reference for **anafpy**, a Python package for Romania's ANAF
> tax-authority services (e-Factura + e-Transport), with a later MCP server that
> exposes the functionality as Cowork skills.
>
> Status: design agreed 2026-06-28. This document is the spec we build from.
> PyPI/import name: **`anafpy`** (the working label "pyanaf" was already taken on PyPI).

## 1. Goals & scope

anafpy is a **thin, stateless transport client** for ANAF's **e-Factura** and
**e-Transport** services, optimized **MCP/Claude-first**. It is **not** invoice-authoring
software: Romanian law presumes the entity already runs its own invoicing system, and
e-Factura is a *filing endpoint*, not an invoicing app. anafpy moves documents to and from
ANAF; it does not compose them.

- **e-Factura outbound = XML pass-through.** The caller (or Claude) supplies a
  **complete UBL XML**, exported by their invoicing software. anafpy validates it
  against ANAF's server-side `validare`, uploads, polls, and downloads. It never
  builds invoice XML from structured input.
- **e-Transport = full translation to typed models** *(REVISED 2026-07-03; was
  pass-through like e-Factura)*. The pass-through premise doesn't hold for
  e-Transport: there is usually **no upstream software** producing declaration XML
  (firms fill ANAF's web form by hand), the proprietary XSD is **small and fully
  enumerated** (one file; nomenclatures dominate it), and the UIT lifecycle
  operations (delete / confirm / change vehicle) are a UIT plus two-three attributes
  — demanding XML for those is hostile. So anafpy translates the whole schema: the
  flat models are **bidirectional** (author + view) and cover all four operations
  (declaration/correction `FlatTransport`, `FlatDeletion`, `FlatConfirmation`,
  `FlatVehicleChange`; union `FlatSubmission`). XML input remains supported for
  callers who do have it.
- **Read-only inbound (e-Factura only).** List the message inbox (id, type, date,
  counterparty CIF), download the original zip/XML/PDF **as-is**, and parse received UBL
  into a friendly **flat read view** (`FlatInvoice`) for display/triage. e-Transport stays
  outbound + own-declaration status only.
- **`FlatInvoice` is a read view, not an authoring surface.** It is produced *from*
  UBL — the only e-Factura mapping direction is **UBL → flat**. It renders the
  inbound inbox, is intentionally **lossy** (raw
  bytes + full UBL stay authoritative), and carries a `complete` flag +
  `dropped_fields` when it can't represent something. anafpy never goes flat → UBL:
  no invoice composition. The e-Transport flat models are the deliberate exception
  (previous bullet): full-fidelity, both directions, strict validation on authoring
  (XSD patterns/lengths as pydantic constraints; enum fields accept ANAF codes or
  member names and serialize as names).
- **Stateless** beyond the OAuth token store: callers own persistence of upload indices,
  message ids, and statuses. Discrete one-call-one-result methods, no transport retry.

Phases & requirements:

- **Phase 1 — typed async clients** for e-Factura and e-Transport (ANAF OAuth2 + a
  qualified digital certificate, XML payloads). *(Implemented.)*
- **Phase 2 — a local MCP server** wrapping the clients, exposing the operations as Claude
  Cowork skills. *(In progress — see §8.)*
- **Public no-auth services** — `PublicClient` for the registry lookups + financial
  statements on `webservicesp.anaf.ro` (see §6). *(Implemented.)*
- **Local ANAF API reference docs**, compiled from ANAF's scattered online sources.
- **Python 3.12+**, **httpx**, **Pydantic v2**.

Out of scope: invoice composition / structured authoring **of e-Factura UBL**
(e-Transport authoring is in scope — see above); local persistence of documents;
reconciliation / accounting logic; inbound e-Transport; SPV; e-TVA; CII syntax;
e-Transport API v1.

## 2. Cross-cutting architecture

- **Async is the source of truth; a sync facade is generated via `unasync`.**
  The MCP server (async) drives the async core; batch/script users get sync.
- **Single distribution** `anafpy` with optional extras (not a multi-package repo):
  - runtime: `httpx`, `pydantic`, `xsdata-pydantic`, `tenacity`, `pyjwt`
    (unverified `exp` reads only, to schedule token refresh — verification is
    ANAF's job)
  - `anafpy[mcp]` → MCP SDK
  *(an `anafpy[validation]` → `saxonche` extra existed and was removed — see §4
  Validation)*
- **`src/` layout** (ships generated code as package source).

```
src/anafpy/
  _transport/      # shared httpx layer; per-service base URL; env (test/prod)
  auth/            # TokenProvider, TokenStore, OAuth bootstrap, callback listener
  efactura/
    ubl/           # generated UBL models (Invoice + CreditNote closure)
    client.py
    models.py      # value types + FlatInvoice read view + UBL→flat reader
  etransport/
    schema/        # generated models from ANAF e-Transport XSD (v2)
    client.py      # incl. upload_document (flat -> XML -> upload)
    models.py      # value types + bidirectional flat models (4 ops) + read/build/render
  cli/             # `anafpy auth login`, etc.
  mcp/             # MCP server (extra: anafpy[mcp])
    models.py      # UBL XML pass-through inputs + prepared-submission gate
    documents.py   # resolve XML input -> bytes; parse bytes -> client flat models
    nomenclatures.py  # e-Transport code lists from the XSD enums
    server.py      # FastMCP tools + resources; config.py / context.py / tokens.py
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
- **Callback URL does not need a public server** — only the user's browser hits it —
  **but it must be `https://`**: the developer portal rejects `http://` callbacks with
  an HTTP 400 at registration (live-verified 2026-07-02; the F5 APM backend enforces
  the scheme). Register `https://localhost:PORT/callback` (live-verified registrable
  2026-06-28) and capture the code one of three ways: **paste mode** (`--paste`, no
  listener — the user copies the redirect URL off the browser's error page; the
  security baseline, zero external dependencies), a **TLS listener** with a
  user-supplied certificate (`--tls-cert`/`--tls-key`, e.g. self-signed), or the plain
  HTTP listener behind an external TLS terminator. The CLI falls back to paste mode
  when the listener can't start. (Evaluated and rejected: third-party redirect
  bounces — dangling-domain/custody risks; `localhost.direct`-style public-CA
  loopback certs — the distributed cert was found expired since 2025-02, the
  revocation cat-and-mouse makes it structurally unreliable.)

Design (layered):

- Core depends on an abstract **`TokenProvider`**.
- Ship a batteries-included bootstrap: authorize-URL builder, **localhost callback
  listener** (plain HTTP or TLS via `ssl_context`) plus a **paste-mode parser**
  (`parse_redirect_url`), code→token exchange, file-backed **`TokenStore`**,
  **transparent refresh** (incl. refresh-on-401 — this stays in the client; it's
  credential management, not network retry).
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
  `XmlParser`/`XmlSerializer` (zero serializer code). The one hand-written piece is a
  defensive **UBL→flat reader** producing the `FlatInvoice` read view (parties, lines, VAT
  breakdown, totals, dates; `complete`/`dropped_fields` on loss), backing the inbound
  inbox and `download` tier 3. There is **no flat→UBL write mapping**: anafpy
  reads UBL into the flat view, it never composes UBL.

### Operations (option C: discrete primary + optional orchestration)

- Discrete 1:1 methods are the **primary** surface (and the MCP tools): `upload`,
  `get_status`, `download`, `list_messages`, plus XML→PDF conversion.
- Optional `upload_and_wait(...)` convenience polls until terminal state.
- Flow: `upload` → `id_încărcare`; poll `stareMesaj` (`în prelucrare` → `ok`/`nok`);
  `descărcare` → ZIP (signed invoice + ANAF signature).
- **Listing is one async iterator.** `list_messages` (window by `days` **or**
  `start`/`end`) pages `listaMesajePaginatieFactura` under the hood and yields each
  `MessageListItem`; it replaces the old `list_messages` + `list_messages_paged` pair.
  ANAF overloads its `eroare` field for both "no messages" and real errors, so the former
  yields an **empty iterator** and the latter **raises `AnafResponseError`** (wording-matched
  via `is_empty_result_message`; the total-pages field is inferred, so an empty page is the
  real stop). `ETransportClient.list_notifications` mirrors the shape.
- **Inbound**: `list_messages` doubles as the received-invoice inbox; `download` plus the
  UBL→flat reader yields the `FlatInvoice` read view of supplier invoices issued to you.

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

- `download` returns a **raw-preserving `DownloadedMessage`** with three read tiers:
  (1) raw ZIP + raw signed-invoice XML bytes (the legally valid artifact, archived
  ~10 years) + signature; (2) a lazily-parsed full `ubl.Invoice`; (3) the lazily-built
  `FlatInvoice` read view (easy to read; lossy with `complete`/`dropped_fields`). Tier 1 is
  authoritative; never parse-only.

### Validation

**REVISED 2026-07-02: local Schematron dropped; validation is ANAF's server-side
`validare` endpoint** (`EFacturaClient.validate_remote`, `POST /validare/{FACT1|FCN}`).

- The original design shipped an opt-in `anafpy[validation]` extra: vendored CIUS-RO
  Schematron compiled to XSLT 2.0, run via `saxonche`. It was removed because the
  costs outweighed the pre-filter value for a thin transport client:
  - `saxonche` is a heavy native dependency; vendored rule sets drift as ANAF
    revises CIUS-RO (~yearly), and a stale ruleset produces false failures;
  - the MCP `prepare` gate withheld the confirmation token on a local failure —
    inverting "local pass is never authoritative" — while silently skipping the
    check when the extra wasn't installed (gate strictness depended on an extra);
  - ANAF exposes its own validator over HTTP, authoritative by definition.
- e-Factura: `validate_remote` returns an invalid document as a **typed value**
  (`RemoteValidationResult`, findings in `messages`), never an exception.
- e-Transport has no standalone remote validator: the pre-filing check is
  parse + human-reviewed preview; ANAF validates on upload (findings as values).
- Do **not** reintroduce a local rule engine; `prepare` must not block on validation.

## 5. e-Transport

Mirrors e-Factura, with differences (some corrected after compiling the 29.07.2024 API
doc — see `docs/anaf-reference/etransport/api.md`):

- Same OAuth2; operations: `upload` (→ UIT + `index_incarcare`), `stareMesaj`,
  `lista` (days 1–60 + CIF), `info` (transporter lookup). Same discrete-methods +
  `upload_and_wait` + hybrid errors. No standalone validator (ANAF validates on
  upload).
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
- **Structured authoring (ADDED 2026-07-03).** e-Transport is the deliberate
  exception to "outbound = XML pass-through" (§1): the flat models in
  `etransport/models.py` are bidirectional and cover the XSD's four root operations —
  `FlatTransport` (a `notificare`, optionally a correction via `correction_of_uit`),
  `FlatDeletion` (`stergere`), `FlatConfirmation` (`confirmare`), `FlatVehicleChange`
  (`modifVehicul`) — plus the root attributes (`declarant_code`, `declarant_ref`,
  `post_incident`). `build_etransport` composes the wire model (filling
  `cod_declarant` from the upload CIF; a conflicting explicit value raises),
  `render_etransport` serializes, and `ETransportClient.upload_document` does
  compose→upload in one call. Authoring validation is **structural only** (XSD
  patterns, lengths, decimal shapes, exactly-one-of border-point/customs-office/
  address per route end) — business rules stay ANAF's, per §4 Validation. Enum-coded
  fields are typed with the generated XSD enums, accept member **names or ANAF
  codes** on input (plates/UITs are normalized), and serialize as names for readable
  previews. Reading is the same models via `read_flat_transport` — a full
  translation (only the XSD's unused `xs:any` hooks are not carried), so the
  authored document and its preview can never drift. The TEST roundtrip
  (2026-07-02, re-based onto the flat models 2026-07-03) files a declaration
  composed this way.

## 6. Public (no-auth) services

`anafpy.public.PublicClient` wraps ANAF's unauthenticated lookups on
`webservicesp.anaf.ro` (registries + financial statements — see
`docs/anaf-reference/public/api.md`, live-confirmed 2026-07-02). Decisions:

- **A third client, not a mode of the OAuth ones.** Different host, no test/prod
  split, no `TokenProvider`/`environment` — it sits outside `service_base_url`
  (`PUBLIC_HOST` in `_transport/base.py`). Same shape otherwise: async, owns its
  `httpx.AsyncClient`, context-manager, hybrid error model.
- **Client-side pacing (deliberate exception to "no auto-backoff").** ANAF states the
  public host's 1 req/s limit as a usage *rule* ("va fi pedepsită"), not via 429s, so
  the client spaces its own requests (`min_request_interval`, default 1.0 s; `0`
  opts out). Reads are idempotent, so pacing carries none of the repeat-a-POST risk
  that motivated the no-retry stance.
- **Operations**: `lookup_taxpayers` (v9 — VAT, VAT-on-collection, inactive,
  split-VAT, e-Factura register membership in one call), `lookup_efactura_register`,
  `lookup_farmers`, `lookup_cult_entities`, `get_financial_statement`. Registry
  queries are batched CUIs at one as-of date, capped per ANAF (100 / 500). The
  **async job variant** of the taxpayer lookup is deliberately not wrapped: its
  result downloads exactly once and the not-ready response is undocumented.
- **Business-vs-error mapping**: `notFound` CUIs and `registered is False` records
  are values; the e-Factura register's **404-with-`found`/`notFound`-body** is a
  business "not found" (returned), while a non-200 `cod` inside an HTTP 200 envelope
  raises `AnafResponseError`. Membership always reads from the status booleans
  (RegAgric/RegCult return unknown CUIs under `found`).
- **English models over wire names.** The wire mixes casings (`scpTVA`,
  `statusRO_e_Factura`); models expose snake_case English fields with the wire names
  as pydantic aliases, raw bytes retained on every container.
- **Testing (hybrid)**: the respx suite is the gate; an opt-in `live` marker
  (`ANAFPY_LIVE=1`) re-confirms the wire shapes against production — possible here
  precisely because no credentials are needed, but never a CI gate (registry data
  drifts; ANAF punishes hammering).

## 7. Local ANAF reference docs

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

## 8. MCP server (phase 2)

A **local stdio connector** built on the phase-1 clients (extra `anafpy[mcp]`,
`python -m anafpy.mcp`). It exposes the operations as Claude Cowork skills, owns the
XML pass-through tool *inputs* (the friendly flat models come from the client
layer, §4/§5), reads the existing token store, and refreshes headlessly.
*(Implemented: the gated prepare→submit flow for e-Transport, composed
e-Transport filing, the flat previews and the e-Factura inbox, and the compiled
reference as resources.)*

- **No e-Factura filing tools** *(REVISED 2026-07-03; the XML pass-through pair
  `efactura_prepare_invoice`/`efactura_submit_invoice` was implemented, then
  removed)*. There is no MCP use case: outbound UBL comes from third-party
  invoicing software, and that software files with ANAF directly — routing its
  export through a chat-driven MCP gate adds risk without adding value. The MCP
  e-Factura surface is **read-only**: inbox, download, `efactura_validate`
  (`UblXmlInput {xml|path}` now feeds only the validator). `efactura_get_status`
  went with the filing tools — an e-Factura upload id was only ever produced by
  them, and processed invoices surface in the inbox. `EFacturaClient.upload` and
  `get_status` remain the library filing path. If filing tools ever return, they must stay XML
  pass-through: no invoice composition, no flat→UBL mapping (`FlatInvoice` is only
  ever a *read* projection of UBL — never an input).
- **e-Transport outbound = composed from structured fields** (§5; REVISED
  2026-07-03). `etransport_prepare_declaration` takes the client-layer
  `FlatTransport` as tool input; `etransport_prepare_deletion` / `_confirmation` /
  `_vehicle_change` take scalars and build the tiny flat models. Each renders the
  XML via `render_etransport` and returns it in `PreparedSubmission.xml` next to the
  preview (the *read-back* of the rendered bytes, so the human approves exactly what
  will be filed) and the confirmation token (bound to those bytes). The caller
  passes the XML back to the shared `etransport_submit` verbatim — a mangled echo
  fails the token check, never files. `etransport_prepare` (`EtransportXmlInput`)
  stays for ready-made XML; `etransport_nomenclature` (read-only,
  `mcp/nomenclatures.py`) lists the XSD code lists so the model can map "vama
  Nădlac" → `NADLAC` instead of guessing codes.
- **Display names**: every tool carries an English MCP `title` — the human-facing
  name clients show instead of the snake_case `name` — following
  `Service: operation` ("e-Factura: Validate invoice", "e-Transport: Prepare
  declaration", "ANAF Info: Taxpayer lookup" for the public lookups, "ANAF:
  Authentication status" for `auth_status`). One language only: MCP has no title
  localization, and the model never sees titles (it works from `name` +
  `description`), so Romanian conversation quality is unaffected.
- **Safety: read-first, two-step gated filing.** Read-only tools (`*_list*`, `*_status`,
  `*_lookup`, `*_validate`, `auth_status`) are annotated `readOnlyHint` and
  freely callable; `efactura_download` is equally freely callable but annotated
  honestly (`readOnlyHint=False`, idempotent, non-destructive) since it may write
  artifact files at caller-given paths (next bullet). Filing (e-Transport only) is split `etransport_prepare*` →
  `etransport_submit`: `prepare` parses (or composes) the XML into the
  **flat models** to render a preview and
  returns an HMAC **confirmation token** bound to the exact XML bytes plus the submission
  context (CIF); `submit` requires that token (same bytes, same CIF)
  **and** `confirm=True`, and redeems it **single-use** so one approval files at most
  once. Not a `dry_run` bool.
- **Validation is ANAF's own**: `efactura_validate` calls the server-side `validare`
  endpoint (authoritative); `prepare` never blocks on validation — the human review
  and ANAF's verdict are the gates (see §4 Validation for the Schematron reversal).
- **Read-only e-Factura inbox**: `efactura_list_messages` (id, type, date, counterparty
  CIF) → `efactura_download` → the `FlatInvoice` **read view** for
  display/triage, from the same client-layer reader. e-Transport stays outbound +
  `lista`/`stareMesaj`.
- **Binary artifacts: files first, one PDF resource, never context** (decided
  2026-07-03). The model operates on the flat view; the ZIP and PDF are for the
  *human*, and current hosts read resources *into model context* (no save/open
  affordance), so base64 blobs in tool results or resource reads are the wrong
  delivery for batch flows. Since the server is local stdio, its filesystem IS the
  user's: `efactura_download` takes `save_zip_as` (the legally archivable signed
  ZIP) and `save_pdf_as` (ANAF's `transformare` rendering, called with
  `validate=False` — the message was validated at filing — and **best-effort**: a
  non-PDF answer surfaces as `pdf_error`, never fails the download). Caller-given
  full paths, not a directory + naming convention: the agent composes filenames
  from invoice metadata ("`<date> - <partner>.pdf`"). The PDF is additionally the
  stateless resource template `anafmsg://{message_id}/pdf` (fetch + convert on
  read) for hosts that grow real resource UX; there is deliberately **no ZIP
  resource** — a base64 ZIP serves neither the model nor any host UI.
- **Public lookups as `anaf_*` tools** (over `PublicClient`, §6): `anaf_lookup_taxpayers`
  / `anaf_lookup_efactura_register` / `anaf_lookup_farmers` / `anaf_lookup_cult_entities`
  / `anaf_financial_statement`. Read-only, **no auth required** (usable before
  `anafpy auth login`), 1:1 on the client methods; `raw` bytes stay client-side
  (excluded from tool payloads). The counterparty sanity-check before filing lives
  here.
- **ANAF reference exposed as MCP resources** (with draft/Romanian notes) so the skill can
  ground BR-RO explanations and code lists. Prompts deferred.
- **Auth handling**: server reads the token store + transparent refresh; interactive login
  stays the host-side CLI. A read-only **`auth_status`** reports validity; all tools fail
  with a clear "run `anafpy auth login`" remediation when unauthenticated.

## 9. Tooling

- **uv** (deps + lockfile), **hatchling** (build), **ruff** (lint+format),
  **mypy `--strict`**, **pytest** + **pytest-asyncio** + **respx**, **pre-commit**.
- **SemVer**, pre-1.0 (`0.x`). Support + test **3.12 and 3.13**.
- **License: Apache-2.0** (explicit patent grant; ship `NOTICE`).
- **CI: GitHub Actions** (lint + type + test matrix; later publish-to-PyPI).
- **Testing (layered)**: respx mock suite as the credential-free CI gate + an opt-in
  live suite. Two tiers:
  1. golden round-trip on generated UBL models (catch regen/serialization regressions);
  2. client behavior via respx (upload→poll→download, `nok`, 401-refresh, 429).
  The live tier exists today as the `live` marker (`ANAFPY_LIVE=1`) smoke-testing the
  public services (§6) and, since 2026-07-02, the authenticated TEST endpoints
  (`tests/test_oauth_live.py` — read-only list/echo calls; credentials from the
  gitignored repo-root `.env`, token store from `anafpy auth login`).

## 10. Open / deferred items

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
6. ~~Public CUI/VAT lookup~~ **DONE 2026-07-02** (`anafpy.public.PublicClient`, §6;
   exposed as the MCP `anaf_*` lookup tools, §8). **SPV, e-TVA, CII, e-Transport v1**
   remain out of scope; revisit only if needed. Still open within the public family:
   the async job variant of the taxpayer lookup (deliberately unwrapped).
7. ~~Code realignment to thin transport~~ **DONE.** Outbound is XML pass-through (flat→UBL
   mapping removed); `FlatInvoice`/`FlatTransport` are client-layer read views built by a
   single `read_flat_invoice` / `read_flat_transport` (+ `complete` / `dropped_fields`),
   exposed as `download` tier 3 (`DownloadedMessage.view`), the MCP e-Transport
   prepare preview, and
   the e-Factura inbox. All three gates green. **PARTLY REVERSED 2026-07-03 for
   e-Transport only**: its flat models became bidirectional full translations of the
   XSD (§5 Structured authoring) — the read-view-only stance now applies to
   `FlatInvoice` alone.

## 11. Distribution

> Decided 2026-07-02. anafpy is distributed **free and as-is**, for anyone to use.

The package is provided **as-is** under Apache-2.0 — no warranty, no service
obligations. The thin-transport scope of §1 is also the legal posture: anafpy
moves documents, it does not give tax advice, and filing outcomes are the user's
responsibility. The **MCP server is best-effort**: installing it, configuring the
environment, provisioning the OAuth application on ANAF's portal, and holding the
qualified certificate are the user's responsibility.

The MCP server is and stays a **local stdio server**: tool calls run on the
user's machine against the user's own tokens — the zero-custody design of §3
Deployment. Hosted-service code (token custody, multi-tenancy, an OAuth-provider
surface toward Claude) is out of scope.

**Audience bound that no packaging removes:** every user needs a qualified
certificate and their own ANAF OAuth app registration, capping the audience at
people who already deal with ANAF professionally.
