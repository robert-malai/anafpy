"""UBL → FlatInvoice read view (the easy-to-read projection used by download + MCP)."""

from __future__ import annotations

from decimal import Decimal

from _wire import build_credit_note, build_invoice
from anafpy.efactura import parse_ubl_document, read_flat_invoice
from anafpy.efactura.ubl.common import ubl_common_basic_components_2_1 as cbc


def test_reads_invoice_header_party_and_lines() -> None:
    view = read_flat_invoice(build_invoice())
    assert view.document_type == "invoice"
    assert view.number == "INV-1"
    assert view.currency == "RON"
    assert view.issue_date == "2026-06-28"
    assert view.due_date == "2026-07-28"
    assert view.type_code == "380"
    assert view.seller.name == "Seller"
    assert view.seller.vat_id == "RO1"
    assert view.seller.city == "Bucuresti"
    assert view.buyer.name == "Buyer"
    assert len(view.lines) == 1
    line = view.lines[0]
    assert line.description == "Widget"
    assert line.quantity == Decimal("2")
    assert line.unit_code == "C62"
    assert line.unit_price == Decimal("10.50")
    assert line.vat_category == "S"
    assert line.vat_rate == Decimal("19")
    assert line.line_amount == Decimal("21.00")


def test_reads_document_totals_and_is_complete() -> None:
    view = read_flat_invoice(build_invoice())
    assert view.total_without_vat == Decimal("21.00")
    assert view.total_vat == Decimal("3.99")
    assert view.total_with_vat == Decimal("24.99")
    assert view.complete is True
    assert view.dropped_fields == []


def test_credit_note_document_type() -> None:
    view = read_flat_invoice(build_credit_note())
    assert view.document_type == "credit_note"
    assert view.number == "CN-1"
    assert view.type_code == "381"
    assert len(view.lines) == 1
    assert view.lines[0].quantity == Decimal("2")


def test_flags_incomplete_when_document_has_allowances() -> None:
    invoice = build_invoice()
    invoice.legal_monetary_total.allowance_total_amount = cbc.AllowanceTotalAmount(
        value=Decimal("5.00"), currency_id="RON"
    )
    view = read_flat_invoice(invoice)
    assert view.complete is False
    assert "allowance_total_amount" in view.dropped_fields


def test_parse_ubl_document_handles_good_and_bad_input() -> None:
    from xsdata_pydantic.bindings import XmlSerializer

    xml = XmlSerializer().render(build_invoice()).encode("utf-8")
    parsed = parse_ubl_document(xml)
    assert parsed is not None
    assert read_flat_invoice(parsed).number == "INV-1"
    assert parse_ubl_document(b"<not-a-ubl-doc/>") is None
