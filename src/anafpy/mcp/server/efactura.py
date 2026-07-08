"""e-Factura MCP tools: inbox, download (with artifact saving), validate, filing.

Filing is the same two-step gate as e-Transport (``DESIGN.md`` §8), with two
STEP-1 shapes: ``efactura_prepare`` takes complete UBL XML produced by the user's
invoicing software (the recommended path when such software exists) and
``efactura_prepare_invoice`` composes the XML from the flat
:class:`~anafpy.efactura.authoring.InvoiceDocument` (reinstated 2026-07-08 — the
authoring package lets an agent draft a full invoice with no upstream system).
Prepare runs anafpy's translated CIUS-RO rule check for *informational*
``local_findings`` but never withholds the token — human review and ANAF's own
validation stay the gates. ``efactura_download`` writes the signed ZIP /
``transformare`` PDF to caller-given paths so binary artifacts stay out of the
model's context.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ...efactura.authoring import InvoiceDocument, render_invoice
from ...efactura.authoring import validate as validate_invoice_rules
from ...efactura.models import Filter, UploadStandard
from ...exceptions import AnafConfigError, AnafError, AnafResponseError
from ...public.models import TransformStandard
from ..config import ServerConfig
from ..context import AppContext
from ..documents import invoice_view, resolve_xml, upload_standard
from ..models import PreparedInvoice, SubmitResult, UblXmlInput
from ..tokens import ConfirmationError, issue_token, verify_token
from ._shared import ARTIFACT_SAVING, MUTATING, READ_ONLY

__all__ = ["register"]

_INVOICE_KIND = "efactura.invoice"

_TOKEN_USED_MESSAGE = (
    "confirmation token already used — filing is never repeated on the same "
    "approval; run the prepare step again"
)


def _invoice_context(cif: str) -> str:
    """Submission parameters bound into an e-Factura confirmation token."""
    return f"cif={cif}"


def register(mcp: FastMCP, ctx: AppContext, cfg: ServerConfig) -> None:
    @mcp.tool(
        title="e-Factura: List messages",
        annotations=READ_ONLY,
        description="List e-Factura messages (sent/received/errors) for a fiscal code. "
        "Give a window as EITHER `days` (1-60) OR an ISO `start`+`end` date range "
        "(e.g. '2026-06-01'); all pages are fetched and flattened automatically. "
        "ANAF retains messages for 60 days, so the window must lie within the "
        "last 60 days and `end` may be neither before `start` nor in the future.",
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

    @mcp.tool(
        title="e-Factura: Upload status",
        annotations=READ_ONLY,
        description="Get the processing state of an e-Factura upload by its upload "
        "id (index_incarcare, from efactura_submit). A terminal 'ok' carries the "
        "download_id of the signed archive — fetch it with efactura_download; "
        "'nok' carries the rejection findings in errors.",
    )
    async def efactura_get_status(upload_id: str) -> dict[str, object]:
        status = await ctx.efactura().get_status(upload_id)
        return {
            "state": status.state.value,
            "errors": status.errors,
            "is_terminal": status.is_terminal,
            "download_id": status.download_id,
        }

    @mcp.tool(
        title="e-Factura: Prepare invoice",
        annotations=MUTATING,
        description="STEP 1 of filing an e-Factura invoice or credit note composed "
        "from STRUCTURED fields — no XML and no invoicing software needed: render "
        "the CIUS-RO UBL from the given invoice (totals and the VAT breakdown are "
        "computed from the lines unless supplied) and return the exact XML + the "
        "invoice preview + local_findings (anafpy's translated CIUS-RO rule check "
        "— informational; ANAF's validation is authoritative) + a confirmation "
        "token. Show the preview and any findings for approval; then call "
        "efactura_submit with document={'xml': <the returned xml>}, the token, and "
        "confirm=True. Does NOT file. When the user's invoicing software already "
        "produced the XML, prefer efactura_prepare with that XML instead of "
        "re-composing it here.",
    )
    async def efactura_prepare_invoice(
        invoice: InvoiceDocument, cif: str | None = None
    ) -> PreparedInvoice:
        try:
            resolved = cfg.require_cif(cif)
        except AnafError as exc:
            return PreparedInvoice(valid=False, message=str(exc))
        xml = render_invoice(invoice, skip_validation=True)
        report = validate_invoice_rules(invoice)
        token = issue_token(
            cfg.signing_key,
            kind=_INVOICE_KIND,
            payload=xml,
            context=_invoice_context(resolved),
        )
        note = (
            "no local findings"
            if not report.findings
            else f"{len(report.fatal)} fatal / "
            f"{len(report.findings) - len(report.fatal)} warning local finding(s) "
            "— review them with the user; they do not block filing"
        )
        return PreparedInvoice(
            valid=True,
            confirmation_token=token,
            cif=resolved,
            invoice_preview=invoice,
            local_findings=report.findings,
            xml=xml.decode("utf-8"),
            message=f"composed; {note}. ANAF validates authoritatively on upload "
            "(or pre-check with efactura_validate). Review the preview with the "
            "user, then pass the returned xml and token to efactura_submit with "
            "confirm=True.",
        )

    @mcp.tool(
        title="e-Factura: Prepare XML filing",
        annotations=MUTATING,
        description="STEP 1 of filing an e-Factura invoice/credit note the caller "
        "already has as complete UBL XML — the RECOMMENDED path when the user's "
        "invoicing software produced it: return an easy-to-read invoice preview + "
        "a confirmation token bound to this exact document and CIF; the bytes go "
        "to ANAF verbatim. (To compose an invoice from structured fields instead, "
        "use efactura_prepare_invoice.) Show the preview for approval; then call "
        "efactura_submit with the same document, the token, and confirm=True. "
        "Does NOT file; pre-check with efactura_validate if in doubt.",
    )
    async def efactura_prepare(
        document: UblXmlInput, cif: str | None = None
    ) -> PreparedInvoice:
        try:
            xml = resolve_xml(document)
            resolved = cfg.require_cif(cif)
        except AnafError as exc:
            return PreparedInvoice(valid=False, message=str(exc))
        preview = invoice_view(xml)
        token = issue_token(
            cfg.signing_key,
            kind=_INVOICE_KIND,
            payload=xml,
            context=_invoice_context(resolved),
        )
        message = (
            "not pre-validated (ANAF is authoritative; efactura_validate "
            "pre-checks without filing). Review the preview with the user, then "
            "submit with the confirmation token."
            if preview is not None
            else "the document did not parse into the flat invoice view — no "
            "preview; review the XML carefully (efactura_validate pre-checks it) "
            "before submitting with the confirmation token."
        )
        return PreparedInvoice(
            valid=True,
            confirmation_token=token,
            cif=resolved,
            invoice_preview=preview,
            message=message,
        )

    @mcp.tool(
        title="e-Factura: Submit filing",
        annotations=MUTATING,
        description="STEP 2 of filing an e-Factura document: upload the supplied "
        "XML to ANAF and return the upload id (poll it with efactura_get_status). "
        "Requires the confirmation_token from efactura_prepare or "
        "efactura_prepare_invoice for the SAME document (for the composing tool, "
        "document={'xml': <the xml it returned>}) and confirm=True.",
    )
    async def efactura_submit(
        document: UblXmlInput,
        confirmation_token: str,
        confirm: bool = False,
        cif: str | None = None,
    ) -> SubmitResult:
        if not confirm:
            return SubmitResult(
                accepted=False,
                message="confirm=False — set confirm=True only after the user "
                "approves the preview from efactura_prepare*.",
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
                kind=_INVOICE_KIND,
                payload=xml,
                context=_invoice_context(resolved),
            )
        except ConfirmationError as exc:
            return SubmitResult(accepted=False, message=str(exc))
        # Resolve the client BEFORE consuming the token: missing credentials is a
        # deterministic config error, and must not burn the human's approval.
        client = ctx.efactura()
        if not ctx.token_ledger.consume(confirmation_token, expires_at):
            return SubmitResult(accepted=False, message=_TOKEN_USED_MESSAGE)
        # The token is consumed BEFORE the upload, deliberately: on an ambiguous
        # failure (e.g. a timeout after the request was sent) replaying the same
        # token must not be able to double-file — the human re-approves instead.
        try:
            result = await client.upload(
                xml, cif=resolved, standard=upload_standard(xml)
            )
        except AnafError as exc:
            return SubmitResult(
                accepted=False,
                errors=[str(exc)],
                message=(
                    "the upload failed and the outcome is UNKNOWN — the request "
                    "may or may not have reached ANAF. The confirmation token is "
                    "spent. Before preparing this filing again, check whether it "
                    "went through (efactura_list_messages, or efactura_get_status "
                    "if an upload id is known) so it is not filed twice."
                ),
            )
        return SubmitResult(
            accepted=result.accepted,
            upload_id=result.upload_id,
            errors=result.errors,
            message=(
                f"filed — upload id {result.upload_id}; poll efactura_get_status "
                "to a terminal state"
                if result.accepted
                else "ANAF rejected the document at submission"
            ),
        )


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
