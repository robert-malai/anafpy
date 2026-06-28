"""MCP tool input/return types (``DESIGN.md`` §7).

Outbound filing is **XML pass-through**: the only inputs are :class:`UblXmlInput` /
:class:`EtransportXmlInput`, carrying a complete document the caller's invoicing
software produced. anafpy never composes a document from structured fields. The values
the tools *return* (the prepared-submission gate, submit outcomes) live here; the
easy-to-read previews reuse the client-layer flat read views (``FlatInvoice`` from
:mod:`anafpy.efactura`, ``FlatTransport`` from :mod:`anafpy.etransport`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..efactura.models import FlatInvoice
from ..etransport.models import FlatTransport
from ..validation import ValidationFinding

__all__ = [
    "EtransportXmlInput",
    "PreparedSubmission",
    "SubmitResult",
    "UblXmlInput",
]


class UblXmlInput(BaseModel):
    """A complete e-Factura UBL invoice / credit-note as XML.

    Exactly one of ``xml`` / ``path`` must be set. The document is parsed and locally
    validated, then filed verbatim — anafpy does not modify or recompute it.
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
    """Result of a ``prepare`` step: preview + local validation + confirmation token.

    ``confirmation_token`` is ``None`` when local validation failed — fix the findings
    and prepare again. When present, pass it (with the *same* document) to the matching
    ``submit`` tool to file. ``invoice_preview`` / ``transport_preview`` is the easy-to-
    read projection of the supplied XML, for the human to confirm before filing.
    """

    valid: bool
    findings: list[ValidationFinding] = []
    validation_available: bool = True
    confirmation_token: str | None = None
    invoice_preview: FlatInvoice | None = None
    transport_preview: FlatTransport | None = None
    message: str = ""


class SubmitResult(BaseModel):
    """Result of a ``submit`` step."""

    accepted: bool
    upload_id: str | None = None
    uit: str | None = None
    errors: list[str] = []
    message: str = ""
