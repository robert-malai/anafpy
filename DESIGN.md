# anafpy — Design

> Canonical design record for **anafpy**, a Python package for Romania's ANAF
> tax-authority services (e-Factura + e-Transport + public no-auth lookups), with an
> MCP server exposing the operations as Claude Cowork skills.
>
> Design agreed 2026-06-28; phase 1 (typed clients) and phase 2 (MCP server) are
> implemented. This document records the decisions and their rationale — including
> reversals — so they are not relitigated. PyPI/import name: **`anafpy`** (the
> working label "pyanaf" was already taken on PyPI).

## 1. Goals & scope

anafpy is a **thin, stateless transport client** for ANAF's **e-Factura** and
**e-Transport** services, optimized **MCP/Claude-first**. It is **not**
invoice-authoring software: Romanian law presumes the entity already runs its own
invoicing system, and e-Factura is a *filing endpoint*, not an invoicing app. anafpy
moves documents to and from ANAF; it does not compose them.

- **e-Factura outbound = XML pass-through.** The caller (or Claude) supplies a
  **complete UBL XML** exported by their invoicing software; anafpy validates it
  against ANAF's server-side `validare`, uploads, polls, and downloads. It never
  builds invoice XML from structured input.
- **e-Transport = full translation to typed models** *(REVISED 2026-07-03; was
  pass-through like e-Factura)*. The pass-through premise doesn't hold here: there
  is usually **no upstream software** producing declaration XML (firms fill ANAF's
  web form by hand), the proprietary XSD is **small and fully enumerated**, and the
  UIT lifecycle operations (delete / confirm / change vehicle) are a UIT plus
  two-three attributes — demanding XML for those is hostile. So the flat models are
  **bidirectional** (author + view) and cover all four operations
  (declaration/correction `FlatTransport`, `FlatDeletion`, `FlatConfirmation`,
  `FlatVehicleChange`; union `FlatSubmission`). XML input remains supported for
  callers who have it.
- **Read-only inbound (e-Factura only).** List the message inbox, download the
  original zip/XML/PDF **as-is**, and parse received UBL into the friendly
  **flat read view** (`FlatInvoice`). e-Transport stays outbound +
  own-declaration status only.
- **`FlatInvoice` is a read view, not an authoring surface.** Produced *from* UBL —
  the only e-Factura mapping direction is **UBL → flat**. Intentionally **lossy**
  (raw bytes + full UBL stay authoritative), with a `complete` flag +
  `dropped_fields` when it can't represent something. anafpy never goes flat → UBL.
  The e-Transport flat models are the deliberate exception (above): full-fidelity,
  both directions, strict field validation on authoring (XSD patterns/lengths as
  pydantic constraints; enum fields accept ANAF codes or member names, serialize as
  names).
- **Stateless** beyond the OAuth token store: callers own persistence of upload
  indices, message ids, and statuses. Discrete one-call-one-result methods, no
  transport retry.

Python **3.12+** (floor set by PEP 695 syntax in the flat models and lookups; dev
pin is 3.13), **httpx**, **Pydantic v2**.

Out of scope: invoice composition / structured authoring **of e-Factura UBL**
(e-Transport authoring is in scope — see above); local persistence of documents;
reconciliation / accounting logic; inbound e-Transport; SPV; e-TVA; CII syntax;
e-Transport API v1; a sync facade *(dropped 2026-07-03 — the consumers that exist
are async: the MCP server and `asyncio.run` scripts; was to be generated via
`unasync`)*.

## 2. Cross-cutting architecture

- **Async only** (see §1 for the dropped sync facade).
- **Single distribution** `anafpy` with optional extras (not a multi-package repo):
  - runtime: `httpx`, `pydantic`, `xsdata-pydantic`, `tenacity`, `pyjwt`
    (unverified `exp` reads only, to schedule token refresh — verification is
    ANAF's job), `keyring` (core since the token-store default flipped, §3)
  - `anafpy[mcp]` → the MCP SDK + `pydantic-settings` (env config) +
    `python-frontmatter` (SKILL.md → prompts)
  - a former `anafpy[validation]` (`saxonche`) extra was removed — see §4 Validation
- **`src/` layout** (ships generated code as package source). The full annotated
  layout lives in CLAUDE.md; in brief:

```
src/anafpy/
  exceptions.py    # AnafError hierarchy
  _transport/      # shared httpx layer; per-service base URL; env (test/prod)
  auth/            # TokenProvider, TokenStore, OAuth bootstrap, callback listener
  efactura/        # generated UBL models (Invoice+CreditNote closure) + client
                   # + FlatInvoice read view / UBL→flat reader
  etransport/      # generated XSD models + client + bidirectional flat models
  public/          # PublicClient: no-auth lookups + financial statements (§6)
  cli/             # `anafpy auth login|status|logout`
  mcp/             # MCP server (extra: anafpy[mcp]) — tools, resources, prompts,
                   # confirmation tokens, nomenclatures, UN/ECE unit codes
skills/            # workflow skills, served by the MCP server as same-name prompts
docs/anaf-reference/   # agent-compiled local reference (+ _sources/)
```

## 3. Authentication (shared)

ANAF OAuth2, Authorization Code grant. Endpoints:
`https://logincert.anaf.ro/anaf-oauth2/v1/{authorize,token,revoke}`.

- The **`authorize`** step happens in the **user's browser**, authenticating with a
  **qualified digital certificate (USB/PKCS#11)** over mutual TLS — inherently
  host-side and human-driven; no library can drive it.
- Token lifetimes: **access ~90 days, refresh ~365 days** (observed lifetimes
  matched on the first real login, 2026-07-02). The certificate is only needed for
  the browser `authorize` step — verified 2026-06-28 that `/token` accepts a
  cert-free HTTPS POST (standard OAuth error, no mutual TLS), so code exchange and
  refresh are headless: an unattended runtime refreshes for the full ~365-day
  window; re-bootstrap is needed ~once a year (or on revocation).
- **Callback URL must be `https://`** — the developer portal rejects `http://`
  callbacks with an HTTP 400 at registration (live-verified 2026-07-02; F5 APM
  enforces the scheme) — but needs no public server: only the user's browser hits
  it. Register `https://localhost:PORT/callback` (live-verified registrable
  2026-06-28) and capture the code one of three ways: **paste mode** (`--paste`,
  no listener, the security baseline), a **TLS listener** with a user-supplied
  certificate (`--tls-cert`/`--tls-key`), or the plain HTTP listener behind an
  external TLS terminator; the CLI falls back to paste when the listener can't
  start. A denied cert step surfaces as an `access_denied` error redirect, raised
  cleanly. (Evaluated and rejected: third-party redirect bounces —
  dangling-domain/custody risks; `localhost.direct`-style public-CA loopback certs
  — the distributed cert was found expired since 2025-02; structurally unreliable.)
- **Layered design**: core depends on an abstract **`TokenProvider`**; a
  batteries-included bootstrap ships the authorize-URL builder, callback listener,
  paste parser (`parse_redirect_url`), code→token exchange, `TokenStore`, and
  **transparent refresh** incl. refresh-on-401 (credential management, not network
  retry — it stays in the client).
- **Login CSRF: a per-attempt OAuth `state`** (added 2026-07-04). `auth login`
  binds a random `state` into the authorize URL; the listener answers 400 (and
  keeps waiting) for redirects that don't echo it, and the paste parser rejects a
  URL whose `state` is missing or different. A pasted **bare code** is exempt (a
  deliberate manual extraction, and the escape hatch if ANAF ever stops echoing
  `state` — its reference flow leaves `state` empty but echoes it back). No PKCE:
  ANAF's flow doesn't offer it; the client is confidential (secret-authenticated)
  anyway.
- **Token store**: `TokenStore` protocol (`load`/`save`/`clear`).
  **`KeyringTokenStore` is the default backend** (added 2026-07-03, made default
  2026-07-05 — which promoted `keyring` from an extra to a **core dependency**; a
  default that may not be installed would be self-contradictory). One
  implementation covers macOS Keychain, Windows Credential Manager, Linux Secret
  Service/KWallet. Windows caps a credential blob at 2560 bytes (< one ANAF JWT),
  so the store splits the token set across continuation entries (`tokens#1`, ...)
  there and prunes stale ones on rewrite (an MSAL-style DPAPI-encrypted file was
  rejected as a second platform-specific code path). `FileTokenStore` (plain JSON)
  stays the opt-out for Docker/headless hosts; selected via
  `ANAFPY_TOKEN_STORE_BACKEND` / `--store-backend`. The test suite installs an
  in-memory fake keyring autouse so tests never touch a real credential store.
- **`anafpy auth login`** runs host-side (browser + cert). The MCP server consumes
  the token store and auto-refreshes; it never drives the interactive step.
- **`anafpy auth logout` is purely local** (added 2026-07-05): it clears the token
  store and makes **no network call** — without the refresh token no new access
  tokens can be minted. A best-effort RFC 7009 call to `/revoke` was built and
  removed the same day: a live probe (2026-07-05) showed `/revoke` is **not
  reachable headlessly** — ANAF's F5 gateway 302s to its certificate login wall,
  byte-identical to a nonexistent path, while `/token` answers OAuth JSON directly
  (see the oauth reference §3) — and shipping a call that always fails only trains
  users to ignore its warning. `REVOKE_URL` stays in `auth/oauth.py` as a
  documented fact; **don't re-add a revoke call unless ANAF routes the endpoint.**
  A corrupt store is cleared rather than blocking on the parse error. Deliberately
  no MCP logout tool — destroying credentials stays a human, CLI-side act.

### Deployment

- The MCP server is a **local stdio connector**, launched host-side by Claude
  Desktop and bridged into Cowork. A remote/hosted server can't drive the USB cert
  and would make us custodian of users' ANAF tokens — avoid (§11 records why a
  hosted shape is out of scope).
- **Docker is optional** (dependency control): token store as a RW volume, OAuth
  callback via `-p` port mapping; the server must also run as `python -m anafpy.mcp`.
- Claude's built-in connector OAuth (Protected Resource Metadata → OAuth 2.1 +
  PKCE) **cannot** drive ANAF auth: remote-only, no client-certificate mutual TLS.
  Confirms the host-side CLI approach.

## 4. e-Factura

- Format: **UBL 2.1 + CIUS-RO** (`CustomizationID =
  urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1`).
  **UBL only** (no CII).
- **Models**: Pydantic v2 generated from the **OASIS UBL 2.1 XSDs** with
  **`xsdata-pydantic`**, scoped to the **`UBL-Invoice` + `UBL-CreditNote`**
  transitive closure (not the ~80 other UBL document types). Vendored XSDs + a
  regeneration script. The client speaks these UBL models internally and publicly.
- **Serialization**: `xsdata-pydantic`'s `XmlParser`/`XmlSerializer` — zero
  serializer code (no marshmallow). The one hand-written piece is the defensive
  **UBL→flat reader** producing `FlatInvoice` (parties, lines, VAT breakdown,
  totals, dates; `complete`/`dropped_fields` on loss). **No flat→UBL write
  mapping, ever.**

### Operations (discrete primary + optional orchestration)

- Discrete 1:1 methods are the **primary** surface (and the MCP tools): `upload`,
  `get_status`, `download`, `list_messages`, plus XML→PDF conversion; optional
  `upload_and_wait` polls to a terminal state.
- Flow: `upload` → `id_încărcare`; poll `stareMesaj` (`în prelucrare` →
  `ok`/`nok`); `descărcare` → ZIP (signed invoice + ANAF signature).
- **Listing is one async iterator**: `list_messages` (window by `days` **or**
  `start`/`end`) pages `listaMesajePaginatieFactura` and yields `MessageListItem`s.
  ANAF overloads its `eroare` field for both "no messages" and real errors: the
  former yields an **empty iterator**, the latter **raises `AnafResponseError`**
  (classified by `is_empty_result_message`; the total-pages field is inferred, so
  an empty page is the real stop). `ETransportClient.list_notifications` mirrors
  the shape.
- **Inbound**: `list_messages` doubles as the received-invoice inbox; `download` +
  the UBL→flat reader yield the `FlatInvoice` view of supplier invoices.

### Retries & errors

- **The client does no transport retry** — single transparent calls (never repeat
  the non-idempotent `upload` POST). Consumers bring their own retry. On 429 the
  client raises `AnafRateLimitError` exposing `retry_after`; no auto-backoff.
- **`tenacity` is used in exactly one place**: the `upload_and_wait` poll loop
  (retry on the *business* processing state, not transport errors).
- **Hybrid error model**: exceptions for transport/auth/programming errors
  (`AnafError` → `AnafAuthError`, `AnafRateLimitError`, `AnafTransportError`, …);
  **business outcomes** (`nok`, BR-RO findings) are **typed return values**
  (`MessageStatus`, `RemoteValidationResult`, …), never exceptions.

### Download

- `download` returns a **raw-preserving `DownloadedMessage`** with three tiers:
  (1) raw ZIP + raw signed-invoice XML bytes (the legally valid artifact, archived
  ~10 years) + signature; (2) lazily-parsed full `ubl.Invoice`; (3) the lazily-built
  `FlatInvoice` read view. Tier 1 is authoritative; never parse-only.

### Validation

**REVISED 2026-07-02: local Schematron dropped; validation is ANAF's server-side
`validare` endpoint** (`PublicClient.validate_invoice`, `POST /validare/{FACT1|FCN}`;
moved from `EFacturaClient` 2026-07-04 — `validare`/`transformare` are public,
no-auth, **prod-only** services on `webservicesp.anaf.ro`, exactly `PublicClient`'s
host, so validation needs no OAuth credentials at all).

- The original `anafpy[validation]` extra (vendored CIUS-RO Schematron compiled to
  XSLT 2.0, run via `saxonche`) was removed: a heavy native dependency; vendored
  rulesets drift as ANAF revises CIUS-RO (~yearly), producing false failures; the
  MCP `prepare` gate's strictness ended up depending on whether an optional extra
  was installed — while ANAF exposes its own authoritative validator over HTTP.
- Invalid documents are **typed values** (`RemoteValidationResult`, findings in
  `messages`), never exceptions. e-Transport has no standalone remote validator:
  the pre-filing check is parse + human-reviewed preview; ANAF validates on upload.
- **Do not reintroduce a local rule engine; `prepare` must not block on validation.**

## 5. e-Transport

Mirrors e-Factura, with differences (see `docs/anaf-reference/etransport/api.md`):

- Same OAuth2; operations: `upload` (→ UIT + `index_incarcare`), `stareMesaj`,
  `lista` (days 1–60 + CIF), `info` (transporter lookup). Same discrete methods +
  `upload_and_wait` + hybrid errors. No standalone validator.
- **Same OAuth host as e-Factura — `api.anaf.ro/{prod,test}`** (NOT a different
  host; `webserviceapl.anaf.ro` is only the cert-direct mode we don't use). The
  per-service difference is the **path prefix** (`/ETRANSPORT/ws/v1/` vs
  `/FCTEL/rest/`) → shared `_transport` varies the prefix, not the host.
- **No `descarcare`/ZIP download**: the UIT + signed content come back at upload;
  state is read via `lista`/`stareMesaj`. e-Transport does NOT reuse
  `DownloadedMessage`.
- Upload body is **`application/xml`** (e-Factura upload uses `text/plain`). Path
  segment `standard` = **`ETRANSP`**; data-schema **`versiune=2`** in the v2 upload
  form (`/upload/ETRANSP/{cif}/2`).
- **Proprietary ANAF XSD** (`schema_ETR_v2_20230126.xsd`, not UBL) → generated via
  `xsdata-pydantic` into `etransport/schema/`.
- **Structured authoring (ADDED 2026-07-03)** — the deliberate exception to
  "outbound = XML pass-through" (§1). The flat models in `etransport/models.py`
  are bidirectional and cover the XSD's four root operations — `FlatTransport`
  (a `notificare`, optionally a correction via `correction_of_uit`), `FlatDeletion`
  (`stergere`), `FlatConfirmation` (`confirmare`), `FlatVehicleChange`
  (`modifVehicul`) — plus the root attributes (`declarant_code`, `declarant_ref`,
  `post_incident`). `build_etransport` composes the wire model (filling
  `cod_declarant` from the upload CIF; a conflicting explicit value raises),
  `render_etransport` serializes, and `ETransportClient.upload_document` does
  compose→upload in one call. Authoring validation is **field-level shape only**:
  the XSD's patterns/lengths/decimal shapes, tightened (2026-07-03) by the
  *unconditional* rules of ANAF's e-Transport Schematron (vendored under
  `docs/anaf-reference/_sources/`) — UIT check digits (BR-019), gross ≥ net per
  goods line (BR-020), no leading zero in the declarant code (BR-002), min-2-char
  locality/street (BR-214/215), a note required on an 'ALTELE' document (BR-026),
  the withdrawn `AN` country code rejected (BR-CL-001), exactly-one-of
  border-point/customs-office/address per route end (BR-210/211). Those rules
  reject with certainty, so failing at construction is data hygiene, not a rule
  engine. The Schematron's *operation-type conditional* rules (partner-country,
  purpose-code, route-endpoint matrices) stay ANAF's to enforce on upload, per §4
  Validation — they surface only as field descriptions (which the MCP tool schemas
  carry to the composing model). Enum-coded fields are typed with the generated
  XSD enums, accept member **names or ANAF codes** (plates/UITs normalized), and
  serialize as names for readable previews. Reading is the same models via
  `read_flat_transport` — a full translation (only the XSD's unused `xs:any` hooks
  are not carried), so the authored document and its preview can never drift.

## 6. Public (no-auth) services

`anafpy.public.PublicClient` wraps ANAF's unauthenticated lookups on
`webservicesp.anaf.ro` (registries + financial statements — see
`docs/anaf-reference/public/api.md`, live-confirmed 2026-07-02). Decisions:

- **A third client, not a mode of the OAuth ones.** Different host, no test/prod
  split, no `TokenProvider`/`environment` — it sits outside `service_base_url`
  (`PUBLIC_HOST` in `_transport/base.py`). Same shape otherwise: async, owns its
  `httpx.AsyncClient`, context-manager, hybrid error model.
- **Client-side pacing (deliberate exception to "no auto-backoff").** ANAF states
  the public host's 1 req/s limit as a usage *rule* ("va fi pedepsită"), not via
  429s, so the client spaces its own requests (`min_request_interval`, default
  1.0 s; `0` opts out). Reads are idempotent, so pacing carries none of the
  repeat-a-POST risk that motivated the no-retry stance.
- **Operations**: `lookup_taxpayers` (v9 — VAT, VAT-on-collection, inactive,
  split-VAT, e-Factura register membership in one call),
  `lookup_efactura_register`, `lookup_farmers`, `lookup_cult_entities`,
  `get_financial_statement`. Registry queries are batched CUIs at one as-of date,
  capped per ANAF (100 / 500). The **async job variant** of the taxpayer lookup is
  deliberately not wrapped: its result downloads exactly once and the not-ready
  response is undocumented.
- **Business-vs-error mapping**: `notFound` CUIs and `registered is False` records
  are values; the e-Factura register's **404-with-`found`/`notFound`-body** is a
  business "not found" (returned), while a non-200 `cod` inside an HTTP 200
  envelope raises `AnafResponseError`. Membership always reads from the status
  booleans (RegAgric/RegCult return unknown CUIs under `found`).
- **English models over wire names**: snake_case English fields with the wire names
  as pydantic aliases; raw bytes retained on every container.
- **Testing (hybrid)**: the respx suite is the gate; an opt-in `live` marker
  (`ANAFPY_LIVE=1`) re-confirms wire shapes against production — possible here
  precisely because no credentials are needed, but never a CI gate (registry data
  drifts; ANAF punishes hammering).

## 7. Local ANAF reference docs

- A version-pinned local reference *about ANAF*, mirrored from
  PDFs/HTML/XSD/Schematron.
- **Agent-driven (LLM) compilation** — reconcile scattered sources into coherent
  Markdown, authored as committed, human-reviewed artifacts with a repeatable
  regeneration procedure; automate later if worth it.
- Guardrails (tax spec → correctness critical):
  - **Preserve raw sources verbatim** under `docs/anaf-reference/_sources/`;
    XSD/Schematron never LLM-rewritten.
  - **Per-section provenance** (cite the source per claim).
  - **Frontmatter** on every file: title, service, `sources[]` (url, title,
    source_revision, retrieved), compiled, compiled_by, last_verified,
    `status: draft|reviewed`.
  - Keep **original Romanian** (+ English index). Organize by service.

Response schemas come from ANAF's official per-endpoint swagger presentations
(vendored 2026-07-02); the API PDFs cover URLs/params only. The documented shapes
were live-confirmed 2026-07-02 by full TEST roundtrips of both OAuth services and
by production calls to the public services (one doc gap found: e-Transport `info`'s
no-results case is a top-level singular `error` string, not `Errors[]`).

## 8. MCP server (phase 2)

A **local stdio connector** built on the phase-1 clients (extra `anafpy[mcp]`,
`python -m anafpy.mcp`). It exposes the operations as Claude Cowork skills, owns
the XML pass-through tool *inputs* (the friendly flat models come from the client
layer, §4/§5), reads the existing token store, and refreshes headlessly.
*(Implemented.)*

- **No e-Factura filing tools** *(REVISED 2026-07-03; the pass-through pair
  `efactura_prepare_invoice`/`efactura_submit_invoice` was implemented, then
  removed)*. There is no MCP use case: outbound UBL comes from third-party
  invoicing software, which files with ANAF directly — routing its export through
  a chat-driven MCP gate adds risk without value. The MCP e-Factura surface is
  **read-only**: inbox, download, `efactura_validate` (`UblXmlInput {xml|path}`
  now feeds only the validator). `efactura_get_status` went with the filing tools
  — an upload id was only ever produced by them; processed invoices surface in the
  inbox. `EFacturaClient.upload`/`get_status` remain the library filing path. If
  filing tools ever return, they must stay XML pass-through: no invoice
  composition, no flat→UBL mapping.
- **e-Transport outbound = composed from structured fields** (§5).
  `etransport_prepare_declaration` takes the client-layer `FlatTransport` as tool
  input; `etransport_prepare_deletion` / `_confirmation` / `_vehicle_change` take
  scalars and build the tiny flat models. Each renders the XML via
  `render_etransport` and returns it in `PreparedSubmission.xml` next to the
  preview (the *read-back* of the rendered bytes, so the human approves exactly
  what will be filed) and the confirmation token (bound to those bytes). The
  caller passes the XML back to the shared `etransport_submit` verbatim — a
  mangled echo fails the token check, never files. `etransport_prepare`
  (`EtransportXmlInput`) stays for ready-made XML; `etransport_nomenclature`
  (read-only) lists the XSD code lists — so the model can map "vama Nădlac" →
  `NADLAC` instead of guessing — plus the UN/ECE Rec 20/21 `unit_codes` ANAF's
  Schematron enforces on goods lines.
- **Safety: read-first, two-step gated filing.** Read-only tools (`*_list*`,
  `*_status`, `*_lookup`, `*_validate`, `auth_status`) are annotated
  `readOnlyHint` and freely callable; `efactura_download` is equally freely
  callable but annotated honestly (`readOnlyHint=False`, idempotent,
  non-destructive) since it may write files at caller-given paths. Filing
  (e-Transport only) is split `etransport_prepare*` → `etransport_submit`:
  `prepare` renders a preview and returns an HMAC **confirmation token** bound to
  the exact XML bytes plus the CIF; `submit` requires that token (same bytes, same
  CIF) **and** `confirm=True`, and redeems it **single-use** so one approval files
  at most once. **Not a `dry_run` bool.**
- **Validation is ANAF's own**: `efactura_validate` calls the server-side
  `validare`; `prepare` never blocks on validation — the human review and ANAF's
  verdict are the gates (§4 Validation).
- **Read-only e-Factura inbox**: `efactura_list_messages` → `efactura_download` →
  the `FlatInvoice` read view, from the same client-layer reader.
- **Binary artifacts: files first, one PDF resource, never context** (decided
  2026-07-03). The model operates on the flat view; the ZIP and PDF are for the
  *human*, and current hosts read resources *into model context*, so base64 blobs
  in tool results or resource reads are the wrong delivery. The server is local
  stdio, so its filesystem IS the user's: `efactura_download` takes `save_zip_as`
  (the legally archivable signed ZIP) and `save_pdf_as` (ANAF's `transformare`
  rendering, called with `validate=False` — the message was validated at filing —
  and **best-effort**: a non-PDF answer surfaces as `pdf_error`, never fails the
  download). Caller-given full paths, not a directory + naming convention: the
  agent composes filenames from invoice metadata ("`<date> - <partner>.pdf`"). An
  existing file is **never silently replaced** (2026-07-04): a collision is
  refused and reported per artifact (`pdf_error`/`zip_error`); `overwrite=true`
  replaces deliberately. (Overwrite-and-flag notices the collision only after the
  first file is gone; auto-deduplicated names turn a re-export into duplicates.)
  The PDF is additionally the stateless resource template
  `anafmsg://{message_id}/pdf`; there is deliberately **no ZIP resource** — a
  base64 ZIP serves neither the model nor any host UI.
- **Public lookups as `anaf_*` tools** (over `PublicClient`, §6): read-only, no
  auth required (usable before `anafpy auth login`), 1:1 on the client methods;
  `raw` bytes stay client-side. The counterparty sanity-check before filing lives
  here.
- **Display names**: every tool carries an English MCP `title` following
  `Service: operation` ("e-Factura: Validate invoice", "ANAF Info: Taxpayer
  lookup", "ANAF: Authentication status"). One language only: MCP has no title
  localization, and the model never sees titles (it works from `name` +
  `description`), so Romanian conversation quality is unaffected.
- **ANAF reference exposed as MCP resources** (with draft/Romanian notes) so the
  skill can ground BR-RO explanations and code lists.
- **Workflow skills served as MCP prompts** (2026-07-03): each `skills/*/SKILL.md`
  becomes a prompt of the same name — frontmatter `description` as the prompt
  description, the body as the prompt text, plus an optional `source` argument.
  Prompts are the closest MCP primitive to a skill but **user-invoked** — this is
  how the playbooks reach every MCP consumer. The SKILL.md files stay the single
  source of truth (read at server start via `python-frontmatter`, failing loudly
  when `name`/`description` are missing).
- **Auth handling**: the server reads the token store + transparent refresh;
  interactive login stays the host-side CLI (an in-session `begin_login` tool is
  deferred by design). A read-only `auth_status` reports validity; authenticated
  tools fail with a clear "run `anafpy auth login`" remediation.

## 9. Tooling

- **uv** (deps + lockfile), **hatchling** (build), **ruff** (lint+format),
  **mypy `--strict`**, **pytest** + **pytest-asyncio** + **respx**, **pre-commit**.
- **SemVer**, pre-1.0 (`0.x`). Support + test **3.12 and 3.13** (dev pin 3.13).
- **License: Apache-2.0** (explicit patent grant; ship `NOTICE`).
- **CI: GitHub Actions** (lint + type + test matrix; later publish-to-PyPI) —
  planned, not done.
- **Testing (layered)**: respx mock suite as the credential-free CI gate + an
  opt-in live suite (`ANAFPY_LIVE=1`). Mock tiers: (1) golden round-trip on
  generated UBL models (regen/serialization regressions); (2) client behavior via
  respx (upload→poll→download, `nok`, 401-refresh, 429). The live tier smoke-tests
  the public services (§6) and the authenticated TEST endpoints (read-only), plus
  the two deliberate filing exceptions: the e-Factura and e-Transport TEST
  roundtrip files (TEST only, never prod).

## 10. Open / deferred items

Resolved items are folded into their sections: `/token` needs no cert (§3),
callback UX (§3), keyring default (§3, which also settles token-at-rest for the
common case — the opt-out `FileTokenStore` remains plain JSON under OS perms),
public lookups (§6), skills-as-prompts (§8), live shape confirmation (§7).
Still open:

1. **CLI surface beyond `auth login|status|logout`** (e.g. `validate`, `submit`,
   `status`).
2. **Cowork local-stdio availability** — whether local connectors run directly in
   Cowork vs only via Claude Desktop. ANAF's cert forces local execution
   regardless; affects only which surface hosts it. Verify at build time.
3. Within the public family: the **async job variant** of the taxpayer lookup
   stays deliberately unwrapped (§6).
4. **In-session `begin_login`** MCP tool — deferred by design (§8); login stays
   CLI-side.

## 11. Distribution

> Decided 2026-07-02, revised 2026-07-07. anafpy is distributed **free and
> as-is**, for anyone to use.

**The stance.** The package is provided **as-is** under Apache-2.0 — no warranty,
no service obligations. The thin-transport scope of §1 is also the legal posture:
anafpy moves documents, it does not give tax advice, and filing outcomes are the
user's responsibility. The **MCP server is best-effort**: installing it,
configuring the environment, provisioning the OAuth application on ANAF's portal,
and holding the qualified certificate are the **user's responsibility** —
[INSTALL.md](INSTALL.md) walks through all of it.

**Local-only, by design.** The MCP server is and stays a **local stdio server**:
tool calls run on the user's machine against the user's own tokens — the
zero-custody design of §3 Deployment. A hosted remote server would mean accepting
**token custody** — per-user encrypted token storage, single-flight refresh
locking (ANAF rotates the refresh token; a refresh race between replicas bricks
the grant), a web-initiated OAuth bootstrap with session binding, and a second
OAuth surface (an OAuth *provider* to the connecting client while remaining an
OAuth *client* to ANAF) — and it could not drive the qualified-certificate step
anyway. **No hosted-service code lands in this repo** (decided 2026-07-04): token
custody, multi-tenancy, and an OAuth-provider surface toward Claude are out of
scope.

**Practicalities** (non-blocking — the tool is already usable from a checkout):

- **PyPI release + CI + SemVer discipline + security policy** (§9 — planned,
  not done).
- **Contribution terms** — Apache-2.0; settle CLA vs DCO before accepting
  external PRs.
- **Naming** — `anafpy` is fine as a library name; anything distributed more
  widely under the tax authority's name risks implying unauthorized affiliation
  and would need its own name.

**Audience bound that no packaging removes:** every user needs a qualified
certificate and their own ANAF OAuth app registration, capping the audience at
people who already deal with ANAF professionally.

**Distribution vehicles:** the MCP server registered
straight from a source checkout — `claude mcp add anafpy -- uv run --directory
<checkout> --frozen --extra mcp anafpy-mcp` — so no PyPI release is needed and the
locked deps travel with the checkout. *(A Claude Code plugin — `.claude-plugin/`
manifests making the repo its own single-plugin marketplace — shipped 2026-07-03
and was **REMOVED the same day** in favor of plain MCP registration; don't
reintroduce it without a new decision here.)* The workflow **skills** under
`skills/` reach consumers as the MCP server's same-name prompts (§8) — the first
is `etransport-declare` (extract transport data from any source → map to
`FlatTransport` → prepare → human approval → submit → poll), which encodes the
regulatory guardrails (2.5 t / 500 kg / 10,000 RON scope check, 3-days-before and
5-vs-15-day UIT validity windows) and the never-invent-a-value /
never-self-approve rules the two-step gate assumes. After the PyPI release: an
MCPB bundle for Claude Desktop (`server.type: "uv"` so the host manages Python;
`user_config` with `sensitive` fields → OS keychain, mapped onto the existing
`ANAFPY_*` env vars) — a thin wrapper over `anafpy[mcp]`.
