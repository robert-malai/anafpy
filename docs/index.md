# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), and the
**public no-auth registries** (VAT/taxpayer lookups, financial statements) — plus a
local MCP server that exposes them as [Claude Cowork](https://claude.com) skills.

anafpy is a **thin transport client** — no persistence, no accounting logic. For
**e-Factura** there are two ways out: bring the invoice XML your own invoicing
system produced (the strongly recommended path — anafpy validates, files, tracks,
and never re-composes it; ANAF's SPV purges filed messages after ~60 days, so
your system of record stays yours), or, with no upstream system at all, compose a
complete CIUS-RO invoice or credit note from plain business fields with the
[authoring models](library/authoring.md) — totals and the VAT breakdown computed
for you. Documents you read back come wrapped in a friendly **flat read view**
for easy display. **e-Transport** is fully translated too: you author
declarations, UIT deletions, confirmations, and vehicle changes from structured
fields, no XML handling needed.

Requires **Python 3.12+**. Built on **httpx** and **Pydantic v2**. Licensed
[Apache-2.0](https://github.com/robert-malai/anafpy/blob/main/LICENSE) —
independent / unofficial, not affiliated with ANAF, provided **as-is**.

## Two ways in

The documentation is organized for two very different readers — pick your track:

**You want ANAF operations inside Claude** (Claude Desktop, Claude Code, Cowork) —
an accountant's track, no programming involved. anafpy ships a local MCP server:
Claude can look up business partners, work your e-Factura inbox (list, download,
save PDFs), and file e-Transport declarations with a human confirmation step.

- Start at the [setup walkthrough](mcp/setup.md) — ANAF app registration, the
  one-time certificate login, and the Claude configuration, written for a
  non-developer.
- Then see [what the tools can do](mcp/tools.md) and the
  [workflow skills](mcp/skills.md).

**You want the Python library** — typed async clients over ANAF's APIs, for your
own software.

- Start at the [quickstart](library/quickstart.md), then the per-service guides:
  [authentication](library/auth.md), [e-Factura](library/efactura.md),
  [e-Transport](library/etransport.md), [public services](library/public.md), and
  the [error model](library/errors.md) (worth reading before shipping anything).
- The [API reference](api/efactura.md) documents the public surface from the
  docstrings.

## Extras

- [ANAF API reference](anaf-reference/README.md) — a compiled, English-language
  local reference of ANAF's own APIs (OAuth, e-Factura, e-Transport, public
  services), with per-section provenance back to ANAF's original documents.
- Contributing or curious about the internals? The design rationale lives in
  [DESIGN.md](https://github.com/robert-malai/anafpy/blob/main/DESIGN.md) in the
  repository — developer material, kept next to the code.
