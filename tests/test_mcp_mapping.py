"""Curated flat models → wire XML mapping (e-Factura UBL, e-Transport)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from xsdata_pydantic.bindings import XmlParser

from anafpy.efactura import Invoice
from anafpy.etransport.schema.schema_etr_v2_20230126 import ETransport
from anafpy.exceptions import AnafConfigError
from anafpy.mcp.mapping import (
    build_invoice_xml,
    build_transport_xml,
    flat_invoice_to_ubl,
    invoice_preview,
    transport_preview,
)
from anafpy.mcp.models import (
    CIUS_RO,
    FlatInvoice,
    FlatInvoiceLine,
    FlatParty,
    FlatTransport,
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
    FlatTransportPartner,
    FlatTransportVehicle,
    UblXmlInput,
)


def _party(name: str) -> FlatParty:
    return FlatParty(
        name=name,
        vat_id=f"RO{name}",
        county="RO-B",
        city="Bucuresti",
        address="Str A 1",
    )


def _invoice(lines: list[FlatInvoiceLine]) -> FlatInvoice:
    return FlatInvoice(
        invoice_number="INV-1",
        issue_date="2026-06-28",
        due_date="2026-07-28",
        currency="RON",
        seller=_party("Seller"),
        buyer=_party("Buyer"),
        lines=lines,
    )


def test_single_rate_totals_and_cius_marker() -> None:
    inv = _invoice(
        [
            FlatInvoiceLine(
                description="Widget",
                quantity=Decimal("2"),
                unit_price=Decimal("10.50"),
                vat_category="S",
                vat_rate=Decimal("19"),
            )
        ]
    )
    ubl = flat_invoice_to_ubl(inv)
    # 2 * 10.50 = 21.00 net; 19% VAT = 3.99; payable 24.99.
    line_ext = ubl.legal_monetary_total.line_extension_amount
    assert line_ext is not None and line_ext.value == Decimal("21.00")
    assert ubl.tax_total[0].tax_amount.value == Decimal("3.99")
    assert ubl.legal_monetary_total.payable_amount.value == Decimal("24.99")
    assert ubl.customization_id is not None
    assert ubl.customization_id.value == CIUS_RO

    preview = invoice_preview(inv)
    assert preview.total_without_vat == Decimal("21.00")
    assert preview.total_vat == Decimal("3.99")
    assert preview.total_with_vat == Decimal("24.99")


def test_multiple_vat_rates_group_into_subtotals() -> None:
    inv = _invoice(
        [
            FlatInvoiceLine(
                description="Standard",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                vat_category="S",
                vat_rate=Decimal("19"),
            ),
            FlatInvoiceLine(
                description="Reduced",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                vat_category="S",
                vat_rate=Decimal("9"),
            ),
        ]
    )
    ubl = flat_invoice_to_ubl(inv)
    subtotals = ubl.tax_total[0].tax_subtotal
    assert len(subtotals) == 2
    # 19 + 9 = 28 total VAT; payable 200 + 28.
    assert ubl.tax_total[0].tax_amount.value == Decimal("28.00")
    assert ubl.legal_monetary_total.payable_amount.value == Decimal("228.00")


def test_invoice_xml_roundtrips_to_ubl_model() -> None:
    inv = _invoice(
        [
            FlatInvoiceLine(
                description="X",
                quantity=Decimal("1"),
                unit_price=Decimal("1"),
                vat_rate=Decimal("19"),
            )
        ]
    )
    xml = build_invoice_xml(inv)
    parsed = XmlParser().from_bytes(xml, Invoice)
    assert parsed.id.value == "INV-1"
    assert len(parsed.invoice_line) == 1


def test_ubl_passthrough_returns_bytes() -> None:
    raw = "<Invoice>passthrough</Invoice>"
    out = build_invoice_xml(UblXmlInput(xml=raw))
    assert out == raw.encode("utf-8")


def test_ubl_passthrough_rejects_both_xml_and_path() -> None:
    with pytest.raises(AnafConfigError, match="only one"):
        build_invoice_xml(UblXmlInput(xml="<x/>", path="/tmp/x.xml"))


def test_ubl_passthrough_requires_one_source() -> None:
    with pytest.raises(AnafConfigError, match="required"):
        build_invoice_xml(UblXmlInput())


# --- e-Transport -------------------------------------------------------------------


def _transport() -> FlatTransport:
    return FlatTransport(
        operation_type="30",
        partner=FlatTransportPartner(name="Foreign GmbH", country="DE", code="DE9"),
        vehicle=FlatTransportVehicle(
            plate="B100XYZ",
            carrier_name="Carrier SRL",
            carrier_country="RO",
            carrier_code="123",
            transport_date="2026-06-28",
        ),
        start_location=FlatTransportLocation(
            county_code="40", locality="Bucuresti", street="Str A", number="1"
        ),
        end_location=FlatTransportLocation(
            county_code="12", locality="Cluj", street="Str B"
        ),
        goods=[
            FlatTransportGood(
                operation_scope="301",
                name="Marfa",
                quantity=Decimal("100"),
                unit_code="KGM",
                gross_weight=Decimal("120"),
                net_weight=Decimal("100"),
            )
        ],
        documents=[
            FlatTransportDocument(doc_type="20", number="FAC1", date="2026-06-27")
        ],
    )


def test_transport_xml_carries_declarant_and_roundtrips() -> None:
    xml = build_transport_xml(_transport(), cif="999")
    parsed = XmlParser().from_bytes(xml, ETransport)
    assert parsed.cod_declarant == "999"
    notificare = parsed.notificare
    assert notificare is not None
    assert notificare.cod_tip_operatiune.value == 30
    assert len(notificare.bunuri_transportate) == 1
    locatie = notificare.loc_start_traseu_rutier.locatie
    assert locatie is not None
    assert locatie.cod_judet.value == 40


def test_transport_preview_sums_gross_weight() -> None:
    preview = transport_preview(_transport())
    assert preview.goods_count == 1
    assert preview.total_gross_weight == Decimal("120")
    assert preview.vehicle_plate == "B100XYZ"
