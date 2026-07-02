"""Value types returned by :class:`anafpy.efactura.client.EFacturaClient`.

These are deliberately small, transport-facing types. Business outcomes (an upload
rejected at submission, a ``nok`` status) are represented here as *values*, never
exceptions — see :mod:`anafpy.exceptions` for the error half of the hybrid model.

The richer document models (``Invoice``/``CreditNote``) are the generated UBL types;
``DownloadedMessage`` preserves the raw signed bytes and parses them lazily.
"""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from enum import StrEnum
from functools import cached_property
from typing import Annotated, Any, cast

from pydantic import BaseModel, BeforeValidator, ConfigDict

from .ubl.maindoc import CreditNote, Invoice

__all__ = [
    "DownloadedMessage",
    "Filter",
    "FlatInvoice",
    "FlatInvoiceLine",
    "FlatParty",
    "MessageListItem",
    "MessageState",
    "MessageStatus",
    "RemoteValidationResult",
    "SignatureValidationResult",
    "TransformStandard",
    "UploadResult",
    "UploadStandard",
    "parse_ubl_document",
    "read_flat_invoice",
]

# Coerce any non-None JSON value to str; mirrors the defensive s() helper previously
# used in from_json classmethods (ANAF occasionally returns numeric ids as numbers).
_StrNone = Annotated[
    str | None, BeforeValidator(lambda v: None if v is None else str(v))
]


class UploadStandard(StrEnum):
    """``standard`` query param for ``/upload`` (the document kind being submitted)."""

    UBL = "UBL"  # invoice
    CN = "CN"  # credit note
    CII = "CII"
    RASP = "RASP"  # buyer -> issuer message


class TransformStandard(StrEnum):
    """``std`` path segment for ``/validare`` and ``/transformare``."""

    INVOICE = "FACT1"
    CREDIT_NOTE = "FCN"


class Filter(StrEnum):
    """``filtru`` query param for the message-list endpoints."""

    ERRORS = "E"  # ERORI FACTURA
    SENT = "T"  # FACTURA TRIMISA
    RECEIVED = "P"  # FACTURA PRIMITA
    BUYER_MESSAGE = "R"  # MESAJ CUMPARATOR


class MessageState(StrEnum):
    """Terminal/non-terminal states reported by ``stareMesaj``."""

    OK = "ok"
    NOK = "nok"
    PROCESSING = "in prelucrare"
    REJECTED = "XML cu erori nepreluat de sistem"

    @classmethod
    def from_raw(cls, value: str) -> MessageState:
        normalized = " ".join(value.strip().lower().split())
        for state in cls:
            if state.value.lower() == normalized:
                return state
        raise ValueError(f"unrecognised stareMesaj state: {value!r}")


class UploadResult(BaseModel):
    """Outcome of ``/upload``.

    ``upload_id`` (``index_incarcare``) is set when ANAF accepted the document for
    processing; ``errors`` carries any messages when it was rejected at submission.
    """

    upload_id: str | None
    errors: list[str] = []
    raw: bytes = b""

    @property
    def accepted(self) -> bool:
        return self.upload_id is not None


class MessageStatus(BaseModel):
    """Outcome of ``stareMesaj``."""

    state: MessageState
    download_id: str | None = None
    errors: list[str] = []
    raw: bytes = b""

    @property
    def is_processing(self) -> bool:
        return self.state is MessageState.PROCESSING

    @property
    def is_terminal(self) -> bool:
        return self.state is not MessageState.PROCESSING


class RemoteValidationResult(BaseModel):
    """Outcome of ANAF's server-side ``validare`` endpoint.

    An invalid document is a *business* outcome: ``valid`` is ``False`` and
    ``messages`` carries ANAF's findings — never an exception.
    """

    valid: bool
    messages: list[str] = []
    trace_id: str | None = None
    raw: bytes = b""


class SignatureValidationResult(BaseModel):
    """Outcome of ``POST /api/validate/signature`` (MF signature over an invoice).

    Both outcomes are HTTP 200 with a prose ``msg``; ``valid`` reflects which of the
    two documented wordings ANAF answered with. A failed validation is a *business*
    outcome — never an exception.
    """

    valid: bool
    message: str
    raw: bytes = b""


class MessageListItem(BaseModel):
    """One entry from a message-list response."""

    id: _StrNone = None
    id_solicitare: _StrNone = None
    tip: _StrNone = None
    data_creare: _StrNone = None
    cif: _StrNone = None
    cif_emitent: _StrNone = None
    cif_beneficiar: _StrNone = None
    detalii: _StrNone = None


def parse_ubl_document(xml: bytes) -> Invoice | CreditNote | None:
    """Parse e-Factura wire XML into its UBL model.

    Returns an :class:`Invoice` or :class:`CreditNote`, or ``None`` when the bytes are
    not a parseable UBL document (e.g. a ``nok`` errors file). Never raises.
    """
    # Imported here to keep import-time cost off the hot path for raw-bytes users.
    from xsdata.exceptions import ParserError
    from xsdata_pydantic.bindings import XmlParser

    parser = XmlParser()
    for model in (Invoice, CreditNote):
        try:
            parsed = parser.from_bytes(xml, model)
        except (ParserError, ValueError):
            continue
        return cast("Invoice | CreditNote", parsed)
    return None


class DownloadedMessage(BaseModel):
    """A ``descarcare`` ZIP, with raw bytes preserved.

    Three read tiers, cheapest first: ``raw_zip`` / ``content_xml`` (the legally
    meaningful, archived bytes), ``document`` (the full generated UBL model), and
    ``view`` (the easy-to-read :class:`FlatInvoice` projection). The latter two parse
    lazily; tier 1 stays authoritative.
    """

    model_config = ConfigDict(ignored_types=(cached_property,))

    raw_zip: bytes
    content_xml: bytes | None = None
    signature_xml: bytes | None = None

    @classmethod
    def from_zip(cls, raw_zip: bytes) -> DownloadedMessage:
        content: bytes | None = None
        signature: bytes | None = None
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                data = zf.read(name)
                if "semnatura" in name.lower():
                    signature = data
                else:
                    content = data
        return cls(raw_zip=raw_zip, content_xml=content, signature_xml=signature)

    @cached_property
    def document(self) -> Invoice | CreditNote | None:
        """Parse the content member into its UBL model, or ``None`` if it is not a UBL
        document (e.g. a ``nok`` errors file)."""
        if self.content_xml is None:
            return None
        return parse_ubl_document(self.content_xml)

    @cached_property
    def view(self) -> FlatInvoice | None:
        """The easy-to-read :class:`FlatInvoice` projection of :attr:`document`, or
        ``None`` when the content is not a parseable UBL invoice/credit-note."""
        doc = self.document
        return read_flat_invoice(doc) if doc is not None else None


# --- flat read view: UBL -> easy-to-read projection --------------------------------
#
# These types are produced *from* UBL only (read direction). anafpy never composes UBL
# from them — outbound filing is XML pass-through. The view is intentionally lossy: a
# supplier's UBL can carry structure it does not represent, so a top-level ``complete``
# flag / ``dropped_fields`` mark when the reader left something out, and the raw bytes
# plus the full :class:`Invoice` / :class:`CreditNote` stay authoritative.


class FlatParty(BaseModel):
    """A seller or buyer, flattened from the UBL ``Party`` tree."""

    name: str | None = None
    vat_id: str | None = None
    company_id: str | None = None
    country: str | None = None
    county: str | None = None
    city: str | None = None
    address: str | None = None
    postal_zone: str | None = None


class FlatInvoiceLine(BaseModel):
    """One invoice / credit-note line, read from UBL."""

    description: str | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None
    unit_price: Decimal | None = None
    vat_category: str | None = None
    vat_rate: Decimal | None = None
    line_amount: Decimal | None = None


class FlatInvoice(BaseModel):
    """An invoice or credit note flattened into an easy-to-read shape.

    A lossy projection of UBL for display / triage. ``complete`` is ``False`` (and
    ``dropped_fields`` names what) when the source document carries structure this shape
    does not represent; consult the full UBL model or raw bytes in that case.
    """

    document_type: str
    number: str | None = None
    issue_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    type_code: str | None = None
    note: str | None = None
    seller: FlatParty = FlatParty()
    buyer: FlatParty = FlatParty()
    lines: list[FlatInvoiceLine] = []
    total_without_vat: Decimal | None = None
    total_vat: Decimal | None = None
    total_with_vat: Decimal | None = None
    complete: bool = True
    dropped_fields: list[str] = []


def _val(obj: Any) -> Any:
    """``obj.value`` if *obj* is present, else ``None`` (UBL basic components wrap a
    single ``value``)."""
    return None if obj is None else obj.value


def _first(seq: Any) -> Any:
    """First element of a possibly-empty UBL repeat, else ``None``."""
    return seq[0] if seq else None


def _read_party(party: Any) -> FlatParty:
    if party is None:
        return FlatParty()
    legal = _first(getattr(party, "party_legal_entity", None))
    tax_scheme = _first(getattr(party, "party_tax_scheme", None))
    name_obj = _first(getattr(party, "party_name", None))
    address = getattr(party, "postal_address", None)
    country = getattr(address, "country", None) if address else None
    return FlatParty(
        name=_val(getattr(name_obj, "name", None))
        or _val(getattr(legal, "registration_name", None)),
        vat_id=_val(getattr(tax_scheme, "company_id", None)),
        company_id=_val(getattr(legal, "company_id", None)),
        country=_val(getattr(country, "identification_code", None)),
        county=_val(getattr(address, "country_subentity", None)) if address else None,
        city=_val(getattr(address, "city_name", None)) if address else None,
        address=_val(getattr(address, "street_name", None)) if address else None,
        postal_zone=_val(getattr(address, "postal_zone", None)) if address else None,
    )


def _read_line(line: Any) -> FlatInvoiceLine:
    qty = getattr(line, "invoiced_quantity", None) or getattr(
        line, "credited_quantity", None
    )
    item = getattr(line, "item", None)
    tax_cat = _first(getattr(item, "classified_tax_category", None)) if item else None
    price = getattr(line, "price", None)
    return FlatInvoiceLine(
        description=_val(getattr(item, "name", None)) if item else None,
        quantity=_val(qty),
        unit_code=getattr(qty, "unit_code", None),
        unit_price=_val(getattr(price, "price_amount", None)) if price else None,
        vat_category=_val(getattr(tax_cat, "id", None)),
        vat_rate=_val(getattr(tax_cat, "percent", None)),
        line_amount=_val(getattr(line, "line_extension_amount", None)),
    )


def read_flat_invoice(doc: Invoice | CreditNote) -> FlatInvoice:
    """Project a UBL :class:`Invoice` / :class:`CreditNote` to a :class:`FlatInvoice`.

    Reads (never computes) the document totals; flags as dropped any document- or
    line-level structure the flat shape cannot carry (allowances/charges, prepaid
    amounts, extra payment means, more than one tax total).
    """
    is_invoice = isinstance(doc, Invoice)
    lines_src = getattr(doc, "invoice_line", None) or getattr(
        doc, "credit_note_line", None
    )
    type_code = getattr(doc, "invoice_type_code", None) or getattr(
        doc, "credit_note_type_code", None
    )

    dropped: list[str] = []
    if getattr(doc, "allowance_charge", None):
        dropped.append("allowance_charge")
    if getattr(doc, "payment_means", None):
        dropped.append("payment_means")
    if getattr(doc, "delivery", None):
        dropped.append("delivery")

    tax_totals = getattr(doc, "tax_total", None) or []
    total_vat = _val(getattr(_first(tax_totals), "tax_amount", None))
    if len(tax_totals) > 1:
        dropped.append("multiple_tax_total")

    lmt = getattr(doc, "legal_monetary_total", None)
    for extra in ("allowance_total_amount", "charge_total_amount", "prepaid_amount"):
        if _val(getattr(lmt, extra, None)):
            dropped.append(extra)

    lines = [_read_line(line) for line in (lines_src or [])]
    if any(getattr(line, "allowance_charge", None) for line in (lines_src or [])):
        dropped.append("line_allowance_charge")

    return FlatInvoice(
        document_type="invoice" if is_invoice else "credit_note",
        number=_val(getattr(doc, "id", None)),
        issue_date=_date_str(getattr(doc, "issue_date", None)),
        due_date=_date_str(getattr(doc, "due_date", None)),
        currency=_val(getattr(doc, "document_currency_code", None)),
        type_code=_val(type_code),
        note=_val(_first(getattr(doc, "note", None))),
        seller=_read_party(
            getattr(getattr(doc, "accounting_supplier_party", None), "party", None)
        ),
        buyer=_read_party(
            getattr(getattr(doc, "accounting_customer_party", None), "party", None)
        ),
        lines=lines,
        total_without_vat=_val(getattr(lmt, "tax_exclusive_amount", None)),
        total_vat=total_vat,
        total_with_vat=_val(getattr(lmt, "payable_amount", None)),
        complete=not dropped,
        dropped_fields=dropped,
    )


def _date_str(obj: Any) -> str | None:
    """Render a UBL date component as ISO text, or ``None``."""
    value = _val(obj)
    return None if value is None else str(value)
