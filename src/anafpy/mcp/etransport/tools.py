"""e-Transport MCP tools: read-only lookups plus the two-step gated filing flow.

Filing is split ``etransport_prepare*`` → ``etransport_submit``: prepare parses (or
composes) the XML for a preview and returns a single-use HMAC confirmation token
bound to the exact XML bytes and the CIF; submit requires that token and an
explicit ``confirm=True``. The STEP-2 skeleton is the shared
:func:`anafpy.mcp.gate.run_submit`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from ...etransport.client import ETransportClient
from ...etransport.models import (
    FlatConfirmation,
    FlatDeletion,
    FlatSubmission,
    FlatTransport,
    FlatVehicleChange,
    render_etransport,
)
from ...exceptions import AnafError
from ..artifacts import MUTATING, READ_ONLY
from ..config import ServerConfig
from ..context import AppContext
from ..gate import SubmitResult, issue_token, run_submit, submission_context
from .models import EtransportXmlInput, PreparedTransport, transport_view
from .nomenclature import nomenclature_entries

__all__ = ["register"]

_TRANSPORT_KIND = "etransport.declaration"


def register(mcp: FastMCP, ctx: AppContext, cfg: ServerConfig) -> None:
    @mcp.tool(
        title="e-Transport: List notifications",
        annotations=READ_ONLY,
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
        title="e-Transport: Upload status",
        annotations=READ_ONLY,
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
        title="e-Transport: Look up active declarations",
        annotations=READ_ONLY,
        description="Look up active e-Transport declarations where a fiscal code is "
        "the transport organiser (the `info` endpoint).",
    )
    async def etransport_lookup(
        organizer_cui: str,
        declarant_cui: str | None = None,
        uit: str | None = None,
        declarant_ref: str | None = None,
    ) -> dict[str, object]:
        result = await ctx.etransport().info(
            organizer_cui=organizer_cui,
            declarant_cui=declarant_cui,
            uit=uit,
            declarant_ref=declarant_ref,
        )
        return {
            "items": [i.model_dump() for i in result.items],
            "error": result.error,
        }

    @mcp.tool(
        title="e-Transport: Code lists",
        annotations=READ_ONLY,
        description="List one e-Transport nomenclature (code list) as "
        "{name, code[, label]} entries. `kind` is one of: operation_types, "
        "operation_scopes, counties, border_points, customs_offices, countries, "
        "document_types, confirmation_types, unit_codes. The names are accepted "
        "anywhere the etransport_prepare_* tools take an enum-coded field. "
        "unit_codes is code-only: the closed UN/ECE Rec 20/21 list ANAF accepts "
        "for a goods line's unit_code — check it before guessing a unit (kilogram "
        "is KGM, piece is H87; 'KG'/'PCS' are not on the list).",
    )
    def etransport_nomenclature(kind: str) -> dict[str, object]:
        return {"kind": kind, "entries": nomenclature_entries(kind)}

    @mcp.tool(
        title="e-Transport: Prepare declaration",
        annotations=MUTATING,
        description="STEP 1 of filing an e-Transport declaration from STRUCTURED "
        "fields — no XML needed: compose the ANAF declaration XML from the given "
        "fields (set correction_of_uit to file a correction of an issued UIT) and "
        "return the exact XML + an easy-to-read preview + a confirmation token. "
        "Show the preview for approval; then call etransport_submit with "
        "document={'xml': <the returned xml>}, the token, and confirm=True. Does "
        "NOT file. Enum-coded fields accept ANAF codes or member names (see "
        "etransport_nomenclature).",
    )
    async def etransport_prepare_declaration(
        declaration: FlatTransport, cif: str | None = None
    ) -> PreparedTransport:
        return _prepare_composed_transport(cfg, declaration, cif=cif)

    @mcp.tool(
        title="e-Transport: Prepare deletion",
        annotations=MUTATING,
        description="STEP 1 of deleting an issued e-Transport UIT: compose the "
        "stergere XML and return it + a preview + a confirmation token. Then call "
        "etransport_submit with document={'xml': <the returned xml>}, the token, "
        "and confirm=True.",
    )
    async def etransport_prepare_deletion(
        uit: str, cif: str | None = None, declarant_ref: str | None = None
    ) -> PreparedTransport:
        return _prepare_composed_transport(
            cfg, FlatDeletion, cif=cif, uit=uit, declarant_ref=declarant_ref
        )

    @mcp.tool(
        title="e-Transport: Prepare confirmation",
        annotations=MUTATING,
        description="STEP 1 of confirming an issued e-Transport UIT: compose the "
        "confirmare XML and return it + a preview + a confirmation token. "
        "confirmation_type is CONFIRMAT (10), CONFIRMAT_PARTIAL (20) or INFIRMAT "
        "(30). Then call etransport_submit with document={'xml': <the returned "
        "xml>}, the token, and confirm=True.",
    )
    async def etransport_prepare_confirmation(
        uit: str,
        confirmation_type: str,
        note: str | None = None,
        cif: str | None = None,
        declarant_ref: str | None = None,
    ) -> PreparedTransport:
        return _prepare_composed_transport(
            cfg,
            FlatConfirmation,
            cif=cif,
            uit=uit,
            confirmation_type=confirmation_type,
            note=note,
            declarant_ref=declarant_ref,
        )

    @mcp.tool(
        title="e-Transport: Prepare vehicle change",
        annotations=MUTATING,
        description="STEP 1 of changing the vehicle on an issued e-Transport UIT: "
        "compose the modifVehicul XML and return it + a preview + a confirmation "
        "token. Then call etransport_submit with document={'xml': <the returned "
        "xml>}, the token, and confirm=True.",
    )
    async def etransport_prepare_vehicle_change(
        uit: str,
        plate: str,
        trailer1: str | None = None,
        trailer2: str | None = None,
        note: str | None = None,
        cif: str | None = None,
        declarant_ref: str | None = None,
    ) -> PreparedTransport:
        return _prepare_composed_transport(
            cfg,
            FlatVehicleChange,
            cif=cif,
            uit=uit,
            plate=plate,
            trailer1=trailer1,
            trailer2=trailer2,
            note=note,
            declarant_ref=declarant_ref,
        )

    @mcp.tool(
        title="e-Transport: Prepare XML filing",
        annotations=MUTATING,
        description="STEP 1 of filing an e-Transport document the caller already "
        "has as XML: parse it and return an easy-to-read preview + a confirmation "
        "token bound to this document and CIF. (To file from structured fields, "
        "use etransport_prepare_declaration and friends instead.) Show the preview "
        "for approval; then call etransport_submit with the token and the same "
        "cif. Does NOT file. (There is no standalone validator — ANAF validates "
        "the declaration on upload.)",
    )
    async def etransport_prepare(
        document: EtransportXmlInput, cif: str | None = None
    ) -> PreparedTransport:
        return _prepare_transport(cfg, document, cif=cif)

    @mcp.tool(
        title="e-Transport: Submit filing",
        annotations=MUTATING,
        description="STEP 2 of filing any e-Transport document: file the supplied "
        "XML with ANAF and return the UIT code. Requires the confirmation_token "
        "from an etransport_prepare* tool for the SAME document (for the composing "
        "tools, document={'xml': <the xml they returned>}) and confirm=True.",
    )
    async def etransport_submit(
        document: EtransportXmlInput,
        confirmation_token: str,
        confirm: bool = False,
        cif: str | None = None,
    ) -> SubmitResult:
        return await run_submit(
            document,
            confirmation_token,
            confirm=confirm,
            cif=cif,
            cfg=cfg,
            ledger=ctx.token_ledger,
            kind=_TRANSPORT_KIND,
            prepare_tools="etransport_prepare",
            check_hint="etransport_list, or etransport_get_status "
            "if an upload id is known",
            client=ctx.etransport,
            upload=_upload,
        )


async def _upload(client: ETransportClient, xml: bytes, cif: str) -> SubmitResult:
    """The e-Transport leg of the shared submit skeleton (see ``gate.run_submit``)."""
    result = await client.upload(xml, cif=cif)
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
    cfg: ServerConfig,
    document: EtransportXmlInput,
    *,
    cif: str | None = None,
) -> PreparedTransport:
    try:
        xml = document.resolve()
        resolved = cfg.require_cif(cif)
    except AnafError as exc:
        return PreparedTransport(valid=False, message=str(exc))
    preview = transport_view(xml)
    token = issue_token(
        cfg.signing_key,
        kind=_TRANSPORT_KIND,
        payload=xml,
        context=submission_context(resolved),
    )
    return PreparedTransport(
        valid=True,
        confirmation_token=token,
        cif=resolved,
        transport_preview=preview,
        message=_prepare_message(parsed=preview is not None),
    )


def _prepare_composed_transport(
    cfg: ServerConfig,
    document: FlatSubmission | Callable[..., FlatSubmission],
    *,
    cif: str | None,
    **fields: Any,
) -> PreparedTransport:
    """Compose a flat e-Transport document and gate it like any other filing.

    ``document`` is either a ready flat model or a flat-model class to construct
    from ``fields`` — construction failures (bad enum names, malformed UIT/plate)
    come back as an invalid :class:`PreparedTransport`, not a raised tool error.
    The confirmation token is bound to the *rendered* bytes, which are echoed in
    ``xml`` for the submit step.
    """
    try:
        resolved = cfg.require_cif(cif)
        model = (
            document
            if isinstance(
                document,
                FlatTransport | FlatDeletion | FlatConfirmation | FlatVehicleChange,
            )
            else document(**fields)
        )
        xml = render_etransport(model, declarant_code=resolved)
    except (AnafError, ValidationError) as exc:
        return PreparedTransport(valid=False, message=str(exc))
    token = issue_token(
        cfg.signing_key,
        kind=_TRANSPORT_KIND,
        payload=xml,
        context=submission_context(resolved),
    )
    return PreparedTransport(
        valid=True,
        confirmation_token=token,
        cif=resolved,
        transport_preview=transport_view(xml),
        xml=xml.decode("utf-8"),
        message="composed; not pre-validated (ANAF validates on upload). Review "
        "the preview with the user, then pass the returned xml and token to "
        "etransport_submit with confirm=True.",
    )


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
