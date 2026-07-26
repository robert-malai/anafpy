# CLAUDE.md

Guidance for working in this repository. [DESIGN.md](DESIGN.md) is the decision
record — rationale, dates, and reversals live there; this file states only the
current rules. [docs/anaf-reference/](docs/anaf-reference/) is the compiled
local reference of ANAF's APIs. `docs/` is also the MkDocs source of the public
docs site (Read the Docs, `https://anafpy.readthedocs.io`).

## What this is

`anafpy` — typed async Python clients for Romania's **ANAF** tax-authority
services, plus a local stdio **MCP server** (`anafpy.mcp`, extra `anafpy[mcp]`)
exposing the same operations as Claude tools and skills. It is a **thin,
stateless transport client** — no persistence, no accounting logic; client
methods map 1:1 onto MCP tools. Python **3.12+** (dev pin 3.13), **httpx**,
**Pydantic v2**.

The service strands:

- **e-Factura** (electronic invoicing). Outbound has two shapes (DESIGN.md §1):
  **XML pass-through is strongly recommended** when the caller runs invoicing
  software — bring its complete UBL XML; anafpy never re-composes an upstream
  document, and ANAF's SPV is *not* invoice storage (it purges filed messages
  after ~60 days, so the durable record lives upstream). **Structured
  authoring** (`efactura.authoring`) is the first-class path without one: a
  bidirectional `InvoiceDocument` covers invoice + credit note (`kind` picks
  the render target), totals/VAT computed with explicit overrides preserved, a
  hand-translated EN 16931 + CIUS-RO rule set (`validate()`, findings with
  official BR-* ids; ANAF stays authoritative), byte-stable
  render/read round-trips, `EFacturaClient.upload_invoice`. The same model
  backs the inbox: `DownloadedMessage.view` reads downloads strictly but never
  raises (`None` when not representable; raw bytes + full UBL model are the
  fallback tiers).
- **e-Transport** (goods transport) — **fully translated**: bidirectional flat
  models author a filing and view a parsed one, covering all four operations
  (declaration/correction, deletion, confirmation, vehicle change); XML input
  remains supported.
- **Public no-auth services** (`anafpy.public`) — registry lookups, financial
  statements, and the stateless e-Factura `validare`/`transformare`.
- **SPV** (`anafpy.spv`) — read-only mailbox over a certificate cookie session.
- **Declarations** (`anafpy.declaratii`, DESIGN.md §12) — local authoring +
  validation via ANAF's DUKIntegrator (managed-installed from ANAF's update
  feed), official-PDF rendering, qualified signing (the raw op delegated to the
  OS token — no key material or PIN in-process), portal filing
  (production-only; opt-out `ANAFPY_DECLARATII_UPLOAD=off`), and no-auth
  StareD112 status/recipisa tracking.

Distribution is **free and as-is**: the MCP server is best-effort, and
configuring it — including provisioning the OAuth application on ANAF's portal —
is the user's responsibility (DESIGN.md §11).

## Commands

```bash
uv sync --all-extras                 # set up env with all dev dependency groups
uv run pytest -q                     # tests (respx-mocked, credential-free)
uv run pytest tests/test_auth.py     # one file
uv run ruff check . && uv run ruff format --check .
uv run mypy                          # strict
uv run mkdocs build --strict         # docs site (broken internal links fail); `serve` to preview
ANAFPY_LIVE=1 uv run pytest -m live  # opt-in live smoke: public services + authenticated TEST (needs .env + auth login)
```

Run the MCP server (host-side, where the `anafpy auth login` token store lives):

```bash
ANAFPY_CLIENT_ID=... ANAFPY_CLIENT_SECRET=... ANAFPY_CIF=... \
  uv run python -m anafpy.mcp        # stdio; or the `anafpy-mcp` console script
```

Server config is env-only — `ServerConfig()` **is** the environment (a
`BaseSettings`; kwargs override it, which is how the tests inject values), and an
invalid value raises `AnafConfigError`, not pydantic's `ValidationError`, so a
misconfiguration stays inside the `AnafError` hierarchy. The variable-by-variable
semantics live in [mcp/config.py](src/anafpy/mcp/config.py)'s docstrings and the
[docs/mcp/tools.md](docs/mcp/tools.md) table — don't retell them here. The
cross-cutting facts: credentials are optional (without them the public `anaf_*`
tools still serve); `ANAFPY_DOCS_DIR`'s wheel copy is a curated hatchling
force-include (a wheel-map tripwire in `test_mcp_server.py` catches a subtree
missing from the map); `ANAFPY_CURL` (both certificate bootstraps; needed on
Windows-on-ARM — SPV reference §1.1) is read at the transport layer, not by
`ServerConfig`; `ANAFPY_DECLARATII_UPLOAD=off` strips the portal-filing tools.

Codegen (only when re-vendoring XSDs / Schematron sources — see "Generated code"):

```bash
uv run python scripts/generate_ubl.py
uv run python scripts/generate_etransport.py
uv run python scripts/generate_efactura_codelists.py  # BR-CL code lists from the .sch
```

All four gates (pytest / ruff / mypy --strict / mkdocs build --strict) must
stay green.

## Layout

Module docstrings carry each file's full contract — this tree is for navigation.

```
src/anafpy/
  exceptions.py          # AnafError hierarchy (see "Error model")
  _store.py              # JsonFileStore — the 0600 atomic JSON custody shared by
                         # the OAuth token store and the SPV session store
  _transport/base.py     # Environment/Service, shared enums, CUI normalization,
                         # error raising (Environment re-exported from `anafpy`)
  _transport/http.py     # HttpClientBase: owned/injected httpx lifecycle +
                         # network-error translation + _request_checked (the
                         # shared non-success raise); injected is never mutated,
                         # empty base_url raises AnafConfigError
  _transport/poll.py     # poll_until — the ONE business-state poll loop behind
                         # upload_and_wait (both services) and wait_for_report
  _transport/subprocess.py # bounded async runner; kills the process group on
                           # timeout (DUK JVM + platform curl)
  _transport/curl.py     # CurlBootstrapperBase — shared platform-curl machinery
                         # of the two APM certificate bootstraps (SPV + portal):
                         # curl resolution (ANAFPY_CURL), cert selectors, failure
                         # taxonomy; subclasses own choreography + judgment
  auth/                  # OAuth2 layer: models, store, oauth, provider,
                         # callback, tlscert
  cli/main.py            # cyclopts CLI: `anafpy auth|spv|declaratii|duk ...`
  efactura/
    README.md            # module map: layer diagram (flat <-> UBL <-> wire),
                         # outbound/inbound flows, who-owns-what table
    ubl/                 # GENERATED UBL 2.1 models — do not hand-edit
    authoring/           # bidirectional CIUS-RO models: models.py, rules.py
                         # (validate() -> BR-* findings), build.py / read.py,
                         # codes.py, _codelists.py (GENERATED — do not hand-edit)
    client.py            # EFacturaClient — incl. upload_invoice
    models.py            # value types (UploadResult, MessageStatus,
                         # DownloadedMessage.view -> authoring)
  etransport/
    schema/              # GENERATED XSD models — do not hand-edit
    client.py            # ETransportClient — incl. upload_document
    models.py            # value types + bidirectional flat models (4 ops)
                         # + read/build/render
  public/
    client.py            # PublicClient (no auth): lookups + validare/transformare
    models.py            # lookup value types + RemoteValidationResult
  spv/                   # SPV read-only client — certificate cookie session
    bootstrap.py         # CurlBootstrapper — the ONLY step touching the cert
    session.py           # SpvSession (cookie set = bearer credential) +
                         # SessionStore protocol, FileSessionStore (0600)
    auth.py              # SpvSessionProvider + SpvAuth (follows policy-nonce
                         # hops; login wall -> AnafAuthError; NO auto re-login)
    certs.py             # Keychain identity discovery
    client.py            # SpvClient: listaMesaje, descarcare, cerere,
                         # wait_for_report
    models.py            # SpvEnvelope, SpvMessage, ReportType nomenclature +
                         # ReportRequest (per-type param validation)
  declaratii/            # declarations: local authoring/signing + public status
    duk.py               # DukIntegrator: -v/-p headless; judge by err-file,
                         # never exit code; per-run temp cwd + -c offLine=Y
                         # config dir; UTF-8 err files via jvm_args
    install.py           # DukInstaller: managed dist at ~/.anafpy/duk-dist from
                         # ANAF's (self-sufficient) update feed — https + host
                         # pinned, manifest-audited, convergent; default_duk_dir
                         # is the fallback when ANAFPY_DUK_DIR is unset
    models.py            # declaration-family value types (no pyHanko import)
    _html.py             # shared JSP-parser text handling
    status.py            # DeclarationStatusClient (no auth): StareD112 filing
                         # status + recipisa PDF (parsel extraction, our checks)
    nr_evid.py           # the 23-char nr_evid composers (pure functions):
                         # D300 / D100+D710 / D101 / D301
    upload.py            # portal filing (WAS6DUS): PortalCurlBootstrapper +
                         # DeclarationUploadClient (rejection page = returned
                         # outcome; probe() = no-2FA session check)
    signing.py           # RawSigner protocol + KeychainRawSigner (macOS,
                         # ctypes -> Security.framework; no key material)
    pdfsign.py           # sign_pdf via pyHanko — needs anafpy[declaratii]
  mcp/                   # MCP server — split BY SERVICE; the shared core is
                         # only what 2+ services genuinely use
    app.py               # composition root: create_server, main, auth_status
    config.py            # ServerConfig — BaseSettings over ANAFPY_*
    context.py           # AppContext: providers + lazy clients + token ledger
                         # + SPV same-day request log
    gate.py              # the two-step filing gate: HMAC confirmation tokens +
                         # TokenLedger, XmlInput ({xml|path} -> bytes),
                         # PreparedSubmission/SubmitResult, run_submit
    artifacts.py         # tool annotations + ensure_writable/write_artifact
    reference.py         # docs/anaf-reference/ as anafref:// resources
    prompts.py           # the workflow skills re-served as same-name prompts
    efactura/ etransport/ public/ spv/ declaratii/
                         # per-service tools.py, plus models/nomenclatures
                         # (incl. UN/ECE Rec 20/21 unit codes) where the service
                         # needs them; resource templates anafmsg:// and spvmsg://
    __main__.py          # `python -m anafpy.mcp` (stdio)
.claude-plugin/          # marketplace.json — publishes the two plugins below
plugins/anafpy-setup/    # skill that installs + configures anafpy on an end
                         # user's machine (writes claude_desktop_config.json;
                         # local sessions only). SKILL.md = platform-neutral
                         # spine; command blocks live in macos.md / windows.md
plugins/anafpy-workflows/skills/  # the workflow playbooks' SINGLE home
                         # (etransport-declare, declaratie-prepare,
                         # personal-income-summary) — Cowork Agent Skills AND
                         # the MCP server's same-name prompts; never duplicate
schemas/                 # vendored XSDs + Schematron sources (git-tracked, not
                         # shipped; feed the codegen)
scripts/                 # codegen scripts
imgs/                    # brand assets; README hotlinks the social preview
docs/                    # MkDocs source tree (mkdocs.yml at repo root; RTD
                         # builds via uv); docs/assets/ = site image copies
  mcp/                   # setup.md (end-user walkthrough, accountant
                         # audience), tools.md, skills.md
  library/               # library guides       api/  # mkdocstrings pages
  anaf-reference/        # compiled ANAF reference — ALSO served as MCP
                         # resources, don't move it; declaratii/forms/ = the
                         # form inventory + per-form completion guides;
                         # METHOD.md = the generation playbook
tests/                   # respx-mocked suite + opt-in live files (filing
                         # boundaries: see "Conventions for changes")
```

## Architecture & conventions

- **Both OAuth services share one host** `api.anaf.ro`, differing only by path
  prefix (`FCTEL/rest` vs `ETRANSPORT/ws/v1`) and `test`/`prod` segment — all
  in [_transport/base.py](src/anafpy/_transport/base.py); clients take an
  `environment`.
- **`PublicClient` is the odd one out**: `webservicesp.anaf.ro`, no
  `TokenProvider`, no `environment` (production only), and it **paces its own
  requests** (`min_request_interval`, default 1 req/s — ANAF states the limit
  as a usage rule, not via 429s). Registry membership reads the `registered`
  booleans, never presence in `found`; the e-Factura register's
  404-with-`found`/`notFound`-body is a returned "not found". It also carries
  the stateless `validate_invoice`/`render_invoice_pdf` (public, no-auth,
  **prod-only** — their TEST paths 404); only the MF signature check stays on
  `EFacturaClient`.
- **SPV is the certificate outlier** (read-only by design — no submissions).
  The qualified certificate (keys non-exportable; Python's `ssl` cannot present
  them) is used only by the interactive login bootstrap, which drives the
  OS-shipped curl against the platform key store (macOS SecureTransport by
  Keychain name; Windows Schannel by thumbprint; NSURLSession hangs on the APM
  renegotiation — don't go back there). All other calls are plain httpx on the
  persisted cookie session; `/my.policy_nonce` hops are followed, a bare login
  wall raises `AnafAuthError` — the client never re-runs the 2FA-firing
  bootstrap on its own. Deviation from the no-retry rule: the idempotent-GET
  reads retry transient transport errors; `request_report` stays single-shot
  with **no client-side dedupe** (the library is stateless — guarding agent
  loops is the MCP layer's job). Wire facts:
  [docs/anaf-reference/spv/api.md](docs/anaf-reference/spv/api.md) §1.1.
- **Auth is a separate layer.** Clients receive a `TokenProvider` and drive
  httpx via `AnafAuth`, which handles transparent refresh (incl. on 401). The
  certificate happens only in the interactive `anafpy auth login` browser flow
  — **don't add cert/mTLS handling to clients**. Because ANAF registers only
  `https://` callbacks (and no public CA issues for localhost), the default
  login listener serves a per-attempt ephemeral self-signed cert
  (`auth/tlscert.py`; alternatives `--tls-cert/--tls-key`, `--paste`,
  `--no-tls`; it binds before the browser opens and falls back to paste —
  rationale in DESIGN.md §3). Every login binds a random OAuth `state`;
  mismatching redirects are rejected (a pasted bare code is exempt).
  `anafpy auth logout` is **purely local** — ANAF's `/revoke` is not reachable
  headlessly; **don't (re)add a revoke call** unless ANAF routes the endpoint
  (DESIGN.md §3). Token persistence is the `TokenStore` protocol:
  `KeyringTokenStore` (default; Windows-specific splitting per DESIGN.md §3) or
  `FileTokenStore` (the Docker/headless opt-out), selected by
  `ANAFPY_TOKEN_STORE_BACKEND` / `--store-backend`. The test suite installs an
  autouse in-memory fake keyring and an autouse isolated managed-DUK dir so no
  test touches real user state.
- **Clients are async**, own their `httpx.AsyncClient` (unless one is
  injected), and are async context managers.
- **Discrete methods do NO transport retry** — one call, one result-or-raise —
  so the non-idempotent `upload` POST is never silently repeated. Consumers
  bring their own retry. `tenacity` appears only in the business-state poll
  loops (`upload_and_wait`, `wait_for_report` — all three go through
  `_transport/poll.py`'s `poll_until`) and the SPV read deviation.
- **Module style**: `from __future__ import annotations`, explicit `__all__`,
  module + class docstrings, Google-style docstring sections. Line length 88.
  Keep new code in the voice of the surrounding files.
- **Favour structured pattern matching** (DESIGN.md §2) — 3.12+ is the floor,
  so `match` is always available. Use it wherever a branch dispatches on **one
  subject's shape or value**: closed-union `isinstance` chains (close with
  `case _: assert_never(x)` so `mypy --strict` flags an unhandled new member),
  value dispatch on ANAF codes / form names, flag truth tables, presence-of-
  field checks on parsed models (`case ETransport(stergere=CorectieType())`),
  and shape checks on decoded JSON (`case {"eroare": error}`). Keep plain `if`
  for substring/regex tests, single binary checks, and dict-lookup dispatch —
  the test is whether the pattern makes the condition structural and *shorter*
  to read, not whether it can be expressed as one.
- **Favour the walrus operator** (DESIGN.md §2) — fold an assign-then-test pair
  into the condition (`if (exp := _jwt_exp(token)) is not None:`,
  `if message := child.get("errorMessage"):`,
  `if (jar := Path(jar_path)).exists():`) **when the binding's whole lifetime
  is that branch**. Keep the separate assignment when the name is the subject
  of the rest of the function (a `docs = _docs_dir(cfg)` guard whose `docs`
  drives everything below), when the merged line would wrap or exceed 88
  columns, or when the right-hand side already needs its own line. Loop
  counters and accumulators are not walrus material.
- **English identifiers everywhere in hand-written code**: ANAF's Romanian wire
  names survive only as pydantic validation aliases (`data_creare` →
  `created_at`), string literals, and the generated schema models. Domain
  acronyms with no sensible translation (`cui`, `cif`, `uit`, `caen`) and enum
  members named after ANAF's own codes stay as-is.
- **Branded service names in prose**: in strings, messages, and docs the
  services are written exactly `e-Factura` and `e-Transport`, even at sentence
  start. Identifiers stay English-convention (`EFacturaClient`, `efactura_*`);
  ANAF wire facts and quotes keep ANAF's own spelling.

## MCP server (`anafpy.mcp`)

`create_server(config)` returns a `FastMCP`; `AppContext` owns one
`TokenProvider` plus lazily-built clients, closed in the server lifespan. The
server reads the existing token store and refreshes headlessly — the OAuth
browser login stays CLI-side. The tool inventory with per-tool descriptions is
[docs/mcp/tools.md](docs/mcp/tools.md); the rules:

- **Read-first, two-step gated filing.** Read-only tools carry `readOnlyHint`
  and are freely callable (the `anaf_*` lookups and `efactura_validate` work
  with no OAuth credentials at all). Every ANAF filing — e-Factura,
  e-Transport, declarations — is split `*_prepare*` → `*_submit`: prepare
  returns a human-reviewable preview plus an HMAC **confirmation token**
  (`mcp/gate.py`) bound to the exact bytes (+ the CIF where one applies);
  submit requires that token **and** `confirm=True` and redeems it
  **single-use** (`TokenLedger`), so one approval files at most once. **Don't
  collapse this into a `dry_run` bool.** `declaratie_submit` re-probes the
  portal session *before* consuming the token, so a lapsed login never burns
  the human's approval. SPV has no gate — nothing is filed there;
  `spv_cerere`'s additive side effect is carried by honest REQUESTING
  annotations plus an in-process same-day dedupe.
- **`prepare` never blocks on a local check.** Validation authority is ANAF's:
  the server-side `validare` for e-Factura, DUK's validator jars for
  declarations, upload-time validation for e-Transport. Local checks
  (construction-time shape checks in both flat families; the translated
  `authoring.validate()` rule set) surface as informational `local_findings` —
  the token is always issued; the human review and ANAF's verdict are the
  gates. Only the library-level `render_invoice`/`upload_invoice` fail closed
  by default (`skip_validation=True` opts out).
- **Binary artifacts go to disk, never into context.** Caller-given full paths
  through the shared `write_artifact`/`ensure_writable` collision guard — an
  existing file is never silently replaced; `overwrite=true` is the deliberate
  path. Never return base64 blobs from tools. PDFs are additionally the
  resource templates `anafmsg://{message_id}/pdf` and `spvmsg://{mesaj_id}/pdf`
  (deliberately no ZIP resource).
- **Consequential interactive tools** (`spv_login`, `declaratie_sign`,
  `declaratie_portal_login`) are gated on `confirm=true` — the model must relay
  the user's explicit ask — one attempt per call, and report failure as
  `logged_in`/`signed` = `false` plus guidance, **not** exceptions. **No MCP
  tool ever accepts a PIN**: the raw signature/login is delegated to the OS
  token middleware, and the out-of-band PIN/2FA prompt is the human gate.
- **Nomenclatures are tools** (`etransport_nomenclature`, `spv_nomenclature`)
  so the model maps user intent onto exact ANAF codes instead of guessing;
  enum-coded fields accept names or ANAF codes, and a wrong value errors with
  the accepted list so the flow self-heals.
- **Workflow skills have one home**, `plugins/anafpy-workflows/skills/*/SKILL.md`
  — surfaced in Cowork as Agent Skills (marketplace install) *and* re-served by
  the server as same-name MCP prompts (`mcp/prompts.py`; missing
  `name`/`description` frontmatter fails at server start). Never duplicate a
  playbook.
- **Tool descriptions are `cleandoc` literals**, written inline in the
  `@mcp.tool` / `@mcp.resource` decorator — FastMCP ships a description verbatim
  (it dedents nothing of its own), so `inspect.cleandoc` is what strips the
  decorator indent and the framing blank lines. Structure the shipped text:
  a paragraph per concern, `-` bullets for every enumeration (the ANAF state
  wordings, per-form `nr_evid` inputs, the three `accepted` verdicts, a
  nomenclature's `kind`s). Only a description that interpolates a runtime
  fragment is an `f` string — most carry literal braces (`{"xml": ...}`,
  `anafmsg://{message_id}/pdf`). Parameter-level `Field(description=...)` stays
  a plain string.
- **Tool display names**: an English MCP `title` per tool, `Service: operation`
  (`e-Factura`, `e-Transport`, `ANAF Info`, `SPV`, `Declarations`; bare `ANAF`
  for `auth_status`). Titles are UI-only — the model sees `name` +
  `description` — keep them single-language.

## Error model (important)

Hybrid, per design — do not collapse it:

- **Exceptions** (`AnafError` → `AnafAuthError`, `AnafTransportError`/`AnafResponseError`,
  `AnafRateLimitError`, `AnafConfigError`) are for transport / auth / programming errors.
  HTTP 429 raises `AnafRateLimitError` exposing `retry_after`; the client does **not**
  auto-back-off.
- **Business outcomes** (e-Factura `nok`/`REJECTED`, upload rejections with BR-RO
  findings) are returned as **typed values** (e.g. `UploadResult.accepted is False`,
  `MessageStatus.state`), never raised.
- **Listing and `info`** (`list_messages` / `list_notifications` / e-Transport `info`) are
  where a 200-with-error-note is split: ANAF overloads the note (e-Factura: `eroare`;
  e-Transport: `Errors[].errorMessage`, `info` also a top-level `error` string) for both
  "no results" and real errors, so a no-results note yields an **empty iterator** (`info`:
  an empty `InfoList` with the note in `.error`) while a genuine error **raises
  `AnafResponseError`** (`status_code=200`). The classifier is
  `_transport.base.is_empty_result_message`.

## Generated code — do not hand-edit

`src/anafpy/efactura/ubl/` and `src/anafpy/etransport/schema/` are generated by
the `scripts/generate_*.py` scripts from vendored XSDs in `schemas/` —
[schemas/README.md](schemas/README.md) is the provenance record and
re-vendoring playbook (incl. the step-by-step for a CIUS-RO revision). They are
committed as source but excluded from ruff/mypy/pyright (see `pyproject.toml`).
To change them, edit the script / re-vendor and regenerate. `xsdata[cli]` is
pinned `<25` — the `xsdata-pydantic` plugin targets the 24.x line and newer
core emits invalid fields. The e-Transport script post-processes nomenclature
enums into descriptive member names from the XSD's own annotations
(`CodJudetType.CLUJ`, `CodTipOperatiuneType.TTN`, ...).

`src/anafpy/efactura/authoring/_codelists.py` is likewise generated (from the
vendored EN16931/CIUS-RO Schematron — the `BR-CL-*` closed code lists). It is
lint/type-clean so it is NOT excluded from the gates; same rule: regenerate,
never hand-edit.

Public UBL entry points: `from anafpy.efactura import Invoice, CreditNote`.

## ANAF response formats

Response schemas come from ANAF's official per-endpoint **swagger
presentations** (vendored under `docs/anaf-reference/_sources/`, folded into
`docs/anaf-reference/*/api.md`); the API PDFs cover URLs/params only, and the
swagger wins when they disagree — e.g. the e-Factura message list's
`cif_emitent`/`cif_beneficiar` are never emitted despite the PDF; the CIFs ride
only in the free-text `detalii`. All documented shapes are live-confirmed, and
the `live`-marked tests re-confirm them on demand. When touching parsing code,
treat the reference doc as the source of truth and prefer being explicit over
silently returning empty results.

## Conventions for changes

- Keep the four gates green; add/extend respx tests for client behavior changes
  (upload→poll→download, `nok` path, 401-refresh, 429 surfacing). The respx
  suite is the gate; the `live`-marked smokes only re-confirm wire shapes on
  demand (`ANAFPY_LIVE=1`; credentials from the gitignored `.env`; the conftest
  `live_token_store` may use the real OS keyring — the one sanctioned exception
  to the autouse fake). Don't move behavioural assertions there; keep live
  tests read-only. The **three deliberate filing exceptions**:
  `test_etransport_roundtrip_live.py` and `test_efactura_roundtrip_live.py`
  file documents composed via the authoring models to **TEST only, never
  prod**; `test_declaratii_upload_live.py` files **D406T** — ANAF's sanctioned
  no-fiscal-effect SAF-T test declaration; declarations have no TEST
  environment — on the production portal, double-gated
  (`ANAFPY_LIVE_FILE_D406T=1`, it fires the certificate 2FA twice). Don't add
  uploads to any other live file, and never file anything but D406T in that
  one. `test_efactura_roundtrip_live.py`'s
  `test_validare_agrees_with_local_rules` is the **drift tripwire** for CIUS-RO
  revisions — when it fires: re-vendor the `.sch`, regenerate the code lists,
  re-align the translated rules ([schemas/README.md](schemas/README.md)).
- **Keep the docs in sync — each fact in ONE home, link instead of retelling.**
  CLAUDE.md states current rules and layout (no dates, no history);
  [DESIGN.md](DESIGN.md) owns decisions, dates, and reversals; module
  docstrings own per-file contracts; `docs/anaf-reference/` owns ANAF wire
  facts (keep its provenance frontmatter intact); [README.md](README.md) and
  the docs site (`docs/mcp/setup.md` — end-user walkthrough, accountant
  audience; `docs/mcp/tools.md` + `skills.md` — the MCP surface;
  `docs/library/*` — the library guides) own the user-facing story. A new page
  goes into `mkdocs.yml`'s `nav`. Update the affected homes in the same change.
- **Repo boundary**: this repo is the whole publishable project (clients + MCP
  server + skills + docs). Never add hosted-service code — token custody,
  multi-tenancy, and an OAuth-provider surface toward Claude are out of scope
  (DESIGN.md §11).
- Don't commit, push, or create branches/PRs unless asked.
- Remote: `github.com/robert-malai/anafpy`. CI (`.github/workflows/ci.yml`):
  pytest on 3.12 + 3.13 across ubuntu/macos/windows (the SPV and signing layers
  have platform seams), plus ruff / mypy --strict / the strict docs build on
  the ubuntu leg; every leg uploads coverage **and** JUnit results to Codecov
  under per-leg flags (details in the workflow file; two quirks are deliberate:
  the test-results upload runs `if: ${{ !cancelled() }}`, and
  `junit_family = "legacy"` stays in `pyproject.toml` for Codecov's UI).
  `release.yml` re-runs the gates on a `v*` tag, checks the tag against
  `pyproject.toml`'s version, and publishes to PyPI via trusted publishing
  (OIDC, no stored token). The version lives in `pyproject.toml` **and**
  `anafpy.__version__`; `tests/test_version.py` keeps them agreeing.
