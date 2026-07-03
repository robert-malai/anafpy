"""MCP tool input/return types (``DESIGN.md`` §8).

**Filing tools exist for e-Transport only** (the e-Factura filing pair was removed
2026-07-03 — outbound invoices come from third-party invoicing software that files
with ANAF directly; :class:`UblXmlInput` now only feeds ``efactura_validate``).
**e-Transport is fully translated**:
the ``etransport_prepare_*`` tools take the client-layer flat models
(:class:`~anafpy.etransport.models.FlatTransport` and siblings) and compose the
declaration XML themselves (there is usually no upstream software producing it);
:class:`EtransportXmlInput` remains for callers who do bring their own XML. The values
the tools *return* (the prepared-submission gate, submit outcomes) live here; the
easy-to-read previews reuse the client-layer flat submissions from
:mod:`anafpy.etransport`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..etransport.models import FlatSubmission

__all__ = [
    "EtransportXmlInput",
    "PreparedSubmission",
    "SubmitResult",
    "UblXmlInput",
]


class UblXmlInput(BaseModel):
    """A complete e-Factura UBL invoice / credit-note as XML.

    Exactly one of ``xml`` / ``path`` must be set. The document is sent to ANAF's
    validator verbatim — anafpy does not modify or recompute it.
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
    could not be resolved (bad ``xml``/``path``, invalid fields, no CIF). Otherwise
    pass the token (with the *same* document and ``cif``) to the matching ``submit``
    tool to file; the token is single-use and bound to both. ``cif`` echoes the
    fiscal code the filing was prepared for. ``transport_preview`` is the
    easy-to-read projection of the document, for the
    human to confirm before filing — nothing here is validated against ANAF's rules
    (ANAF is authoritative). For the composing
    ``etransport_prepare_*`` tools, ``xml`` carries the exact document that will be
    filed — pass it back to ``etransport_submit`` verbatim (the token is bound to
    those bytes).
    """

    valid: bool
    confirmation_token: str | None = None
    cif: str | None = None
    transport_preview: FlatSubmission | None = None
    xml: str | None = None
    message: str = ""


class SubmitResult(BaseModel):
    """Result of a ``submit`` step."""

    accepted: bool
    upload_id: str | None = None
    uit: str | None = None
    errors: list[str] = []
    message: str = ""
