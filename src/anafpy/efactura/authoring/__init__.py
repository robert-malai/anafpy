"""Bidirectional CIUS-RO invoice authoring models (experimental).

A full battery of flat Pydantic models over the EN 16931 semantic model as
restricted by CIUS-RO: author an :class:`InvoiceDocument` from business fields
(totals and the VAT breakdown are computed), render it to UBL wire XML
(:func:`render_invoice`), read wire XML back into the same models
(:func:`parse_invoice` / :func:`read_invoice`), and check the translated
EN 16931 + CIUS-RO Schematron rule set locally (:func:`validate`). ANAF's
server-side ``validare`` remains the authority.

Example::

    from anafpy.efactura.authoring import (
        InvoiceDocument, InvoiceLine, Party, PostalAddress, Seller,
        render_invoice, validate,
    )

    invoice = InvoiceDocument(
        number="INV-2026-0042",
        issue_date=date(2026, 7, 8),
        currency="RON",
        seller=Seller(name="Furnizor SRL", vat_id="RO12345678", address=...),
        buyer=Party(name="Client SRL", vat_id="RO87654321", address=...),
        lines=[InvoiceLine(name="Servicii", quantity=10, unit="H87",
                           unit_price=Decimal("10.00"),
                           vat_category="S", vat_rate=19)],
    )
    report = validate(invoice)      # findings with BR-* rule ids
    xml = render_invoice(invoice)   # upload-ready bytes
"""

from __future__ import annotations

from .build import build_invoice, render_invoice
from .codes import (
    CIUS_RO_CUSTOMIZATION_ID,
    DocumentKind,
    InvoiceTypeCode,
    VatCategory,
    VatPointDateCode,
)
from .models import (
    Contact,
    CreditTransfer,
    DeliveryInformation,
    DirectDebit,
    DocumentAllowance,
    DocumentCharge,
    ElectronicAddress,
    InvoiceDocument,
    InvoiceLine,
    ItemAttribute,
    ItemClassification,
    LineAllowance,
    LineCharge,
    Note,
    Party,
    Payee,
    PaymentCard,
    PaymentInstructions,
    Period,
    PostalAddress,
    PrecedingInvoice,
    Seller,
    SupportingDocument,
    TaxRepresentative,
    Totals,
    VatBreakdownEntry,
)
from .read import parse_invoice, read_invoice
from .rules import (
    Finding,
    InvoiceValidationError,
    Severity,
    ValidationReport,
    validate,
)

__all__ = [
    "CIUS_RO_CUSTOMIZATION_ID",
    "Contact",
    "CreditTransfer",
    "DeliveryInformation",
    "DirectDebit",
    "DocumentAllowance",
    "DocumentCharge",
    "DocumentKind",
    "ElectronicAddress",
    "Finding",
    "InvoiceDocument",
    "InvoiceLine",
    "InvoiceTypeCode",
    "InvoiceValidationError",
    "ItemAttribute",
    "ItemClassification",
    "LineAllowance",
    "LineCharge",
    "Note",
    "Party",
    "Payee",
    "PaymentCard",
    "PaymentInstructions",
    "Period",
    "PostalAddress",
    "PrecedingInvoice",
    "Seller",
    "Severity",
    "SupportingDocument",
    "TaxRepresentative",
    "Totals",
    "ValidationReport",
    "VatBreakdownEntry",
    "VatCategory",
    "VatPointDateCode",
    "build_invoice",
    "parse_invoice",
    "read_invoice",
    "render_invoice",
    "validate",
]
