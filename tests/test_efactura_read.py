"""``DownloadedMessage.view``: the InvoiceDocument projection of a download.

The view is the authoring reader behind a never-raises guard: parseable UBL
yields a full-fidelity :class:`InvoiceDocument`; anything else (a ``nok`` errors
file, UBL the reader cannot represent) yields ``None`` while the raw bytes and
the full UBL model stay available. The reader itself is exercised in depth by
``test_authoring_roundtrip.py``.

The second half of this file is the inbound-leniency contract: the reader must
never reject a document ANAF itself accepted, so the authoring models'
construction checks stand down on the read path. The shapes exercised there are
the ones a real operator's inbox actually contained (issue #9) — every one of
them made the whole invoice unreadable before.
"""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from typing import Any

import pytest
from xsdata_pydantic.bindings import XmlSerializer

from _wire import build_credit_note, build_invoice, invoice_xml
from anafpy.efactura import DownloadedMessage, Invoice, parse_ubl_document
from anafpy.efactura.authoring import (
    DocumentAllowance,
    DocumentKind,
    InvoiceDocument,
    VatCategory,
    parse_invoice,
    render_invoice,
    validate,
)
from anafpy.efactura.ubl.common import ubl_common_aggregate_components_2_1 as agg
from anafpy.efactura.ubl.common import ubl_common_basic_components_2_1 as cbc


def _message(content: bytes) -> DownloadedMessage:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("1.xml", content)
        zf.writestr("semnatura_1.xml", b"<Signature/>")
    return DownloadedMessage.from_zip(buf.getvalue())


def _view_of(invoice: Invoice) -> InvoiceDocument:
    """Round-trip an invoice through the wire and back into the flat view.

    Serializing rather than calling ``read_invoice`` directly keeps the empty-
    element cases honest: ``<cbc:PostalZone/>`` only exists as XML.
    """
    message = _message(XmlSerializer().render(invoice).encode())
    view = message.view
    assert view is not None, message.view_error
    return view


def test_view_projects_invoice_header_parties_and_lines() -> None:
    view = _message(invoice_xml().encode()).view
    assert view is not None
    assert view.kind is DocumentKind.INVOICE
    assert view.number == "INV-1"
    assert view.currency == "RON"
    assert str(view.issue_date) == "2026-06-28"
    assert str(view.due_date) == "2026-07-28"
    assert view.type_code is not None and view.type_code.value == "380"
    assert view.seller.name == "Seller"
    assert view.seller.vat_id == "RO1"
    assert view.seller.address.city == "SECTOR1"
    assert view.buyer.name == "Buyer"
    (line,) = view.lines
    assert line.name == "Widget"
    assert line.quantity == Decimal("2")
    assert line.unit == "C62"
    assert line.unit_price == Decimal("10.50")
    assert line.vat_category.value == "S"
    assert line.vat_rate == Decimal("19")
    assert line.net_amount == Decimal("21.00")  # wire amount, explicit


def test_view_carries_wire_totals_and_validates() -> None:
    view = _message(invoice_xml().encode()).view
    assert view is not None
    assert view.totals is not None
    assert view.totals.tax_exclusive == Decimal("21.00")
    assert view.totals.vat_total == Decimal("3.99")
    assert view.totals.payable == Decimal("24.99")
    # The view is a real InvoiceDocument: the rule set can judge its arithmetic.
    assert validate(view).ok


def test_view_reads_a_credit_note() -> None:
    xml = XmlSerializer().render(build_credit_note()).encode()
    view = _message(xml).view
    assert view is not None
    assert view.kind is DocumentKind.CREDIT_NOTE
    assert view.number == "CN-1"
    assert view.type_code is not None and view.type_code.value == "381"
    (line,) = view.lines
    assert line.quantity == Decimal("2")


def test_view_is_none_for_non_ubl_content() -> None:
    message = _message(b"<Erori><Eroare mesaj='nok'/></Erori>")
    assert message.document is None
    assert message.view is None
    assert message.view_error is None  # nothing to report: it is not UBL at all


def test_view_is_none_on_code_list_drift_and_says_why() -> None:
    # An off-list currency is the one thing the flat models genuinely cannot
    # represent, so it stays fatal — the documented code-list drift tripwire.
    # The view degrades to None instead of raising, but never silently: the
    # cause is warned about and kept, so "unreadable" cannot pass for "empty".
    invoice = build_invoice()
    assert invoice.document_currency_code is not None
    invoice.document_currency_code.value = "LEI"
    message = _message(XmlSerializer().render(invoice).encode())
    with pytest.warns(UserWarning, match="could not be read"):
        assert message.view is None
    assert message.document is not None
    assert message.view_error is not None
    assert "ISO 4217 currency" in str(message.view_error)


def test_parse_ubl_document_handles_good_and_bad_input() -> None:
    xml = XmlSerializer().render(build_invoice()).encode("utf-8")
    parsed = parse_ubl_document(xml)
    assert parsed is not None
    assert parse_ubl_document(b"<not-a-ubl-doc/>") is None


# --- inbound leniency: shapes a real inbox carries (issue #9) -----------------


def _allowance(**kwargs: Any) -> agg.AllowanceCharge:
    return agg.AllowanceCharge(
        charge_indicator=cbc.ChargeIndicator(value=False),
        allowance_charge_reason=[cbc.AllowanceChargeReason(value="storno")],
        tax_category=[
            agg.TaxCategory(
                id=cbc.Id(value="S"),
                percent=cbc.Percent(value=Decimal("19")),
                tax_scheme=agg.TaxScheme(id=cbc.Id(value="VAT")),
            )
        ],
        **kwargs,
    )


def test_view_reads_the_negative_amounts_of_a_storno_invoice() -> None:
    # RO practice files a storno as a type-380 invoice with negative values
    # rather than as a type-381 credit note, and ANAF accepts it. Amount,
    # percentage, VAT total and unit price all go negative.
    invoice = build_invoice()
    invoice.allowance_charge = [
        _allowance(
            amount=cbc.Amount(value=Decimal("-515.61"), currency_id="RON"),
            multiplier_factor_numeric=cbc.MultiplierFactorNumeric(
                value=Decimal("-13.11")
            ),
        )
    ]
    invoice.tax_total[0].tax_amount = cbc.TaxAmount(
        value=Decimal("-109.20"), currency_id="RON"
    )
    price = invoice.invoice_line[0].price
    assert price is not None and price.price_amount is not None
    price.price_amount.value = Decimal("-10.50")

    view = _view_of(invoice)
    (allowance,) = view.allowances
    assert allowance.amount == Decimal("-515.61")
    assert allowance.percentage == Decimal("-13.11")
    assert view.totals is not None
    assert view.totals.vat_total == Decimal("-109.20")
    assert view.lines[0].unit_price == Decimal("-10.50")


def test_view_reads_empty_optional_elements_as_absent() -> None:
    # UBL treats <cbc:PostalZone/> as an absent value; the flat models used to
    # see a zero-length string and reject it, losing the whole document. Each
    # element here is one an issuer emitted empty on an accepted filing.
    invoice = build_invoice()
    seller = invoice.accounting_supplier_party.party
    assert seller is not None and seller.postal_address is not None
    seller.postal_address.postal_zone = cbc.PostalZone(value="")
    seller.party_identification = [agg.PartyIdentification(id=cbc.Id(value="  "))]
    seller.party_legal_entity[0].company_id = cbc.CompanyId(value="", scheme_id="0088")
    seller.party_tax_scheme.append(
        agg.PartyTaxScheme(
            company_id=cbc.CompanyId(value="12345"),
            tax_scheme=agg.TaxScheme(id=cbc.Id(value="")),
        )
    )
    invoice.order_reference = agg.OrderReference(
        id=cbc.Id(value=""), sales_order_id=cbc.SalesOrderId(value="SO-9")
    )
    invoice.project_reference = [agg.ProjectReference(id=cbc.Id(value=""))]
    invoice.invoice_line[0].item.description = [cbc.Description(value="")]
    invoice.payment_means = [
        agg.PaymentMeans(
            payment_means_code=cbc.PaymentMeansCode(value="30"),
            payee_financial_account=agg.PayeeFinancialAccount(
                id=cbc.Id(value="RO49AAAA1B31007593840000"),
                financial_institution_branch=agg.FinancialInstitutionBranch(
                    id=cbc.Id(value="")
                ),
            ),
        )
    ]

    view = _view_of(invoice)
    assert view.seller.address.postal_zone is None
    assert view.seller.identifiers == []
    assert view.seller.legal_registration_id is None
    assert view.seller.legal_registration_scheme is None
    assert view.seller.tax_registration_id == "12345"
    assert view.seller.tax_registration_scheme is None
    assert view.order_reference is None
    assert view.sales_order_reference == "SO-9"
    assert view.project_reference is None
    assert view.lines[0].description is None
    assert view.payment_instructions is not None
    (transfer,) = view.payment_instructions.credit_transfers
    assert transfer.service_provider_id is None


def test_embedded_content_without_mime_code_reads_and_renders() -> None:
    # The wire can carry an embedded binary with an empty mimeCode; reading
    # keeps the content (the authoring pairing check is stood down), and the
    # renderer drops the binary — its mimeCode attr is schema-required — rather
    # than crashing or writing a malformed attachment.
    invoice = build_invoice()
    invoice.additional_document_reference = [
        agg.AdditionalDocumentReference(
            id=cbc.Id(value="DOC-1"),
            attachment=agg.Attachment(
                embedded_document_binary_object=cbc.EmbeddedDocumentBinaryObject(
                    value=b"pdf-bytes", mime_code="", filename="doc.pdf"
                )
            ),
        )
    ]

    view = _view_of(invoice)
    (document,) = view.supporting_documents
    assert document.content == b"pdf-bytes"
    assert document.mime_code is None
    rendered = parse_invoice(render_invoice(view, skip_validation=True))
    (re_read,) = rendered.supporting_documents
    assert re_read.reference == "DOC-1"
    assert re_read.content is None


def test_view_drops_optional_aggregates_left_without_an_identifier() -> None:
    # A supporting document with no BT-122 and a billing reference with no BT-25
    # carry nothing the flat model could hold. Dropping the two entries beats
    # dropping the invoice they hang off.
    invoice = build_invoice()
    invoice.additional_document_reference = [
        agg.AdditionalDocumentReference(id=cbc.Id(value="")),
        agg.AdditionalDocumentReference(id=cbc.Id(value="DOC-2")),
    ]
    invoice.billing_reference = [
        agg.BillingReference(
            invoice_document_reference=agg.InvoiceDocumentReference(id=cbc.Id(value=""))
        )
    ]

    view = _view_of(invoice)
    assert [doc.reference for doc in view.supporting_documents] == ["DOC-2"]
    assert view.preceding_invoices == []


@pytest.mark.parametrize(
    ("email", "telephone"),
    [
        ("a@x.com; b@y.com", "0722 123 456"),  # two addresses in one BT-43
        ("user@domain.", "-"),  # truncated address, telephone with no digits
        ("first last@x.com", "1"),  # an embedded space
    ],
)
def test_view_keeps_malformed_contact_free_text(email: str, telephone: str) -> None:
    # BT-42/43 are informational and ANAF validates neither, so a typo in a
    # phone number must not cost the invoice. The values are read verbatim.
    invoice = build_invoice()
    seller = invoice.accounting_supplier_party.party
    assert seller is not None
    seller.contact = agg.Contact(
        electronic_mail=cbc.ElectronicMail(value=email),
        telephone=cbc.Telephone(value=telephone),
    )

    view = _view_of(invoice)
    assert view.seller.contact is not None
    assert view.seller.contact.email == email
    assert view.seller.contact.telephone == telephone


def test_view_reads_a_category_o_line_carrying_an_explicit_zero_rate() -> None:
    # BR-O-05 says category O takes no rate; an issuer sent <cbc:Percent>0</>.
    # Reading keeps the wire's own value so the round-trip stays byte-stable.
    invoice = build_invoice()
    category = invoice.invoice_line[0].item.classified_tax_category[0]
    category.id = cbc.Id(value="O")
    category.percent = cbc.Percent(value=Decimal("0"))

    view = _view_of(invoice)
    assert view.lines[0].vat_category.value == "O"
    assert view.lines[0].vat_rate == Decimal("0")
    # Leniently read is still fully re-renderable, and validate() reports what
    # the reader declined to judge — findings, not a lost document.
    once = render_invoice(view, skip_validation=True)
    assert render_invoice(parse_invoice(once), skip_validation=True) == once
    assert "BR-O-01" in {finding.rule for finding in validate(view).findings}


def test_category_o_groups_the_same_whether_the_rate_is_absent_or_zero() -> None:
    # Real documents spell category O's absent rate both ways in one file: no
    # cbc:Percent on the line, an explicit 0 on the tax subtotal. Keying those
    # apart split the group and produced a spurious fatal BR-O-08.
    invoice = build_invoice()
    line_category = invoice.invoice_line[0].item.classified_tax_category[0]
    line_category.id = cbc.Id(value="O")
    line_category.percent = None
    subtotal = invoice.tax_total[0].tax_subtotal[0]
    subtotal.tax_category.id = cbc.Id(value="O")
    subtotal.tax_category.percent = cbc.Percent(value=Decimal("0"))
    subtotal.tax_amount = cbc.TaxAmount(value=Decimal("0.00"), currency_id="RON")
    invoice.tax_total[0].tax_amount = cbc.TaxAmount(
        value=Decimal("0.00"), currency_id="RON"
    )

    view = _view_of(invoice)
    assert view.lines[0].vat_rate is None
    assert view.vat_breakdown[0].rate == Decimal("0")
    assert "BR-O-08" not in {f.rule for f in validate(view).findings}


def test_view_reads_bt_111_when_the_accounting_currency_equals_the_invoice_one() -> (
    None
):
    # BT-6 == BT-5 is legal and common: one TaxTotal then carries both BT-110
    # and BT-111, and BR-53 asks only that a TaxAmount in the accounting
    # currency exists. Reading it as BT-110 alone flagged a fatal BR-53 on
    # documents ANAF had accepted.
    invoice = build_invoice()
    invoice.tax_currency_code = cbc.TaxCurrencyCode(value="RON")

    view = _view_of(invoice)
    assert view.tax_currency == "RON"
    assert view.totals is not None
    assert view.totals.vat_total == Decimal("3.99")
    assert view.totals.vat_total_tax_currency == Decimal("3.99")
    assert "BR-53" not in {f.rule for f in validate(view).findings}


def test_a_storno_read_off_the_wire_renders_back() -> None:
    # The bidirectional contract holds for the lenient shapes too: the computed
    # totals are derived from the very amounts that make them negative, so
    # re-judging them made a read storno unrenderable.
    invoice = build_invoice()
    invoice.tax_total[0].tax_amount = cbc.TaxAmount(
        value=Decimal("-3.99"), currency_id="RON"
    )
    invoice.tax_total[0].tax_subtotal[0].tax_amount = cbc.TaxAmount(
        value=Decimal("-3.99"), currency_id="RON"
    )
    invoice.tax_total[0].tax_subtotal[0].taxable_amount = cbc.TaxableAmount(
        value=Decimal("-21.00"), currency_id="RON"
    )
    view = _view_of(invoice)

    assert view.compute_totals().vat_total == Decimal("-3.99")
    assert view.effective_totals().vat_total == Decimal("-3.99")
    once = render_invoice(view, skip_validation=True)
    assert render_invoice(parse_invoice(once), skip_validation=True) == once


def test_authoring_still_refuses_what_reading_accepts() -> None:
    # The leniency is the read path's alone: composing these same shapes for
    # filing still fails fast, which is what the construction checks are for.
    view = _view_of(build_invoice())
    contact = view.seller.contact
    assert contact is None

    with pytest.raises(ValueError, match="plausible email"):
        type(view.seller)(
            **view.seller.model_dump() | {"contact": {"email": "a@x.com; b@y.com"}}
        )
    # An allowance stays a positive amount under a false charge indicator when
    # authoring — the totals it feeds are the ones free to go negative.
    with pytest.raises(ValueError, match="must not be negative"):
        DocumentAllowance(
            amount=Decimal("-515.61"),
            reason="storno",
            vat_category=VatCategory.STANDARD,
            vat_rate=Decimal("19"),
        )
