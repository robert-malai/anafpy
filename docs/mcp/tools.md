# Tools

The `anafpy[mcp]` extra ships a **local stdio MCP server** that wraps the typed
clients as tools for Claude (Desktop, Code, Cowork). It runs on your own machine:
tool calls use your own tokens, and downloaded files land on your own filesystem.
The [setup walkthrough](setup.md) gets you from zero to a working connection.

The server is **read-first**: everything that only looks things up is freely
callable, and the only thing that files anything with ANAF — e-Transport — is
gated behind an explicit human confirmation.

## Public lookups — no login needed

These ride ANAF's public no-auth services, so they work even before the
certificate login (and with no OAuth credentials configured at all):

| Tool | What it does |
|---|---|
| `anaf_lookup_taxpayers` | Verify partners by CUI/CIF: name, address, VAT status, TVA la încasare, split-VAT, inactive flag — in bulk if you like |
| `anaf_lookup_efactura_register` | RO e-Factura register membership |
| `anaf_lookup_farmers` | Farmers' register (RegAgric) |
| `anaf_lookup_cult_entities` | Religious-entities register (RegCult) |
| `anaf_financial_statement` | A company's filed financial statements (bilanț) for a year |
| `efactura_validate` | ANAF's authoritative server-side invoice validation (CIUS-RO / BR-RO) — validates only, files nothing |

## e-Factura inbox — read-only

The e-Factura surface is deliberately **read-only**: outbound invoices come from
your invoicing software, which files with ANAF directly, so there are no invoice
filing tools.

| Tool | What it does |
|---|---|
| `auth_status` | Reports whether the stored ANAF login is valid |
| `efactura_list_messages` | List received/sent messages for a date window |
| `efactura_download` | Download a message as an easy-to-read flat view; optionally save the signed ZIP (`save_zip_as`) and/or ANAF's official PDF rendering (`save_pdf_as`) to paths you name |

Saved artifacts go to **disk, never into the conversation** — that's what powers
batch flows like *"export last month's invoices as `<date> - <partner>.pdf`"*. An
existing file is never silently replaced: a name collision is refused and
reported, and only an explicit `overwrite=true` replaces it. The PDF is also
available as the MCP resource `anafmsg://<message_id>/pdf`.

## e-Transport — reads plus two-step gated filing

Read tools, freely callable:

| Tool | What it does |
|---|---|
| `etransport_list` | Recent notifications for a CIF |
| `etransport_get_status` | An upload's processing status |
| `etransport_lookup` | Active declarations / UIT lookups |
| `etransport_nomenclature` | The XSD code lists (counties, border points, customs offices, operation types, …) plus the UN/ECE unit codes — names are accepted anywhere a coded field is |

Filing is split **prepare → confirm → submit**, and nothing reaches ANAF without
your explicit approval:

| Tool | What it does |
|---|---|
| `etransport_prepare_declaration` | Compose a new declaration (or a correction, via `correction_of_uit`) from structured fields |
| `etransport_prepare_deletion` | Compose a UIT deletion |
| `etransport_prepare_confirmation` | Compose an arrival confirmation |
| `etransport_prepare_vehicle_change` | Compose a vehicle change |
| `etransport_prepare` | Same gate, for ready-made XML you already have |
| `etransport_submit` | File a prepared document |

Every `prepare*` returns a human-readable preview plus a **confirmation token**
cryptographically bound to the exact document bytes and the CIF being filed for.
`etransport_submit` files only when given that token and `confirm=true`, and each
token is **single-use** — so a non-idempotent upload can never be repeated on one
approval, and any mangling of the document between prepare and submit fails
closed.

## Resources and prompts

The compiled [ANAF API reference](../anaf-reference/README.md) is served as
read-only MCP resources, and the [workflow skills](skills.md) as MCP prompts.

## Configuration

Configuration is environment-only, set in the MCP client's server entry:

| Variable | Meaning |
|---|---|
| `ANAFPY_CLIENT_ID` / `ANAFPY_CLIENT_SECRET` | Your ANAF OAuth application. Optional — without them the server still starts and serves the public `anaf_*` lookups and `efactura_validate`; the authenticated tools explain how to enable themselves |
| `ANAFPY_CIF` | Default fiscal code (digits only) used when the conversation doesn't say otherwise |
| `ANAFPY_ENV` | `prod` (default) or `test` — ANAF's TEST environment for practicing |
| `ANAFPY_TOKEN_STORE_BACKEND` | `keyring` (default, OS credential store) or `file` for headless/Docker hosts |
| `ANAFPY_TOKEN_STORE` | Token file path for the `file` backend (default `~/.anafpy/tokens.json`) |
| `ANAFPY_DOCS_DIR` | ANAF reference served as resources (defaults to the repo's `docs/anaf-reference/`) |
| `ANAFPY_SKILLS_DIR` | Workflow skills served as prompts (defaults to the repo's `skills/`) |

The server never drives the certificate/browser login — that stays the host-side
`anafpy auth login` CLI ([authentication](../library/auth.md)); the server only
reads and headlessly refreshes the token store it wrote.
