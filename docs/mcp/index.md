# What you can do

With the anafpy MCP server connected to a Claude client (Claude Desktop, Claude
Code), an accountant in Romania can ask Claude to do everything below. The
[setup walkthrough](setup.md) gets you there — also available
[in Romanian](setup.ro.md) — and the [tools overview](tools.md) documents every
tool individually.

## Check partners and public data — no login required

These ride ANAF's public, no-auth services:

- **Verify a business partner by CUI/CIF** — name, address, VAT status (plătitor de
  TVA), TVA la încasare, split-VAT, inactive flag — one call, in bulk if you like.
- **Check whether a partner is enrolled in RO e-Factura.**
- **Look up the farmers' register (RegAgric) and religious-entities register (RegCult).**
- **Pull a company's filed financial statements (bilanț)** for a given year.
- **Validate an invoice XML** against ANAF's authoritative server-side `validare`
  (CIUS-RO / BR-RO rules) — no filing.

## Work your e-Factura inbox and file invoices

Needs the one-time certificate login:

- **List received and sent invoice messages** for a date window.
- **Download an invoice** as an easy-to-read view, and **save the official signed ZIP
  and/or a rendered PDF** to disk — powering batch flows like "export last month's
  invoices as `<date> - <partner>.pdf`".
- **File an invoice or credit note** — from the XML your invoicing software
  exported (recommended when you have one), or **composed by Claude from plain
  business fields** when you don't. Either way filing is two-step gated: you see
  a preview and nothing reaches ANAF until you explicitly confirm.

## Declare goods transport in e-Transport — with a confirmation step

Needs the login:

- **File a declaration and get a UIT code** from transport data in any source — an
  email, a PDF invoice, a CMR, a spreadsheet — and **correct, delete, confirm, or
  change the vehicle** on an existing one.
- **List recent notifications, check an upload's status, and look up active
  declarations / UIT codes.**
- Filing is **two-step gated**: Claude shows you a preview, and nothing is submitted to
  ANAF until you explicitly confirm.

## Read your SPV mailbox and pull official reports

Needs the certificate — read-only:

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

## Prepare and sign a tax declaration

Local; signing needs your certificate in the macOS Keychain or the Windows
certificate store:

- **Fill in, validate, render, and sign a declaration** from unstructured info —
  an accountant's email, a spreadsheet, "file my VAT return for March": Claude
  picks the form, authors the XML, validates it with ANAF's own DUKIntegrator
  (the authority) in a fix-and-retry loop, renders the official PDF, and signs
  it with your qualified certificate (the PIN/2FA prompt is the human gate).
- **Every electronically filable form is in scope** — ANAF's DUKIntegrator
  carries a validator for each (173 at last count, inventoried in the
  [declaration reference](../anaf-reference/declaratii/forms/README.md)) — and
  the declarations a typical SME actually files come with hands-on **completion
  guides** (purpose and deadlines, row-by-row filling maps, validated examples,
  filing gotchas) that Claude reads before authoring:

  | Form | What it is |
  |---|---|
  | D300 | VAT return (decont de TVA) |
  | D390 | EU recapitulative statement (VIES) |
  | D394 | Informative return on domestic supplies/purchases |
  | D100 | Payment obligations to the state budget |
  | D112 | Payroll: wage income tax + social contributions |
  | D101 | Annual corporate profit tax |
  | D710 | Rectifying declaration (corrects D100-family filings) |
  | D301 | Special VAT return (persons not VAT-registered who owe VAT) |
  | D700 | Fiscal registration / fiscal-vector changes |
  | D406 | SAF-T (Standard Audit File for Tax) |
  | D205 | Annual informative on income tax withheld at source |
  | D212 | Individuals' unified declaration (declarația unică) |

- **File from Claude, with you approving every consequential step** — the
  portal login (your certificate PIN/2FA) and the filing itself each require
  your explicit go-ahead, through the same two-step prepare→submit gate as
  e-Factura and e-Transport. Declarations file on ANAF's real portal (there is
  no test environment), and the feature is opt-out
  (`ANAFPY_DECLARATII_UPLOAD=off`) if you prefer uploading the signed PDF
  yourself.
- **Track the filing afterwards, with no login at all** — given the upload index
  the portal returns, Claude checks whether the declaration was accepted (ANAF's
  public status service) and saves the digitally signed filing receipt PDF —
  which ANAF keeps available for only ~60 days.

## Good to know

The e-Factura and e-Transport tools need a one-time login with your **qualified
digital certificate** (the same one you use on ANAF's SPV) — the public checks
above work without it. The server runs **locally** on your own machine, so
downloaded invoices and PDFs land on your own filesystem. Beyond individual
tools, the [workflow skills](skills.md) chain them into complete playbooks —
declaring a transport from a CMR photo, preparing a declaration from an email,
summarizing a person's yearly income from SPV certificates.
