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
**e-Transport** services, optimized **MCP/Claude-first**. It is not accounting
software — no persistence, no reconciliation, no ledger — but it **can fully
author an e-Factura document** (design update 2026-07-08): the bidirectional
flat models in `efactura.authoring` compose a complete CIUS-RO invoice or
credit note from business fields, for callers (and agents) with no upstream
invoicing system.

- **e-Factura outbound: structured authoring fully supported, upstream
  invoicing software strongly recommended.** When the caller runs invoicing
  software, they supply the **complete UBL XML** it exported and anafpy never
  re-composes it — the upstream document is authoritative, re-deriving it adds
  only drift, and — decisively — **ANAF's SPV is not invoice storage**: it
  purges filed messages after ~60 days (e-Factura reference §3), so the
  durable record must live in a system the caller owns, which an invoicing
  system provides for free. Where no such system exists, `efactura.authoring`
  is the first-class path (§4 Authoring has the full design); archiving the
  signed ZIPs is then the caller's own job. `EFacturaClient.upload` files XML;
  `upload_invoice` files an authored document.
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
  original zip/XML/PDF **as-is**, and parse received UBL into the flat
  `InvoiceDocument` view. e-Transport stays outbound + own-declaration status
  only.
- **One e-Factura flat surface.** `authoring.InvoiceDocument` is the
  full-fidelity bidirectional model (§4 Authoring) — strict when authoring,
  lenient when reading (§4, *Reading is not authoring*, 2026-07-28).
  `DownloadedMessage.view` degrades to `None` (never raises) on what remains
  unreadable, e.g. code-list edition drift until the vendored lists are
  refreshed. The e-Transport flat models keep the same bidirectional contract.
- **Stateless** beyond the OAuth token store: callers own persistence of upload
  indices, message ids, and statuses. Discrete one-call-one-result methods, no
  transport retry.

Python **3.12+** (floor set by PEP 695 syntax in the flat models and lookups; dev
pin is 3.13), **httpx**, **Pydantic v2**.

Since shipped, expanding the original scope: **SPV** (read-only mailbox over a
certificate-bootstrapped cookie session — landed 2026-07-12) and
**declaration authoring + signing** (`anafpy.declaratii`, landing 2026-07-15 —
local D300 authoring, DUKIntegrator validation, qualified signing; plus
StareD112 filing-status/recipisa tracking, public no-auth, added 2026-07-16;
see §12). **Declaration filing landed too** (M2): the WAS6DUS portal-upload
client was live-verified 2026-07-17 (D406T) and the MCP two-step filing gate
followed 2026-07-20 — an **opt-out** feature (`ANAFPY_DECLARATII_UPLOAD=off`),
since declarations file on the production portal only.

Out of scope: local persistence of documents; reconciliation / accounting logic;
inbound e-Transport; e-TVA; CII syntax; e-Transport API v1; a sync facade
*(dropped 2026-07-03 — the consumers that exist are async: the MCP server and
`asyncio.run` scripts; was to be generated via `unasync`)*.

## 2. Cross-cutting architecture

- **Async only** (see §1 for the dropped sync facade).
- **Structured pattern matching is the preferred branch form** (adopted
  2026-07-26). The 3.12 floor means `match` is always available, and the three
  hand-written places that already used it (SPV's `required_parameters`, the
  login-flag truth table in `anafpy auth login`, `spv_nomenclature`) read
  better than the chains they replaced — so it became the house default. The
  operative rule — which branch shapes take `match`, which stay plain `if` —
  lives in CLAUDE.md. Not a rewrite mandate.
- **The walrus operator is the preferred assign-then-test form** (adopted
  2026-07-26, the companion rule). The codebase had grown two spellings of the
  same shape — a standalone assignment followed by its test, next to the
  `if (x := f()) is None:` already used in ~40 places — and the two-line form
  buries the fact that the binding exists only to be tested. The deciding
  criterion is **lifetime, not brevity**: fold only when the binding lives and
  dies with the condition's branch. The operative rule and its exclusions live
  in CLAUDE.md. Both this and the pattern-matching rule are review
  conventions, not lint gates — ruff has no check that encodes either.
- **Single distribution** `anafpy` with optional extras (not a multi-package
  repo): `anafpy[mcp]` (the server) and `anafpy[declaratii]` (pyHanko signing,
  §12). The dependency inventory and each dependency's rationale live as
  comments in `pyproject.toml`; the notable reversals: `keyring` was promoted
  from an extra to core when it became the token-store default (§3), and a
  former `anafpy[validation]` (`saxonche`) extra was removed (§4 Validation).
- **`src/` layout** (ships generated code as package source); the annotated
  tree lives in CLAUDE.md.

The six network clients share only a small `_transport.HttpClientBase`
chassis: owned-versus-injected `httpx.AsyncClient` lifecycle, trailing-slash
base-URL convention, and network-error translation. An owned client is
constructed with the resolved service URL; an injected client is **never
mutated** — one with a non-empty `base_url` is accepted as-is (the test/proxy
seam), while an empty `base_url` raises `AnafConfigError` at construction
(silently stamping a URL onto a caller-owned client would mis-route a second
anafpy client sharing it). Request semantics and business-outcome parsing
remain in each service client. Package-level `models.py` modules are the
value-type homes; in particular, `declaratii/models.py` owns the DUK, signing,
portal-upload, and StareD112 outcomes without importing the optional pyHanko
stack.

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
  2026-06-28). No public CA may issue for localhost (CA/Browser Forum baseline
  requirements), so a silently-trusted local listener cannot exist; the **default**
  (decided 2026-07-21) is a TLS listener with a **per-attempt ephemeral
  self-signed certificate** (`auth/tlscert.py`; key pair in-memory, one expected
  browser interstitial announced by the CLI — proportionate to the ~yearly login
  cadence). Alternatives: a **user-supplied trusted certificate**
  (`--tls-cert`/`--tls-key`, e.g. mkcert — removes the warning, custody stays with
  the user), **paste mode** (`--paste`, no listener, the security baseline and
  automatic fallback when the listener can't start), or plain HTTP behind an
  external TLS terminator (`--no-tls`). A denied cert step surfaces as an
  `access_denied` error redirect, raised cleanly. (Evaluated and rejected:
  third-party redirect bounces — dangling-domain/custody risks;
  `localhost.direct`-style public-CA loopback certs — the distributed cert was
  found expired since 2025-02; structurally unreliable. Re-evaluated and rejected
  2026-07-21: shipping any cert+key in the wheel — a distributed private key is
  compromised by definition, and for a public-CA cert triggers 24h revocation;
  auto-installing a trust anchor mkcert-style — trust-store mutation on end-user
  machines, elevated prompts, Firefox/NSS matrix, anchor outlives uninstall; a
  hosted redirect page or Plex-style per-user cert issuance under a project
  domain — both put a project-owned domain in every user's ANAF registration
  (lapsed-domain code interception) and reverse the §11 no-hosted-surface
  boundary.)
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
  serializer code (no marshmallow). Hand-written on top: the **authoring
  package** (`efactura/authoring/`), whose strict `build`/`read` modules map
  `InvoiceDocument` ⇄ generated UBL both ways — strict reading covers every
  ANAF-validated document.

### Authoring (`efactura.authoring`, added 2026-07-08)

- One semantic model, EN 16931's: `InvoiceDocument` covers invoice *and* credit
  note (`kind` picks the render target; BT-3 type codes restricted per
  BR-RO-020), with the full business-group surface CIUS-RO admits — parties
  (seller/buyer/payee/tax representative), delivery, payment instructions
  (transfers/card/direct debit), document & line allowances/charges, item
  identifiers/classifications/attributes, attachments, periods, preceding
  references.
- **Computed by default, explicit override validated**: totals (BR-CO-10..16
  arithmetic) and the VAT breakdown (grouped by category+rate, BR-CO-17 rounding)
  are derived from the lines; explicit values — e.g. when reproducing an upstream
  document — are preserved on render and cross-checked by `validate()`.
- **Two-tier validation.** Construction enforces what one model knows
  unconditionally: formats, the `BR-RO-L*` length caps, the `BR-CL-*` closed code
  lists (generated from the vendored EN 16931 Schematron by
  `scripts/generate_efactura_codelists.py`), decimal budgets, per-category VAT
  rate shapes, RO county/sector rules. `validate()` runs the hand-translated
  cross-aggregate rule set (category regimes BR-S/Z/E/AE/K/G/O/L/M, totals,
  breakdown consistency, RO document rules) and returns findings with the
  **official rule ids**, mirroring the Schematron's own numeric tolerances.
  Live-confirmed 2026-07-08: ANAF's `validare` answers `valid` for a
  maximal-surface authored invoice; one divergence found and mirrored — ANAF
  enforces BR-51 as a fatal `string-length(BT-87) <= 10`, not the EN 16931
  digit-count warning. The same day, an authored invoice was **filed to TEST
  end to end** via `upload_invoice` (accepted, `stare=ok`, downloaded, and read
  back through the strict `view` cleanly); the live suite keeps both honest —
  `test_efactura_roundtrip_live.py` re-files on demand, and its
  `test_validare_agrees_with_local_rules` is the **drift tripwire** asserting
  local `validate()` verdicts track ANAF's both ways, so a CIUS-RO revision
  announces itself (the step-by-step re-vendor/regenerate/re-align playbook is
  `schemas/README.md`).
  - **The exemption reason is tier 2, not tier 1** (2026-07-26). The BR-*-10
    reason (BT-120/121) on categories E/AE/K/G/O looked like a single-model fact
    and was enforced only at construction — but the breakdown entry is *computed*
    when the author supplies none, and a computed entry has nowhere to get a
    reason. So an ordinary reverse-charge or intra-community invoice made
    `compute_vat_breakdown()` raise a raw pydantic `ValidationError` from inside
    `validate()` / `render_invoice()` / `compute_totals()` — out of the
    `AnafError` hierarchy, from a function documented never to raise. Computed
    entries are now built through a validation context that skips just that
    check, and `validate()` reports the gap as a fatal `BR-E/AE/IC/G/O-10`
    finding. A hand-written entry still must carry the reason at construction:
    that one *is* data hygiene.
  - **The tax registration identifier belongs to both parties** (2026-07-26,
    reversing the original standard-pure reading; issue #7). `Party` was modelled
    strictly on EN 16931, whose buyer block runs BT-44..49 and has no counterpart
    to the seller's BT-32 — so `tax_registration_id` lived on `Seller` and the
    reader dropped the buyer's. But CIUS-RO reuses that syntax slot: BR-RO-120
    identifies the buyer by `PartyLegalEntity/CompanyID` **or any**
    `PartyTaxScheme/CompanyID` — no VAT-scheme filter, unlike BR-AE-02/BR-IC-02
    next to it — and RO issuers put the bare CIF of a buyer below the
    VAT-registration threshold there, marked `!VAT`. Standard purity therefore
    cost real data on ordinary documents: the buyer's CIF was parsed and
    discarded, read→render was lossy, no field could author one, and our
    BR-RO-120 — translated as `BT-47 or BT-48`, narrower than the Schematron —
    fatally flagged documents ANAF had accepted, so a re-file failed closed.
    The field (plus `tax_registration_scheme`, which keeps the issuer's own
    marker through a round-trip) now sits on `Party`, and BR-RO-120 gained its
    third limb. BT-33 stays seller-only — UBL-CR-244 genuinely forbids
    `CompanyLegalForm` on the customer party. Renders default the marker per
    role: `FC` for the seller's BT-32, unchanged from what has been filed, and
    `!VAT` for the buyer, matching the market.
- **The reader is full-fidelity**: `read_invoice`/`parse_invoice` land every
  wire amount in the explicit fields (never recomputed), so round-trips are
  byte-stable and `validate()` can judge an upstream document's arithmetic.
  `DownloadedMessage.view` wraps it never-raising for the inbox.
  - **Reading is not authoring** *(REVISED 2026-07-28; the reader was strict,
    sharing the authoring construction checks)*. The premise — "every filed
    document passed ANAF's validation, whose rules the checks mirror, so strict
    reading is safe" — was simply false, and expensively so: across one
    operator's real inbox of **85 valid CIUS-RO downloads, `read_invoice`
    succeeded on zero**. All 85 parsed into `Invoice`/`CreditNote` and then died
    in the flat translation, silently, because `view` swallows the error into
    `None` (issue #9; found via `anaf-sync`, where every one landed as
    `unknown_unknown_unknown_<id>`). Four families, partitioning the corpus:
    negative amounts (34 — RO practice files a *storno* as a **type-380 invoice
    with negative values**, not a type-381 credit note); an empty optional
    element (25 — `<cbc:PostalZone/>` and friends, which UBL means as *absent*
    and pydantic saw as a zero-length string); contact free-text (25 — two
    addresses in one BT-43, a telephone of `-`); and a category-O line carrying
    an explicit `0` rate (1). So the reader now validates through a
    `_DERIVED_CONTEXT` marker that stands the construction checks down, while
    coercion, defaults and normalisation still run; empty/whitespace-only
    elements read as absent; and an orphan `schemeID` on an absent identifier
    is dropped. Rejected alternatives: `model_construct` (loses the coercion and
    defaults the reader needs) and an opt-in `strict=` flag (a default nobody
    would find, guarding a contract nobody wants).
    - **What stays fatal on read** is what the models genuinely cannot hold: a
      missing mandatory element, and the closed `BR-CL-*` code lists — which is
      the code-list drift tripwire `view` has always documented, now the *only*
      thing it means. `view` no longer fails silently either: the cause is kept
      on `view_error` and a `UserWarning` is emitted.
    - **Two authoring checks were wrong, not merely strict**, and were relaxed
      in both directions: BT-146's `ge=0` (CIUS-RO 1.0.9 **comments BR-27 out**
      of its UBL binding — the file's own header says "to correct problems
      regarding negative values for item net price"; BR-28 on BT-148 stays
      live), and category O rejecting a redundant explicit `0`, now read as
      "no rate". Everything else keeps its authoring strictness untouched.
  - **Derived values are never re-judged either** *(2026-07-28, same change)*.
    Running the 85-document corpus through the fixed reader found the leniency
    leaking: 12 of them read fine and then **failed to render**, because
    `compute_totals` / `effective_totals` rebuilt a plain `Totals` outside any
    context and the authoring checks re-fired on sums derived from the very
    amounts that make a storno negative. A read document that cannot render
    breaks the bidirectional contract outright. So the marker covers both cases
    and is named for the general one, `_DERIVED_CONTEXT`: a value the caller did
    not author — read off the wire, or computed by this module — is never
    judged. That subsumes the older `_COMPUTED_ENTRY_CONTEXT` (the BR-*-10 case
    above), which was the same lesson learned narrowly. `Totals` also lost its
    sign constraints outright: no EN 16931 or CIUS-RO rule constrains the sign
    of BT-107/108/110/111/113, and 12/85 accepted documents carry a negative
    BT-110.
  - **The corpus found two more reader bugs**, both producing *spurious fatal
    findings* on documents ANAF accepted — the failure mode a local rule set can
    least afford:
    - **BT-111 was dropped when BT-6 == BT-5** (48 of 85 documents). Issuers do
      set the accounting currency equal to the invoice currency; the single
      `TaxTotal` is then both BT-110 and BT-111, and BR-53 asks only that a
      `TaxAmount` in the accounting currency *exists*. `_totals` read it with an
      `elif`, so BT-111 stayed `None` and `validate` flagged a fatal BR-53.
      (Rendering was always safe — `build.py` only writes the second `TaxTotal`
      when the currencies differ.)
    - **Category O's rate grouped two ways** (1 document). One file spells the
      absent rate both ways: no `cbc:Percent` on the line, an explicit `0` on
      the tax subtotal. Keying them apart split the BG-23 group and produced a
      fatal BR-O-08. The four key constructions (three in `models.py`, one in
      `rules.py`) now share one `vat_group_key`, which keys category O without a
      rate at all per BR-O-05..07.
  - **Verified against the corpus** (2026-07-28, 85 real ANAF-accepted
    downloads): 85/85 read, 85/85 render back, 85/85 byte-stable on re-render,
    and `validate()` reports **zero findings** across all of them — local
    verdicts agreeing with ANAF's on every document, which is the strongest
    signal the translated rule set has had outside `validare`.
- `render_invoice` refuses fatally-invalid documents unless
  `skip_validation=True` (`InvoiceValidationError` carries the report);
  `EFacturaClient.upload_invoice` composes + uploads with the right `standard`.

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
  the authoring reader yield the `InvoiceDocument` view of supplier invoices.

### Retries & errors

The operative rules live in CLAUDE.md ("Error model"); the decisions behind
them: discrete methods do no transport retry so the non-idempotent `upload`
POST is never silently repeated (429 raises `AnafRateLimitError` with
`retry_after`, no auto-backoff — consumers own their retry policy); `tenacity`
is allowed only where the retried thing is safe — the business-state poll loops
and the SPV client's idempotent-GET reads; and the hybrid error model keeps
ANAF's business verdicts (`nok`, BR-RO findings) as typed return values, never
exceptions — a rejection is data, not control flow.

### Download

- `download` returns a **raw-preserving `DownloadedMessage`** with three tiers:
  (1) raw ZIP + raw signed-invoice XML bytes (the legally valid artifact, archived
  ~10 years) + signature; (2) lazily-parsed full `ubl.Invoice`; (3) the lazily-built
  `InvoiceDocument` view (the authoring reader in its lenient wire mode; `None`
  instead of raising, with the cause on `view_error` plus a warning).
  Tier 1 is authoritative; never parse-only.
- *(ADDED 2026-07-30)* **The closed 60-day window is its own exception,
  `AnafDownloadExpiredError(AnafResponseError)`.** `descarcare` answers HTTP 200
  with `{"eroare": "Fisierul nu mai poate fi descarcat …"}` once a message ages
  out (live-observed on 3 messages of a client archive; wire facts in
  `docs/anaf-reference/efactura/api.md` §4.1). Lumping it in with unknown-id and
  malformed-request faults left callers substring-matching Romanian prose out of
  `str(exc)` to tell "retry this" from "this is gone" — and ANAF's vocabulary is
  anafpy's job, not theirs. It is not a business outcome (nothing was judged) and
  not a returned value: `download` has no shape for "no document", and a caller
  who ignores it would archive nothing silently. Two constraints follow:
  - **The recognizer under-matches by design.** A downstream archiver uses this
    to skip a message *permanently*, so a false positive loses an invoice once
    the real window shuts. It parses the JSON body and reads `eroare` (never the
    composed message), matches one accent-stripped core clause rather than the
    whole sentence (ANAF rewords), and treats a parse failure, a missing/non-string
    `eroare`, or an unrecognised wording as "not this" — falling through to the
    plain `AnafResponseError`.
  - **Classification only, no retry change.** It subclasses `AnafResponseError`,
    which every `tenacity` predicate in the tree already excludes (the SPV reads'
    `retry_if_not_exception_type(AnafResponseError)`), so a terminal condition can
    never become retryable by inheritance. The wording test lives beside
    `is_empty_result_message` in `_transport/base.py`, ready for the same note on
    another endpoint.
  - Reachable without caller error: `listaMesaje` and `descarcare` anchor their
    60 days differently, so ANAF lists messages it then refuses to hand over —
    any 60-day lookback meets the boundary band.

### Validation

**The authoritative validator is ANAF's server-side `validare` endpoint**
(`PublicClient.validate_invoice`, `POST /validare/{FACT1|FCN}`; moved from
`EFacturaClient` 2026-07-04 — `validare`/`transformare` are public, no-auth,
**prod-only** services on `webservicesp.anaf.ro`, exactly `PublicClient`'s host,
so validation needs no OAuth credentials at all).

- *(REVISED 2026-07-02)* The original `anafpy[validation]` extra (vendored
  CIUS-RO Schematron compiled to XSLT 2.0, run via `saxonche`) was removed: a
  heavy native dependency; vendored rulesets drift as ANAF revises CIUS-RO
  (~yearly), producing false failures; and the MCP `prepare` gate's strictness
  ended up depending on whether an optional extra was installed.
- Local validation exists today in a different shape: the
  authoring package's **hand-translated rule set** (`authoring.validate()`, pure
  Python, no XSLT engine, no new dependency) — see *Authoring* above. Its role is
  **developer/agent feedback with official rule ids**, not a gate: `validate()`
  returns findings as values, and the MCP prepare tools surface them as
  informational `local_findings` while **still issuing the confirmation token**
  (the failure mode that killed the old extra — a local check silently blocking
  the flow — stays designed out). Only the library-level
  `render_invoice`/`upload_invoice` fail closed by default, and
  `skip_validation=True` is one flag away.
- Remote-invalid documents are **typed values** (`RemoteValidationResult`,
  findings in `messages`), never exceptions. e-Transport has no standalone remote
  validator: the pre-filing check is parse + human-reviewed preview; ANAF
  validates on upload.
- **A local pass is never authoritative; MCP `prepare` must not block on
  validation.** ANAF's verdict and the human review are the gates.

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
- **Structured authoring (ADDED 2026-07-03)** — e-Factura offers the same dual
  shape (§1, §4 Authoring). The flat models in `etransport/models.py`
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
- **Operations** map 1:1 onto the documented endpoints (registry lookups +
  financial statements; batched CUIs at one as-of date, capped per ANAF). The
  **async job variant** of the taxpayer lookup is deliberately not wrapped: its
  result downloads exactly once and the not-ready response is undocumented.
- **Business-vs-error mapping**: `notFound` CUIs and `registered is False` records
  are values; the e-Factura register's **404-with-`found`/`notFound`-body** is a
  business "not found" (returned), while a non-200 `cod` inside an HTTP 200
  envelope raises `AnafResponseError`. Membership always reads from the status
  booleans (RegAgric/RegCult return unknown CUIs under `found`).
- *(ADDED 2026-07-30)* **ANAF's WAF is a third channel, and it is ours to
  absorb.** The F5 fronting `webservicesp.anaf.ro` scans the posted invoice XML
  and answers a `Request Rejected` HTML page **with HTTP 200** when the document
  matches an attack signature — which real, ANAF-accepted invoices do (4 of ~525
  archived inbound messages: a relative `xsi:schemaLocation` reads as path
  traversal, `;CP ` in an address reads as a shell command). Wire facts and the
  live matrix: `docs/anaf-reference/efactura/api.md` §6.1. Three decisions:
  - **Detected in the shared transport, raised as
    `AnafWafRejectionError(AnafResponseError)`.** It is neither a PDF nor ANAF's
    JSON error shape, so without this every caller has to sniff `%PDF` itself and
    a naive one writes HTML into a `.pdf`. It belongs in `_request_checked`
    rather than in `PublicClient` because the page is infrastructure, not a
    service's answer — and it subclasses `AnafResponseError` so existing handlers
    keep working. It is *not* a business outcome: ANAF never judged the document.
  - **`xsi:schemaLocation` is stripped before posting** to `validare` and
    `transformare`. The attribute is advisory (the PDF is byte-identical with it,
    without it, and with an `http://` URL there), and it is the bait one issuer
    class emits on *every* document. Only the root start tag is rewritten, so
    element text that quotes the attribute survives untouched.
  - **`render_invoice_pdf(validate=False)` retries once on the validating path**
    when the `/DA` URL — which carries the stricter policy of the two — is
    blocked. A deliberate, narrow exception to "discrete methods do no transport
    retry": the service is stateless, public, and files nothing, the retried
    request is a different URL rather than a repeat, and the alternative is
    losing the artifact for documents ANAF itself accepted. It warns, so a caller
    who asked to skip validation learns that ANAF validated after all. Content
    signatures (`;CP `) are *not* neutralised — XML character references do not
    fool the WAF (tested), and rewriting an address would change what the PDF
    shows.

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

- **`ServerConfig()` is the only constructor** (adopted 2026-07-26, replacing a
  `ServerConfig.from_env()` classmethod). The factory existed only to translate
  pydantic's `ValidationError` into `AnafConfigError`, which left two doors to
  the same `BaseSettings` — and the door that skipped the translation was the one
  the tests used. Folding it in keeps every misconfiguration inside the
  `AnafError` hierarchy (§4 Retries & errors) at the cost of no longer naming the
  env read at the call site; `BaseSettings` reading the environment is taken as
  known. Done as a **`model_validator(mode="wrap")`, not an `__init__`
  override**: pydantic marks its metaclass `@dataclass_transform`, so a
  hand-written constructor — in any signature form — replaces the one type
  checkers synthesize from the fields, and a wrong keyword argument degrades from
  a static error to a runtime one. An explicit typed signature would also have to
  duplicate every field and default, and forwarding those defaults would beat the
  env entirely (init kwargs are pydantic-settings' highest-priority source, so
  `client_id=None` silently erases `ANAFPY_CLIENT_ID`). The wrap validator sits
  inside validation, so it covers construction from env and from kwargs alike;
  errors a settings *source* raises before validation (`SettingsError` on
  malformed JSON for a complex field) stay untranslated — moot while every field
  is scalar. The message is `str(exc)` verbatim: each field carries a
  `validation_alias`, so pydantic already names the offending variable and its
  accepted values, where the previous hand-written hint listed a fixed two and
  went stale as fields were added.
- **e-Factura filing tools.** An agent can draft a complete invoice for a user
  with no invoicing software — the MCP use case the authoring package (§4)
  unlocked. Two STEP-1 shapes feed one gate: `efactura_prepare` takes complete
  UBL XML verbatim (the **strongly recommended** path whenever upstream
  software produced the document, §1) and `efactura_prepare_invoice` composes
  it from the client-layer `InvoiceDocument` (§4 Authoring). Both return the
  preview (the strict read-back of the exact bytes) and a confirmation token
  bound to those bytes + the CIF; the composed path adds informational
  `local_findings` from the translated rule set (never withholding the token).
- **e-Transport outbound = composed from structured fields** (§5). The prepare
  tools take the flat models (scalars for the tiny lifecycle operations),
  render via `render_etransport`, and return the XML next to its *read-back*
  preview — the human approves exactly what will be filed — plus the token
  bound to those bytes; the caller echoes the XML to `etransport_submit`, and a
  mangled echo fails the token check, never files. `etransport_prepare` stays
  for ready-made XML; `etransport_nomenclature` exists so the model maps "vama
  Nădlac" → `NADLAC` instead of guessing (plus the UN/ECE Rec 20/21
  `unit_codes` ANAF's Schematron enforces on goods lines).
- **Safety: read-first, two-step gated filing** — the operative rule is in
  CLAUDE.md. The shape is deliberately **not a `dry_run` bool**: prepare
  returns an HMAC token bound to the exact bytes (+ CIF), submit requires it
  plus `confirm=True` and redeems it single-use, so one human approval files at
  most once. `efactura_download` is freely callable but annotated honestly
  (`readOnlyHint=False`, idempotent, non-destructive) since it writes files at
  caller-given paths.
- **Validation authority is ANAF's** (§4 Validation): `prepare` never blocks on
  a local check — `local_findings` inform the human review, the token is issued
  regardless.
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
- **SPV tools** (added 2026-07-12/13): read-only mailbox access, plus
  `spv_cerere` carried by honest REQUESTING annotations and an **in-process
  same-day dedupe** in `AppContext` (a persistent cache was rejected — the
  library stays stateless; a repeated `cerere` is harmless at the client
  layer, guarding agent loops is the MCP layer's job). **The certificate/2FA
  login IS a tool** (`spv_login`, 2026-07-13 — reversing the earlier
  logins-stay-CLI stance): unlike the OAuth browser flow it needs no host UI
  (the human gate is the out-of-band PIN/2FA approval), and APM sessions die
  in under an hour, so per-hour terminal round-trips would kill the Cowork
  UX. It is confirm-gated, one attempt per call, failures returned as
  `logged_in=false` + guidance. Report-type selection is model-driven over
  `spv_nomenclature`'s per-type English descriptions (decided 2026-07-13); an
  MCP-elicitation host-side picker was **parked** — Claude Desktop/Cowork
  answer `elicitation/create` with a synthetic instant cancel — and a wrong
  `motiv` errors with the full accepted list so the flow self-heals. No
  two-step gate anywhere in SPV: report requests are additive information
  requests, not filings.
- **Tool descriptions are structured, not packed** (adopted 2026-07-26; the
  operative rule is in CLAUDE.md). Every description became an inline
  `cleandoc("""…""")` literal rather than implicit string concatenation. Two
  reasons. The shipped text: a concatenated description reaches the model as
  one unbroken line, which buried genuine tables (StareD112's state wordings,
  the per-form `nr_evid` inputs, the `accepted` verdicts, the nomenclature
  `kind` lists) that now render as bullets. And maintenance: ruff never reflows
  string literals, so a one-word edit meant hand-rewrapping every line after
  it. `inspect.cleandoc` (not `textwrap.dedent`) because FastMCP ships
  `description or fn.__doc__` **verbatim** with no dedent of its own, and
  cleandoc strips the decorator indent *and* the framing blank lines in one
  call. Function docstrings were rejected for the same reason — no cleandoc on
  that path, so the indent would leak onto the wire, and these are model-facing
  instructions rather than the human contract.
- **Display names**: an English `title` per tool, `Service: operation` (the
  operative rule is in CLAUDE.md). One language only: MCP has no title
  localization, and the model never sees titles (it works from `name` +
  `description`), so Romanian conversation quality is unaffected.
- **ANAF reference exposed as MCP resources** (with draft/Romanian notes) so the
  skill can ground BR-RO explanations and code lists.
- **Workflow skills served as MCP prompts** (2026-07-03; the skills' home moved
  to the `anafpy-workflows` plugin 2026-07-18, see §11): prompts are the
  closest MCP primitive to a skill but **user-invoked** — this is how the
  playbooks reach every MCP consumer. The SKILL.md files stay the single source
  of truth (read at server start via `python-frontmatter`, failing loudly when
  `name`/`description` are missing).
- **Auth handling**: the server reads the token store + transparent refresh;
  interactive login stays the host-side CLI (an in-session `begin_login` tool is
  deferred by design). A read-only `auth_status` reports validity; authenticated
  tools fail with a clear "run `anafpy auth login`" remediation.

## 9. Tooling

- **uv** (deps + lockfile), **hatchling** (build), **ruff** (lint+format),
  **mypy `--strict`**, **pytest** + **pytest-asyncio** + **respx**, **pre-commit**.
- **SemVer**, pre-1.0 (`0.x`). Support + test **3.12 and 3.13** (dev pin 3.13).
- **License: Apache-2.0** (explicit patent grant; ship `NOTICE`).
- **CI: GitHub Actions** — `ci.yml` (test matrix + gates + Codecov uploads) and
  `release.yml` (tag↔version check, PyPI trusted publishing on `v*` tags); the
  operative details live in CLAUDE.md and the workflow files.
- **The GitHub release is automated after PyPI, its prose is not** (2026-07-26).
  A `v*` tag now creates the GitHub release itself, downstream of the publish
  job — the release is the announcement, so it must never point at a version
  `pip install` cannot yet reach. The body comes from `release-notes/<tag>.md`
  committed with the release: through v0.6.0 those notes were written by hand
  after the fact, and a generated commit list would have been a downgrade, so
  the automation moves the *creation* into CI and leaves the *writing* where it
  was. GitHub's generated notes remain the fallback when a tag ships no such
  file, so a release always exists for a published version. The v0.1.0–v0.6.0
  notes were **backfilled into `release-notes/` from the published bodies**, so
  the directory — not the GitHub API — is now the corpus; only the compare link
  was dropped from each, being the one line the workflow derives. Notes are
  **not** duplicated into the packaged README for PyPI's sake (PyPI has no
  notes field, and the shipped README would then drift from the repo's): a
  `Changelog` project URL points every version's project page at the releases.
- **Testing (layered)**: respx mock suite as the credential-free CI gate + an
  opt-in live suite (`ANAFPY_LIVE=1`) that re-confirms wire shapes — never a CI
  gate (registry data drifts; ANAF punishes hammering the public host). Mock
  tiers: (1) golden round-trip on generated UBL models (regen/serialization
  regressions); (2) client behavior via respx. The live tier is read-only
  except the deliberate filing exceptions listed in CLAUDE.md ("Conventions
  for changes").

## 10. Open / deferred items

Resolved items are folded into their sections: `/token` needs no cert (§3),
callback UX (§3), keyring default (§3, which also settles token-at-rest for the
common case — the opt-out `FileTokenStore` remains plain JSON under OS perms),
public lookups (§6), skills-as-prompts (§8), live shape confirmation (§7), the
CLI surface (grew organically into the `auth` / `spv` / `declaratii` / `duk`
command groups), and Cowork local-stdio availability (settled: the connector is
registered in `claude_desktop_config.json`, which the Cowork tab reads — the
`anafpy-setup` skill writes it). Still open:

1. Within the public family: the **async job variant** of the taxpayer lookup
   stays deliberately unwrapped (§6).
2. **In-session `begin_login`** MCP tool for the OAuth browser flow — deferred
   by design (§8); that login stays CLI-side (the certificate-only logins,
   `spv_login` / `declaratie_portal_login`, later became tools — §12).

## 11. Distribution

> Decided 2026-07-02, revised 2026-07-07. anafpy is distributed **free and
> as-is**, for anyone to use.

**The stance.** The package is provided **as-is** under Apache-2.0 — no warranty,
no service obligations. The thin-transport scope of §1 is also the legal posture:
anafpy moves documents, it does not give tax advice, and filing outcomes are the
user's responsibility. The **MCP server is best-effort**: installing it,
configuring the environment, provisioning the OAuth application on ANAF's portal,
and holding the qualified certificate are the **user's responsibility** —
[the setup walkthrough](docs/mcp/setup.md) walks through all of it.

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

- **CI + release automation are in place** (§9); still open: SemVer discipline
  as versions accrue + a security policy.
- **Contribution terms** — Apache-2.0; settle CLA vs DCO before accepting
  external PRs.
- **Naming** — `anafpy` is fine as a library name; anything distributed more
  widely under the tax authority's name risks implying unauthorized affiliation
  and would need its own name.

**Audience bound that no packaging removes:** every user needs a qualified
certificate and their own ANAF OAuth app registration, capping the audience at
people who already deal with ANAF professionally.

**Distribution vehicles:** since the PyPI release, the MCP server installs as a
uv tool — `uv tool install "anafpy[mcp]"`, then
`claude mcp add anafpy -- anafpy-mcp` or the `anafpy-mcp` binary path in
`claude_desktop_config.json` (the setup walkthrough and the `anafpy-setup`
skill both use this; pivoted 2026-07-20 from the earlier
run-from-checkout registration, which remains the developer path). The wheel
bundles the compiled ANAF reference and the workflow-skills tree (hatchling
force-include, same date), so the PyPI install serves the `anafref://`
resources and the MCP prompts too — the repo trees stay the single source.
*(Plugin history — two distinct decisions.* A Claude Code plugin wrapping the
**MCP server registration** — `.claude-plugin/` as a single-plugin marketplace —
shipped 2026-07-03 and was **removed the same day** in favor of plain MCP
registration; that shape stays out. **Superseded in part 2026-07-18**: the repo
again publishes a `.claude-plugin/` marketplace, now distributing the
**skills** — `anafpy-workflows` (the playbooks; verified 2026-07-18 that
claude.ai plugins bring bundled skills into chat + Cowork, unlike Claude Code
marketplace plugins, which are Code-tab-only) and `anafpy-setup` (the
installer skill). The MCP *server* still installs via `uv tool install` + plain
registration, never as a plugin.)* The workflow **skills** under
`plugins/anafpy-workflows/skills/` reach consumers both as Cowork Agent Skills
and as the MCP server's same-name prompts (§8) — the first
is `etransport-declare` (extract transport data from any source → map to
`FlatTransport` → prepare → human approval → submit → poll), which encodes the
regulatory guardrails (2.5 t / 500 kg / 10,000 RON scope check, 3-days-before and
5-vs-15-day UIT validity windows) and the never-invent-a-value /
never-self-approve rules the two-step gate assumes. After the PyPI release: an
MCPB bundle for Claude Desktop (`server.type: "uv"` so the host manages Python;
`user_config` with `sensitive` fields → OS keychain, mapped onto the existing
`ANAFPY_*` env vars) — a thin wrapper over `anafpy[mcp]`.

## 12. Declarations (authoring + signing + status tracking)

> Landed 2026-07-15 (`anafpy.declaratii`, M1): **local document generation and
> signing, exposed via MCP.** Recipisa/status tracking landed 2026-07-16, the
> recon-grade library upload client 2026-07-17, and the MCP filing gate
> 2026-07-20 — M2 complete. See the later subsections below.

**The problem.** A taxpayer with no upstream software needs to produce a valid,
signed tax declaration (D300 VAT return first; the design is per-form generic).
Unlike e-Factura/e-Transport, ANAF exposes **no submission web service** for
declarations — filing is a portal upload behind the same F5 APM cert wall as SPV.
So M1 stopped at a signed PDF the user files manually; M2 automated the upload
(the portal client and the MCP filing gate — see the subsections below).

**Pipeline**: unstructured info → author the XML from
the form's XSD → **DUKIntegrator `-v`** (validate-fix loop until `ok`) →
**DUKIntegrator `-p`** (official PDF with the XML embedded) → **pyHanko + a
platform raw-signer** (qualified signature) → signed PDF on disk — all local,
no ANAF host — then the M2 portal upload and StareD112 confirmation (below).

**Must-keep invariants.**

1. **anafpy never touches key material.** The raw RSASSA-PKCS1-v1_5/SHA-256
   signature is delegated to the OS (Security.framework on macOS, the certificate
   store on Windows); the PIN/2FA is owned by the token middleware. **No MCP tool
   accepts a PIN — ever** (it would enter model context). The raw signer is a
   `RawSigner` protocol (`certificate()` + async `sign()`) with one
   implementation per platform, chosen by `platform_raw_signer` — the only
   platform branch in the strand. macOS is `KeychainRawSigner`, ctypes against
   Security.framework (`SecKeyCreateSignature`), chosen over a compiled Swift
   helper (a toolchain dependency) and over `pyobjc` (a heavy runtime dependency;
   kept as the documented fallback); Windows is `WindowsStoreRawSigner` (the
   subsection below).
2. **Validation authority is ANAF's.** DUK's per-form validator jars *are* ANAF's
   code; anafpy runs them and never re-implements a rule. The composed values —
   the `nr_evid` payment-evidence numbers of the self-assessed forms
   (D300/D100/D710/D101/D301, four composers in `declaratii/nr_evid.py`) — are
   pure functions (decoded from the validator bytecode, confirmed against the
   annex examples and live `-v` runs) — composition, not validation. Success is judged by the err-file content, never
   by DUK's exit code (`0` even on failure).
3. **Signing is consequential.** `declaratie_sign` is gated on `confirm=true`
   (the model must relay the user's explicit ask), one attempt per call, failures
   returned as `signed=false` + guidance (mirroring `spv_login`, not exceptions).
   M1 had **no two-step filing gate** — nothing was filed with ANAF; M2's gate
   is the subsection below.
4. **Binary artifacts go to disk** at caller-given paths through the shared
   `write_artifact` collision guard, never base64 into context.

**The CryptoTokenKit finding.** On macOS, certSIGN Paperless vToken is a
CryptoTokenKit extension with **no PKCS#11 dylib**, so DUK's `sunpkcs11` signing
path (and Windows-only `mscapi`) cannot reach the key — it is reachable only
through Security.framework, and CPython's `ssl` cannot present a non-exportable
platform-store key. This is why signing is a separate pyHanko + raw-signer path
rather than DUK `-s`, and why M1 signing shipped **macOS-only** (Windows is the
subsection below). Details and the proven Swift reference semantics live in
[the DUK reference](docs/anaf-reference/declaratii/duk.md).

**Distribution.** Signing needs the optional `anafpy[declaratii]` extra
(pyHanko); the tools import-guard and raise a "install anafpy[declaratii]"
`AnafConfigError` when it is absent, like the `mcp` extra.

**DUKIntegrator is managed-installed** (decided 2026-07-26, reversing the
original "user's to install" stance — the OAuth app and certificate remain the
user's). The trigger was the accountant-audience install burden: download a
2020 zip, discard a bundled JRE 6, hand-drop jars, chase the update feed
manually. The enabler was establishing that **ANAF's update feed is
self-sufficient**: its `<integrator>` element lists the core jar (`zJars`),
the shared + third-party lib jars (`sJars`/`iJars`), and the `config/` files
(`cFisiere`) — everything a working dist contains — so
`anafpy.declaratii.install.DukInstaller` (`anafpy duk install|update`, MCP
`declaratie_duk_install`) assembles a dist file by file at `~/.anafpy/duk-dist`
and the legacy zip is never downloaded. Guardrails for the unsigned feed:
downloads are pinned to `static.anaf.ro` over HTTPS (foreign hosts refused),
and a manifest records every file's source URL + SHA-256, making the install
auditable and the operation **convergent** (current files skipped; a
hand-assembled dist is adopted in place, never wiped). Resolution order:
explicit `ANAFPY_DUK_DIR` always wins; the managed dist is only the fallback.
That manifest is also **the authority for the installed version** (2026-07-26,
issue #8): it records the feed's own `versiuneJ` per fetched file, so
`installed_forms()` reads it first and only falls back to scraping
`<form>IstoriaVersiunilor.txt` for a manifest-less dist. The original scrape
took the file's first line, which is free text or the oldest release — it
reported every form stale forever, right after a correct install. The corrected
scrape takes the *last* `J…` token (the files are chronological, oldest first);
`declaratie_duk_status` now also keeps `not installed` and `not in feed`
(D406T — unlistable, so unjudgeable) apart from `stale`.
Scope choices: a bare install covers the top two usage buckets of the form
inventory plus whatever is already installed; **D406T** (jars only inside the
~91 MB `duk_SAFT` zip, absent from the feed) downloads only when named
explicitly; **Java stays guide-only** — anafpy never fetches a JRE. Rejected
alternatives from the same review: a warm-JVM/shim execution model (fragile
against `System.exit`, needs ANAF's non-public jar APIs) and a Docker image
(wrong fit for a local stdio server).

**Status tracking (StareD112).** Recon for M2 (2026-07-16) found that recipisa
tracking needs no certificate at all: ANAF's `www.anaf.ro/StareD112/` service is
**public and unauthenticated** — the upload index + CUI pair is knowledge-based
access to the CUI's filings from the last 3 months (max 200), with per-document
processing state and the signed recipisa PDF (downloadable ~60 days from
filing; an unknown/expired index answers HTTP 200 with an *empty* PDF body).
So `DeclarationStatusClient` (`declaratii/status.py`) landed ahead of the upload
client: a small no-auth httpx client with strict HTML parsing — "no declaration
identified" is a returned business outcome (`found=False`), an unrecognised
page raises, per the error model. Scraping is offloaded to **parsel** (Scrapy's
selector layer: CSS/XPath over lxml, `py.typed`; a core dependency since
2026-07-16) — decided when the WAS6DUS recon confirmed the upload portal is
HTML-only too, making HTML extraction a pattern rather than a one-off; the
strict shape checks stay ours, parsel only does the extraction. This narrows M2 to the upload itself; the
recipisa-via-SPV route (`Duplicat Recipisa` cerere) remains the fallback for
documents older than StareD112's windows. MCP: `declaratie_status` (read-only)
+ `declaratie_recipisa` (artifact-saving); both work with zero configuration.
Wire reference:
[docs/anaf-reference/declaratii/stared112.md](docs/anaf-reference/declaratii/stared112.md).

**M2 live-verification vehicle: D406T — and the recon-grade upload client.**
There is no separate TEST environment for declaration filing, but ANAF's SAF-T
voluntary-testing programme (a permanent assistance service, verified
2026-07-17) accepts the **D406T** test declaration on the **production** portal
with **no legal or fiscal effect** — the data is excluded from risk analyses
and deleted after the verification report. D406T is its own DUK form (namespace
`mfp:anaf:dgti:d406t:declaratie:v1`; jars only in ANAF's dedicated `duk_SAFT`
distribution — sourcing and structure gotchas in the
[DUK reference](docs/anaf-reference/declaratii/duk.md)). On that basis the
first M2 slice landed the same day: `declaratii/upload.py` —
`PortalCurlBootstrapper` (the WAS6DUS certificate choreography, discrete curl
steps, SPV's platform-keystore model) + `DeclarationUploadClient` (cookie-borne
multipart POST; the known rejection page is a returned business outcome). The
live test (`tests/test_declaratii_upload_live.py`, gated
`ANAFPY_LIVE_FILE_D406T=1` since it fires the certificate 2FA twice) files the
committed minimal D406T (`tests/fixtures/declaratii/d406t-minimal.xml`) end to
end; its **first run (2026-07-17) verified the whole chain in one pass** —
the success page was captured (upload index in "Indexul este …"; the parse is
hardened on the real shape), the **pyHanko CMS signature was accepted** by the
portal, and **StareD112 listed the D406T** (`In prelucrare`) within a minute.
Note the portal's own caveat: the success page is not the registration
confirmation — the recipisa is. See the
[portal-upload reference](docs/anaf-reference/declaratii/portal-upload.md) §4-§5.

**MCP filing gate (landed 2026-07-20).** The MCP exposure completes M2 as a
`declaratie_prepare`/`declaratie_submit` pair over the shared `mcp/gate.py`
token primitives, with three deliberate deviations from the e-Factura/
e-Transport shape, all decided with the user:

- **Opt-out, not opt-in.** The filing tools are served by default and removed
  by `ANAFPY_DECLARATII_UPLOAD=off` (declarations file on the **production**
  portal — there is no test environment — so a user who wants the MCP server
  authoring-only can strip the capability entirely; `declaratie_sign`'s
  guidance then points at manual portal filing).
- **Login outside the submit cycle.** `declaratie_portal_login` is its own
  confirm-gated tool (mirrors `spv_login`: fires the certificate PIN/2FA, one
  attempt per call, failures return `logged_in=false` + guidance). The session
  lives in-memory on the long-lived `DeclarationUploadClient`
  (`install_session`) — unlike SPV's it is deliberately not persisted, since
  the portal kills sessions after ~10 idle minutes.
- **Probe before spending the approval.** `DeclarationUploadClient.probe()` is
  a no-2FA session check (a plain GET of the upload app; landing anywhere but
  the upload form is "not logged in"), exposed as `declaratie_portal_status`
  and run by `declaratie_submit` *before* the single-use confirmation token is
  consumed — a lapsed session never burns the human's approval; the same token
  files after a re-login.

The token binds the exact signed-PDF bytes plus the multipart filename (the
declaration's CUI rides inside the signed document itself, so unlike the other
filings there is no separate CIF context to bind). `declaratie_prepare` also
runs a cheap local signature sniff (`/ByteRange` + `adbe.pkcs7.detached`) —
informational only, per the prepare-never-blocks rule. A mid-upload APM bounce
(the portal redirecting the POST) is reported as "nothing was filed"; any other
upload failure is an UNKNOWN outcome that directs the model to check
StareD112 before re-preparing, so a filing is never silently repeated.

**Windows signing (code landed 2026-07-26; live verification pending).**
`WindowsStoreRawSigner` closes the last macOS-only seam in the strand: everything
downstream of `RawSigner` was already platform-neutral, so the work was one class
plus making label resolution and signer construction platform-aware
(`resolve_signing_label` now returns
`SelectedIdentity.bootstrap_identity` — the Keychain **name** on macOS, the SHA-1
**thumbprint** on Windows — and ignores a selection made on the other platform,
which a synced home directory can carry across). Decisions:

- **PowerShell over ctypes.** The signer drives `powershell.exe` over
  `Cert:\CurrentUser\My` (the store `spv/certs.py` already enumerates) rather
  than binding `ncrypt.dll`/`crypt32.dll`:
  `RSACertificateExtensions.GetRSAPrivateKey(...).SignData(...)` covers a CNG/KSP
  key **and** a legacy CSP key in one call, where the ctypes route needs a
  `CERT_NCRYPT_KEY_SPEC` branch with `NCryptSignHash` on one side and
  `CryptSignHash` on the other. Same bytes, half the surface, and it reuses the
  PowerShell-discovery pattern already in the repo. .NET Framework 4.6+ (so
  Windows PowerShell 5.1) is the floor for that `SignData` overload.
- **Thumbprint, not name.** A thumbprint cannot be ambiguous, so the macOS
  namesake refusal (a renewed certificate beside the old one) has no Windows
  counterpart. Selectors are shape-checked to 40 hex digits.
- **Everything through the environment.** Both scripts read their inputs from
  `ANAFPY_SIGN_*` variables and answer with one compact JSON object, so there is
  no argv quoting or injection surface; an expected condition is
  `{"error": "<slug>"}` at exit 0, leaving a non-zero exit to mean "PowerShell
  itself failed". A test pins the referenced variable set.
- **Bounded like the rest.** The signing run goes through
  `_transport/subprocess.py`, so an unanswered PIN dialog is killed at the
  `_SIGN_TIMEOUT` deadline instead of hanging (the macOS `asyncio.to_thread`
  path can only abandon its thread).
- **DUK `-s`/`mscapi` stays rejected** — it would route the PIN through DUK's
  process, against invariant 1.

Both signers are covered on **every** CI leg by a fake of their own platform seam
(`_Frameworks`; the two PowerShell runners). What remains is hardware:
whether certSIGN's Windows vToken packaging exposes the key through CNG or a CSP
at all is only answerable on a real box, and the same box owes the strand's two
other unverified Windows legs — a live DUK `-v`/`-p` run, and the portal curl
bootstrap (Schannel by thumbprint, never yet exercised). The D406T live filing is
the end-to-end proof.
