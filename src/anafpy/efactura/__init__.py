"""e-Factura: typed client and UBL 2.1 / CIUS-RO models.

The :mod:`anafpy.efactura.ubl` subpackage is generated from the vendored OASIS UBL 2.1
XSDs (see ``scripts/generate_ubl.py``). The two document roots used by e-Factura are
re-exported here for convenience; richer component types live under
``anafpy.efactura.ubl.common``.
"""

from __future__ import annotations

from .client import EFacturaClient
from .models import (
    DownloadedMessage,
    Filter,
    FlatInvoice,
    FlatInvoiceLine,
    FlatParty,
    MessageListItem,
    MessageState,
    MessageStatus,
    TransformStandard,
    UploadResult,
    UploadStandard,
    parse_ubl_document,
    read_flat_invoice,
)
from .ubl.maindoc import CreditNote, CreditNoteType, Invoice, InvoiceType

__all__ = [
    "CreditNote",
    "CreditNoteType",
    "DownloadedMessage",
    "EFacturaClient",
    "Filter",
    "FlatInvoice",
    "FlatInvoiceLine",
    "FlatParty",
    "Invoice",
    "InvoiceType",
    "MessageListItem",
    "MessageState",
    "MessageStatus",
    "TransformStandard",
    "UploadResult",
    "UploadStandard",
    "parse_ubl_document",
    "read_flat_invoice",
]
