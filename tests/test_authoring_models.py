"""Construction-time shape checks and computations of the authoring flat models.

Tier 1 of the two-tier validation: what the models enforce at construction
(formats, lengths, code lists, decimal budgets, local consistency) plus the
computed totals and VAT breakdown. The cross-aggregate rule set is exercised in
``test_authoring_rules.py``; the wire mapping in ``test_authoring_roundtrip.py``.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from _authoring import make_address, make_invoice, make_line
from anafpy.efactura.authoring import (
    Contact,
    DocumentAllowance,
    DocumentCharge,
    DocumentKind,
    InvoiceTypeCode,
    ItemAttribute,
    LineAllowance,
    LineCharge,
    Note,
    Period,
    PostalAddress,
    SupportingDocument,
    Totals,
    VatBreakdownEntry,
    VatCategory,
)

# --- document shape -----------------------------------------------------------


def test_type_code_defaults_by_kind() -> None:
    assert make_invoice().type_code is InvoiceTypeCode.COMMERCIAL_INVOICE
    credit_note = make_invoice(kind="credit_note")
    assert credit_note.type_code is InvoiceTypeCode.CREDIT_NOTE


def test_type_code_must_match_kind() -> None:
    with pytest.raises(ValidationError, match="BR-RO-020"):
        make_invoice(type_code="381")
    with pytest.raises(ValidationError, match="BR-RO-020"):
        make_invoice(kind="credit_note", type_code="380")
    assert make_invoice(type_code="384").type_code is InvoiceTypeCode.CORRECTED_INVOICE


def test_type_code_accepts_member_names() -> None:
    doc = make_invoice(type_code="SELF_BILLED_INVOICE")
    assert doc.type_code is InvoiceTypeCode.SELF_BILLED_INVOICE


def test_invoice_number_needs_a_digit() -> None:
    # BR-RO-010
    with pytest.raises(ValidationError):
        make_invoice(number="FARA-CIFRE")
    assert make_invoice(number="A1").number == "A1"


def test_vat_point_date_and_code_are_exclusive() -> None:
    # BR-CO-03
    with pytest.raises(ValidationError, match="BR-CO-03"):
        make_invoice(vat_point_date=dt.date(2026, 7, 1), vat_point_date_code="35")
    assert make_invoice(vat_point_date_code="3").vat_point_date_code is not None


def test_non_ron_invoice_requires_ron_tax_currency() -> None:
    # BR-RO-030
    with pytest.raises(ValidationError, match="BR-RO-030"):
        make_invoice(currency="EUR")
    assert make_invoice(currency="EUR", tax_currency="RON").tax_currency == "RON"
    # RON invoices may skip it, or set anything (the rule's odd third combo).
    assert make_invoice().tax_currency is None
    assert make_invoice(tax_currency="EUR").tax_currency == "EUR"


def test_currency_code_list_is_enforced() -> None:
    with pytest.raises(ValidationError, match="ISO 4217"):
        make_invoice(currency="LEI")


def test_sales_order_reference_requires_order_reference() -> None:
    with pytest.raises(ValidationError, match="BT-13"):
        make_invoice(sales_order_reference="SO-1")
    doc = make_invoice(order_reference="PO-1", sales_order_reference="SO-1")
    assert doc.sales_order_reference == "SO-1"


def test_note_count_and_length_limits() -> None:
    # BR-RO-A020 / BR-RO-L300
    with pytest.raises(ValidationError):
        make_invoice(notes=[Note(text=f"nota {i}") for i in range(21)])
    with pytest.raises(ValidationError):
        Note(text="x" * 301)
    assert Note(text="#nu e cod", subject_code="AAI").subject_code == "AAI"
    with pytest.raises(ValidationError, match="UNCL 4451"):
        Note(text="ok", subject_code="XYZ")


def test_at_least_one_line_is_required() -> None:
    # BR-16
    with pytest.raises(ValidationError):
        make_invoice(lines=[])


# --- addresses -----------------------------------------------------------------


def test_romanian_address_requires_a_county_code() -> None:
    # BR-RO-110
    with pytest.raises(ValidationError, match="ISO 3166-2:RO"):
        make_address(county=None)
    with pytest.raises(ValidationError, match="ISO 3166-2:RO"):
        make_address(county="Cluj")


def test_bucharest_city_is_a_sector_and_gets_normalised() -> None:
    # BR-RO-100
    address = make_address(county="RO-B", city="sector 3")
    assert address.city == "SECTOR3"
    with pytest.raises(ValidationError, match="SECTOR"):
        make_address(county="RO-B", city="Bucuresti")


def test_foreign_address_needs_no_county() -> None:
    address = PostalAddress(street="Hauptstr. 1", city="Berlin", country="DE")
    assert address.county is None
    with pytest.raises(ValidationError, match="ISO 3166"):
        PostalAddress(street="x", city="y", country="XX")


# --- contacts, parties ----------------------------------------------------------


def test_contact_email_and_telephone_shapes() -> None:
    contact = Contact(name="Ion", telephone="+40 721 000 000", email="ion@firma.ro")
    assert contact.email == "ion@firma.ro"
    with pytest.raises(ValidationError, match="email"):
        Contact(email="nu-e-email")
    with pytest.raises(ValidationError, match="3 digits"):
        Contact(telephone="abcdef")


def test_vat_id_requires_country_prefix() -> None:
    # BR-CO-09
    from _authoring import make_seller

    with pytest.raises(ValidationError):
        make_seller(vat_id="12345678")
    assert make_seller(vat_id="EL123456789").vat_id == "EL123456789"


# --- periods, allowances, lines --------------------------------------------------


def test_period_needs_a_bound_and_ordering() -> None:
    # BR-CO-19 / BR-29
    with pytest.raises(ValidationError, match="start date"):
        Period()
    with pytest.raises(ValidationError, match="precedes"):
        Period(start=dt.date(2026, 7, 2), end=dt.date(2026, 7, 1))
    assert Period(start=dt.date(2026, 7, 1)).end is None


def test_allowance_requires_a_reason() -> None:
    # BR-33 / BR-CO-21
    with pytest.raises(ValidationError, match="reason"):
        DocumentAllowance(
            amount=Decimal("5.00"),
            vat_category=VatCategory.STANDARD,
            vat_rate=Decimal("19"),
        )
    allowance = DocumentAllowance(
        amount=Decimal("5.00"),
        reason_code="95",
        vat_category=VatCategory.STANDARD,
        vat_rate=Decimal("19"),
    )
    assert allowance.reason_code == "95"
    with pytest.raises(ValidationError, match="reason"):
        LineAllowance(amount=Decimal("1.00"))


def test_amounts_carry_at_most_two_decimals() -> None:
    # BR-DEC
    with pytest.raises(ValidationError):
        DocumentCharge(
            amount=Decimal("5.001"),
            reason="transport",
            vat_category=VatCategory.STANDARD,
            vat_rate=Decimal("19"),
        )
    with pytest.raises(ValidationError):
        make_line(net_amount=Decimal("10.123"))
    # Prices are not decimal-budgeted.
    assert make_line(unit_price=Decimal("0.1234")).unit_price == Decimal("0.1234")


def test_vat_rate_shape_per_category() -> None:
    # BR-S-05, BR-E-05, BR-O-05...
    with pytest.raises(ValidationError, match="above zero"):
        make_line(vat_category=VatCategory.STANDARD, vat_rate=Decimal("0"))
    with pytest.raises(ValidationError, match="requires a rate"):
        make_line(vat_category=VatCategory.STANDARD, vat_rate=None)
    exempt = make_line(vat_category=VatCategory.EXEMPT, vat_rate=None)
    assert exempt.vat_rate == 0
    with pytest.raises(ValidationError, match="0% rate"):
        make_line(vat_category=VatCategory.REVERSE_CHARGE, vat_rate=Decimal("19"))
    not_subject = make_line(vat_category=VatCategory.NOT_SUBJECT, vat_rate=None)
    assert not_subject.vat_rate is None
    with pytest.raises(ValidationError, match="no rate"):
        make_line(vat_category=VatCategory.NOT_SUBJECT, vat_rate=Decimal("0"))


def test_vat_category_accepts_names_and_lowercase_codes() -> None:
    assert make_line(vat_category="standard").vat_category is VatCategory.STANDARD
    assert make_line(vat_category="s").vat_category is VatCategory.STANDARD
    assert (
        make_line(vat_category="REVERSE_CHARGE", vat_rate=None).vat_category
        is VatCategory.REVERSE_CHARGE
    )


def test_line_item_shape_checks() -> None:
    with pytest.raises(ValidationError, match="BR-64"):
        make_line(standard_item_id="5901234123457")
    line = make_line(standard_item_id="5901234123457", standard_item_scheme="0088")
    assert line.standard_item_scheme == "0088"
    with pytest.raises(ValidationError, match="Rec 20/21"):
        make_line(unit="KG")  # not on the list; KGM is
    with pytest.raises(ValidationError):
        make_line(name="x" * 101)  # BR-RO-L100
    too_many = [ItemAttribute(name=f"a{i}", value="v") for i in range(51)]
    with pytest.raises(ValidationError):
        make_line(attributes=too_many)


def test_unit_price_may_not_be_negative() -> None:
    # BR-27
    with pytest.raises(ValidationError):
        make_line(unit_price=Decimal("-1"))
    # ... but quantity and net amount may (credit-style corrections).
    line = make_line(quantity=Decimal("-2"), net_amount=Decimal("-20.00"))
    assert line.effective_net_amount == Decimal("-20.00")


def test_supporting_document_embedded_content_needs_metadata() -> None:
    with pytest.raises(ValidationError, match="mime_code"):
        SupportingDocument(reference="DOC-1", content=b"pdf")
    document = SupportingDocument(
        reference="DOC-1",
        content=b"pdf",
        mime_code="application/pdf",
        filename="doc.pdf",
    )
    assert document.mime_code == "application/pdf"


def test_breakdown_entry_exemption_reason_rules() -> None:
    # BR-E-10 and BR-S-10
    with pytest.raises(ValidationError, match="exemption reason"):
        VatBreakdownEntry(category=VatCategory.EXEMPT)
    entry = VatBreakdownEntry(
        category=VatCategory.EXEMPT, exemption_reason="scutit conform art. 292"
    )
    assert entry.rate == 0
    with pytest.raises(ValidationError, match="no exemption reason"):
        VatBreakdownEntry(
            category=VatCategory.STANDARD, rate=Decimal("19"), exemption_reason="nu"
        )
    with pytest.raises(ValidationError, match="VATEX"):
        VatBreakdownEntry(category=VatCategory.EXEMPT, exemption_reason_code="NU-E-COD")
    coded = VatBreakdownEntry(
        category=VatCategory.EXEMPT, exemption_reason_code="VATEX-EU-132"
    )
    assert coded.exemption_reason_code == "VATEX-EU-132"
    with pytest.raises(ValidationError, match="zero tax"):
        VatBreakdownEntry(
            category=VatCategory.INTRA_COMMUNITY,
            exemption_reason="livrare intracomunitara",
            tax_amount=Decimal("19.00"),
        )


# --- computed totals and VAT breakdown -------------------------------------------


def test_line_net_amount_computed_and_rounded() -> None:
    line = make_line(quantity=Decimal("3"), unit_price=Decimal("0.333"))
    assert line.effective_net_amount == Decimal("1.00")  # 0.999 -> 1.00 half-up
    line = make_line(
        quantity=Decimal("10"),
        unit_price=Decimal("2.50"),
        price_base_quantity=Decimal("5"),
    )
    assert line.effective_net_amount == Decimal("5.00")


def test_line_net_amount_includes_line_allowances_and_charges() -> None:
    line = make_line(
        allowances=[LineAllowance(amount=Decimal("10.00"), reason="discount")],
        charges=[LineCharge(amount=Decimal("2.50"), reason="ambalaj")],
    )
    assert line.effective_net_amount == Decimal("92.50")


def test_explicit_line_net_amount_wins() -> None:
    line = make_line(net_amount=Decimal("99.99"))
    assert line.effective_net_amount == Decimal("99.99")


def test_vat_breakdown_groups_by_category_and_rate() -> None:
    doc = make_invoice(
        lines=[
            make_line(),  # 100.00 @ S/19
            make_line(unit_price=Decimal("5.00"), vat_rate=Decimal("9")),  # 50 @ S/9
            make_line(unit_price=Decimal("20.00"), vat_rate=Decimal("19")),  # 200
        ]
    )
    breakdown = doc.effective_vat_breakdown()
    assert [
        (entry.rate, entry.taxable_amount, entry.tax_amount) for entry in breakdown
    ] == [
        (Decimal("9"), Decimal("50.00"), Decimal("4.50")),
        (Decimal("19"), Decimal("300.00"), Decimal("57.00")),
    ]


def test_vat_breakdown_shifts_by_document_allowances_and_charges() -> None:
    doc = make_invoice(
        allowances=[
            DocumentAllowance(
                amount=Decimal("10.00"),
                reason="discount",
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
        charges=[
            DocumentCharge(
                amount=Decimal("4.00"),
                reason="transport",
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
    )
    (entry,) = doc.effective_vat_breakdown()
    assert entry.taxable_amount == Decimal("94.00")
    assert entry.tax_amount == Decimal("17.86")


def test_exemption_reason_carried_from_explicit_entry() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.EXEMPT, vat_rate=None)],
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.EXEMPT, exemption_reason="art. 292 CF"
            )
        ],
    )
    (entry,) = doc.effective_vat_breakdown()
    assert entry.exemption_reason == "art. 292 CF"
    assert entry.taxable_amount == Decimal("100.00")
    assert entry.tax_amount == Decimal("0.00")


def test_totals_chain_and_rounding() -> None:
    doc = make_invoice(
        allowances=[
            DocumentAllowance(
                amount=Decimal("10.00"),
                reason="discount",
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
        totals=Totals(prepaid=Decimal("50.00"), rounding=Decimal("0.10")),
    )
    totals = doc.effective_totals()
    assert totals.lines_total == Decimal("100.00")
    assert totals.allowance_total == Decimal("10.00")
    assert totals.charge_total is None
    assert totals.tax_exclusive == Decimal("90.00")
    assert totals.vat_total == Decimal("17.10")
    assert totals.tax_inclusive == Decimal("107.10")
    assert totals.payable == Decimal("57.20")  # BR-CO-16 with prepaid + rounding


def test_explicit_totals_members_win_over_computed() -> None:
    doc = make_invoice(totals=Totals(payable=Decimal("120.00")))
    totals = doc.effective_totals()
    assert totals.payable == Decimal("120.00")  # explicit preserved
    assert totals.lines_total == Decimal("100.00")  # rest computed


def test_document_kind_enum_coercion() -> None:
    assert make_invoice(kind="credit_note").kind is DocumentKind.CREDIT_NOTE
    assert make_invoice(kind="CREDIT_NOTE").kind is DocumentKind.CREDIT_NOTE
