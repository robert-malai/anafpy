# anafpy-workflows

The ANAF workflow **skills** for Claude Cowork, packaged as a plugin so they can be
installed from the `anafpy` marketplace (`/plugin marketplace add robert-malai/anafpy`)
and surface in Cowork as Agent Skills.

- `skills/etransport-declare/` — file an RO e-Transport declaration and obtain a UIT.
- `skills/declaratie-prepare/` — author, validate (DUKIntegrator), render, and sign a
  tax declaration; manual filing, then status/recipisa.
- `skills/personal-income-summary/` — summarize a person's realized income from the
  SPV mailbox (income certificates + Declarația Unică).

## This directory is the single source of truth for the skills

`plugins/anafpy-workflows/skills/` is the **one** home of these playbooks. The MCP
server (`anafpy.mcp`) re-serves the very same files as same-name MCP **prompts** for
prompt-capable clients — its `ANAFPY_SKILLS_DIR` defaults to this directory
(`src/anafpy/mcp/prompts.py`). Edit the SKILL.md files here; nothing copies or
duplicates them.

## These skills need the anafpy connector

A skill is a playbook — it drives the anafpy MCP server's tools (`etransport_*`,
`declaratie_*`, `spv_*`). Installing this plugin alone gives Cowork the playbooks but
not the tools; the anafpy MCP server must also be configured (the **anafpy-setup**
plugin's skill wires it into `claude_desktop_config.json`). Without the connector, a
skill will fire but have no tools to call.
