# Tools

The `anafpy[mcp]` extra ships a **local stdio MCP server** that wraps the typed
clients as tools for Claude (Desktop, Code, Cowork). It runs on your own machine:
tool calls use your own tokens, and downloaded files land on your own filesystem.
The [setup walkthrough](setup.md) gets you from zero to a working connection.

The server is **read-first**: everything that only looks things up is freely
callable, and everything that files anything with ANAF — e-Factura and
e-Transport alike — is gated behind an explicit human confirmation.

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

## e-Factura — inbox, plus two-step gated filing

Read tools, freely callable:

| Tool | What it does |
|---|---|
| `auth_status` | Reports whether the stored ANAF login is valid |
| `efactura_list_messages` | List received/sent messages for a date window |
| `efactura_download` | Download a message as an easy-to-read flat view; optionally save the signed ZIP (`save_zip_as`) and/or ANAF's official PDF rendering (`save_pdf_as`) to paths you name |
| `efactura_get_status` | An upload's processing state (`ok`/`nok`), with the download id when accepted |

Saved artifacts go to **disk, never into the conversation** — that's what powers
batch flows like *"export last month's invoices as `<date> - <partner>.pdf`"*. An
existing file is never silently replaced: a name collision is refused and
reported, and only an explicit `overwrite=true` replaces it. The PDF is also
available as the MCP resource `anafmsg://<message_id>/pdf`.

Filing uses the same **prepare → confirm → submit** gate as e-Transport, with
two ways in:

| Tool | What it does |
|---|---|
| `efactura_prepare` | Gate ready-made UBL XML your invoicing software produced — the strongly recommended path when you have such software (its ledger, not ANAF's SPV, is your durable record: SPV purges messages after ~60 days); the bytes go to ANAF verbatim |
| `efactura_prepare_invoice` | Compose a complete CIUS-RO invoice or credit note from structured fields — no XML and no invoicing software needed; totals and the VAT breakdown are computed, and `local_findings` reports anafpy's translated rule check (informational — ANAF stays authoritative) |
| `efactura_submit` | File a prepared document; returns the upload id for `efactura_get_status` |

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

Every `prepare*` — e-Factura and e-Transport — returns a human-readable preview
plus a **confirmation token** cryptographically bound to the exact document
bytes and the CIF being filed for. The matching `*_submit` files only when given
that token and `confirm=true`, and each token is **single-use** — so a
non-idempotent upload can never be repeated on one approval, and any mangling of
the document between prepare and submit fails closed.

## SPV — the taxpayer's mailbox, read-only

The `spv_*` tools read **SPV (Spațiul Privat Virtual)** — receipts, decisions,
notifications — and request official reports. They authenticate with your
**qualified certificate**, not the OAuth application, and are read-only by
design: no declaration submission of any kind.

Pick a certificate once (`spv_list_certificates` / `spv_select_certificate`,
or `anafpy spv certs` + `anafpy spv select`), then establish a session either
by asking Claude to log in (**`spv_login`** — gated on your explicit approval,
because it fires your token/2FA prompt) or by running **`anafpy spv login`**
in a terminal. Sessions idle out in under an hour; the tools then ask for a
fresh login rather than failing obscurely.

| Tool | What it does |
|---|---|
| `spv_list_certificates` | Certificates usable for SPV in the OS key store (Keychain / CertStore), token and cloud-HSM ones included |
| `spv_select_certificate` | Persist which certificate the SPV login uses |
| `spv_login` | Establish a fresh SPV session — requires your explicit approval (`confirm=true`) since it fires your certificate PIN/2FA |
| `spv_status` | Session smoke test; reports the certificate's CNP/serial and `authorized_cuis` — every CUI/CNP it has SPV rights for |
| `spv_lista_mesaje` | Inbox messages from the last N days, filterable by CUI and message kind, paged |
| `spv_descarca` | Download one message's PDF to a path you name (never into context; existing files never replaced without `overwrite`) |
| `spv_nomenclature` | The SPV code lists: every report type `spv_cerere` accepts, each with a plain-language description of what it contains (so "my VAT return for March" finds `D300` without you knowing the code) and its per-type parameters, and ANAF's fixed reason (`motiv`) list for income certificates — Claude maps your stated purpose onto the exact wording ANAF prints on the certificate |
| `spv_cerere` | Request a report — `VECTOR FISCAL`, `Obligatii de plata`, `Istoric declaratii`, the `D1xx`/`D3xx` duplicates, `Duplicat Recipisa`, `Adeverinte Venit`, … Parameters are validated per report type before anything is sent; identical same-day repeats are deduped |
| `spv_asteapta_raport` | Wait for a requested report to land in the inbox and save its PDF; a `pending` answer just means "call again later" |

Like the e-Factura PDF, a message's document is also available as the MCP
resource `spvmsg://<mesaj_id>/pdf` — a disk-free path for hosts with resource
UX. It needs an active SPV session (a resource read can't ask for a login);
`spv_descarca` remains the save-to-disk path.

## Declarations — author, validate, render, sign, track (local; no filing yet)

Prepare tax declarations (D300 VAT return first) entirely on your machine:
ANAF's own DUKIntegrator validates and renders the official PDF, and your
qualified certificate signs it. Nothing is filed with ANAF in this release —
you file the signed PDF on the portal, then track it with `declaratie_status`
using the upload index the portal returned. The authoring tools need
`ANAFPY_DUK_DIR` set and signing is macOS-only for now; the status/recipisa
tools ride ANAF's public StareD112 service and need no configuration and no
login at all.

| Tool | What it does |
|---|---|
| `declaratie_validate` | Validate a declaration with ANAF's own DUKIntegrator (authoritative); returns its findings verbatim — the compose→validate→fix loop. Missing DUK/Java configuration is a tool error, not an invalid-document result |
| `declaratie_render` | Render the official multi-page PDF (XML embedded) directly to a path you name; validates first, so a failure writes no PDF. Missing DUK/Java configuration is a tool error |
| `declaratie_sign` | Sign a rendered PDF with your qualified certificate — requires your explicit approval (`confirm=true`) since it fires your PIN/2FA prompt; failures come back as `signed=false` + guidance |
| `declaratie_nr_evid` | Compose the D300 `nr_evid` payment-evidence number (it has a check digit — never compute it by hand) |
| `declaratie_duk_status` | The DUKIntegrator install: directory, Java version, and installed-vs-current validator versions (CLI-mode DUK does not auto-update); the current feed is still returned before DUK is installed |
| `declaratie_status` | Check a filed declaration's processing state by upload index + CUI — returns the client-layer `DeclarationStatusList` directly, containing all the CUI's filings from the last 3 months (max 200). Config/network/input failures return the same typed shape with `found=false` and `message` |
| `declaratie_recipisa` | Save the digitally signed recipisa (filing receipt) PDF to a path you name — available only ~60 days from filing, so archive it |

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
| `ANAFPY_SPV_SESSION` | SPV cookie-session store written by `anafpy spv login` (default `~/.anafpy/spv-session.json`) |
| `ANAFPY_SPV_IDENTITY_FILE` | Persisted SPV certificate selection (default `~/.anafpy/spv-identity.json`) |
| `ANAFPY_DUK_DIR` | The extracted DUKIntegrator `dist/` folder — enables the `declaratie_*` tools (no default) |
| `ANAFPY_DUK_JAVA` | The `java` binary DUKIntegrator runs under (optional; falls back to `java` on `PATH`) |
| `ANAFPY_SIGN_IDENTITY` | Keychain identity name to sign declarations with (optional; falls back to the persisted SPV certificate selection) |

The OAuth certificate/browser login stays host-side (`anafpy auth login` —
it structurally needs a browser; the server only reads and headlessly
refreshes the token store it wrote). The SPV login is the one interactive step
exposed as a tool: it needs no host UI — the human gate is your out-of-band
PIN/2FA approval — and `spv_login` demands your explicit go-ahead per attempt.
