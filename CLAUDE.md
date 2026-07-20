# CLAUDE.md

Guidance for working in this repository. See [DESIGN.md](DESIGN.md) for the full
design rationale and [docs/anaf-reference/](docs/anaf-reference/) for a compiled local
reference of ANAF's APIs. `docs/` is also the MkDocs source tree for the public
documentation site (Read the Docs, `https://anafpy.readthedocs.io`).

## What this is

`anafpy` — typed Python clients for Romania's **ANAF** tax-authority web services,
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), and the
**public no-auth services** (`anafpy.public`: registry lookups + financial
statements). It is a **thin, stateless transport client** (no persistence, no
accounting logic). **e-Factura outbound has two shapes** (DESIGN.md §1):
**XML pass-through is the strongly recommended path** when the caller
runs invoicing software — bring the complete UBL XML it exported; anafpy never
re-composes an upstream system's document, and ANAF's SPV is **not invoice
storage** (it purges filed messages after ~60 days), so the durable record must
live in a system the caller owns — and **structured authoring**
(`anafpy.efactura.authoring`) is the first-class path for callers with no
upstream system (they then own archiving the signed ZIPs): bidirectional flat
models (one `InvoiceDocument` covers invoice
+ credit note; `kind` picks the render target) with computed totals/VAT breakdown
(explicit overrides preserved), a hand-translated EN 16931 + CIUS-RO rule set
(`validate()`, findings with official BR-* ids; ANAF stays authoritative),
`render_invoice`/`read_invoice`/`parse_invoice` (byte-stable round-trips), and
`EFacturaClient.upload_invoice`. The same `InvoiceDocument` backs the
e-Factura inbox: `DownloadedMessage.view` reads downloads through the strict
`read_invoice` (never raising — `None` when the content is not representable;
strict reading covers every ANAF-validated document, and the raw bytes + full
UBL model remain the fallback tiers). **e-Transport is fully
translated** (decided 2026-07-03): the flat models are **bidirectional** — the
same models author a filing (`build_etransport`/`render_etransport`,
`upload_document`) and view a parsed one (`read_flat_transport`), covering all
four operations (declaration/correction, deletion, confirmation, vehicle change).
Phase 1 is the typed async clients; phase 2 is
the **MCP server** (`anafpy.mcp`, extra `anafpy[mcp]`) exposing the operations as
Claude Cowork skills. The client methods map 1:1 onto MCP tools — discrete operations,
serializable typed inputs/outputs, good docstrings. A third strand is
**`anafpy.declaratii`** (added 2026-07-15): **local** tax-declaration
authoring, validation (via ANAF's DUKIntegrator), official-PDF rendering, and
qualified signing (the raw op delegated to the OS token — no key material or PIN
in-process), exposed as `declaratie_*` MCP tools. M1 is authoring + signing;
**status tracking landed** 2026-07-16:
`DeclarationStatusClient` checks a filed declaration's processing state and
downloads the signed recipisa over ANAF's **public, no-auth** StareD112 service
(upload index + CUI are the access key), so the post-filing confirmation
loop is automated. **M2 (filing) is complete**:
`DeclarationUploadClient` (`declaratii/upload.py`) does the WAS6DUS portal
certificate login + multipart filing POST, live-verified 2026-07-17 by filing
**D406T**, ANAF's sanctioned no-fiscal-effect SAF-T test declaration (the only
permitted production filing; DESIGN.md §12), and the **MCP filing gate landed
2026-07-20**: `declaratie_portal_login` (confirm-gated, outside the submit
cycle) + `declaratie_portal_status` (no-2FA session probe) +
`declaratie_prepare` → `declaratie_submit` over the shared two-step gate —
served by default, **opt-out** via `ANAFPY_DECLARATII_UPLOAD=off` (declarations
file on the production portal only). Distribution is **free and
as-is**: the library is for anyone to use; the MCP server is **best-effort**, and
configuring it — including provisioning the OAuth application on ANAF's portal —
is the user's responsibility (DESIGN.md §11).

Python **3.12+** (`requires-python`; the repo `.python-version` dev pin stays 3.13).
Built on **httpx** and **Pydantic v2**.

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

Config is env-only — `anafpy.mcp.config.ServerConfig` is a `pydantic-settings`
`BaseSettings` (use `ServerConfig.from_env()` for a friendly `AnafConfigError`):
`ANAFPY_CLIENT_ID`,
`ANAFPY_CLIENT_SECRET` (optional — without them the server still starts and serves
the public `anaf_*` lookups; the authenticated tools raise a how-to-enable
`AnafConfigError`), `ANAFPY_TOKEN_STORE` (default `~/.anafpy/tokens.json`),
`ANAFPY_TOKEN_STORE_BACKEND` (`keyring`/`file`, default `keyring` — tokens live in
the OS credential store via `KeyringTokenStore` (`keyring` is a core dependency);
`file` is the opt-out for Docker/headless hosts without a credential store; the
CLI honours the same variable and `--store-backend`),
`ANAFPY_ENV` (`test`/`prod`, default `prod`), `ANAFPY_CIF` (default fiscal code), `ANAFPY_DOCS_DIR`
(reference resources, defaults to the repo `docs/anaf-reference/` when present,
else the copy packaged into the wheel — hatchling force-include, curated
subtrees enumerated one by one because force-include bypasses `exclude` and
`_sources/` must stay out; a wheel-map tripwire in `test_mcp_server.py` catches
a new subtree missing from the map),
`ANAFPY_SKILLS_DIR` (workflow skills re-served as MCP prompts, defaults to the
`anafpy-workflows` plugin's `plugins/anafpy-workflows/skills/` when present,
else the wheel-packaged copy),
`ANAFPY_SPV_SESSION` (SPV cookie-session store, default
`~/.anafpy/spv-session.json`), `ANAFPY_SPV_IDENTITY_FILE` (persisted SPV
certificate selection, default `~/.anafpy/spv-identity.json`),
`ANAFPY_CURL` (override the curl binary of **both** certificate
bootstraps — SPV and the declaration upload portal; read at the shared
`_transport/curl.py` base, so it covers CLI and MCP alike; renamed from
`ANAFPY_SPV_CURL` 2026-07-17, no compat alias; needed
on Windows-on-ARM, where x64-only vendor KSPs — certSIGN vToken — require an
x64 Schannel curl such as Git for Windows', see the SPV reference §1.1),
`ANAFPY_DUK_DIR` (the extracted DUKIntegrator `dist/` folder — enables the
`declaratie_*` tools; no default), `ANAFPY_DUK_JAVA` (the java binary; optional),
`ANAFPY_SIGN_IDENTITY` (Keychain identity name to sign declarations with;
optional — falls back to the persisted SPV certificate selection),
`ANAFPY_DECLARATII_UPLOAD` (default on; `off` opts out of the declaration
portal-filing tools — the server then serves authoring/status only and
`declaratie_sign` guides manual filing).

Codegen (only when re-vendoring XSDs / Schematron sources — see below):

```bash
uv run python scripts/generate_ubl.py
uv run python scripts/generate_etransport.py
uv run python scripts/generate_efactura_codelists.py  # BR-CL code lists from the .sch
```

All four gates (pytest / ruff / mypy --strict / mkdocs build --strict) are currently
green and must stay green.

## Layout

```
src/anafpy/
  exceptions.py          # AnafError hierarchy (see "Error model")
  _transport/base.py     # Environment/Service + shared enums/CUI normalization/error raising
                         # (Environment is re-exported from the top-level `anafpy` —
                         # it appears in public client signatures)
  _transport/http.py     # HttpClientBase: six clients' owned/injected lifecycle
                         # (owned gets the service base_url; injected is never
                         # mutated — empty base_url raises AnafConfigError)
                         # + network-error translation
  _transport/subprocess.py # bounded async subprocess runner; kills the process
                           # group on timeout (DUK JVM + platform curl)
  _transport/curl.py     # CurlBootstrapperBase — shared platform-curl machinery of
                         # the two APM certificate bootstraps (SPV + declaration
                         # portal): curl resolution (ANAFPY_CURL), cert
                         # selectors, TLS-backend pin, failure taxonomy;
                         # subclasses own choreography + success judgment
  auth/                  # OAuth2 layer: models, store, oauth, provider, callback
  cli/main.py            # cyclopts CLI: `anafpy auth login|status|logout` +
                         # `anafpy spv certs|select|login|status|logout` +
                         # `anafpy declaratii validate|render|sign|status|recipisa`
  efactura/
    README.md            # module map: layer diagram (flat <-> generated UBL <-> wire),
                         # outbound/inbound flows, who-owns-what table
    ubl/                 # GENERATED UBL 2.1 models (xsdata-pydantic) — do not hand-edit
    authoring/           # BIDIRECTIONAL CIUS-RO invoice models:
                         #   models.py (InvoiceDocument + parts, computed totals/VAT),
                         #   rules.py (validate() -> findings with BR-* ids),
                         #   build.py / read.py (flat <-> UBL), codes.py,
                         #   _codelists.py (GENERATED BR-CL lists — do not hand-edit)
    client.py            # EFacturaClient (async) — incl. upload_invoice (flat -> XML -> upload)
    models.py            # value types (UploadResult, MessageStatus, DownloadedMessage.view -> authoring)
    __init__.py          # re-exports Invoice, CreditNote from ubl.maindoc
  etransport/
    schema/              # GENERATED e-Transport XSD models — do not hand-edit
    client.py            # ETransportClient (async) — incl. upload_document (flat -> XML -> upload)
    models.py            # value types + BIDIRECTIONAL flat models (4 ops) + read/build/render
  public/
    client.py            # PublicClient (async, no auth) — webservicesp.anaf.ro lookups
                         # + the stateless e-Factura document services (validare/transformare)
    models.py            # lookup value types (TaxpayerRecord, RegistryLookup[...], ...)
                         # + TransformStandard, RemoteValidationResult
  spv/                   # SPV (Spațiul Privat Virtual) read-only client — cert mTLS
    bootstrap.py         # SessionBootstrapper protocol + CurlBootstrapper (over the
                         # _transport/curl.py base) — the ONLY step that touches
                         # the certificate (APM login); owns the SPV choreography
                         # (one --location probe) + the SPV-JSON success judgment
    session.py           # SpvSession (APM cookie set = bearer credential) +
                         # SessionStore protocol, FileSessionStore (0600)
    auth.py              # SpvSessionProvider (mirrors TokenProvider; owns login)
                         # + SpvAuth (httpx.Auth: attach cookies, follow
                         # /my.policy_nonce hops, login wall -> AnafAuthError;
                         # deliberately NO auto re-login — that fires the 2FA)
    certs.py             # Keychain identity discovery (`security find-identity`)
    client.py            # SpvClient (async; takes an SpvSessionProvider like the
                         # OAuth clients take a TokenProvider): listaMesaje,
                         # descarcare, cerere, wait_for_report
    models.py            # SpvEnvelope (shared identity stamp: title/cnp/serial) ->
                         # MessageList, ReportRequestResult; SpvMessage, ReportType
                         # nomenclature + ReportRequest (per-type param validation),
                         # error hints
  declaratii/            # tax-declaration authoring/validation/signing (M1, local:
                         # subprocess + crypto) + StareD112 filing status (public):
    duk.py               # DukIntegrator (async): validate/render via ANAF's DUK
                         # (-v/-p headless; judge by err-file, never exit code),
                         # installed_forms + free fetch_feed_versions staleness
    models.py            # declaration-family value-type home: DUK, upload, PDF-sign
                         # outcomes + DeclarationState/Document/StatusList
    _html.py             # whole-text/accent handling shared by both JSP parsers
    status.py            # DeclarationStatusClient (async, NO auth): filing status
                         # + recipisa PDF via www.anaf.ro/StareD112 (index+CUI are
                         # the access key; empty-PDF answer = receipt unavailable);
                         # HTML extraction via parsel (core dep) — shape checks ours
    nr_evid.py           # the 23-char nr_evid composers (pure): payment_evidence_number
                         # (D300) + obligation_evidence_number (D100/D710) +
                         # profit_tax_evidence_number (D101) + special_vat_evidence_number (D301)
    upload.py            # M2 portal upload (decl.anaf.mfinante.gov.ro/WAS6DUS):
                         # PortalCurlBootstrapper (cert login, discrete curl
                         # steps, over the _transport/curl.py base) +
                         # DeclarationUploadClient (cookie multipart POST;
                         # rejection page = returned business outcome; success
                         # page -> upload index — LIVE-VERIFIED 2026-07-17 by
                         # filing a D406T, pyHanko CMS accepted; probe() =
                         # no-2FA session check, install_session() = the seam
                         # for externally-run bootstraps)
    signing.py           # RawSigner protocol + KeychainRawSigner (ctypes ->
                         # Security.framework: SecKeyCreateSignature; no key material,
                         # 2FA is the human gate) + shared framework cache,
                         # default_signed_path/load_pdfsign/resolve_signing_label
    pdfsign.py           # sign_pdf (pyHanko: adbe.pkcs7.detached incremental update,
                         # AIA issuer fetch) — needs the anafpy[declaratii] extra
  mcp/                   # MCP server (extra: anafpy[mcp]) — phase 2, split BY SERVICE:
                         # each service package owns its tools + models + helpers;
                         # the shared core is only what 2+ services genuinely use
    app.py               # composition root: `create_server`, `main`, server
                         # instructions, auth_status tool
    config.py            # ServerConfig.from_env (creds, store path, env, default CIF)
    context.py           # AppContext: TokenProvider + lazy clients + token ledger
                         # + SPV same-day request log; auth_status
    gate.py              # the two-step filing gate shared by both filing services:
                         # HMAC confirmation tokens + TokenLedger, XmlInput base
                         # ({xml|path} -> bytes), PreparedSubmission/SubmitResult,
                         # run_submit (the STEP-2 skeleton with its two orderings)
    artifacts.py         # tool annotations + shared ensure_writable/write_artifact
    reference.py         # docs/anaf-reference/ as anafref:// resources
    prompts.py           # anafpy-workflows plugin's skills/*/SKILL.md loader +
                         # same-name MCP prompts (one source, two consumers)
    efactura/            # tools.py (tools + anafmsg:// resource), models.py
                         # (UblXmlInput, PreparedInvoice), documents.py (previews,
                         # upload standards, transformare PDF rendering)
    etransport/          # tools.py, models.py (EtransportXmlInput, PreparedTransport,
                         # transport_view), nomenclature.py (XSD code lists) +
                         # unitcodes.py (UN/ECE Rec 20/21)
    public/              # tools.py — the no-auth anaf_* lookup tools
    spv/                 # tools.py (+ spvmsg:// resource), nomenclature.py
                         # (report types + per-type wire params)
    declaratii/          # tools.py (declaratie_validate/render/sign/nr_evid/
                         # duk_status — LOCAL — + declaratie_status/recipisa
                         # over the public StareD112 + the portal filing gate:
                         # declaratie_portal_login/portal_status/prepare/submit,
                         # opt-out via ANAFPY_DECLARATII_UPLOAD), models.py
    __main__.py          # `python -m anafpy.mcp` (stdio)
.claude-plugin/          # marketplace.json — the `anafpy` plugin marketplace
                         # published from this repo (`/plugin marketplace add
                         # robert-malai/anafpy`); lists the two plugins below
plugins/anafpy-setup/    # plugin: an `anafpy-setup` skill that installs + configures
                         # anafpy on an end user's computer and connects it to Claude
                         # (writes claude_desktop_config.json, which the Cowork tab
                         # reads). Runs in a LOCAL session (needs a shell) — refuses
                         # cloud/remote. Separate from the MCP server because it must
                         # run BEFORE that server exists. Split 2026-07-20: SKILL.md
                         # is the platform-neutral spine (steps, rules, user-facing
                         # prose); the command blocks live in macos.md / windows.md,
                         # routed by the step-0 platform probe so the agent never
                         # sees the other platform's commands.
plugins/anafpy-workflows/ # plugin: the workflow SKILLS themselves. Its skills/ is
  skills/                #   the SINGLE home of the playbooks (etransport-declare:
                         #   source data -> FlatTransport -> prepare -> approval ->
                         #   submit -> status; declaratie-prepare: unstructured data
                         #   -> form selection -> completion-guide read -> CUI-lookup
                         #   inference + ask -> author XML -> validate loop -> render
                         #   -> approval -> sign -> manual filing -> status/recipisa;
                         #   personal-income-summary; declaratie-compose replaced
                         #   2026-07-18). Installed from the marketplace these
                         #   surface in Cowork as Agent Skills — the claude.ai plugin
                         #   ecosystem DOES bring bundled skills into chat + Cowork
                         #   (verified 2026-07-18), distinct from Claude Code
                         #   marketplace plugins which are Code-tab-only. The MCP
                         #   server re-serves this SAME tree as MCP prompts
                         #   (ANAFPY_SKILLS_DIR default points here) — one source,
                         #   two consumers. Skills drive the MCP tools, so the anafpy
                         #   connector (anafpy-setup) must also be configured.
schemas/                 # vendored XSDs + EN16931 Schematron sources (git-tracked,
                         # NOT shipped in the wheel; the .sch feed the codelist codegen)
scripts/                 # codegen scripts
imgs/                    # brand assets (icon SVG/PNGs, wordmark SVG light/dark variants
                         # + PNG, social preview) — README's top banner hotlinks the
                         # social preview from here (raw.githubusercontent URL so PyPI
                         # renders it too); docs-site copies live in docs/assets/
docs/                    # MkDocs source tree for the docs site (mkdocs.yml at repo root,
                         # .readthedocs.yaml drives the RTD build via uv)
  assets/                # site images (copies from imgs/): icon SVG = theme logo +
                         # favicon (mkdocs.yml), wordmark SVGs = index.md hero via
                         # Material #only-light/#only-dark + stylesheets/extra.css
  index.md               # site landing page (two-audience split: MCP users / library users)
  mcp/                   # setup.md (the end-user walkthrough, ex-INSTALL.md), tools.md, skills.md
  library/               # quickstart, auth, efactura, etransport, public, errors guides
  api/                   # mkdocstrings pages over the hand-written public modules
  anaf-reference/        # compiled ANAF API reference (oauth/efactura/etransport/public/spv;
                         # spv sources = vendored MfpAnaf/ClientSPV repo under _sources/clientspv/;
                         # declaratii/forms/ = e-guvernare form inventory (README = all 173
                         # DUK-filable forms bucketed by SME usage) + per-declaration
                         # completion guides dXXX.md (hands-on for the top two buckets):
                         # purpose & legal basis, who-files-&-when, row->XSD filling map,
                         # DUK-validated example instances, researched gotchas, then the
                         # technical XSD/DUK layer; big lookup tables split into dXXX-
                         # nomenclatoare.md (D100, D112); METHOD.md = the playbook for
                         # generating/updating them);
                         # ALSO served as MCP resources (ANAFPY_DOCS_DIR default) — don't move it
tests/                   # respx-mocked unit tests incl. test_mcp_spv.py (+ opt-in live: test_public_live.py, test_oauth_live.py, test_spv_live.py read-only; test_{efactura,etransport}_roundtrip_live.py file to TEST; test_declaratii_upload_live.py files D406T — sanctioned no-effect — to PROD, double-gated)
```

## Architecture & conventions

- **Both OAuth services share one host** `api.anaf.ro`, differing only by path prefix
  (`FCTEL/rest` vs `ETRANSPORT/ws/v1`) and `test`/`prod` segment. All of that lives in
  [_transport/base.py](src/anafpy/_transport/base.py); clients take an `environment`.
- **`PublicClient` is the odd one out**: the unauthenticated registries/bilanț live on
  `PUBLIC_HOST` (`webservicesp.anaf.ro`) — no `TokenProvider`, no `environment`
  (production only). Unlike the OAuth clients' no-auto-backoff stance, it **paces its
  own requests** (`min_request_interval`, default 1 req/s) because ANAF states that
  limit as a usage *rule*, not via 429s. Registry membership is read from the
  `registered` booleans, never from presence in `found` (RegAgric/RegCult return
  unknown CUIs in `found` with empty fields). The e-Factura register's HTTP 404 with a
  `found`/`notFound` body is a business "not found" (returned), not raised.
  `PublicClient` also carries the **stateless e-Factura document services**
  `validate_invoice` (`validare`) and `render_invoice_pdf` (`transformare`) — they
  live on the same host, need no auth, and exist only under the `prod` segment
  (moved from `EFacturaClient` 2026-07-04 so validation works with no OAuth
  credentials configured); only the MF signature check (`validate_signature`, on
  `api.anaf.ro`) stays on `EFacturaClient`.
- **SPV is the certificate-auth outlier** (`anafpy.spv`, added 2026-07-12,
  read-only by design — no submissions). It lives on `webserviced.anaf.ro`
  behind an F5 APM **cookie session**: the qualified certificate (USB token /
  cloud HSM, keys non-exportable — Python's `ssl` cannot present them) is used
  only by the interactive `SpvClient.login()` bootstrap, which drives the
  **OS-shipped curl** against the platform key store (macOS SecureTransport by
  Keychain name; Windows Schannel by thumbprint; NSURLSession hangs on the APM
  renegotiation — don't go back there). All other calls are plain httpx riding
  the persisted cookie session (a bearer credential, stored 0600 like tokens);
  `/my.policy_nonce` revalidation hops are followed transparently, a bare
  `/my.policy` bounce raises `AnafAuthError` — the client never re-runs the
  2FA-firing bootstrap on its own. **Deviation from the no-retry rule**: the
  SPV reads (`list_messages`, `download_document`) retry transient transport
  errors (expo+jitter, 3 attempts) since every SPV call is an idempotent GET;
  `request_report` stays single-shot and does **no client-side dedupe** —
  the library is a thin stateless transport (decided 2026-07-12: a client-layer
  dedupe cache was built, then removed; a repeated `cerere` is harmless), and
  guarding agent loops against repeat filings is the MCP layer's job (M2).
  The wire reference is
  [docs/anaf-reference/spv/api.md](docs/anaf-reference/spv/api.md); live facts
  (choreography, 2FA-per-bootstrap, flakiness) are recorded in its §1.1.
- **Auth is a separate layer.** Clients receive a `TokenProvider` and drive httpx via
  the `AnafAuth` (`httpx.Auth`) class, which handles transparent token refresh. The
  qualified-certificate step happens only in the interactive `anafpy auth login` browser
  flow; code-exchange and refresh are headless. Don't add cert/mTLS handling to clients.
  ANAF's portal only registers `https://` callback URLs (an `http://` one 400s —
  verified 2026-07-02); the login captures the code via `--paste` (no listener, the
  baseline), a TLS listener (`--tls-cert/--tls-key`), or plain HTTP behind an external
  TLS terminator — the listener binds *before* the browser opens (a fast redirect must
  not outrun it) and the CLI falls back to paste if it can't start or times out.
  Every login binds a random OAuth `state` (login-CSRF protection, 2026-07-04):
  the listener 400s (and keeps waiting on) redirects that don't echo it, and the
  paste parser rejects a mismatching URL — a pasted bare code is exempt.
  `anafpy auth logout` is **purely local** — it clears the token store and makes
  no network call: ANAF's documented `/revoke` is not reachable headlessly
  (live-probed 2026-07-05: 302 to the F5 APM login wall, identical to a
  nonexistent path — see the oauth reference §3), so tokens end only by expiry
  or the portal's Renunțare Oauth. Don't (re)add a revoke call unless ANAF
  actually routes the endpoint.
  Token persistence is the `TokenStore` protocol (`load`/`save`/`clear`):
  `KeyringTokenStore` (OS credential store — the **default** backend since
  2026-07-05, `keyring` is a core dependency; splits the set across vault
  entries on Windows, whose 2560-byte blob cap is smaller than one ANAF JWT) or
  `FileTokenStore` (JSON file, the opt-out for Docker/headless hosts); selected
  by `ANAFPY_TOKEN_STORE_BACKEND` / `--store-backend`. The test suite installs
  an in-memory fake keyring **autouse** so no test can touch the real OS store.
- **Clients are async**, own their `httpx.AsyncClient` (unless one is injected), and are
  async context managers (`async with EFacturaClient(...) as c:`).
- **Discrete methods do NO transport retry** — one call, one result-or-raise — so the
  non-idempotent `upload` POST is never silently repeated. Consumers bring their own
  retry. `tenacity` appears only in the `upload_and_wait` poll loop (retries on the
  *business* processing state, not on transport errors) and in the SPV client's
  documented deviation (idempotent-GET reads retry plain network failures only —
  received HTTP answers, 429 included, surface immediately; `wait_for_report` is
  another business poll).
- **Module style**: `from __future__ import annotations`, explicit `__all__`, module +
  class docstrings, Google-style docstring sections. Line length 88. Keep new code in the
  voice of the surrounding files.
- **English identifiers everywhere in hand-written code**: variables, parameters, and
  model field names are descriptive English; ANAF's Romanian wire names survive only
  as Pydantic validation aliases (`data_creare` -> `created_at`), string literals
  (dict keys, query params, URL segments), and the generated schema models. Domain
  acronyms with no sensible translation (`cui`, `cif`, `uit`, `caen`) and enum
  members named after ANAF's own codes stay as-is.

## MCP server (`anafpy.mcp`)

- **Local stdio connector built on the phase-1 clients.** `create_server(config)`
  returns a `FastMCP`; `AppContext` owns one `TokenProvider` + lazily-built clients and
  closes them in the server lifespan. The server reads the existing token store and
  refreshes headlessly — it never drives the cert/browser step (that stays the CLI).
- **Workflow skills live in the `anafpy-workflows` plugin, and are ALSO served as
  MCP prompts** (skills-as-prompts 2026-07-03; plugin-as-source 2026-07-18). The
  playbooks' single home is `plugins/anafpy-workflows/skills/*/SKILL.md`: installed
  from the marketplace they surface in Cowork as Agent Skills (the claude.ai plugin
  ecosystem brings bundled skills into chat + Cowork — verified 2026-07-18 — unlike
  Claude Code marketplace plugins, which are Code-tab-only), and the MCP server
  re-serves that same tree as same-name prompts (`ANAFPY_SKILLS_DIR` defaults there;
  `anafpy.mcp.prompts` reads frontmatter + body; optional `source` argument seeds
  the workflow) for prompt-capable clients (Claude Desktop, `claude mcp add`). One
  source, two consumers — the server reads the plugin's SKILL.md files, never
  duplicating them; parsing is `python-frontmatter`'s (the `mcp` extra), with
  `mcp/prompts.py` only enforcing that `name`/`description` are present (missing
  fields fail loudly at server start). A skill drives the MCP tools, so the Cowork
  user needs both the plugin (skills) and the anafpy connector (tools, via
  `anafpy-setup`).
- **e-Factura filing tools.** Two STEP-1 shapes feed one gate: `efactura_prepare`
  takes complete UBL XML (`UblXmlInput {xml|path}`) verbatim — the strongly
  recommended path when upstream invoicing software produced the document
  (DESIGN.md §1: SPV purges after ~60 days; the durable record lives
  upstream) — and
  `efactura_prepare_invoice` composes the XML from the client-layer
  `InvoiceDocument`. Prepare returns the invoice preview (strict read-back of
  the exact bytes), a confirmation token, and — composed path — informational
  `local_findings` from `authoring.validate()` that **never withhold the token**.
  `efactura_submit` verifies + redeems the token single-use and uploads with the
  `standard` derived from the XML (UBL/CN); `efactura_get_status` polls to
  `ok`/`nok` and hands `download_id` to `efactura_download`.
- **Binary artifacts go to disk (or a resource), never into context.** The model
  works from the flat `invoice` view; `efactura_download` optionally writes the
  signed archive ZIP (`save_zip_as`) and ANAF's `transformare` PDF rendering
  (`save_pdf_as`, best-effort — failures surface in `pdf_error`, never fail the
  download; rendered with `validate=False` since the message already passed ANAF
  validation at filing) to caller-given paths — the server is local stdio, so its
  filesystem is the user's (this is what enables batch flows like "save last
  month's invoices as `<date> - <partner>.pdf`", where the agent names the files).
  An **existing file is never silently replaced** (added 2026-07-04): a name
  collision is refused and reported in `pdf_error`/`zip_error`, and only an
  explicit `overwrite=true` replaces the file — so a batch flow can't lose an
  invoice to two identical names, while a deliberate re-export stays one flag away.
  The PDF is also the resource template `anafmsg://{message_id}/pdf`
  (fetch+convert on read); there is deliberately **no ZIP resource** — a base64
  ZIP serves neither the model nor any host UI. Don't return base64 blobs from
  tools (decided 2026-07-03). `etransport_prepare_declaration` /
  `_deletion` / `_confirmation` / `_vehicle_change` take the client-layer flat models
  or scalars, render the XML via `render_etransport`, and return it in
  `PreparedTransport.xml` alongside the preview and token (the e-Factura tools
  return the sibling `PreparedInvoice`; both extend the shared
  `PreparedSubmission` gate shape); the caller passes that
  XML back to `etransport_submit` verbatim (the token is bound to the rendered
  bytes, so any mangling fails closed). `etransport_prepare` (`EtransportXmlInput`)
  remains for callers with ready-made XML. `etransport_nomenclature` lists the XSD
  code lists (names accepted anywhere an enum-coded field is) plus the code-only
  `unit_codes` — the UN/ECE Rec 20/21 list ANAF's Schematron enforces for goods
  lines, carried in
  [mcp/etransport/unitcodes.py](src/anafpy/mcp/etransport/unitcodes.py) — see
  [mcp/etransport/nomenclature.py](src/anafpy/mcp/etransport/nomenclature.py).
- **SPV tools are read-only mailbox access** (added 2026-07-12): `spv_status`
  (session smoke test — surfaces `authorized_cuis`, the certificate's
  authorization inventory), `spv_lista_mesaje` (paged, `tip`-filterable),
  `spv_descarca` / `spv_asteapta_raport` (PDFs to caller-given paths via the
  shared `write_artifact` collision guard — ARTIFACT_SAVING annotations; a
  message's document is also the resource template `spvmsg://{mesaj_id}/pdf`,
  the SPV sibling of `anafmsg://` — needs an active session, since a resource
  read can't prompt a login), and
  `spv_cerere` (per-type param validation at the `ReportRequest` model;
  **in-process same-day dedupe** in `AppContext.spv_request_log` guards agent
  loops — the persistent-cache idea was rejected, the library stays stateless;
  annotated REQUESTING — mutating, non-destructive, non-idempotent — since it
  files an additive request with ANAF, so a host must not auto-invoke it as a
  read).
  `spv_nomenclature` lists the report types — each with a one-line English
  description (`ReportType.description`: members are `(value, description)`
  tuples via the enum-with-attributes pattern, carried from the reference's
  §4.1 tables; a member without one fails at import) so the model can map
  "my VAT return for March" onto `D300` — with per-type
  params, a CAF-not-requestable note, and the fixed
  `Adeverinte Venit` `motiv` list — the model is **meant** to map the user's
  stated purpose onto the exact entry (decided 2026-07-13; an MCP-elicitation
  host-side picker was parked: Claude Desktop/Cowork answers
  `elicitation/create` with a synthetic instant cancel), and a wrong `motiv`
  errors with the full accepted list so the flow self-heals.
  Certificate selection is `spv_list_certificates` + `spv_select_certificate`
  (persists to `ANAFPY_SPV_IDENTITY_FILE`). The certificate/2FA login IS a tool
  (`spv_login`, added 2026-07-13 reversing the M2 stance): unlike the OAuth
  browser flow it needs no host UI — the human gate is the out-of-band PIN/2FA
  approval — and APM sessions die in under an hour, so terminal round-trips per
  hour would kill the Cowork UX. It is gated on `confirm=true` (the model must
  relay the user's explicit ask; one attempt per call, flaky-handshake failures
  come back as `logged_in=false` + retry guidance, not exceptions), uses a
  throwaway `SpvSessionProvider` over the shared store (single source of truth
  — the long-lived client picks the session up on its next read), and
  `anafpy spv login` remains the CLI path. No two-step gate anywhere in SPV:
  no declaration is ever filed (reports are information requests) — honesty
  about `spv_cerere`'s side effect lives in its annotations, not a gate.
- **Declaration authoring tools are LOCAL** (`anafpy.mcp.declaratii`, added
  2026-07-15 — M1: authoring + signing): `declaratie_validate` /
  `declaratie_render` run ANAF's DUKIntegrator (validation authority is ANAF's —
  we run its per-form validator jars, never re-implement rules; the `nr_evid`
  helper is composition, not validation), `declaratie_nr_evid` composes the
  payment-evidence number for the self-assessed forms (`form=` D300/D100/D710/
  D101/D301 — each with its own code slot, prefix, and position-18 flag),
  `declaratie_duk_status` surfaces CLI-mode DUK's non-auto-update
  staleness. `declaratie_sign` is consequential: gated on `confirm=true`
  (mirrors `spv_login` — failures return `signed=false` + guidance, not
  exceptions) because it fires the certificate's PIN/2FA, and **no MCP tool ever
  accepts a PIN** — the raw signature is delegated to the OS
  (`KeychainRawSigner`), never entering model context. PDFs land on disk via
  the shared `write_artifact` collision guard, never base64. Needs
  `ANAFPY_DUK_DIR`; signing is macOS-only for now (the `RawSigner` protocol is
  the Windows seam). See the [DUK reference](docs/anaf-reference/declaratii/duk.md).
  Two tools close the post-filing loop over the **public, no-auth**
  StareD112 service (added 2026-07-16; they need neither `ANAFPY_DUK_DIR` nor any
  login): `declaratie_status` (READ_ONLY; upload index + CUI → the CUI's
  last-3-months filings with per-document state — the "no declaration identified"
  page is a returned business outcome, `found=false`) and `declaratie_recipisa`
  (ARTIFACT_SAVING; saves the signed filing-receipt PDF — ANAF answers an empty
  PDF body for an unknown/expired index, returned as `ok=false`; recipisas last
  ~60 days). Wire reference:
  [docs/anaf-reference/declaratii/stared112.md](docs/anaf-reference/declaratii/stared112.md).
- **Declaration FILING is the M2 gate** (added 2026-07-20, **opt-out** via
  `ANAFPY_DECLARATII_UPLOAD=off` — filing goes to the production portal only,
  so a user can strip the capability; the sign tool's guidance then points at
  manual filing). Four tools over `DeclarationUploadClient`, with the portal
  login deliberately OUTSIDE the submit cycle: `declaratie_portal_login`
  (confirm-gated like `spv_login`; builds a per-attempt
  `PortalCurlBootstrapper` from the persisted SPV certificate selection and
  installs the cookie set into the long-lived client — in-memory only, portal
  sessions die after ~10 idle minutes, nothing worth persisting),
  `declaratie_portal_status` (READ_ONLY no-2FA probe: `probe()` GETs the app
  landing page and judges by the upload-form marker), and the two-step
  `declaratie_prepare` → `declaratie_submit` over the shared `gate.py`
  primitives (kind `declaratie.upload`; token bound to the exact signed-PDF
  bytes + the multipart filename — no CIF context, the CUI rides inside the
  signed document). `declaratie_submit` **re-probes the session before
  consuming the single-use token**, so a lapsed login never burns the human's
  approval (the same token files after re-login); an APM bounce on the POST is
  reported as "nothing was filed", any other upload failure as UNKNOWN with a
  check-StareD112-before-refiling instruction. `declaratie_prepare` runs a
  local signature sniff (`/ByteRange` + `adbe.pkcs7.detached`), informational
  only — the prepare-never-blocks rule holds.
- **Flat models live at the client layer**
  ([efactura/authoring/](src/anafpy/efactura/authoring/),
  [etransport/models.py](src/anafpy/etransport/models.py)) — the MCP layer only
  consumes them. Two families, both **strict and bidirectional**. The authoring
  `InvoiceDocument` family: `read_invoice` views full-fidelity,
  `build_invoice`/`render_invoice` author; wire amounts land in explicit fields
  so round-trips are byte-stable; `DownloadedMessage.view` wraps the reader
  never-raising for the inbox (strict reading covers every ANAF-validated
  document, and the raw bytes + full UBL model remain the fallback tiers).
  The e-Transport
  `FlatTransport` / `FlatDeletion` / `FlatConfirmation` / `FlatVehicleChange`
  (union `FlatSubmission`) are a **full translation** of the XSD:
  `read_flat_transport` views, `build_etransport` / `render_etransport` author
  (only the schema's unused `xs:any` hooks are not carried); enum-coded fields
  are typed with the generated XSD enums, accept name or code, and serialize as
  names.
- **Tool display names**: every tool has an English MCP `title` following
  `Service: operation` — services are `e-Factura`, `e-Transport`, `ANAF Info`
  (public no-auth lookups), `SPV`, and `Declarations`, plus bare `ANAF` for
  `auth_status`. Titles are UI-only (the model sees `name` + `description`);
  keep them single-language.
- **Branded service names in prose**: in strings, messages, and docs the services
  are written exactly `e-Factura` and `e-Transport` — even at the start of a
  sentence or title. This is the branding ANAF itself uses on its website
  (decided 2026-07-03). Exceptions: identifiers stay English-convention
  (`EFacturaClient`, `efactura_*`), ANAF wire facts stay verbatim (the
  `eTransport` XML root/namespace, endpoint names, URLs), and quotes of ANAF's
  own material in `docs/anaf-reference/` keep ANAF's spelling.
- **Read-first, two-step gated mutations.** Read-only tools (`*_list*`, `*_status`,
  `*_lookup`, `etransport_nomenclature`, `auth_status`, and — over the no-auth
  `PublicClient`, so usable even with no OAuth credentials configured —
  `efactura_validate` and the `anaf_*` public lookups, registries + financial
  statements) are annotated `readOnlyHint` and freely
  callable. `efactura_download` is also freely callable but carries honest
  annotations (`readOnlyHint=False`, idempotent, non-destructive) because it may
  write files at caller-given paths; the two-step gate is for ANAF filings only.
  Filing — **both services** — is split `*_prepare*` →
  `*_submit`: prepare parses (or composes) the XML for a preview and returns an
  HMAC **confirmation token** (`mcp/gate.py`) bound to the exact XML bytes and
  the CIF; submit requires that token (same document, same CIF) **and**
  `confirm=True`, and each token is **single-use** (`TokenLedger`) so a
  non-idempotent upload is never repeated on one approval. Don't collapse this
  into a `dry_run` bool.
- **Validation authority is ANAF's.** `efactura_validate` calls the server-side
  `validare` endpoint via `PublicClient.validate_invoice` (authoritative by
  definition). `validare`/`transformare` are **public, no-auth, prod-only** (their
  TEST paths 404), which is why they live on `PublicClient`
  (`webservicesp.anaf.ro/prod`) — validation works on test configs too, needs no
  OAuth credentials, and files
  nothing; e-Transport has no standalone validator — ANAF validates on upload.
  Local checks exist at two tiers, neither authoritative: **field-level shape
  checks at model construction** (both flat families — e-Transport mirrors its
  Schematron's unconditional rules: UIT check digits, gross ≥ net, ...; the
  authoring models enforce formats, `BR-RO-L*` lengths, `BR-CL-*` code lists,
  decimal budgets, VAT rate shapes) and, for e-Factura authoring only, the
  **hand-translated cross-aggregate rule set** `authoring.validate()` (findings
  with official BR-* ids as *values*; pure Python — the Schematron/saxonche
  *engine* removed 2026-07-02 stays removed). The inviolable rule kept from that
  removal: **MCP `prepare` never blocks on a local check** — findings ride
  `local_findings` informationally, the token is always issued, and the human
  review + ANAF's verdict are the gates. Only the library-level
  `render_invoice`/`upload_invoice` fail closed by default
  (`skip_validation=True` opts out).

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

`src/anafpy/efactura/ubl/` and `src/anafpy/etransport/schema/` are generated by the
`scripts/generate_*.py` scripts from vendored XSDs in `schemas/` —
[schemas/README.md](schemas/README.md) is the **provenance record and
re-vendoring playbook** (source URLs, vendored subsets, and the step-by-step for
a CIUS-RO revision, including re-aligning the hand-translated rules). They are committed as
source but excluded from ruff, mypy, and pyright/Pylance (see `extend-exclude` /
`exclude` in [pyproject.toml](pyproject.toml)). To change them, edit the script /
re-vendor the XSD and regenerate; never edit the output by hand. Note: `xsdata[cli]`
is pinned `<25` — the `xsdata-pydantic` plugin targets the 24.x line and newer core
emits invalid fields. The e-Transport script post-processes the output: nomenclature
enum members get descriptive names derived from the XSD's own `xs:documentation`
annotations (`CodJudetType.CLUJ`, `CodTaraType.ROMANIA`; operation types use ANAF's
sigla with the full label as a trailing comment: `CodTipOperatiuneType.TTN`, ...)
instead of `VALUE_<code>`.

`src/anafpy/efactura/authoring/_codelists.py` is likewise generated — by
`scripts/generate_efactura_codelists.py` from the EN16931/CIUS-RO Schematron
sources vendored under `schemas/efactura/schematron/1.0.9/` (the `BR-CL-*` closed
code lists: currencies, countries, units, VATEX, EAS, ...). It is lint/type-clean
so it is NOT excluded from the gates, but the same rule applies: regenerate,
never hand-edit.

Public UBL entry points: `from anafpy.efactura import Invoice, CreditNote`.

## ANAF response formats

Response schemas come from ANAF's official per-endpoint **swagger presentations**
(vendored 2026-07-02 under `docs/anaf-reference/_sources/{efactura,etransport}-swagger/`
and folded into `docs/anaf-reference/*/api.md`) — the API PDFs cover URLs/params only.
First live TEST confirmations 2026-07-02: the e-Factura paginated list's no-results
shape (200 + `eroare` note) and the e-Transport `lista` no-results shape
(`Errors[].errorMessage`, `ExecutionStatus: 1`) both matched the docs exactly. A full
e-Transport TEST **roundtrip** 2026-07-02 (upload → `stareMesaj` `in prelucrare`→`ok`
→ `lista` → `info`) confirmed the upload/status/lista-with-results shapes and surfaced
one doc gap: `info`'s no-results case rides a **top-level singular `error` string**
(not `Errors[]`) — now handled by `_InfoEnvelope` / `_parse_info`. A full **e-Factura
TEST roundtrip** the same day (upload → `stareMesaj` `in prelucrare`→`ok` →
`descarcare` ZIP → paginated list with results) confirmed the e-Factura
upload/status/download shapes, and established that **`validare` and `transformare`
are prod-only** (the `test` paths answer HTTP 404) — since they are also public and
no-auth, they live on `PublicClient` (`validate_invoice` / `render_invoice_pdf`),
which always calls them on `webservicesp.anaf.ro/prod`. A **production** message-list
pull (2026-07-06, 522 messages) established that the list's `cif_emitent` /
`cif_beneficiar` are **never emitted** despite ANAF's API PDF listing them as
response fields — the swagger `Mesaj` schema (the response-schema authority) omits
them, and the CIFs ride only inside the free-text `detalii` (see the e-Factura
reference §3). The
`live`-marked `tests/test_oauth_live.py` re-confirms the authenticated TEST shapes on
demand (needs `.env` credentials + `anafpy auth login`). The **public services** have no swagger —
their reference (`docs/anaf-reference/public/api.md`) is compiled from ANAF's
instruction files and **was live-confirmed in production** (2026-07-02); the `live`
test marker re-confirms those shapes on demand. When touching parsing code, treat the
doc as the source of truth and prefer being explicit over silently returning empty
results.

## Conventions for changes

- Keep `pytest`, `ruff`, `mypy --strict`, and `mkdocs build --strict` green;
  add/extend respx tests for client
  behavior changes (upload→poll→download, `nok` path, 401-refresh, 429 surfacing).
  The respx suite is the gate; the `live`-marked smoke tests
  ([tests/test_public_live.py](tests/test_public_live.py) — public services;
  [tests/test_oauth_live.py](tests/test_oauth_live.py) — authenticated TEST, read-only,
  credentials from the gitignored repo-root `.env` loaded by `tests/conftest.py`) exist
  only to re-confirm wire shapes on demand (`ANAFPY_LIVE=1`) and are skipped by
  default — don't move behavioural assertions there, and keep them read-only. The **three
  deliberate exceptions** are the filing files —
  [tests/test_etransport_roundtrip_live.py](tests/test_etransport_roundtrip_live.py)
  **files** a domestic declaration composed via the flat authoring models — also
  keeping anafpy's own rendered XML honest — (upload → `stareMesaj` → `lista` →
  `info`) and
  [tests/test_efactura_roundtrip_live.py](tests/test_efactura_roundtrip_live.py)
  **files** a minimal CIUS-RO invoice composed via the authoring models and
  filed with `upload_invoice` (upload → `stareMesaj` → `descarcare` → list),
  also proving the strict `DownloadedMessage.view` on ANAF's returned XML —
  **TEST only, never prod** — to keep the filing wire shapes honest — and
  [tests/test_declaratii_upload_live.py](tests/test_declaratii_upload_live.py),
  which **files a D406T on the production portal**: D406T is ANAF's sanctioned
  no-fiscal-effect SAF-T test declaration (there is no TEST environment for
  declaration filing — DESIGN.md §12), and the test is double-gated
  (`ANAFPY_LIVE_FILE_D406T=1`) because it fires the certificate 2FA twice.
  Don't add uploads to any other live file, and never file anything but D406T
  in that one. The same file's `test_validare_agrees_with_local_rules`
  is the **drift tripwire**: it asserts local `authoring.validate()` verdicts
  track ANAF's `validare` both ways (clean passes clean; a BR-CO-16 break is
  flagged by both with the same rule id) — when a CIUS-RO revision lands, this
  is the test that announces it (then: re-vendor the `.sch`, regenerate the code
  lists, re-align the translated rules). All live suites resolve credentials
  from the gitignored `.env` and the token store via the conftest
  `live_token_store` fixture (file store if present, else the REAL OS keyring —
  the one sanctioned exception to the autouse fake).
- **Keep the docs in sync with the change.** When a change alters the public surface,
  status, layout, or conventions, update the affected docs in the same change:
  [README.md](README.md) (the GitHub/PyPI landing page — overview, install, quick
  usage; deep detail lives on the docs site, which README links with absolute
  `anafpy.readthedocs.io` URLs), the docs-site pages under `docs/`
  ([docs/mcp/setup.md](docs/mcp/setup.md) — the end-user setup walkthrough,
  accountant audience: ANAF app registration, cert login, Claude/Cowork config;
  [docs/mcp/tools.md](docs/mcp/tools.md) + [docs/mcp/skills.md](docs/mcp/skills.md)
  — the MCP surface; `docs/library/*` — the library guides), this `CLAUDE.md`
  (layout, commands, conventions), [DESIGN.md](DESIGN.md) (design
  decisions), and `docs/anaf-reference/` (only when ANAF API facts change — keep
  its provenance frontmatter intact). A new page goes into `mkdocs.yml`'s `nav`.
  Don't let docs drift behind the code.
- **Repo boundary**: this repo is the whole project (typed clients + local stdio MCP
  server + skills + docs) and is intended to be publishable. Never add hosted-service
  code here — token custody, multi-tenancy, and an OAuth-provider surface toward
  Claude are out of scope (DESIGN.md §11, decided 2026-07-04).
- Don't commit, push, or create branches/PRs unless asked.
- The remote is `github.com/robert-malai/anafpy`. CI is GitHub Actions:
  `.github/workflows/ci.yml` runs pytest on 3.12 + 3.13 across
  ubuntu/macos/windows (the SPV layer has platform seams; the suite itself is
  respx-mocked and credential-free everywhere) with ruff / mypy --strict / the
  strict docs build on the ubuntu leg for every
  push/PR. Every test leg uploads coverage to Codecov (merged per commit —
  the macOS/Windows legs execute SPV platform seams ubuntu never does;
  generated model packages are omitted via `[tool.coverage.run]`; upload
  failures never fail CI); `release.yml` re-runs them on a `v*` tag, checks the tag against
  `pyproject.toml`'s version, builds, and publishes to PyPI via trusted
  publishing (OIDC, environment `pypi` — no stored token). The version is
  declared in `pyproject.toml` **and** `anafpy.__version__`;
  `tests/test_version.py` keeps them agreeing.
