"""e-Transport: typed client for ANAF e-Transport declarations (ETRANSPORT/ws/v1)."""

from __future__ import annotations

from .client import ETransportClient
from .models import (
    FlatTransport,
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
    FlatTransportPartner,
    FlatTransportVehicle,
    InfoItem,
    InfoList,
    Location,
    MessageState,
    MessageStatus,
    Notification,
    NotificationMessage,
    UploadResult,
    parse_etransport_document,
    read_flat_transport,
)
from .schema.schema_etr_v2_20230126 import ETransport

__all__ = [
    "ETransport",
    "ETransportClient",
    "FlatTransport",
    "FlatTransportDocument",
    "FlatTransportGood",
    "FlatTransportLocation",
    "FlatTransportPartner",
    "FlatTransportVehicle",
    "InfoItem",
    "InfoList",
    "Location",
    "MessageState",
    "MessageStatus",
    "Notification",
    "NotificationMessage",
    "UploadResult",
    "parse_etransport_document",
    "read_flat_transport",
]
