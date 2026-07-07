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
