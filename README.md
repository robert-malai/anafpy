# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), and the
**public no-auth registries** (VAT/taxpayer lookups, financial statements) — plus a
local MCP server that exposes them as [Claude Cowork](https://claude.com) skills.

anafpy is a **thin transport client**, not invoicing software. For **e-Factura** you
bring invoice XML that your own invoicing system produced, and anafpy validates it,
files it with ANAF, tracks status, and pulls documents back — wrapping the XML you read
back (your filings and invoices suppliers issued to you) in a friendly **flat read
view** for easy display. (e-Factura is a filing endpoint; Romanian law presumes you
already run an invoicing system.) **e-Transport is different**: there is usually no
upstream software producing declaration XML, so anafpy translates ANAF's whole (small,
fully enumerated) schema into friendly typed models — you author declarations, UIT
deletions, confirmations, and vehicle changes from structured fields, no XML handling
needed, and the same models render what you read back.

> Status: **early / alpha** (`0.x`), not yet published to PyPI. The OAuth2 auth layer,
> both async clients (with an easy-to-read flat view of downloaded documents), and the
> MCP server (structured e-Transport filing and a read-only e-Factura surface —
> inbox, download, validate) are implemented and tested.
> Validation is ANAF's own server-side `validare` endpoint — there is no local rule
> engine. See [`DESIGN.md`](DESIGN.md) for the full design and
> [`docs/anaf-reference/`](docs/anaf-reference/) for a compiled local reference of ANAF's
> APIs.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**.

## What works today

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx.Auth` integration for the clients.
- **`EFacturaClient`** (async) — `upload`, `get_status`, `download`, `to_pdf`,
  `validate_remote` (ANAF's authoritative server-side validation, no filing — uses the
  public no-auth production validator, so it works whatever environment the client
  targets), `validate_signature` (checks the MF signature over a downloaded invoice), the
  `upload_and_wait` poll-until-terminal helper, and `list_messages` — a single async
  iterator that pages the message list under the hood (window by `days` or `start`/`end`;
  empty window → empty iterator, real ANAF errors → raise). `download` exposes three read
  tiers: raw signed bytes, the full UBL model, and an easy-to-read `FlatInvoice` **view**.
- **`ETransportClient`** (async) — `upload`, `get_status`, `info`, `upload_and_wait`,
  `list_notifications` (same async-iterator shape), and **`upload_document`**, which
  composes and files any of the four flat documents — a `FlatTransport`
  declaration/correction, `FlatDeletion`, `FlatConfirmation`, or `FlatVehicleChange` —
  without the caller touching XML.
- **`PublicClient`** (async) — ANAF's **unauthenticated** public services on
  `webservicesp.anaf.ro`: `lookup_taxpayers` (VAT registration, VAT-on-collection,
  inactive, split-VAT, and RO e-Factura register membership in one call),
  `lookup_efactura_register`, `lookup_farmers`, `lookup_cult_entities`, and
  `get_financial_statement` (public bilanț indicators). No credentials, no test/prod
  split; requests are paced client-side at ANAF's stated 1 req/s rule.
- **Flat models** — `read_flat_invoice` projects UBL into a small, easy-to-read
  `FlatInvoice` **read view** (lossy, with a `complete` flag); anafpy never composes
  UBL from it. The e-Transport flat models are **bidirectional**: `read_flat_transport`
  views a parsed document and `build_etransport` / `render_etransport` author one —
  full translation of ANAF's XSD, with enum-coded fields (counties, border points,
  customs offices, operation types...) accepted by name or code.
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **MCP server** (`anafpy[mcp]`) — a local stdio connector exposing the operations as
  Cowork skills, with read-first, two-step gated e-Transport filing and a read-only
  e-Factura surface (see below).

Not yet built: CI and PyPI publishing. (A sync facade was dropped as a goal — the
clients are async-only.)

## Install

Setting up a **fresh machine end to end** — ANAF app registration, the certificate
login, and the Claude / Cowork configuration, written for a non-developer — follow
[`INSTALL.md`](INSTALL.md). The short version for developers:

Not on PyPI yet — install from source:

```bash
git clone https://github.com/robert-malai/anafpy && cd anafpy
uv sync --all-extras
```

The distribution offers one extra: `anafpy[mcp]` (the MCP server).

## Authentication

ANAF uses OAuth2 (Authorization Code) gated by a **qualified digital certificate**. The
one-time, interactive bootstrap runs on your machine (the cert lives there):

```bash
anafpy auth login --client-id <ID> --client-secret <SECRET> \
                  --redirect-uri https://localhost:9002/callback --paste
anafpy auth status        # show stored token validity
```

Register the callback URL with the **`https://` scheme** — ANAF's developer portal
rejects `http://` callbacks (HTTP 400 at registration; verified 2026-07-02). The
callback still doesn't need a public server; pick how the code gets captured:

- **`--paste` (recommended default).** No listener runs. After the certificate step the
  browser shows a connection error — expected — and you paste the redirect URL from the
  address bar into the CLI. Paste promptly: ANAF's code expires in ~60 seconds.
- **`--tls-cert` / `--tls-key`.** The local listener serves TLS directly with a
  certificate you supply — a self-signed one works. Generate it once (browsers
  require a `subjectAltName`, not just the CN):

  ```bash
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -keyout ~/.anafpy/callback-key.pem -out ~/.anafpy/callback-cert.pem \
    -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  ```

  then pass `--tls-cert ~/.anafpy/callback-cert.pem --tls-key ~/.anafpy/callback-key.pem`
  instead of `--paste`. The browser shows a one-time "proceed to localhost" warning
  (click through — it's your own cert on your own loopback); trust the cert in the OS
  keychain, or use [mkcert](https://github.com/FiloSottile/mkcert), to remove the
  warning entirely. On **Windows** (no stock OpenSSL), prefer mkcert:
  `choco install mkcert` (or `scoop install mkcert`), then `mkcert -install` and
  `mkcert localhost 127.0.0.1` — the emitted PEM pair plugs into
  `--tls-cert`/`--tls-key` unchanged, with no browser warning at all.
- **Neither flag.** The listener speaks plain HTTP; put your own TLS terminator in
  front of it. If the listener can't start — or no callback arrives in time — the
  CLI falls back to paste mode.

This opens your browser for the certificate step, captures the authorization code,
exchanges it for tokens, and stores them under
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

e-Transport declarations are authored from typed models — no XML in sight:

```python
import datetime as dt
from decimal import Decimal

from anafpy.etransport import (
    ETransportClient, FlatDeletion, FlatTransport, FlatTransportAddress,
    FlatTransportDocument, FlatTransportGood, FlatTransportLocation,
    FlatTransportPartner, FlatTransportVehicle,
)
from anafpy.etransport.schema.schema_etr_v2_20230126 import (
    CodJudetType, CodScopOperatiuneType, CodTaraType, CodTipOperatiuneType,
    TipDocumentType,
)

declaration = FlatTransport(
    operation_type=CodTipOperatiuneType.TTN,           # domestic transport
    partner=FlatTransportPartner(
        name="Partener SRL", country=CodTaraType.ROMANIA, code="12345678",
    ),
    vehicle=FlatTransportVehicle(
        plate="CJ01ABC", carrier_name="Transport SRL", carrier_code="23456789",
        carrier_country=CodTaraType.ROMANIA, transport_date=dt.date(2026, 7, 10),
    ),
    start_location=FlatTransportLocation(address=FlatTransportAddress(
        county=CodJudetType.CLUJ, locality="Cluj-Napoca", street="Memorandumului",
    )),
    end_location=FlatTransportLocation(address=FlatTransportAddress(
        county=CodJudetType.MUNICIPIUL_BUCURESTI, locality="Bucuresti",
        street="Calea Victoriei",
    )),
    goods=[FlatTransportGood(
        operation_scope=CodScopOperatiuneType.COMERCIALIZARE,
        name="Materiale constructii", quantity=Decimal("100"), unit_code="KGM",
        gross_weight=Decimal("110"), net_weight=Decimal("100"),
        value_ron=Decimal("2500"), tariff_code="6810",
    )],
    documents=[FlatTransportDocument(
        doc_type=TipDocumentType.CMR, date=dt.date(2026, 7, 9), number="FAC-001",
    )],
)

async with ETransportClient(provider) as etransport:
    result = await etransport.upload_document(declaration, cif="12345678")
    print(result.uit)  # the UIT code, issued at upload time
    # later: delete / confirm / change vehicle on that UIT the same way, e.g.
    await etransport.upload_document(FlatDeletion(uit=result.uit), cif="12345678")
```

The public registries need no auth at all:

```python
from anafpy.public import PublicClient

async with PublicClient() as public:
    lookup = await public.lookup_taxpayers(["RO12345678"])
    if lookup.found:
        record = lookup.found[0]
        print(record.name, record.vat_registered, record.efactura_registered)
```

## MCP server

The `anafpy[mcp]` extra ships a **local stdio MCP server** that wraps the clients as
Cowork skills. Run it host-side, where the token store written by `anafpy auth login`
lives:

```bash
ANAFPY_CLIENT_ID=... ANAFPY_CLIENT_SECRET=... ANAFPY_CIF=... \
  python -m anafpy.mcp        # or the `anafpy-mcp` console script
```

It exposes **freely callable read tools** (`auth_status`; the e-Factura inbox via
`efactura_list_messages` / `efactura_download` — the latter
can also **save artifacts for the user**: `save_zip_as` writes the signed archive
ZIP and `save_pdf_as` writes ANAF's official PDF rendering (`transformare`,
best-effort) to caller-given paths, which powers flows like "export last month's
invoices as `<date> - <partner>.pdf`"; the PDF is also exposed as the MCP resource
`anafmsg://<message_id>/pdf`; `etransport_list`
/ `etransport_get_status` / `etransport_lookup` / `etransport_nomenclature`;
`efactura_validate`, which runs
ANAF's authoritative server-side validator without filing; and the `anaf_*` public
lookups — taxpayer/VAT registry, RO e-Factura register, farmers/cult registers, and
financial statements — which need **no login at all**) plus **two-step gated
filing for e-Transport**: `etransport_prepare*` returns a preview + a confirmation
token bound to the exact document and the CIF being filed for; `etransport_submit`
files only when
given that token (same document, same CIF) and `confirm=True`, and each token is
single-use — filing again requires a fresh prepare. **The MCP e-Factura surface is
read-only** — there are no invoice filing tools (removed 2026-07-03: outbound UBL
comes from invoicing software that files with ANAF itself; `EFacturaClient.upload`
remains for library users). **e-Transport filing is composed for you**:
`etransport_prepare_declaration` (a new declaration or, via `correction_of_uit`, a
correction), `etransport_prepare_deletion`, `etransport_prepare_confirmation`, and
`etransport_prepare_vehicle_change` take structured fields (enum-coded values by ANAF
code or by name — `TTN`, `CLUJ`, `NADLAC`; discoverable via `etransport_nomenclature`),
compose the declaration XML, and return it alongside the preview and token;
`etransport_prepare` still accepts ready-made XML. Both the e-Factura inbox and the
e-Transport `prepare`
previews present documents as friendly **flat models** parsed from the XML (for
invoices, easy to read and lossy by design — the raw bytes stay authoritative). The
compiled ANAF reference is surfaced as read-only resources. Auth stays
the host-side CLI — the server only reads and refreshes the token store. Configuration is
environment-only; see [`CLAUDE.md`](CLAUDE.md).

Register the server with any MCP client — e.g. with Claude Code, from a source
checkout (locked deps, no PyPI needed):

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- uv run --directory /path/to/anafpy --frozen --extra mcp anafpy-mcp
```

**No credentials yet?** The server still starts and the public `anaf_*` lookups
(registries, financial statements) are fully usable. The e-Factura / e-Transport
tools unlock once you set the credentials and run the one-time `anafpy auth login`
in a terminal.

The server also ships workflow playbooks as MCP **prompts** — a user-invoked entry
point (Claude Desktop's "+" menu, or `/mcp__anafpy__etransport-declare` in Claude
Code). `etransport-declare` walks Claude through filing an e-Transport declaration
from whatever source the data lives in (an email, a PDF invoice, a CMR, a
spreadsheet) — extract, map to the structured declaration, prepare, show the
preview for your approval, submit, then poll until ANAF issues a valid UIT. The
playbooks live under [`skills/`](skills/) (`SKILL.md` files, the single source of
truth) and travel with any connection method.

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
