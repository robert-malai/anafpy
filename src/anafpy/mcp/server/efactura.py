"""e-Factura MCP tools: inbox listing, download (with artifact saving), validate.

The e-Factura surface is read-only — see the package docstring for why the filing
pair was removed. ``efactura_download`` writes the signed ZIP / ``transformare``
PDF to caller-given paths so binary artifacts stay out of the model's context.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ...efactura.models import Filter, UploadStandard
from ...exceptions import AnafConfigError, AnafError, AnafResponseError
from ...public.models import TransformStandard
from ..config import ServerConfig
from ..context import AppContext
from ..documents import resolve_xml, upload_standard
from ..models import UblXmlInput
from ._shared import ARTIFACT_SAVING, READ_ONLY

__all__ = ["register"]


def register(mcp: FastMCP, ctx: AppContext, cfg: ServerConfig) -> None:
    @mcp.tool(
        title="e-Factura: List messages",
        annotations=READ_ONLY,
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
        try:
            flt = Filter(filter) if filter else None
        except ValueError as exc:
            valid = ", ".join(f"{f.value} ({f.name})" for f in Filter)
            raise AnafConfigError(
                f"efactura_list_messages: unknown `filter` {filter!r}; one of: {valid}"
            ) from exc
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
        title="e-Factura: Download message",
        annotations=ARTIFACT_SAVING,
        description="Download a processed e-Factura message (the signed invoice/errors "
        "ZIP) by id. Returns the decoded content and an easy-to-read `invoice` view of "
        "the received document when it is a parseable invoice/credit-note — work from "
        "the view. The binary artifacts are for the user, not the context: pass "
        "`save_zip_as` to write the signed archive ZIP and/or `save_pdf_as` to write "
        "ANAF's official PDF rendering to those file paths (name them from the "
        "invoice metadata, e.g. '<date> - <partner>.pdf'). An existing file is never "
        "replaced unless overwrite=true: a refused write is reported in "
        "`pdf_error`/`zip_error` — pick another name, or pass overwrite=true only "
        "for a deliberate re-export. The PDF is best-effort: a conversion failure "
        "is reported in `pdf_error` and never fails the download. The PDF is also "
        "readable as the resource anafmsg://{message_id}/pdf.",
    )
    async def efactura_download(
        message_id: str,
        save_pdf_as: str | None = None,
        save_zip_as: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        msg = await ctx.efactura().download(message_id)
        content = (
            msg.content_xml.decode("utf-8", errors="replace")
            if msg.content_xml is not None
            else None
        )
        view = msg.view
        pdf_path: str | None = None
        pdf_error: str | None = None
        if save_pdf_as is not None:
            if msg.content_xml is None:
                pdf_error = "the message has no XML content to render"
            else:
                try:
                    pdf_path = _write_artifact(
                        save_pdf_as,
                        await _render_pdf(ctx, msg.content_xml),
                        overwrite=overwrite,
                    )
                except AnafError as exc:
                    pdf_error = str(exc)
        zip_path: str | None = None
        zip_error: str | None = None
        if save_zip_as is not None:
            try:
                zip_path = _write_artifact(
                    save_zip_as, msg.raw_zip, overwrite=overwrite
                )
            except AnafError as exc:
                zip_error = str(exc)
        return {
            "has_content": msg.content_xml is not None,
            "has_signature": msg.signature_xml is not None,
            "content_xml": content,
            "invoice": view.model_dump(mode="json") if view is not None else None,
            "zip_path": zip_path,
            "zip_error": zip_error,
            "pdf_path": pdf_path,
            "pdf_error": pdf_error,
        }

    @mcp.resource(
        "anafmsg://{message_id}/pdf",
        name="e-Factura message PDF",
        description="ANAF's official PDF rendering (transformare) of a downloaded "
        "e-Factura message, fetched and converted on read.",
        mime_type="application/pdf",
    )
    async def efactura_message_pdf(message_id: str) -> bytes:
        msg = await ctx.efactura().download(message_id)
        if msg.content_xml is None:
            raise AnafResponseError(
                "the message has no XML content to render", status_code=200
            )
        return await _render_pdf(ctx, msg.content_xml)

    @mcp.tool(
        title="e-Factura: Validate invoice",
        annotations=READ_ONLY,
        description="Validate a complete UBL invoice / credit note (XML) with ANAF's "
        "own server-side validator, without filing. Authoritative — the same rules "
        "the upload is checked against. Uses ANAF's public no-auth validator, which "
        "exists only in production, so it works (and answers identically) whatever "
        "environment this server is configured for — even with no OAuth "
        "credentials configured; nothing is filed anywhere.",
    )
    async def efactura_validate(document: UblXmlInput) -> dict[str, object]:
        xml = resolve_xml(document)
        result = await ctx.public().validate_invoice(
            xml, standard=_transform_standard(xml)
        )
        return {
            "valid": result.valid,
            "messages": result.messages,
            "trace_id": result.trace_id,
        }


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


def _write_artifact(target: str, data: bytes, *, overwrite: bool) -> str:
    """Write a downloaded artifact to a caller-given path, creating parent dirs.

    An existing file is never silently replaced: a batch flow naming files from
    invoice metadata ("<date> - <partner>.pdf") must not lose one invoice to a
    name collision. Raises :class:`AnafConfigError` unless ``overwrite`` is set.
    """
    path = Path(target).expanduser()
    if path.exists() and not overwrite:
        raise AnafConfigError(
            f"refusing to overwrite existing file {path} — pick another name, or "
            "pass overwrite=true to replace it deliberately"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


async def _render_pdf(ctx: AppContext, xml: bytes) -> bytes:
    """Render downloaded e-Factura XML to PDF via ANAF's ``transformare``.

    ``validate=False``: the message already passed ANAF's validation when it was
    filed, so re-validating here could only spuriously block the rendering.
    ``transformare`` still answers 200 with a JSON error body when it cannot render,
    so a non-PDF response is raised as :class:`AnafResponseError`, not written out.
    """
    pdf = await ctx.public().render_invoice_pdf(
        xml, standard=_transform_standard(xml), validate=False
    )
    if not pdf.startswith(b"%PDF"):
        raise AnafResponseError(
            "transformare returned no PDF",
            status_code=200,
            body=pdf[:2000].decode("utf-8", errors="replace"),
        )
    return pdf
