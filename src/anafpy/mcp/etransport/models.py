"""e-Transport MCP tool input/return types and the preview projection.

Filing takes two STEP-1 shapes: **XML pass-through** (:class:`EtransportXmlInput`,
``{xml|path}``) carries a complete declaration the caller already has, and
**structured composition** (``etransport_prepare_declaration`` and siblings)
takes the client-layer flat models (:class:`~anafpy.etransport.models.FlatTransport`
and friends) instead. Both feed the shared two-step gate (:mod:`anafpy.mcp.gate`);
:class:`PreparedTransport` is the e-Transport shape of its ``prepare`` result,
and :func:`transport_view` projects the exact bytes into the easy-to-read
preview it carries — alongside :func:`statutory_window`, the window the UIT
would come with, which is a review fact while the transport date is still a
choice and no longer one after filing.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from ...etransport.models import (
    FlatSubmission,
    FlatTransport,
    parse_etransport_document,
    read_flat_transport,
)
from ...etransport.validity import (
    statutory_first_expired_day,
    statutory_last_valid_day,
    statutory_validity_days,
)
from ..gate import PreparedSubmission, XmlInput

__all__ = [
    "EtransportXmlInput",
    "PreparedTransport",
    "UitWindow",
    "statutory_window",
    "transport_view",
]


class EtransportXmlInput(XmlInput):
    """A complete e-Transport declaration as XML (one of ``xml`` / ``path``)."""

    xml: str | None = Field(default=None, description="The declaration as XML text.")
    path: str | None = Field(
        default=None, description="Path to a declaration XML file."
    )


class UitWindow(BaseModel):
    """How long a UIT filed from this declaration would be usable.

    Derived from the declared transport date by OUG 41/2022 art. 11, not read
    from ANAF — nothing has been filed yet, and ANAF would not tell the
    declarant anyway. It belongs in the preview because the transport date is
    still a choice at that point: a route that cannot finish inside the window
    is a planning problem better found before the token is spent than after.
    """

    days: int = Field(description="Calendar days the window runs for: 5, or 15.")
    from_day: dt.date = Field(
        description="The declared transport date — day 1 of the window."
    )
    last_valid_day: dt.date = Field(description="Last day of use, inclusive.")
    first_expired_day: dt.date = Field(
        description="The day it lapses — the shape ANAF's data_exp_uit has."
    )


def statutory_window(view: FlatSubmission | None) -> UitWindow | None:
    """The art. 11 window for a previewed declaration; ``None`` for anything else.

    A deletion, confirmation or vehicle change issues no UIT of its own, so
    there is no window to state.
    """
    if not isinstance(view, FlatTransport):
        return None
    operation = view.operation_type
    transport_date = view.vehicle.transport_date
    return UitWindow(
        days=statutory_validity_days(operation),
        from_day=transport_date,
        last_valid_day=statutory_last_valid_day(operation, transport_date),
        first_expired_day=statutory_first_expired_day(operation, transport_date),
    )


class PreparedTransport(PreparedSubmission):
    """An e-Transport ``prepare`` result.

    ``transport_preview`` is the easy-to-read projection of the document, for the
    human to confirm before filing — nothing here is validated against ANAF's
    rules (ANAF validates on upload). ``uit_window`` is the validity the issued
    UIT would carry, by law rather than by ANAF's word.
    """

    transport_preview: FlatSubmission | None = None
    uit_window: UitWindow | None = None


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
