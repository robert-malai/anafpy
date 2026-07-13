"""e-Transport MCP tool input/return types and the preview projection.

Filing takes two STEP-1 shapes: **XML pass-through** (:class:`EtransportXmlInput`,
``{xml|path}``) carries a complete declaration the caller already has, and
**structured composition** (``etransport_prepare_declaration`` and siblings)
takes the client-layer flat models (:class:`~anafpy.etransport.models.FlatTransport`
and friends) instead. Both feed the shared two-step gate (:mod:`anafpy.mcp.gate`);
:class:`PreparedTransport` is the e-Transport shape of its ``prepare`` result,
and :func:`transport_view` projects the exact bytes into the easy-to-read
preview it carries.
"""

from __future__ import annotations

from pydantic import Field

from ...etransport.models import (
    FlatSubmission,
    parse_etransport_document,
    read_flat_transport,
)
from ..gate import PreparedSubmission, XmlInput

__all__ = ["EtransportXmlInput", "PreparedTransport", "transport_view"]


class EtransportXmlInput(XmlInput):
    """A complete e-Transport declaration as XML (one of ``xml`` / ``path``)."""

    xml: str | None = Field(default=None, description="The declaration as XML text.")
    path: str | None = Field(
        default=None, description="Path to a declaration XML file."
    )


class PreparedTransport(PreparedSubmission):
    """An e-Transport ``prepare`` result.

    ``transport_preview`` is the easy-to-read projection of the document, for the
    human to confirm before filing — nothing here is validated against ANAF's
    rules (ANAF validates on upload).
    """

    transport_preview: FlatSubmission | None = None


def transport_view(xml: bytes) -> FlatSubmission | None:
    """Easy-to-read projection of e-Transport XML, or ``None`` if it does not parse.

    Translation is strict (a parseable document the flat models cannot represent
    yields ``None``, not a partial view); pydantic's ``ValidationError`` is a
    ``ValueError``, so one handler covers both failure shapes.
    """
    doc = parse_etransport_document(xml)
    if doc is None:
        return None
    try:
        return read_flat_transport(doc)
    except ValueError:
        return None
