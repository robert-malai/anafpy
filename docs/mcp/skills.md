# Workflow skills

Beyond individual tools, the server ships **workflow playbooks as MCP prompts** —
a user-invoked entry point for multi-step flows. Each `skills/*/SKILL.md` in the
repository is served as a same-name prompt, so prompt-capable clients surface
them directly: Claude Desktop's "+" menu, or `/mcp__anafpy__<name>` in Claude
Code. An optional `source` argument seeds the workflow with where the data lives.

The SKILL.md files are the single source of truth — they travel with the
checkout, whichever way the server is connected.

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
