"""The anafpy MCP server (phase 2): ANAF operations (e-Factura, e-Transport, SPV,
public lookups) as Cowork skills.

A local stdio connector built on the phase-1 async clients (``DESIGN.md`` §8).
Requires the ``anafpy[mcp]`` extra; run with ``python -m anafpy.mcp`` (host-side,
where the token store written by ``anafpy auth login`` lives).

Read-only skills (status, list, download, lookup, validate) are freely callable.
Filing — **both OAuth services** — is two-step: a ``prepare`` tool renders a preview
and returns a confirmation token bound to the exact document bytes and the CIF, and
the matching ``submit`` tool files only when handed that token back with the *same*
document and an explicit ``confirm=True``; tokens are single-use, so one approval can
never repeat a non-idempotent upload. Each service takes two prepare shapes:
ready-made XML gated verbatim (``efactura_prepare`` / ``etransport_prepare`` — for
invoices the strongly recommended path whenever upstream invoicing software produced
the document) and structured composition from the client-layer flat models
(``efactura_prepare_invoice``; ``etransport_prepare_declaration`` / ``_deletion`` /
``_confirmation`` / ``_vehicle_change``); ``efactura_get_status`` polls a filing to
``ok``/``nok``. Validation authority is ANAF's own: ``efactura_validate`` calls the
server-side ``validare`` endpoint (public, no-auth); the hand-translated local rule
set rides composed prepares only as informational ``local_findings`` and never
withholds the token. The ``anaf_*`` lookups wrap the unauthenticated public
services (``anafpy.public``) and work without a login; the ``spv_*`` tools are
read-only mailbox access over the certificate cookie session (the explicitly gated
``spv_login`` establishes it). ``efactura_download`` keeps binary artifacts out of
the model's context: ``save_zip_as`` / ``save_pdf_as`` write the signed ZIP and
ANAF's ``transformare`` PDF rendering to caller-given paths (this server is local
stdio, so its filesystem is the user's), and the PDF is also a resource template
(``anafmsg://{message_id}/pdf``) for hosts with resource UX — as is an SPV
message's document (``spvmsg://{mesaj_id}/pdf``). The compiled ANAF reference is
surfaced as read-only MCP resources so the model can ground BR-RO explanations and
code lists. The workflow skills (``skills/*/SKILL.md``) are served as MCP
**prompts** of the same name, so prompt-capable clients (Claude Desktop,
``claude mcp add``) get the playbooks as a user-invoked entry point.

The package splits **by service**: each service package owns its tools plus its
own models and helpers — :mod:`.efactura` (tools, gate shapes, XML projections),
:mod:`.etransport` (tools, gate shapes, nomenclatures + UN/ECE unit codes),
:mod:`.spv` (tools, report-type nomenclature), :mod:`.public` (lookup tools).
The shared core is only what at least two services genuinely use: :mod:`.app` is
the composition root (``create_server``, ``main``), :mod:`.config` the env-driven
:class:`ServerConfig`, :mod:`.context` the per-process :class:`~.context.AppContext`
(auth + lazy clients + gate/dedupe state), :mod:`.gate` the two-step filing gate
(confirmation tokens, the ``XmlInput`` base, the shared submit skeleton),
:mod:`.artifacts` the tool annotations + collision-guarded artifact writer,
:mod:`.reference` the ANAF-reference resources, and :mod:`.prompts` the skill
prompts.
"""

from __future__ import annotations

from .app import create_server, main
from .config import ServerConfig

__all__ = ["ServerConfig", "create_server", "main"]
