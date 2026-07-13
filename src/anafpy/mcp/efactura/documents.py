"""Project e-Factura XML: previews, upload standards, ANAF's PDF rendering.

The XML-taking tools (``efactura_validate``, ``efactura_prepare``) take a
*complete* document; this module derives everything the tools need from those
bytes. Nothing is composed here: the bytes go to ANAF verbatim, and the preview
parsing is best-effort (an unparseable document yields ``None``, not an error).
"""

from __future__ import annotations

from ...efactura.authoring import InvoiceDocument, read_invoice
from ...efactura.models import UploadStandard, parse_ubl_document
from ...efactura.ubl.maindoc import CreditNote
from ...exceptions import AnafResponseError
from ...public.models import TransformStandard
from ..context import AppContext

__all__ = ["invoice_view", "render_pdf", "transform_standard", "upload_standard"]


def upload_standard(xml: bytes) -> UploadStandard:
    """The ``standard`` upload param for e-Factura XML: ``CN`` for a credit note,
    else ``UBL``. Unparseable bytes default to ``UBL`` (ANAF rejects them anyway)."""
    doc = parse_ubl_document(xml)
    return UploadStandard.CN if isinstance(doc, CreditNote) else UploadStandard.UBL


def transform_standard(xml: bytes) -> TransformStandard:
    """The ``validare``/``transformare`` path segment matching the document kind."""
    if upload_standard(xml) is UploadStandard.CN:
        return TransformStandard.CREDIT_NOTE
    return TransformStandard.INVOICE


def invoice_view(xml: bytes) -> InvoiceDocument | None:
    """Full-fidelity flat projection of e-Factura UBL, or ``None`` if it does not
    parse or the strict authoring reader cannot represent it.

    Used for the ``efactura_prepare`` preview; wire amounts land in the explicit
    fields, never recomputed. A ``None`` preview does not block the filing — the
    bytes go to ANAF verbatim either way.
    """
    doc = parse_ubl_document(xml)
    if doc is None:
        return None
    try:
        return read_invoice(doc)
    except ValueError:
        return None


async def render_pdf(ctx: AppContext, xml: bytes) -> bytes:
    """Render downloaded e-Factura XML to PDF via ANAF's ``transformare``.

    ``validate=False``: the message already passed ANAF's validation when it was
    filed, so re-validating here could only spuriously block the rendering.
    ``transformare`` still answers 200 with a JSON error body when it cannot render,
    so a non-PDF response is raised as :class:`AnafResponseError`, not written out.
    """
    pdf = await ctx.public().render_invoice_pdf(
        xml, standard=transform_standard(xml), validate=False
    )
    if not pdf.startswith(b"%PDF"):
        raise AnafResponseError(
            "transformare returned no PDF",
            status_code=200,
            body=pdf[:2000].decode("utf-8", errors="replace"),
        )
    return pdf
