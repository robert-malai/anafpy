"""e-Factura MCP tool input/return types (``DESIGN.md`` §8).

Filing takes two STEP-1 shapes: **XML pass-through** (:class:`UblXmlInput`,
``{xml|path}``) carries a complete document the caller's software produced —
the *strongly recommended* path when upstream invoicing software exists
(``DESIGN.md`` §1 — ANAF's SPV purges filed messages after ~60 days; the
upstream system keeps the durable record) — and **structured composition**
(``efactura_prepare_invoice``) takes the client-layer
:class:`~anafpy.efactura.authoring.InvoiceDocument` instead, for callers with
no upstream system. Both feed the shared two-step gate
(:mod:`anafpy.mcp.gate`); :class:`PreparedInvoice` is the e-Factura shape of
its ``prepare`` result.
"""

from __future__ import annotations

from pydantic import Field

from ...efactura.authoring import Finding, InvoiceDocument
from ..gate import PreparedSubmission, XmlInput

__all__ = ["PreparedInvoice", "UblXmlInput"]


class UblXmlInput(XmlInput):
    """A complete e-Factura UBL invoice / credit-note as XML.

    Exactly one of ``xml`` / ``path`` must be set. The document is sent to ANAF
    verbatim — anafpy does not modify or recompute it.
    """

    xml: str | None = Field(default=None, description="The UBL document as XML text.")
    path: str | None = Field(
        default=None, description="Filesystem path to a UBL XML file."
    )


class PreparedInvoice(PreparedSubmission):
    """An e-Factura ``prepare`` result.

    ``invoice_preview`` is the flat projection of the exact document that will be
    filed, for the human to confirm. ``local_findings`` reports anafpy's
    translated EN 16931 + CIUS-RO rule check — informational: findings never
    withhold the token, and ANAF's own validation remains authoritative.
    """

    invoice_preview: InvoiceDocument | None = None
    local_findings: list[Finding] = Field(default_factory=list)
