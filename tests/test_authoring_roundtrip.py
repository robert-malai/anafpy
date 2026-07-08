"""Wire mapping of the authoring models: build/render one way, read/parse back.

The core property is ``render(parse(render(doc))) == render(doc)`` — whatever
the builder writes, the reader recovers, byte-stable — exercised on a
maximal-surface invoice touching every business group and on a credit note
with its syntax quirks (due date via PaymentMeans, project reference via a
type-50 document reference).
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

import pytest

from _authoring import make_address, make_buyer, make_invoice, make_line, make_seller
from anafpy.efactura.authoring import (
    Contact,
    CreditTransfer,
    DeliveryInformation,
    DirectDebit,
    DocumentAllowance,
    DocumentCharge,
    DocumentKind,
    ElectronicAddress,
    InvoiceDocument,
    ItemAttribute,
    ItemClassification,
    LineAllowance,
    LineCharge,
    Note,
    Payee,
    PaymentCard,
    PaymentInstructions,
    Period,
    PrecedingInvoice,
    SupportingDocument,
    TaxRepresentative,
    Totals,
    VatBreakdownEntry,
    VatCategory,
    build_invoice,
    parse_invoice,
    read_invoice,
    render_invoice,
    validate,
)
from anafpy.efactura.models import parse_ubl_document
from anafpy.efactura.ubl.maindoc.ubl_credit_note_2_1 import CreditNote
from anafpy.efactura.ubl.maindoc.ubl_invoice_2_1 import Invoice


def element_text(raw: str, element: str, text: str) -> bool:
    """True when ``<...:element ...>text<`` occurs (namespace declarations are
    re-emitted on every element, so plain substrings cannot match)."""
    return re.search(rf"{element}[^>]*>{re.escape(text)}<", raw) is not None


def maximal_invoice() -> InvoiceDocument:
    """An invoice touching every business group the models carry."""
    return make_invoice(
        number="FULL-2026-001",
        tax_currency="EUR",
        vat_point_date_code="35",
        buyer_reference="REF-BUYER",
        project_reference="PROIECT-7",
        contract_reference="CTR-12",
        order_reference="PO-13",
        sales_order_reference="SO-14",
        receiving_advice_reference="RA-15",
        despatch_advice_reference="DA-16",
        tender_or_lot_reference="LOT-17",
        invoiced_object_id="OBJ-18",
        invoiced_object_scheme="ABZ",
        accounting_reference="4111",
        payment_terms="Plata in 30 de zile",
        notes=[Note(text="nota simpla"), Note(text="cu subiect", subject_code="AAI")],
        invoicing_period=Period(start=dt.date(2026, 6, 1), end=dt.date(2026, 6, 30)),
        preceding_invoices=[
            PrecedingInvoice(number="OLD-1", issue_date=dt.date(2026, 5, 5))
        ],
        seller=make_seller(
            trading_name="Furnizor Comert",
            identifiers=[],
            legal_registration_id="J12/345/2020",
            tax_registration_id="12345678",
            additional_legal_info="Capital social 200 RON",
            electronic_address=ElectronicAddress(address="0000000000", scheme="0088"),
            contact=Contact(
                name="Ion Popescu", telephone="+40 721 000 000", email="ion@firma.ro"
            ),
            address=make_address(
                additional_street="Cladirea B",
                address_line="Etaj 3",
                postal_zone="400001",
            ),
        ),
        buyer=make_buyer(
            trading_name="Client Retail",
            legal_registration_id="J40/1/2019",
            electronic_address=ElectronicAddress(address="1111111111", scheme="0088"),
            contact=Contact(name="Maria", email="maria@client.ro"),
        ),
        payee=Payee(name="Factor Finance SRL", legal_registration_id="J40/9/2010"),
        tax_representative=TaxRepresentative(
            name="Reprezentant Fiscal SRL",
            vat_id="RO99999999",
            address=make_address(),
        ),
        delivery=DeliveryInformation(
            recipient_name="Depozit Central",
            location_id="LOC-1",
            location_scheme="0088",
            date=dt.date(2026, 7, 5),
            address=make_address(county="RO-B", city="SECTOR2"),
        ),
        payment_instructions=PaymentInstructions(
            means_code="30",
            means_text="transfer bancar",
            remittance_information="FULL-2026-001",
            credit_transfers=[
                CreditTransfer(
                    account_id="RO49AAAA1B31007593840000",
                    account_name="Furnizor Test SRL",
                    service_provider_id="BTRLRO22",
                ),
                CreditTransfer(account_id="RO12BBBB1B31007593840001"),
            ],
            card=PaymentCard(number="4111111111", holder_name="ION POPESCU"),
            direct_debit=DirectDebit(
                mandate_reference="MANDAT-9",
                creditor_id="RO88ZZZ9999999",
                debited_account_id="RO77CCCC1B31007593840002",
            ),
        ),
        allowances=[
            DocumentAllowance(
                amount=Decimal("10.00"),
                base_amount=Decimal("100.00"),
                percentage=Decimal("10"),
                reason="Discount volum",
                reason_code="95",
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
        charges=[
            DocumentCharge(
                amount=Decimal("4.00"),
                reason="Transport",
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
        supporting_documents=[
            SupportingDocument(reference="URL-DOC", url="https://exemplu.ro/doc"),
            SupportingDocument(
                reference="PDF-DOC",
                description="Contract semnat",
                content=b"%PDF-1.4 fake",
                mime_code="application/pdf",
                filename="contract.pdf",
            ),
        ],
        lines=[
            make_line(
                id="L1",
                note="linie cu tot",
                object_id="OBJ-128",
                object_id_scheme="ABZ",
                order_line_reference="PO-13-1",
                accounting_reference="704",
                period=Period(start=dt.date(2026, 6, 1), end=dt.date(2026, 6, 15)),
                allowances=[LineAllowance(amount=Decimal("5.00"), reason="discount")],
                charges=[LineCharge(amount=Decimal("1.00"), reason="ambalaj")],
                price_base_quantity=Decimal("1"),
                price_base_unit="H87",
                gross_price=Decimal("12.00"),
                price_discount=Decimal("2.00"),
                description="Consultanta lunara",
                sellers_item_id="SKU-1",
                buyers_item_id="CLI-1",
                standard_item_id="5901234123457",
                standard_item_scheme="0160",
                classifications=[
                    ItemClassification(code="86141", scheme="STI", scheme_version="1")
                ],
                origin_country="RO",
                attributes=[ItemAttribute(name="culoare", value="albastru")],
            ),
            make_line(
                name="Produs redus",
                unit="KGM",
                vat_rate=Decimal("9"),
                unit_price=Decimal("3.5"),
                quantity=Decimal("4"),
            ),
        ],
        totals=Totals(
            prepaid=Decimal("20.00"),
            rounding=Decimal("0.05"),
            vat_total_tax_currency=Decimal("4.20"),
        ),
    )


def test_maximal_invoice_is_locally_valid() -> None:
    report = validate(maximal_invoice())
    assert report.ok, [f.model_dump() for f in report.fatal]


def test_maximal_invoice_roundtrip_is_byte_stable() -> None:
    doc = maximal_invoice()
    xml = render_invoice(doc)
    back = parse_invoice(xml)
    assert render_invoice(back) == xml


def test_roundtrip_preserves_every_business_group() -> None:
    doc = maximal_invoice()
    back = parse_invoice(render_invoice(doc))

    assert back.kind is DocumentKind.INVOICE
    assert back.number == doc.number
    assert back.vat_point_date_code == doc.vat_point_date_code
    assert back.invoicing_period == doc.invoicing_period
    assert back.notes == doc.notes
    assert back.preceding_invoices == doc.preceding_invoices
    assert back.project_reference == "PROIECT-7"
    assert back.invoiced_object_id == "OBJ-18"
    assert back.supporting_documents == doc.supporting_documents

    assert back.seller.tax_registration_id == "12345678"
    assert back.seller.additional_legal_info == "Capital social 200 RON"
    assert back.seller.electronic_address == doc.seller.electronic_address
    assert back.seller.contact == doc.seller.contact
    assert back.buyer.legal_registration_id == "J40/1/2019"
    assert back.payee == doc.payee
    assert back.tax_representative == doc.tax_representative
    assert back.delivery == doc.delivery
    assert back.payment_instructions == doc.payment_instructions
    assert back.allowances == doc.allowances
    assert back.charges == doc.charges

    first = back.lines[0]
    assert first.id == "L1"
    assert first.gross_price == Decimal("12.00")
    assert first.price_discount == Decimal("2.00")
    assert first.classifications == doc.lines[0].classifications
    assert first.attributes == doc.lines[0].attributes
    assert first.period == doc.lines[0].period

    # Wire amounts land in the explicit fields.
    computed = doc.effective_totals()
    assert back.totals is not None
    assert back.totals.lines_total == computed.lines_total
    assert back.totals.payable == computed.payable
    assert back.totals.vat_total_tax_currency == Decimal("4.20")
    assert [entry.category for entry in back.vat_breakdown] == [
        entry.category for entry in doc.effective_vat_breakdown()
    ]
    assert all(entry.taxable_amount is not None for entry in back.vat_breakdown)


def test_credit_note_roundtrip_with_syntax_quirks() -> None:
    doc = make_invoice(
        kind="credit_note",
        number="CN-2026-01",
        project_reference="PROIECT-7",
        preceding_invoices=[PrecedingInvoice(number="INV-2026-0042")],
    )
    xml = render_invoice(doc)
    model = parse_ubl_document(xml)
    assert isinstance(model, CreditNote)
    raw = xml.decode()
    # BT-9 rides PaymentMeans on a credit note, with the schema-required code.
    assert element_text(raw, "PaymentDueDate", "2026-08-07")
    assert element_text(raw, "PaymentMeansCode", "1")
    # BT-11 rides a type-50 AdditionalDocumentReference.
    assert element_text(raw, "DocumentTypeCode", "50")

    back = parse_invoice(xml)
    assert back.kind is DocumentKind.CREDIT_NOTE
    assert back.due_date == doc.due_date
    assert back.project_reference == "PROIECT-7"
    assert back.payment_instructions is None  # the bare carrier is not BG-16
    assert render_invoice(back) == xml


def test_wire_document_shape() -> None:
    doc = maximal_invoice()
    model = build_invoice(doc)
    assert isinstance(model, Invoice)
    raw = render_invoice(doc).decode()
    assert (
        "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
        in raw
    )
    assert element_text(raw, "InvoiceTypeCode", "380")
    # BT-32 rides the second PartyTaxScheme with a non-VAT scheme id.
    assert raw.count("PartyTaxScheme>") >= 4
    assert element_text(raw, "ID", "FC")
    # BT-90 on the payee with schemeID SEPA.
    assert 'schemeID="SEPA">RO88ZZZ9999999<' in raw
    # The second TaxTotal carries BT-111 in the tax currency.
    assert 'currencyID="EUR">4.20<' in raw
    # UBL's mandatory CardAccount/NetworkID filler.
    assert element_text(raw, "NetworkID", "ZZZ")


def test_sepa_creditor_rides_seller_when_no_payee() -> None:
    doc = make_invoice(
        payment_instructions=PaymentInstructions(
            means_code="59",
            direct_debit=DirectDebit(creditor_id="RO88ZZZ9999999"),
        )
    )
    xml = render_invoice(doc)
    back = parse_invoice(xml)
    assert back.payment_instructions is not None
    assert back.payment_instructions.direct_debit is not None
    assert back.payment_instructions.direct_debit.creditor_id == "RO88ZZZ9999999"
    assert back.seller.identifiers == []  # not misread as a plain identifier
    assert render_invoice(back) == xml


def test_exempt_invoice_roundtrip_keeps_exemption_reason() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.EXEMPT, vat_rate=None)],
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.EXEMPT,
                exemption_reason="Scutit conform art. 292",
                exemption_reason_code="VATEX-EU-132",
            )
        ],
    )
    back = parse_invoice(render_invoice(doc))
    (entry,) = back.vat_breakdown
    assert entry.exemption_reason == "Scutit conform art. 292"
    assert entry.exemption_reason_code == "VATEX-EU-132"
    assert entry.rate == 0
    assert validate(back).ok


def test_bucharest_sector_survives_the_roundtrip() -> None:
    doc = make_invoice(
        buyer=make_buyer(address=make_address(county="RO-B", city="sector 3"))
    )
    back = parse_invoice(render_invoice(doc))
    assert back.buyer.address.city == "SECTOR3"
    assert back.buyer.address.county == "RO-B"


def test_read_invoice_accepts_the_generated_model_directly() -> None:
    doc = make_invoice()
    model = build_invoice(doc)
    back = read_invoice(model)
    assert back.number == doc.number
    assert back.lines[0].net_amount == Decimal("100.00")


def test_parse_invoice_rejects_junk() -> None:
    with pytest.raises(ValueError, match="not a parseable UBL"):
        parse_invoice(b"<not-ubl/>")


def test_non_ron_invoice_renders_both_tax_totals() -> None:
    doc = make_invoice(
        currency="EUR",
        tax_currency="RON",
        totals=Totals(vat_total_tax_currency=Decimal("94.53")),
    )
    raw = render_invoice(doc).decode()
    assert 'currencyID="EUR">19.00<' in raw  # BT-110 in the document currency
    assert 'currencyID="RON">94.53<' in raw  # BT-111 in the tax currency
    back = parse_invoice(render_invoice(doc))
    assert back.totals is not None
    assert back.totals.vat_total == Decimal("19.00")
    assert back.totals.vat_total_tax_currency == Decimal("94.53")
