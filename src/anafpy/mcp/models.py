"""MCP tool input/return types (``DESIGN.md`` §8).

Both services file through the same two-step gate, and both offer the two input
shapes. **XML pass-through** (:class:`UblXmlInput` / :class:`EtransportXmlInput`,
``{xml|path}``) carries a complete document the caller's software produced —
the *recommended* e-Factura path when upstream invoicing software exists.
**Structured composition** takes the client-layer flat models instead:
``etransport_prepare_*`` (:class:`~anafpy.etransport.models.FlatTransport` and
siblings) and — since 2026-07-08 — ``efactura_prepare_invoice``
(:class:`~anafpy.efactura.authoring.InvoiceDocument`), for callers with no
upstream system. The values the tools *return* (the prepared-submission gate,
submit outcomes) live here; the easy-to-read previews reuse the client-layer flat
models from :mod:`anafpy.etransport` / :mod:`anafpy.efactura.authoring`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..efactura.authoring import Finding, InvoiceDocument
from ..etransport.models import FlatSubmission

__all__ = [
    "EtransportXmlInput",
    "PreparedInvoice",
    "PreparedSubmission",
    "PreparedTransport",
    "SubmitResult",
    "UblXmlInput",
]


class UblXmlInput(BaseModel):
    """A complete e-Factura UBL invoice / credit-note as XML.

    Exactly one of ``xml`` / ``path`` must be set. The document is sent to ANAF
    verbatim — anafpy does not modify or recompute it.
    """

    xml: str | None = Field(default=None, description="The UBL document as XML text.")
    path: str | None = Field(
        default=None, description="Filesystem path to a UBL XML file."
    )


class EtransportXmlInput(BaseModel):
    """A complete e-Transport declaration as XML (one of ``xml`` / ``path``)."""

    xml: str | None = Field(default=None, description="The declaration as XML text.")
    path: str | None = Field(
        default=None, description="Path to a declaration XML file."
    )


class PreparedSubmission(BaseModel):
    """Shared shape of a ``prepare`` step: the confirmation-token gate.

    ``valid`` is ``False`` (and ``confirmation_token`` ``None``) only when the input
    could not be resolved (bad ``xml``/``path``, invalid fields, no CIF). Otherwise
    pass the token (with the *same* document and ``cif``) to the matching ``submit``
    tool to file; the token is single-use and bound to both. ``cif`` echoes the
    fiscal code the filing was prepared for. For the composing tools
    (``etransport_prepare_*`` / ``efactura_prepare_invoice``), ``xml`` carries the
    exact document that will be filed — pass it back to the matching submit tool
    verbatim (the token is bound to those bytes).

    The per-service results :class:`PreparedTransport` / :class:`PreparedInvoice`
    add the matching preview, so each tool's output schema describes exactly what
    it returns.
    """

    valid: bool
    confirmation_token: str | None = None
    cif: str | None = None
    xml: str | None = None
    message: str = ""


class PreparedTransport(PreparedSubmission):
    """An e-Transport ``prepare`` result.

    ``transport_preview`` is the easy-to-read projection of the document, for the
    human to confirm before filing — nothing here is validated against ANAF's
    rules (ANAF validates on upload).
    """

    transport_preview: FlatSubmission | None = None


class PreparedInvoice(PreparedSubmission):
    """An e-Factura ``prepare`` result.

    ``invoice_preview`` is the flat projection of the exact document that will be
    filed, for the human to confirm. ``local_findings`` reports anafpy's
    translated EN 16931 + CIUS-RO rule check — informational: findings never
    withhold the token, and ANAF's own validation remains authoritative.
    """

    invoice_preview: InvoiceDocument | None = None
    local_findings: list[Finding] = []


class SubmitResult(BaseModel):
    """Result of a ``submit`` step."""

    accepted: bool
    upload_id: str | None = None
    uit: str | None = None
    errors: list[str] = []
    message: str = ""
