# Workflow skills

Beyond individual tools, these multi-step flows ship as **workflow playbooks**,
delivered two ways from one source. Their home is the **`anafpy-workflows`
plugin** (`plugins/anafpy-workflows/skills/*/SKILL.md`): installed from the
`anafpy` marketplace (`/plugin marketplace add robert-malai/anafpy`) they surface
in **Cowork** (and chat) as Agent Skills, invoked in plain language or picked from
the sidebar. The MCP server **also** re-serves the same files as same-name MCP
**prompts**, so other prompt-capable clients get them too: Claude Desktop's "+"
menu, or `/mcp__anafpy__<name>` in Claude Code. An optional `source` argument
seeds the workflow with where the data lives.

There is one source of truth — the plugin's SKILL.md files — with two consumers.
A skill drives the anafpy tools, so a Cowork user needs both the plugin (the
playbooks) and the anafpy connector (the tools; see the
[setup walkthrough](setup.md)).

## `etransport-declare`

Files an e-Transport declaration and obtains a UIT code from transport data found
in **any source** — an email, a PDF invoice, a CMR, a spreadsheet, or the
conversation itself. The playbook walks Claude through the full flow:

1. **Extract** the transport data from the source you point it at.
2. **Map** it onto the structured declaration (looking up ANAF codes via
   `etransport_nomenclature` where needed).
3. **Prepare** — `etransport_prepare_declaration` composes the XML and returns a
   preview plus a confirmation token.
4. **Show you the preview for approval.** Nothing has been filed yet.
5. **Submit** on your explicit approval — `etransport_submit` with the token.
6. **Poll** the status until ANAF issues a valid UIT, and report it.

It also handles corrections of an already-issued UIT (`correction_of_uit`).

The same two-step gate described in [Tools](tools.md) applies throughout: the
skill can never skip the preview-and-approval step, because the submit tool
refuses to file without the single-use confirmation token plus `confirm=true`.

## `personal-income-summary`

Answers *"what was my income?"* for a Romanian natural person by pulling the
authoritative ANAF records from the **SPV mailbox** and presenting a clean
per-year summary — with an optional Excel workbook. It triggers on both formal
and casual phrasing, in Romanian or English (*"veniturile mele"*, *"cât am
câștigat anul trecut"*, "income summary", "adeverință de venit"). The playbook
walks Claude through:

1. **Confirm the SPV session** — `auth_status` then `spv_status` (which returns
   the certificate holder's CNP and authorized CUIs). This skill is read-only:
   it never files anything.
2. **Pick the CNP and years** — defaults to *personal* income (the CNP on the
   certificate) over the last three completed fiscal years; asks only if the
   account also holds company CIFs and the request is ambiguous.
3. **Request the reports** — `spv_cerere` for both `Adeverinte Venit` (the
   authoritative income certificate) and `D212` (the Declarația Unică duplicate,
   as a cross-check) per year.
4. **Wait and download** — `spv_asteapta_raport` saves each PDF to disk (retrying
   the occasional handshake timeout).
5. **Extract and summarize** — reads the figures from the certificates and gives
   a per-year table with totals and a trend line, keeping the official PDFs
   alongside.
6. **Offer an Excel workbook** (optional) — a formula-driven per-year summary
   plus one detail sheet per year, built via the **xlsx** skill.

Because it only uses the read-only `spv_*` tools, there is no filing gate — the
human gate here is the SPV login (certificate PIN / 2FA), described in the
[setup walkthrough](setup.md) step 7.

## `declaratie-prepare`

Builds, validates, renders, signs, files, and tracks a Romanian tax
declaration starting from **unstructured source data** — an accountant's
email, a spreadsheet, pasted numbers, or just "file my VAT return for March".
It drives the `declaratie_*` tools plus the public `anaf_*` lookups. The
playbook walks Claude through:

1. **Identify the form** — named by you it is simply echoed; otherwise inferred
   from the data against the form inventory, asking only when two forms remain
   plausible. `declaratie_duk_status` confirms DUKIntegrator is configured and
   flags a stale validator.
2. **Read the form's completion guide** (served as an `anafref://` resource) —
   who files and when, the row-by-row → XSD attribute map, validated example
   instances, and the known gotchas.
3. **Infer identity via lookup, not questions** — `anaf_lookup_taxpayers` fills
   the company name/address from the CUI and cross-checks eligibility (VAT
   registration, cash accounting, inactive flags); partner CUIs are validated
   the same way.
4. **Ask for the rest in one batch** — period, settlement type, amounts, and
   the form's must-ask fields; amounts are never guessed or extrapolated.
5. **Author the XML** from the guide's mapping, computing derived rows and the
   control sum per its formulas, and `nr_evid` with `declaratie_nr_evid`
   (form-aware), never by hand.
6. **Validate in a loop** — `declaratie_validate`; the findings are ANAF's own
   messages, so fix the XML and retry until `ok` (warning-only forms like D700
   pass with the notice relayed).
7. **Pre-filing reconciliation** — states what ANAF will cross-check this
   filing against (D300 ↔ D394 ↔ D390, e-Factura, SAF-T) so mismatches surface
   before filing, not as conformity notifications after.
8. **Render and review** — `declaratie_render` writes the official PDF for you
   to check.
9. **Sign on your explicit go** — `declaratie_sign` with `confirm=true`, after
   a warning that the certificate PIN/2FA prompt is about to fire.
10. **File on your explicit go** — `declaratie_portal_status` probes the
    portal session (no 2FA); if it lapsed, `declaratie_portal_login` with your
    approval (your certificate prompt fires); then `declaratie_prepare` →
    filing recap → `declaratie_submit` with `confirm=true`. Where the portal
    tools are opted out (`ANAFPY_DECLARATII_UPLOAD`), you file the signed PDF
    at anaf.ro → Depunere declarații yourself and note the upload index.
11. **Confirm** — `declaratie_status` checks acceptance by upload index (no
    login needed) and `declaratie_recipisa` saves the signed filing receipt —
    available only ~60 days, so it's archived promptly.

The human gates are the batched questions, the PDF review, the signature
approval, the portal login (both fire your certificate PIN / 2FA), and the
filing approval; the skill never signs or files without your explicit
go-ahead relayed as `confirm=true`, and a signature approval never doubles as
the filing approval.
