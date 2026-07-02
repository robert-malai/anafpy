"""The anafpy MCP server: e-Factura / e-Transport operations as Cowork skills.

Built on the phase-1 async clients (``DESIGN.md`` §8). Read-only skills (status, list,
download, lookup, validate) are freely callable. Mutating skills are **two-step**: a
``prepare`` tool renders a preview and returns a confirmation token, and the matching
``submit`` tool will only file when handed that token back with the *same* document and
an explicit ``confirm=True``. Validation is ANAF's own: ``efactura_validate`` calls the
server-side ``validare`` endpoint (authoritative); there is no local rule engine. The
``anaf_*`` lookups wrap the unauthenticated public services (``anafpy.public``) and
work without a login. The compiled ANAF reference is surfaced as read-only MCP
resources so the model can ground BR-RO explanations and code lists.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..efactura.models import Filter, TransformStandard, UploadStandard
from ..exceptions import AnafConfigError, AnafError
from ..public.models import RegistryLookup
from .config import ServerConfig
from .context import AppContext, AuthStatus
from .documents import invoice_view, resolve_xml, transport_view, upload_standard
from .models import (
    EtransportXmlInput,
    PreparedSubmission,
    SubmitResult,
    UblXmlInput,
)
from .tokens import ConfirmationError, issue_token, verify_token

__all__ = ["create_server"]

_INSTRUCTIONS = """\
Typed access to Romania's ANAF e-Factura (e-invoicing) and e-Transport services.

Filing an invoice or transport declaration is a two-step, human-gated flow:
  1. call `efactura_prepare_invoice` / `etransport_prepare` — this parses the
     document, returns a preview and totals, and a confirmation token;
  2. show the preview to the user, get explicit approval, then call the matching
     `*_submit_*` tool with that token and confirm=True.

Confirmation tokens are single-use and bound to the exact document, the CIF, and the
upload standard — to file again (or for another CIF), run the prepare step again.

To pre-check an invoice, `efactura_validate` runs ANAF's own server-side validator
without filing (authoritative). e-Transport has no standalone validator — ANAF
validates on upload. If a tool reports "not authenticated", the user must run
`anafpy auth login` host-side.

The `anaf_*` lookup tools query ANAF's PUBLIC no-auth services and work even without
a login: the taxpayer/VAT registry (`anaf_lookup_taxpayers` answers "is this CUI
VAT-registered / e-Factura-registered" and more, in one call — use it to sanity-check
a counterparty before filing), the RO e-Factura opt-in register, the farmers/cult
registers, and public annual financial statements. Registry membership must be read
from the `registered` booleans, not from presence in `found`. Requests are paced at
ANAF's 1 request/second rule, so large batches take time.
"""

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_MUTATING = ToolAnnotations(
    readOnlyHint=False, idempotentHint=False, openWorldHint=True
)

_INVOICE_KIND = "efactura.invoice"
_TRANSPORT_KIND = "etransport.declaration"

_TOKEN_USED_MESSAGE = (
    "confirmation token already used — filing is never repeated on the same "
    "approval; run the prepare step again"
)


def _invoice_context(cif: str, standard: str) -> str:
    """Submission parameters bound into an e-Factura confirmation token."""
    return f"cif={cif};standard={standard}"


def _transport_context(cif: str) -> str:
    """Submission parameters bound into an e-Transport confirmation token."""
    return f"cif={cif}"


def _parse_window_dt(value: str | None, *, field: str) -> datetime | None:
    """Parse an ISO 8601 date/datetime string for a list window, or ``None``."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise AnafConfigError(
            f"efactura_list_messages: `{field}` must be ISO 8601 (got {value!r})"
        ) from exc


def _transform_standard(xml: bytes) -> TransformStandard:
    """The ``validare``/``transformare`` path segment matching the document kind."""
    if upload_standard(xml) is UploadStandard.CN:
        return TransformStandard.CREDIT_NOTE
    return TransformStandard.INVOICE


def create_server(config: ServerConfig | None = None) -> FastMCP:
    """Build the configured :class:`FastMCP` server (stdio transport)."""
    cfg = config or ServerConfig.from_env()
    ctx = AppContext(cfg)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await ctx.aclose()

    mcp = FastMCP("anafpy", instructions=_INSTRUCTIONS, lifespan=lifespan)

    # -- auth ------------------------------------------------------------------------

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Report whether a usable ANAF session is present, and when the "
        "tokens expire. Call this first; if not authenticated, ask the user to run "
        "`anafpy auth login` host-side.",
    )
    def auth_status() -> AuthStatus:
        return ctx.auth_status()

    _register_efactura(mcp, ctx, cfg)
    _register_etransport(mcp, ctx, cfg)
    _register_public(mcp, ctx)
    _register_resources(mcp)
    return mcp


def _register_efactura(mcp: FastMCP, ctx: AppContext, cfg: ServerConfig) -> None:
    @mcp.tool(
        annotations=_READ_ONLY,
        description="List e-Factura messages (sent/received/errors) for a fiscal code. "
        "Give a window as EITHER `days` (1-60) OR an ISO `start`+`end` date range "
        "(e.g. '2026-06-01'); all pages are fetched and flattened automatically.",
    )
    async def efactura_list_messages(
        cif: str | None = None,
        days: int | None = None,
        start: str | None = None,
        end: str | None = None,
        filter: str | None = None,
    ) -> dict[str, object]:
        resolved = cfg.require_cif(cif)
        flt = Filter(filter) if filter else None
        messages = [
            m
            async for m in ctx.efactura().list_messages(
                cif=resolved,
                days=days,
                start=_parse_window_dt(start, field="start"),
                end=_parse_window_dt(end, field="end"),
                filter=flt,
            )
        ]
        return {
            "messages": [m.model_dump() for m in messages],
            "count": len(messages),
        }

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Get the processing state of an e-Factura upload by its upload id "
        "(index_incarcare). Returns ok / nok / in prelucrare and a download id when "
        "ready.",
    )
    async def efactura_get_status(upload_id: str) -> dict[str, object]:
        status = await ctx.efactura().get_status(upload_id)
        return {
            "state": status.state.value,
            "download_id": status.download_id,
            "errors": status.errors,
            "is_terminal": status.is_terminal,
        }

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Download a processed e-Factura message (the signed invoice/errors "
        "ZIP) by id. Returns the decoded content and an easy-to-read `invoice` view of "
        "the received document when it is a parseable invoice/credit-note.",
    )
    async def efactura_download(message_id: str) -> dict[str, object]:
        msg = await ctx.efactura().download(message_id)
        content = (
            msg.content_xml.decode("utf-8", errors="replace")
            if msg.content_xml is not None
            else None
        )
        view = msg.view
        return {
            "has_content": msg.content_xml is not None,
            "has_signature": msg.signature_xml is not None,
            "content_xml": content,
            "invoice": view.model_dump(mode="json") if view is not None else None,
        }

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Validate a complete UBL invoice / credit note (XML) with ANAF's "
        "own server-side validator, without filing. Authoritative — the same rules "
        "the upload is checked against.",
    )
    async def efactura_validate(document: UblXmlInput) -> dict[str, object]:
        xml = resolve_xml(document)
        result = await ctx.efactura().validate_remote(
            xml, standard=_transform_standard(xml)
        )
        return {
            "valid": result.valid,
            "messages": result.messages,
            "trace_id": result.trace_id,
        }

    @mcp.tool(
        annotations=_MUTATING,
        description="STEP 1 of filing an invoice: parse the supplied UBL XML and "
        "return an easy-to-read preview + a confirmation token bound to this document "
        "and CIF. Show the preview to the user for approval; then call "
        "efactura_submit_invoice with the token and the same cif. Does NOT file. "
        "Use efactura_validate first for ANAF's server-side pre-check.",
    )
    async def efactura_prepare_invoice(
        document: UblXmlInput, cif: str | None = None
    ) -> PreparedSubmission:
        return _prepare_invoice(ctx, cfg, document, cif=cif)

    @mcp.tool(
        annotations=_MUTATING,
        description="STEP 2 of filing an invoice: file the supplied UBL XML with ANAF. "
        "Requires the confirmation_token from efactura_prepare_invoice for the SAME "
        "document and confirm=True (set only after the user approved the preview).",
    )
    async def efactura_submit_invoice(
        document: UblXmlInput,
        confirmation_token: str,
        confirm: bool = False,
        cif: str | None = None,
    ) -> SubmitResult:
        if not confirm:
            return SubmitResult(
                accepted=False,
                message="confirm=False — set confirm=True only after the user "
                "approves the preview from efactura_prepare_invoice.",
            )
        try:
            xml = resolve_xml(document)
            resolved = cfg.require_cif(cif)
        except AnafError as exc:
            return SubmitResult(accepted=False, errors=[str(exc)])
        standard = upload_standard(xml)
        try:
            expires_at = verify_token(
                cfg.signing_key,
                confirmation_token,
                kind=_INVOICE_KIND,
                payload=xml,
                context=_invoice_context(resolved, standard.value),
            )
        except ConfirmationError as exc:
            return SubmitResult(accepted=False, message=str(exc))
        if not ctx.token_ledger.consume(confirmation_token, expires_at):
            return SubmitResult(accepted=False, message=_TOKEN_USED_MESSAGE)
        result = await ctx.efactura().upload(xml, cif=resolved, standard=standard)
        return SubmitResult(
            accepted=result.accepted,
            upload_id=result.upload_id,
            errors=result.errors,
            message=(
                f"filed — poll efactura_get_status with upload_id {result.upload_id}"
                if result.accepted
                else "ANAF rejected the document at submission"
            ),
        )


def _prepare_invoice(
    ctx: AppContext,
    cfg: ServerConfig,
    document: UblXmlInput,
    *,
    cif: str | None = None,
) -> PreparedSubmission:
    try:
        xml = resolve_xml(document)
        resolved = cfg.require_cif(cif)
    except AnafError as exc:
        return PreparedSubmission(valid=False, message=str(exc))
    preview = invoice_view(xml)
    token = issue_token(
        cfg.signing_key,
        kind=_INVOICE_KIND,
        payload=xml,
        context=_invoice_context(resolved, upload_standard(xml).value),
    )
    return PreparedSubmission(
        valid=True,
        confirmation_token=token,
        cif=resolved,
        invoice_preview=preview,
        message=_prepare_message(parsed=preview is not None),
    )


def _register_etransport(mcp: FastMCP, ctx: AppContext, cfg: ServerConfig) -> None:
    @mcp.tool(
        annotations=_READ_ONLY,
        description="List e-Transport notifications from the last `days` (1-60) for a "
        "fiscal code.",
    )
    async def etransport_list(days: int, cif: str | None = None) -> dict[str, object]:
        resolved = cfg.require_cif(cif)
        notifications = [
            n
            async for n in ctx.etransport().list_notifications(days=days, cif=resolved)
        ]
        return {
            "notifications": [n.model_dump() for n in notifications],
            "count": len(notifications),
        }

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Get the processing state of an e-Transport upload by its upload "
        "id (index_incarcare).",
    )
    async def etransport_get_status(upload_id: str) -> dict[str, object]:
        status = await ctx.etransport().get_status(upload_id)
        return {
            "state": status.state.value,
            "errors": status.errors,
            "is_terminal": status.is_terminal,
        }

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Look up active e-Transport declarations where a fiscal code is "
        "the transport organiser (the `info` endpoint).",
    )
    async def etransport_lookup(
        cui_op: str,
        cui_decl: str | None = None,
        uit: str | None = None,
        ref_decl: str | None = None,
    ) -> dict[str, object]:
        result = await ctx.etransport().info(
            cui_op=cui_op, cui_decl=cui_decl, uit=uit, ref_decl=ref_decl
        )
        return {
            "items": [i.model_dump() for i in result.items],
            "error": result.error,
        }

    @mcp.tool(
        annotations=_MUTATING,
        description="STEP 1 of filing an e-Transport declaration: parse the supplied "
        "XML and return an easy-to-read preview + a confirmation token bound to this "
        "document and CIF. Show the preview for approval; then call etransport_submit "
        "with the token and the same cif. Does NOT file. (There is no standalone "
        "validator — ANAF validates the declaration on upload.)",
    )
    async def etransport_prepare(
        document: EtransportXmlInput, cif: str | None = None
    ) -> PreparedSubmission:
        return _prepare_transport(ctx, cfg, document, cif=cif)

    @mcp.tool(
        annotations=_MUTATING,
        description="STEP 2 of filing an e-Transport declaration: file the supplied "
        "XML with ANAF and return the UIT code. Requires the confirmation_token from "
        "etransport_prepare for the SAME document and confirm=True.",
    )
    async def etransport_submit(
        document: EtransportXmlInput,
        confirmation_token: str,
        confirm: bool = False,
        cif: str | None = None,
    ) -> SubmitResult:
        if not confirm:
            return SubmitResult(
                accepted=False,
                message="confirm=False — set confirm=True only after the user "
                "approves the preview from etransport_prepare.",
            )
        try:
            xml = resolve_xml(document)
            resolved = cfg.require_cif(cif)
        except AnafError as exc:
            return SubmitResult(accepted=False, errors=[str(exc)])
        try:
            expires_at = verify_token(
                cfg.signing_key,
                confirmation_token,
                kind=_TRANSPORT_KIND,
                payload=xml,
                context=_transport_context(resolved),
            )
        except ConfirmationError as exc:
            return SubmitResult(accepted=False, message=str(exc))
        if not ctx.token_ledger.consume(confirmation_token, expires_at):
            return SubmitResult(accepted=False, message=_TOKEN_USED_MESSAGE)
        result = await ctx.etransport().upload(xml, cif=resolved)
        return SubmitResult(
            accepted=result.accepted,
            upload_id=result.upload_id,
            uit=result.uit,
            errors=result.errors,
            message=(
                f"filed — UIT {result.uit}"
                if result.accepted
                else "ANAF rejected the declaration at submission"
            ),
        )


def _prepare_transport(
    ctx: AppContext,
    cfg: ServerConfig,
    document: EtransportXmlInput,
    *,
    cif: str | None = None,
) -> PreparedSubmission:
    try:
        xml = resolve_xml(document)
        resolved = cfg.require_cif(cif)
    except AnafError as exc:
        return PreparedSubmission(valid=False, message=str(exc))
    preview = transport_view(xml)
    token = issue_token(
        cfg.signing_key,
        kind=_TRANSPORT_KIND,
        payload=xml,
        context=_transport_context(resolved),
    )
    return PreparedSubmission(
        valid=True,
        confirmation_token=token,
        cif=resolved,
        transport_preview=preview,
        message=_prepare_message(parsed=preview is not None),
    )


def _register_public(mcp: FastMCP, ctx: AppContext) -> None:
    """Read-only lookups over ANAF's unauthenticated public services.

    No CIF/auth involved; the client paces requests at ANAF's 1 req/s rule. ``raw``
    body bytes are kept client-side and excluded from the tool payloads.
    """

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Look up CUIs (max 100) in ANAF's public taxpayer/VAT registry — "
        "no auth needed. One call answers, per CUI as of `date` (ISO, default "
        "today): VAT registration, VAT-on-collection, inactive status, split-VAT, "
        "RO e-Factura register membership, and general company data. CUIs with no "
        "data come back in `not_found`. The 'RO' VAT prefix is tolerated.",
    )
    async def anaf_lookup_taxpayers(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_taxpayers(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Query the Registrul RO e-Factura (opt-in register) for CUIs "
        "(max 100) — no auth needed. Mostly relevant for B2G option dates; for a "
        "plain 'is this CUI e-Factura-registered' check prefer anaf_lookup_taxpayers "
        "(its `efactura_registered` answers it alongside everything else).",
    )
    async def anaf_lookup_efactura_register(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_efactura_register(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Query ANAF's farmers' special-regime register (art. 315¹) for "
        "CUIs (max 500) — no auth needed. Membership is the record's `registered` "
        "boolean: unknown CUIs still come back under `found` with empty fields.",
    )
    async def anaf_lookup_farmers(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_farmers(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Query ANAF's register of cult entities (tax-credit eligible "
        "religious entities) for CUIs (max 500) — no auth needed. Membership is the "
        "record's `registered` boolean.",
    )
    async def anaf_lookup_cult_entities(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_cult_entities(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        annotations=_READ_ONLY,
        description="Fetch the public indicators of one CUI's annual financial "
        "statement (bilanț) for a given year — no auth needed. The indicator set "
        "varies by statement type (commercial / banking / insurance).",
    )
    async def anaf_financial_statement(cui: str | int, year: int) -> dict[str, object]:
        statement = await ctx.public().get_financial_statement(cui, year)
        return statement.model_dump(mode="json", exclude={"raw"})


def _lookup_payload(result: RegistryLookup[Any]) -> dict[str, object]:
    payload: dict[str, object] = result.model_dump(mode="json", exclude={"raw"})
    payload["count"] = len(result.found)
    return payload


def _prepare_message(*, parsed: bool) -> str:
    if not parsed:
        return (
            "the document did not parse — no preview; ANAF will likely reject it. "
            "Review carefully before submitting with the confirmation token."
        )
    return (
        "not pre-validated (ANAF is authoritative). Review the preview with the "
        "user, then submit with the confirmation token."
    )


def _docs_dir() -> Path | None:
    override = os.environ.get("ANAFPY_DOCS_DIR")
    if override:
        path = Path(override).expanduser()
        return path if path.is_dir() else None
    candidate = Path(__file__).resolve().parents[3] / "docs" / "anaf-reference"
    return candidate if candidate.is_dir() else None


def _register_resources(mcp: FastMCP) -> None:
    """Expose the compiled ANAF reference Markdown as read-only resources."""
    docs = _docs_dir()
    if docs is None:
        return
    for md in sorted(docs.rglob("*.md")):
        if md.name == "README.md" or "_sources" in md.parts:
            continue
        rel = md.relative_to(docs).with_suffix("")
        uri = f"anafref://{rel.as_posix()}"
        mcp.resource(
            uri,
            name=f"ANAF reference: {rel.as_posix()}",
            description=(
                "Compiled ANAF API reference (status may be draft; partly Romanian)."
            ),
            mime_type="text/markdown",
        )(_make_reader(md))


def _make_reader(path: Path) -> Callable[[], str]:
    def read() -> str:
        return path.read_text(encoding="utf-8")

    return read


def main() -> None:
    """Console entry point: run the server over stdio."""
    create_server().run("stdio")


if __name__ == "__main__":
    main()
