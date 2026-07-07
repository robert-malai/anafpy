"""The anafpy MCP server: e-Factura / e-Transport operations as Cowork skills.

Built on the phase-1 async clients (``docs/design.md`` §8). Read-only skills (status,
list, download, lookup, validate) are freely callable. Mutating skills are
**two-step**: a ``prepare`` tool renders a preview and returns a confirmation token,
and the matching ``submit`` tool will only file when handed that token back with
the *same* document and an explicit ``confirm=True``. Filing tools exist for
**e-Transport only**: the
e-Factura filing pair (``efactura_prepare_invoice`` / ``efactura_submit_invoice``) was
removed 2026-07-03 — outbound e-Factura XML comes from third-party invoicing software,
which files with ANAF directly, so the MCP surface for e-Factura is read-only (inbox,
download, validate); ``efactura_get_status`` went with the filing tools (an e-Factura
upload id only ever came from them; processed invoices surface in the inbox), while
``EFacturaClient.upload``/``get_status`` remain for library users.
Validation is ANAF's own: ``efactura_validate`` calls the
server-side ``validare`` endpoint (authoritative); there is no local rule engine. The
``anaf_*`` lookups wrap the unauthenticated public services (``anafpy.public``) and
work without a login. ``efactura_download`` keeps binary artifacts out of the model's
context: ``save_zip_as`` / ``save_pdf_as`` write the signed ZIP and ANAF's
``transformare`` PDF rendering to caller-given paths (this server is local stdio, so
its filesystem is the user's), and the PDF is also a resource template
(``anafmsg://{message_id}/pdf``) for hosts with resource UX. The compiled ANAF
reference is surfaced as read-only MCP
resources so the model can ground BR-RO explanations and code lists. The workflow
skills (``skills/*/SKILL.md``) are served as MCP **prompts** of the same name, so
prompt-capable clients (Claude Desktop, ``claude mcp add``) get the playbooks as a
user-invoked entry point.

The package splits along the registration groups: :mod:`.app` is the composition
root (``create_server``, ``main``), the tool modules are :mod:`.efactura`,
:mod:`.etransport` and :mod:`.public`, the reference resources live in
:mod:`.resources`, the skill prompts in :mod:`.prompts`, and the shared tool
annotations in :mod:`._shared`.
"""

from __future__ import annotations

from .app import create_server, main

__all__ = ["create_server", "main"]
