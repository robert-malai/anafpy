"""e-Transport: typed client for ANAF e-Transport declarations (ETRANSPORT/ws/v1).

:class:`UitCard` and :func:`load_cardpdf` import without optional
dependencies; rendering a card without ``anafpy[cards]`` raises a clear
:class:`~anafpy.exceptions.AnafConfigError`.
"""

from __future__ import annotations

from .card import CardRenderModule, UitCard, load_cardpdf, partner_label
from .client import ETransportClient
from .models import (
    FlatConfirmation,
    FlatDeletion,
    FlatPriorNotification,
    FlatSubmission,
    FlatTransport,
    FlatTransportAddress,
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
    FlatTransportPartner,
    FlatTransportVehicle,
    FlatVehicleChange,
    InfoItem,
    InfoList,
    Location,
    MessageState,
    MessageStatus,
    Notification,
    NotificationMessage,
    UploadResult,
    build_etransport,
    parse_etransport_document,
    read_flat_transport,
    render_etransport,
)
from .schema.schema_etr_v2_20230126 import ETransport

__all__ = [
    "CardRenderModule",
    "ETransport",
    "ETransportClient",
    "FlatConfirmation",
    "FlatDeletion",
    "FlatPriorNotification",
    "FlatSubmission",
    "FlatTransport",
    "FlatTransportAddress",
    "FlatTransportDocument",
    "FlatTransportGood",
    "FlatTransportLocation",
    "FlatTransportPartner",
    "FlatTransportVehicle",
    "FlatVehicleChange",
    "InfoItem",
    "InfoList",
    "Location",
    "MessageState",
    "MessageStatus",
    "Notification",
    "NotificationMessage",
    "UitCard",
    "UploadResult",
    "build_etransport",
    "load_cardpdf",
    "parse_etransport_document",
    "partner_label",
    "read_flat_transport",
    "render_etransport",
]
