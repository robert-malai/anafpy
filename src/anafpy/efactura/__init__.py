"""e-Factura: typed client and UBL 2.1 / CIUS-RO models.

The :mod:`anafpy.efactura.ubl` subpackage is generated from the vendored OASIS UBL 2.1
XSDs (see ``scripts/generate_ubl.py``). The two document roots used by e-Factura are
re-exported here for convenience; richer component types live under
``anafpy.efactura.ubl.common``.
"""

from __future__ import annotations

from .ubl.maindoc import CreditNote, CreditNoteType, Invoice, InvoiceType

__all__ = [
    "CreditNote",
    "CreditNoteType",
    "Invoice",
    "InvoiceType",
]
