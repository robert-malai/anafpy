"""e-Factura: typed client, UBL 2.1 / CIUS-RO models, and invoice authoring.

The :mod:`anafpy.efactura.ubl` subpackage is generated from the vendored OASIS UBL 2.1
XSDs (see ``scripts/generate_ubl.py``). The two document roots used by e-Factura are
re-exported here for convenience; richer component types live under
``anafpy.efactura.ubl.common``. The flat, bidirectional invoice models — authoring,
the translated CIUS-RO rule set, and the strict wire reader backing
``DownloadedMessage.view`` — live in :mod:`anafpy.efactura.authoring`.
"""

from __future__ import annotations

from .client import EFacturaClient
from .models import (
    DownloadedMessage,
    Filter,
    MessageListItem,
    MessageState,
    MessageStatus,
    SignatureValidationResult,
    UploadResult,
    UploadStandard,
    parse_ubl_document,
)
from .ubl.maindoc import CreditNote, CreditNoteType, Invoice, InvoiceType

__all__ = [
    "CreditNote",
    "CreditNoteType",
    "DownloadedMessage",
    "EFacturaClient",
    "Filter",
    "Invoice",
    "InvoiceType",
    "MessageListItem",
    "MessageState",
    "MessageStatus",
    "SignatureValidationResult",
    "UploadResult",
    "UploadStandard",
    "parse_ubl_document",
]
