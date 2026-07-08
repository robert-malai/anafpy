"""``DownloadedMessage.view``: the strict InvoiceDocument projection of a download.

The view is the authoring reader behind a never-raises guard: parseable,
CIUS-RO-shaped UBL yields a full-fidelity :class:`InvoiceDocument`; anything else
(a ``nok`` errors file, UBL the strict reader cannot represent) yields ``None``
while the raw bytes and the full UBL model stay available. The reader itself is
exercised in depth by ``test_authoring_roundtrip.py``.
"""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal

from xsdata_pydantic.bindings import XmlSerializer

from _wire import build_credit_note, build_invoice, invoice_xml
from anafpy.efactura import DownloadedMessage, parse_ubl_document
from anafpy.efactura.authoring import DocumentKind, validate


def _message(content: bytes) -> DownloadedMessage:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("1.xml", content)
        zf.writestr("semnatura_1.xml", b"<Signature/>")
    return DownloadedMessage.from_zip(buf.getvalue())


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


def test_view_is_none_when_the_strict_reader_balks() -> None:
    # Parseable UBL the authoring models reject (an off-list currency): the view
    # degrades to None instead of raising; document and raw bytes stay available.
    invoice = build_invoice()
    assert invoice.document_currency_code is not None
    invoice.document_currency_code.value = "LEI"
    message = _message(XmlSerializer().render(invoice).encode())
    assert message.document is not None
    assert message.view is None


def test_parse_ubl_document_handles_good_and_bad_input() -> None:
    xml = XmlSerializer().render(build_invoice()).encode("utf-8")
    parsed = parse_ubl_document(xml)
    assert parsed is not None
    assert parse_ubl_document(b"<not-a-ubl-doc/>") is None
