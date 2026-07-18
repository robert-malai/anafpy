<p align="center">
  <a href="https://anafpy.readthedocs.io">
    <img src="https://raw.githubusercontent.com/robert-malai/anafpy/main/imgs/anafpy-social-preview.png"
         alt="anafpy — Python client for ANAF e-Factura &amp; e-Transport" width="720">
  </a>
</p>

<p align="center">
  <a href="https://github.com/robert-malai/anafpy/actions/workflows/ci.yml"><img
    src="https://img.shields.io/github/actions/workflow/status/robert-malai/anafpy/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://codecov.io/gh/robert-malai/anafpy"><img
    src="https://img.shields.io/codecov/c/github/robert-malai/anafpy?branch=main" alt="Coverage"></a>
  <a href="https://pypi.org/project/anafpy/"><img
    src="https://img.shields.io/pypi/v/anafpy" alt="PyPI version"></a>
  <a href="https://pypi.org/project/anafpy/"><img
    src="https://img.shields.io/pypi/pyversions/anafpy" alt="Python versions"></a>
  <a href="https://anafpy.readthedocs.io/en/latest/"><img
    src="https://app.readthedocs.org/projects/anafpy/badge/?version=latest" alt="Docs"></a>
  <a href="https://github.com/robert-malai/anafpy/blob/main/LICENSE"><img
    src="https://img.shields.io/pypi/l/anafpy" alt="License"></a>
</p>

# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), and the
**public no-auth registries** (VAT/taxpayer lookups, financial statements) — plus a
local MCP server that exposes them as [Claude Cowork](https://claude.com) skills.

anafpy is a **thin transport client** — no persistence, no accounting logic. For
**e-Factura** there are two ways out: if you run invoicing software, bring the
invoice XML it produced and anafpy validates it, files it with ANAF, tracks
status, and pulls documents back (the strongly recommended path — your system's
XML is never re-composed); if you don't, the **invoice authoring models** compose
a complete CIUS-RO invoice or credit note from plain business fields — totals and
the VAT breakdown computed for you, checked against a translated EN 16931 +
CIUS-RO rule set before filing. Either way, remember that **ANAF's SPV is not
invoice storage** — it purges filed messages after ~60 days — so your durable
record must live on your side: your invoicing system's ledger, or, when you
author with anafpy, the signed ZIPs you download and keep. Documents you read
back (your filings and
invoices suppliers issued to you) come wrapped in a friendly **flat read view**
for easy display. **e-Transport** is fully translated too: you author
declarations, UIT deletions, confirmations, and vehicle changes from structured
fields, no XML handling needed, and the same models render what you read back.

**Documentation: [anafpy.readthedocs.io](https://anafpy.readthedocs.io)** — the
end-user setup walkthrough, the library guides, and the API reference.

## What can you do with this?

With the MCP server connected to a Claude client (Claude Desktop, Claude Code), an
accountant in Romania can ask Claude to:

**Check partners and public data — no login required** (these ride ANAF's public,
no-auth services):

- **Verify a business partner by CUI/CIF** — name, address, VAT status (plătitor de
  TVA), TVA la încasare, split-VAT, inactive flag — one call, in bulk if you like.
- **Check whether a partner is enrolled in RO e-Factura.**
- **Look up the farmers' register (RegAgric) and religious-entities register (RegCult).**
- **Pull a company's filed financial statements (bilanț)** for a given year.
- **Validate an invoice XML** against ANAF's authoritative server-side `validare`
  (CIUS-RO / BR-RO rules) — no filing.

**Work your e-Factura inbox and file invoices** (needs the certificate login):

- **List received and sent invoice messages** for a date window.
- **Download an invoice** as an easy-to-read view, and **save the official signed ZIP
  and/or a rendered PDF** to disk — powering batch flows like "export last month's
  invoices as `<date> - <partner>.pdf`".
- **File an invoice or credit note** — from the XML your invoicing software
  exported (recommended when you have one), or **composed by Claude from plain
  business fields** when you don't. Either way filing is two-step gated: you see
  a preview and nothing reaches ANAF until you explicitly confirm.

**Declare goods transport in e-Transport — with a confirmation step** (needs the login):

- **File a declaration and get a UIT code** from transport data in any source — an
  email, a PDF invoice, a CMR, a spreadsheet — and **correct, delete, confirm, or
  change the vehicle** on an existing one.
- **List recent notifications, check an upload's status, and look up active
  declarations / UIT codes.**
- Filing is **two-step gated**: Claude shows you a preview, and nothing is submitted to
  ANAF until you explicitly confirm.

**Read your SPV mailbox and pull official reports** (needs the certificate — read-only):

- **Check what arrived in SPV** — receipts (recipise), payment notices, decisions,
  notifications — filtered by company and message kind, and **save any document's
  PDF** to a folder you name.
- **Request official reports and wait for them**: fiscal vector (VECTOR FISCAL),
  outstanding obligations (Obligatii de plata), filing history (Istoric
  declaratii), declaration duplicates (D100/D112/D300/D390/D394...), receipt
  duplicates, income certificates (Adeverinte Venit), D112↔REVISAL mismatches —
  ANAF generates them asynchronously and Claude fetches the PDF when it lands.
- **See exactly which companies your certificate can query** — SPV reports the
  authorization inventory on every call.

**Prepare and sign a tax declaration** (D300 VAT return first — local, macOS signing):

- **Fill in, validate, render, and sign a declaration** from unstructured info —
  Claude authors the XML, validates it with ANAF's own DUKIntegrator (the
  authority) in a fix-and-retry loop, renders the official PDF, and signs it with
  your qualified certificate (the PIN/2FA prompt is the human gate).
- **Filing is not automated yet** — you upload the signed PDF on the portal;
  automating that is the next milestone.
- **Track the filing afterwards, with no login at all** — given the upload index
  the portal returns, Claude checks whether the declaration was accepted (ANAF's
  public status service) and saves the digitally signed filing receipt PDF —
  which ANAF keeps available for only ~60 days.

Setup caveats worth knowing: the e-Factura and e-Transport tools need a one-time login
with your **qualified digital certificate** (the same one you use on ANAF's SPV) — the
public checks above work without it. The server runs **locally** on your own machine,
so downloaded invoices and PDFs land on your own filesystem. See the
[setup walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/) for the
full Claude Desktop + ANAF setup — also available
[in Romanian](https://anafpy.readthedocs.io/en/latest/mcp/setup.ro/).

> Status: **early / alpha** (`0.x`), on PyPI as
> [`anafpy`](https://pypi.org/project/anafpy/). The OAuth2 auth layer, both async
> clients, the bidirectional invoice-authoring models, and the MCP server
> (two-step gated filing for both services, inbox, download, validate) are
> implemented and tested, as is the read-only SPV layer (certificate-mTLS
> mailbox: messages, downloads, report requests). ANAF's own server-side `validare` stays the
> authoritative validator; the authoring models add a local translated rule
> check for fast feedback. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of ANAF's
> APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## What works today

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx.Auth` integration for the clients.
- **`EFacturaClient`** (async) — `upload` (ready-made XML) and `upload_invoice`
  (an authored `InvoiceDocument`), `get_status`, `download`,
  `validate_signature` (checks the MF signature over a downloaded invoice), the
  `upload_and_wait` poll-until-terminal helper, and `list_messages` — a single async
  iterator that pages the message list under the hood (window by `days` or `start`/`end`;
  empty window → empty iterator, real ANAF errors → raise). `download` exposes three read
  tiers: raw signed bytes, the full UBL model, and the flat `InvoiceDocument` **view**
  (the same authoring model, read full-fidelity from the wire).
- **Invoice authoring** (`anafpy.efactura.authoring`) — bidirectional CIUS-RO
  models: one `InvoiceDocument` covers invoice and credit note, totals and the
  VAT breakdown are computed from the lines (explicit values preserved), and a
  hand-translated EN 16931 + CIUS-RO rule set (`validate()`) reports findings
  with the official BR-* ids before anything is filed. `render_invoice` emits
  upload-ready XML; `parse_invoice`/`read_invoice` map wire XML back into the
  same models with byte-stable round-trips.
- **`ETransportClient`** (async) — `upload`, `get_status`, `info`, `upload_and_wait`,
  `list_notifications` (same async-iterator shape), and **`upload_document`**, which
  composes and files any of the four flat documents — a `FlatTransport`
  declaration/correction, `FlatDeletion`, `FlatConfirmation`, or `FlatVehicleChange` —
  without the caller touching XML.
- **`PublicClient`** (async) — ANAF's **unauthenticated** public services on
  `webservicesp.anaf.ro`: `lookup_taxpayers` (VAT registration, VAT-on-collection,
  inactive, split-VAT, and RO e-Factura register membership in one call),
  `lookup_efactura_register`, `lookup_farmers`, `lookup_cult_entities`,
  `get_financial_statement` (public bilanț indicators) — plus the stateless
  e-Factura document services: `validate_invoice` (ANAF's authoritative
  server-side validation, no filing) and `render_invoice_pdf` (the official
  `transformare` PDF rendering); both are prod-only on ANAF's side and need no
  login. No credentials, no test/prod split; requests are paced client-side at
  ANAF's stated 1 req/s rule.
- **`SpvClient`** (async, read-only) — the taxpayer's **SPV mailbox** over the
  qualified certificate: `list_messages` (with the certificate's authorization
  inventory), `download_document` (PDF), `request_report` (the full `cerere`
  nomenclature — 35 report types with per-type parameter validation before any
  wire call), and `wait_for_report`. The certificate step is one interactive
  `anafpy spv login` (macOS Keychain/SecureTransport or Windows
  CertStore/Schannel via the OS-shipped curl — the keys are non-exportable, so
  Python's TLS stack never touches them); everything after rides an APM cookie
  session, prompt-free.
- **Flat models** — the invoice authoring models above double as the inbox
  read view (`DownloadedMessage.view`), so what you download and what you author
  are the same shape. The
  e-Transport flat models are **bidirectional**: `read_flat_transport`
  views a parsed document and `build_etransport` / `render_etransport` author one —
  full translation of ANAF's XSD, with enum-coded fields (counties, border points,
  customs offices, operation types...) accepted by name or code.
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **MCP server** (`anafpy[mcp]`) — a local stdio connector exposing the operations as
  Cowork skills: read-first, with two-step gated filing for **both** services —
  e-Factura invoices (ready-made XML or composed from structured fields) and
  e-Transport declarations (see below).
- **Declarations** (`anafpy.declaratii`, signing via `anafpy[declaratii]`) —
  local authoring/validation/signing of tax declarations (D300 first): a
  DUKIntegrator wrapper (`-v`/`-p`), the `nr_evid` composer, and a pyHanko
  qualified-signature path where the raw op is delegated to the OS token
  (macOS Keychain / CryptoTokenKit; no key material in-process). Filing works
  two ways: manually on the portal, or through `DeclarationUploadClient`
  (certificate login + upload on ANAF's declaration portal — live-verified
  end to end on 2026-07-17); exposing filing as an MCP tool is what remains.
  Filing **status** and the signed recipisa are covered too
  (`DeclarationStatusClient` over ANAF's public no-auth StareD112 service).

A sync facade was dropped as a goal — the clients are async-only.

## Install

Setting up a **fresh machine end to end** — ANAF app registration, the certificate
login, and the Claude / Cowork configuration, written for a non-developer — follow
the [setup walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/). The
short version for developers:

From [PyPI](https://pypi.org/project/anafpy/):

```bash
pip install anafpy               # or: uv add anafpy
pip install 'anafpy[mcp]'        # with the MCP server
pip install 'anafpy[declaratii]' # with declaration signing (pyHanko)
```

The distribution offers two extras: `anafpy[mcp]` (the MCP server) and
`anafpy[declaratii]` (declaration signing).

For the MCP server, prefer running from a **checkout** (as the setup walkthrough
does): the
compiled ANAF reference (`docs/anaf-reference/`, served as MCP resources) and the
workflow skills (`plugins/anafpy-workflows/skills/`, served as MCP prompts) live in
the repo, not in the wheel. A PyPI-installed server runs fine but serves neither
unless `ANAFPY_DOCS_DIR` / `ANAFPY_SKILLS_DIR` point at copies. From source:

```bash
git clone https://github.com/robert-malai/anafpy && cd anafpy
uv sync --all-extras
```

## Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**. The
one-time, interactive bootstrap runs on your machine (the cert lives there):

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback --paste
anafpy auth status        # show stored token validity
anafpy auth logout        # remove the stored tokens (signs this machine out)
```

This opens your browser for the certificate step, captures the authorization code
(pasted, or via a local TLS listener), exchanges it for tokens, and stores them in
the **OS credential store** (macOS Keychain, Windows Credential Manager, Linux
Secret Service/KWallet — the default backend; a JSON-file backend is the opt-out
for Docker/headless hosts). Tokens then refresh **headlessly** for ~a year (access
token 90 days, refresh token 365 days), so the cert is needed only about once a
year. The [authentication guide](https://anafpy.readthedocs.io/en/latest/library/auth/)
covers the capture modes, token storage, and signing out.

## Usage

The clients are async and used as context managers. Build a `TokenProvider` over your
stored tokens, then call discrete operations:

```python
from anafpy.auth import KeyringTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient

provider = TokenProvider(
    client_id="<ID>",
    client_secret="<SECRET>",
    store=KeyringTokenStore(),  # OS credential store (the default backend)
    # or FileTokenStore("~/.anafpy/tokens.json") for headless/Docker hosts
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

e-Transport declarations are authored from typed models — no XML in sight. A
`FlatTransport` holds the partner, vehicle, route, goods, and documents as
structured fields (enum-coded values accepted by ANAF code or by name), and
`upload_document` renders and files it in one step:

```python
from anafpy.etransport import ETransportClient, FlatDeletion, FlatTransport

declaration = FlatTransport(...)  # full example in the e-Transport guide

async with ETransportClient(provider) as etransport:
    result = await etransport.upload_document(declaration, cif="12345678")
    print(result.uit)  # the UIT code, issued at upload time
    # later: delete / confirm / change vehicle on that UIT the same way, e.g.
    await etransport.upload_document(FlatDeletion(uit=result.uit), cif="12345678")
```

The [e-Transport guide](https://anafpy.readthedocs.io/en/latest/library/etransport/)
has the complete worked declaration.

The public registries need no auth at all:

```python
from anafpy.public import PublicClient

async with PublicClient() as public:
    lookup = await public.lookup_taxpayers(["RO12345678"])
    if lookup.found:
        record = lookup.found[0]
        print(record.name, record.vat_registered, record.efactura_registered)
```

Reading SPV takes one interactive login (`anafpy spv certs` → `anafpy spv select
<thumbprint>` → `anafpy spv login`, which fires your token PIN / 2FA once), then:

```python
from anafpy.spv import (
    FileSessionStore, ReportRequest, ReportType, SpvClient, SpvSessionProvider,
)

async with SpvClient(SpvSessionProvider(store=FileSessionStore())) as spv:
    inbox = await spv.list_messages(30)
    print(inbox.authorized_cuis)  # every CUI/CNP your certificate may query
    result = await spv.request_report(
        ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="12345678")
    )
    report = await spv.wait_for_report(result.request_id)  # PDF bytes
```

## MCP server

The `anafpy[mcp]` extra ships a **local stdio MCP server** that wraps the clients as
Cowork skills. The server is **best-effort**: configuring it — including registering
your own OAuth application on ANAF's portal — is your responsibility, and the
[setup walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/) walks you
through every step. Run it host-side, where the token store written by
`anafpy auth login` lives:

```bash
ANAFPY_CLIENT_ID=... ANAFPY_CLIENT_SECRET=... ANAFPY_CIF=... \
  python -m anafpy.mcp        # or the `anafpy-mcp` console script
```

The surface is **read-first**: freely callable read tools (the `anaf_*` public
lookups and `efactura_validate` need **no login at all**; `auth_status`, the
e-Factura inbox — which can also save the signed ZIP and ANAF's official PDF
rendering to disk — and the e-Transport reads need the one-time login) plus
**two-step gated filing for both services**: every `*_prepare*` tool returns a
preview + a single-use confirmation token bound to the exact document and CIF,
and the matching `*_submit` files only with that token and `confirm=True`.
e-Factura filings arrive either as the XML your invoicing software produced
(`efactura_prepare`, the recommended path) or composed from structured fields
(`efactura_prepare_invoice` — no invoicing software needed); e-Transport
declarations are composed from structured fields by `etransport_prepare*`.
The `spv_*` tools read the SPV mailbox (list, download PDFs to disk, request
official reports and await their delivery) over the certificate session
established by `anafpy spv login` — read-only, no submissions.
The compiled ANAF reference is served as read-only resources, and workflow
playbooks as MCP prompts — `etransport-declare`, which takes a declaration from
any source (an email, a PDF invoice, a CMR) through extract → prepare → your
approval → submit → UIT, and `personal-income-summary`, which pulls a person's
realized income from the SPV income certificates into a per-year summary (with an
optional Excel workbook). See the
[tools overview](https://anafpy.readthedocs.io/en/latest/mcp/tools/) and
[workflow skills](https://anafpy.readthedocs.io/en/latest/mcp/skills/) for the
full picture.

Register the server with any MCP client — e.g. with Claude Code, from a source
checkout (locked deps, no PyPI needed):

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- uv run --directory /path/to/anafpy --frozen --extra mcp anafpy-mcp
```

**No credentials yet?** The server still starts; the public `anaf_*` lookups
(registries, financial statements) and `efactura_validate` are fully usable. The
remaining e-Factura / e-Transport tools unlock once you set the credentials and run
the one-time `anafpy auth login` in a terminal.

## Development

```bash
uv sync --all-extras
uv run pytest                              # respx-mocked, credential-free
uv run ruff check . && uv run ruff format --check .
uv run mypy                                # strict
ANAFPY_LIVE=1 uv run pytest -m live        # opt-in: live smoke against real ANAF
```

The `live` marker re-confirms wire shapes against real ANAF endpoints and is skipped
by default (not a gate). It covers the public services (no credentials needed) plus,
with `.env` credentials and an `anafpy auth login` token store, the authenticated
**TEST** environment: read-only shape checks and two roundtrips that actually file a
test document — a minimal CIUS-RO invoice (e-Factura) and a domestic transport
declaration composed via the flat authoring models (e-Transport). The roundtrips
target TEST only, never production.

Models under `efactura/ubl/` and `etransport/schema/` are **generated** (via
`scripts/generate_*.py` from vendored XSDs in `schemas/`) and must not be hand-edited.
See [`CLAUDE.md`](CLAUDE.md) for repository conventions.

## License

[Apache-2.0](LICENSE). Independent / unofficial — not affiliated with ANAF.

anafpy is free to use and provided **as-is**, with no warranty: it moves documents
to and from ANAF, it does not give tax advice, and filing outcomes are your
responsibility. The MCP server is **best-effort** — configuring it, provisioning
your own OAuth application on ANAF's portal, and holding the qualified certificate
are up to you (the
[setup walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/) covers all
of it).
