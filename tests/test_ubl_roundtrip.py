"""Golden round-trip tests for the generated UBL 2.1 models.

These guard against regeneration / serialization regressions (DESIGN §8, tier 1): a
model built in Python must serialize to XML and parse back to an equal model, and the
emitted XML must carry the CIUS-RO customization marker and correct UBL namespace.
"""

from __future__ import annotations

from decimal import Decimal

from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlParser, XmlSerializer

from anafpy.efactura import Invoice
from anafpy.efactura.ubl.common.ubl_common_aggregate_components_2_1 import (
    AccountingCustomerParty,
    AccountingSupplierParty,
    LegalMonetaryTotal,
)
from anafpy.efactura.ubl.common.ubl_common_basic_components_2_1 import (
    CustomizationId,
    DocumentCurrencyCode,
    Id,
    IssueDate,
    PayableAmount,
)

CIUS_RO = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"


def _minimal_invoice() -> Invoice:
    return Invoice(
        customization_id=CustomizationId(value=CIUS_RO),
        id=Id(value="INV-2026-001"),
        issue_date=IssueDate(value=XmlDate(2026, 6, 28)),
        document_currency_code=DocumentCurrencyCode(value="RON"),
        accounting_supplier_party=AccountingSupplierParty(),
        accounting_customer_party=AccountingCustomerParty(),
        legal_monetary_total=LegalMonetaryTotal(
            payable_amount=PayableAmount(value=Decimal("100.00"), currency_id="RON"),
        ),
    )


def test_invoice_roundtrips_to_equal_model() -> None:
    original = _minimal_invoice()
    xml = XmlSerializer().render(original)
    parsed = XmlParser().from_string(xml, Invoice)
    assert parsed == original


def test_serialized_invoice_carries_cius_ro_and_namespace() -> None:
    xml = XmlSerializer().render(_minimal_invoice())
    assert CIUS_RO in xml
    assert "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" in xml
    assert "INV-2026-001" in xml


def test_parse_then_reserialize_is_stable() -> None:
    xml = XmlSerializer().render(_minimal_invoice())
    parsed = XmlParser().from_string(xml, Invoice)
    assert XmlSerializer().render(parsed) == xml
