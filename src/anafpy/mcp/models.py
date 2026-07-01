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
    """Result of a ``prepare`` step: preview + confirmation token.

    ``valid`` is ``False`` (and ``confirmation_token`` ``None``) only when the input
    could not be resolved (bad ``xml``/``path``, no CIF). Otherwise pass the token
    (with the *same* document and ``cif``) to the matching ``submit`` tool to file;
    the token is single-use and bound to both. ``cif`` echoes the fiscal code the
    filing was prepared for. ``invoice_preview`` / ``transport_preview`` is the
    easy-to-read projection of the supplied XML, for the human to confirm before
    filing — nothing here is validated against ANAF's rules (use
    ``efactura_validate`` for that; ANAF is authoritative).
    """

    valid: bool
    confirmation_token: str | None = None
    cif: str | None = None
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
