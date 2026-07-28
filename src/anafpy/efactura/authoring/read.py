"""Read UBL wire XML back into the flat :class:`~.models.InvoiceDocument`.

The inverse of :mod:`.build`, sharing its syntax-mapping conventions (``#CODE#``
note prefixes, the non-``VAT``-schemed tax registration identifier, SEPA-schemed
creditor ids, type-130/50 document references). Every wire amount — line nets,
totals, the VAT breakdown — is read into the *explicit* fields, so a round-trip
preserves the source document's own arithmetic instead of recomputing it; run
:func:`~.rules.validate` on the result to judge that arithmetic.

The reader is **lenient about shape and strict about representability**. It
validates through :data:`~.models._DERIVED_CONTEXT`, which stands the
authoring models' construction-time checks down: what stops *us* filing an
invalid document has no business rejecting one ANAF already accepted, and the
inbox is full of shapes the authoring rules refuse — negative amounts on a
storno filed as a type-380 invoice, an empty ``<cbc:PostalZone/>``, two
addresses in one BT-43, a category-O line carrying an explicit zero rate. Run
:func:`~.rules.validate` on the result to judge the document; the reader's job
is to hand it over whole.

Empty and whitespace-only elements are read as absent, per UBL's own semantics —
and an optional aggregate left with no identifier at all (a supporting document,
a preceding invoice, a credit transfer, a payment card) is dropped rather than
taken to mean the whole document is unreadable.

What still raises is a missing mandatory element (``ValueError``) and the
checks that mirror rules ANAF itself enforces fatally — the closed ``BR-CL-*``
code lists, the format patterns, the ``BR-RO-L*`` length limits and the
``BR-DEC-*`` decimal budgets (a pydantic ``ValidationError``). Those cannot fire
on a document ANAF accepted; when one does, the mirrors have drifted from
ANAF's current edition — the tripwire ``DownloadedMessage.view`` documents. That
wrapper returns ``None`` instead of raising, keeping the raw bytes and the full
UBL model as the fallback tiers.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from ..models import parse_ubl_document
from ..ubl.common import ubl_common_aggregate_components_2_1 as cac
from ..ubl.maindoc.ubl_credit_note_2_1 import CreditNote
from ..ubl.maindoc.ubl_invoice_2_1 import Invoice
from .codes import DocumentKind
from .models import (
    _DERIVED_CONTEXT,
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
    PartyIdentifier,
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

__all__ = ["parse_invoice", "read_invoice"]

_NOTE_PREFIX = re.compile(r"^#([0-9A-Z]{3})#(.*)$", re.S)


def _read[M: BaseModel](model: type[M], **fields: Any) -> M:
    """Build one flat model from wire-derived fields, under the reader's context.

    Every construction in this module goes through here — a plain ``Model(...)``
    call would re-apply the authoring checks and lose the document.
    """
    return model.model_validate(fields, context=_DERIVED_CONTEXT)


def parse_invoice(xml: bytes) -> InvoiceDocument:
    """Parse e-Factura wire XML straight into an :class:`InvoiceDocument`.

    Raises:
        ValueError: when the bytes are not a parseable UBL invoice/credit note,
            or when a mandatory element is missing from one that is.
        pydantic.ValidationError: when a value fails one of the ANAF-certain
            mirrors that stay fatal on read (code lists, format patterns,
            length limits, decimal budgets — see the module docstring).
    """
    document = parse_ubl_document(xml)
    if document is None:
        raise ValueError("the bytes are not a parseable UBL Invoice or CreditNote")
    return read_invoice(document)


def read_invoice(doc: Invoice | CreditNote) -> InvoiceDocument:
    """Translate a generated UBL model into the flat :class:`InvoiceDocument`.

    Wire totals, line net amounts and the VAT breakdown land in the explicit
    fields (never recomputed); :func:`~.rules.validate` afterwards tells whether
    the source document's arithmetic holds up.
    """
    is_invoice = isinstance(doc, Invoice)
    currency = _require(_val(doc.document_currency_code), "DocumentCurrencyCode")
    tax_currency = _val(doc.tax_currency_code)
    period = _first(doc.invoice_period)
    payment_means = list(doc.payment_means)

    invoiced_object, project_from_refs, supporting = _split_references(
        doc.additional_document_reference
    )
    if isinstance(doc, Invoice):
        due_date = _date(doc.due_date)
        type_code = _val(doc.invoice_type_code)
        project = _first(doc.project_reference)
        project_reference = _val(project.id) if project else None
        lines_src: list[Any] = list(doc.invoice_line)
    else:
        due_date = _date(payment_means[0].payment_due_date) if payment_means else None
        type_code = _val(doc.credit_note_type_code)
        project_reference = project_from_refs
        lines_src = list(doc.credit_note_line)

    supplier = _require(
        getattr(doc.accounting_supplier_party, "party", None),
        "AccountingSupplierParty/Party",
    )
    customer = _require(
        getattr(doc.accounting_customer_party, "party", None),
        "AccountingCustomerParty/Party",
    )

    instructions, creditor_hosted_by_seller = _payment_instructions(
        doc, payment_means, is_invoice=is_invoice
    )

    allowances: list[DocumentAllowance] = []
    charges: list[DocumentCharge] = []
    for item in doc.allowance_charge:
        category = _first(item.tax_category)
        base: dict[str, Any] = _allowance_charge_fields(item)
        base["vat_category"] = _require(
            _val(category.id) if category else None, "AllowanceCharge/TaxCategory"
        )
        base["vat_rate"] = _val(category.percent) if category else None
        if _val(item.charge_indicator):
            charges.append(_read(DocumentCharge, **base))
        else:
            allowances.append(_read(DocumentAllowance, **base))

    return _read(
        InvoiceDocument,
        kind=DocumentKind.INVOICE if is_invoice else DocumentKind.CREDIT_NOTE,
        number=_require(_val(doc.id), "ID"),
        issue_date=_require(_date(doc.issue_date), "IssueDate"),
        type_code=type_code,
        currency=currency,
        tax_currency=tax_currency,
        vat_point_date=_date(doc.tax_point_date),
        vat_point_date_code=(_val(_first(period.description_code)) if period else None),
        due_date=due_date,
        buyer_reference=_val(doc.buyer_reference),
        project_reference=project_reference,
        contract_reference=_ref_id(_first(doc.contract_document_reference)),
        order_reference=_val(doc.order_reference.id) if doc.order_reference else None,
        sales_order_reference=(
            _val(doc.order_reference.sales_order_id) if doc.order_reference else None
        ),
        receiving_advice_reference=_ref_id(_first(doc.receipt_document_reference)),
        despatch_advice_reference=_ref_id(_first(doc.despatch_document_reference)),
        tender_or_lot_reference=_ref_id(_first(doc.originator_document_reference)),
        invoiced_object_id=invoiced_object[0],
        invoiced_object_scheme=invoiced_object[1],
        accounting_reference=_val(doc.accounting_cost),
        payment_terms=(
            _val(_first(_first(doc.payment_terms).note))
            if _first(doc.payment_terms)
            else None
        ),
        notes=[_note(text) for note in doc.note if (text := _val(note))],
        invoicing_period=(
            _read(Period, start=_date(period.start_date), end=_date(period.end_date))
            if period and (period.start_date or period.end_date)
            else None
        ),
        preceding_invoices=[
            _read(
                PrecedingInvoice,
                number=number,
                issue_date=_date(ref.invoice_document_reference.issue_date),
            )
            for ref in doc.billing_reference
            if ref.invoice_document_reference is not None
            and (number := _val(ref.invoice_document_reference.id)) is not None
        ],
        seller=_seller(supplier, drop_sepa=creditor_hosted_by_seller),
        buyer=_party(customer, Party),
        payee=_payee(doc.payee_party),
        tax_representative=_tax_representative(doc.tax_representative_party),
        delivery=_delivery(_first(doc.delivery)),
        payment_instructions=instructions,
        allowances=allowances,
        charges=charges,
        supporting_documents=supporting,
        lines=[_line(line, invoice=is_invoice) for line in lines_src],
        vat_breakdown=_vat_breakdown(doc, currency),
        totals=_totals(doc, currency, tax_currency),
    )


# --- helpers ------------------------------------------------------------------


def _text(value: Any) -> Any:
    """UBL semantics: an empty or whitespace-only element carries no value.

    The flat models reject the zero-length string a bare ``<cbc:PostalZone/>``
    parses to; treating it as absent is what the syntax already means, and issuers
    do emit empty optional elements on documents ANAF accepted.
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _val(obj: Any) -> Any:
    return None if obj is None else _text(obj.value)


def _first(seq: Any) -> Any:
    return seq[0] if seq else None


def _date(obj: Any) -> dt.date | None:
    value = _val(obj)
    return None if value is None else value.to_date()


def _require(value: Any, what: str) -> Any:
    if value is None:
        raise ValueError(f"the UBL document carries no {what}")
    return value


def _ref_id(reference: Any) -> str | None:
    return _val(reference.id) if reference is not None else None


def _id_and_scheme(obj: Any) -> tuple[str | None, str | None]:
    """An identifier with its ``schemeID``, both ``None`` when it is absent — a
    scheme attribute on an empty element qualifies nothing."""
    if obj is None or (value := _val(obj)) is None:
        return None, None
    return value, _text(obj.scheme_id)


def _note(text: str) -> Note:
    if match := _NOTE_PREFIX.match(text):
        return _read(Note, text=match.group(2), subject_code=match.group(1))
    return _read(Note, text=text)


def _split_references(
    references: list[cac.AdditionalDocumentReference],
) -> tuple[tuple[str | None, str | None], str | None, list[SupportingDocument]]:
    """Partition AdditionalDocumentReference by type code: 130 = invoiced object
    (BT-18), 50 = project reference on a credit note (BT-11), rest = BG-24."""
    invoiced_object: tuple[str | None, str | None] = (None, None)
    project: str | None = None
    supporting: list[SupportingDocument] = []
    for reference in references:
        type_code = _val(reference.document_type_code)
        if type_code == "130" and invoiced_object == (None, None):
            invoiced_object = _id_and_scheme(reference.id)
            continue
        if type_code == "50" and project is None:
            project = _val(reference.id)
            continue
        if (reference_id := _val(reference.id)) is None:
            # An optional aggregate with no identifier carries nothing the flat
            # model could hold; dropping it beats dropping the whole document.
            continue
        attachment = reference.attachment
        binary = attachment.embedded_document_binary_object if attachment else None
        external = attachment.external_reference if attachment else None
        supporting.append(
            _read(
                SupportingDocument,
                reference=reference_id,
                description=_val(_first(reference.document_description)),
                url=_val(external.uri) if external else None,
                content=binary.value if binary else None,
                mime_code=_text(binary.mime_code) if binary else None,
                filename=_text(binary.filename) if binary else None,
            )
        )
    return invoiced_object, project, supporting


def _address(address: Any) -> PostalAddress:
    line = _first(address.address_line)
    return _read(
        PostalAddress,
        street=_require(_val(address.street_name), "StreetName"),
        additional_street=_val(address.additional_street_name),
        address_line=_val(line.line) if line else None,
        city=_require(_val(address.city_name), "CityName"),
        postal_zone=_val(address.postal_zone),
        county=_val(address.country_subentity),
        country=_require(
            _val(address.country.identification_code if address.country else None),
            "Country/IdentificationCode",
        ),
    )


def _contact(contact: Any) -> Contact | None:
    if contact is None:
        return None
    fields = {
        "name": _val(contact.name),
        "telephone": _val(contact.telephone),
        "email": _val(contact.electronic_mail),
    }
    if not any(fields.values()):
        return None
    return _read(Contact, **fields)


def _party_fields(party: Any, *, drop_sepa: bool = False) -> dict[str, Any]:
    legal = _first(party.party_legal_entity)
    trading = _first(party.party_name)
    vat_id: str | None = None
    tax_registration: str | None = None
    tax_registration_scheme: str | None = None
    for scheme in party.party_tax_scheme:
        scheme_id = _val(scheme.tax_scheme.id) if scheme.tax_scheme else None
        if scheme_id is not None and scheme_id.upper() == "VAT":
            vat_id = _val(scheme.company_id)
        elif (company_id := _val(scheme.company_id)) is not None:
            # The seller's BT-32 and — CIUS-RO's own reading of the slot — the
            # bare CIF of a buyer not registered for VAT; the marker rides
            # along so a re-render reproduces the issuer's own.
            tax_registration = company_id
            tax_registration_scheme = scheme_id
    identifiers = []
    for identification in party.party_identification:
        id_ = identification.id
        if id_ is not None and drop_sepa and id_.scheme_id == "SEPA":
            continue  # BT-90 rides here; surfaced as DirectDebit.creditor_id
        match _id_and_scheme(id_):
            case (None, _):
                continue
            case (value, scheme):
                identifiers.append(_read(PartyIdentifier, id=value, scheme=scheme))
    legal_registration = _id_and_scheme(legal.company_id if legal else None)
    endpoint = party.endpoint_id
    return {
        "name": _require(
            _val(legal.registration_name) if legal else None,
            "PartyLegalEntity/RegistrationName",
        ),
        "trading_name": _val(trading.name) if trading else None,
        "identifiers": identifiers,
        "legal_registration_id": legal_registration[0],
        "legal_registration_scheme": legal_registration[1],
        "vat_id": vat_id,
        "electronic_address": (
            _read(ElectronicAddress, address=endpoint.value, scheme=endpoint.scheme_id)
            if endpoint is not None and endpoint.value and endpoint.scheme_id
            else None
        ),
        "address": _address(_require(party.postal_address, "Party/PostalAddress")),
        "contact": _contact(party.contact),
        "tax_registration_id": tax_registration,
        "tax_registration_scheme": tax_registration_scheme,
        "_legal_form": _val(legal.company_legal_form) if legal else None,
    }


def _party(party: Any, cls: type[Party]) -> Party:
    fields = _party_fields(party)
    fields.pop("_legal_form")  # BT-33 is seller-only (UBL-CR-244)
    return _read(cls, **fields)


def _seller(party: Any, *, drop_sepa: bool) -> Seller:
    fields = _party_fields(party, drop_sepa=drop_sepa)
    fields["additional_legal_info"] = fields.pop("_legal_form")
    return _read(Seller, **fields)


def _payee(payee: Any) -> Payee | None:
    if payee is None:
        return None
    name_obj = _first(payee.party_name)
    legal = _first(payee.party_legal_entity)
    identifier = None
    for identification in payee.party_identification:
        id_ = identification.id
        if id_ is None or id_.scheme_id == "SEPA":
            continue  # the SEPA one is BT-90, read by _payment_instructions
        match _id_and_scheme(id_):
            case (None, _):
                continue
            case (value, scheme):
                identifier = _read(PartyIdentifier, id=value, scheme=scheme)
                break
    legal_registration = _id_and_scheme(legal.company_id if legal else None)
    return _read(
        Payee,
        name=_require(_val(name_obj.name) if name_obj else None, "Payee name"),
        identifier=identifier,
        legal_registration_id=legal_registration[0],
        legal_registration_scheme=legal_registration[1],
    )


def _tax_representative(party: Any) -> TaxRepresentative | None:
    if party is None:
        return None
    name_obj = _first(party.party_name)
    scheme = _first(party.party_tax_scheme)
    return _read(
        TaxRepresentative,
        name=_require(
            _val(name_obj.name) if name_obj else None, "TaxRepresentative name"
        ),
        vat_id=_require(_val(scheme.company_id) if scheme else None, "BT-63"),
        address=_address(_require(party.postal_address, "BG-12")),
    )


def _delivery(delivery: Any) -> DeliveryInformation | None:
    if delivery is None:
        return None
    location = delivery.delivery_location
    delivery_party = delivery.delivery_party
    name_obj = _first(delivery_party.party_name) if delivery_party else None
    location_id, location_scheme = _id_and_scheme(location.id if location else None)
    return _read(
        DeliveryInformation,
        recipient_name=_val(name_obj.name) if name_obj else None,
        location_id=location_id,
        location_scheme=location_scheme,
        date=_date(delivery.actual_delivery_date),
        address=(
            _address(location.address)
            if location is not None and location.address is not None
            else None
        ),
    )


def _payment_instructions(
    doc: Invoice | CreditNote, payment_means: list[Any], *, is_invoice: bool
) -> tuple[PaymentInstructions | None, bool]:
    """Fold the PaymentMeans list back into BG-16.

    Returns the instructions plus whether the SEPA creditor id (BT-90) rides the
    *seller's* party identification (payee absent), so the seller reader can
    exclude it from the plain identifiers.
    """
    if not payment_means:
        return None, False
    first = payment_means[0]
    means_code = _val(first.payment_means_code)
    transfers = []
    for means in payment_means:
        account = means.payee_financial_account
        if account is None or (account_id := _val(account.id)) is None:
            continue
        branch = account.financial_institution_branch
        transfers.append(
            _read(
                CreditTransfer,
                account_id=account_id,
                account_name=_val(account.name),
                service_provider_id=_val(branch.id) if branch else None,
            )
        )
    card = first.card_account
    mandate = first.payment_mandate
    creditor_id = _sepa_identifier(doc.payee_party) or _sepa_identifier(
        getattr(doc.accounting_supplier_party, "party", None)
    )
    direct_debit = None
    if mandate is not None or creditor_id:
        payer = mandate.payer_financial_account if mandate else None
        direct_debit = _read(
            DirectDebit,
            mandate_reference=_val(mandate.id) if mandate else None,
            creditor_id=creditor_id,
            debited_account_id=_val(payer.id) if payer else None,
        )
    means_text = (
        _text(first.payment_means_code.name)
        if first.payment_means_code is not None
        else None
    )
    bare_due_date_carrier = (
        not is_invoice
        and len(payment_means) == 1
        and means_code == "1"
        and not transfers
        and card is None
        and direct_debit is None
        and means_text is None
        and not first.payment_id
    )
    if bare_due_date_carrier:
        # The build-side carrier for a credit note's due date, not real BG-16.
        return None, False
    instructions = _read(
        PaymentInstructions,
        means_code=_require(means_code, "BT-81"),
        means_text=means_text,
        remittance_information=_val(_first(first.payment_id)),
        credit_transfers=transfers,
        card=(
            _read(
                PaymentCard,
                number=card_number,
                holder_name=_val(card.holder_name),
            )
            if card is not None
            and (card_number := _val(card.primary_account_number_id)) is not None
            else None
        ),
        direct_debit=direct_debit,
    )
    seller_hosts_creditor = bool(creditor_id) and doc.payee_party is None
    return instructions, seller_hosts_creditor


def _sepa_identifier(party: Any) -> str | None:
    if party is None:
        return None
    for identification in party.party_identification:
        id_ = identification.id
        if id_ is not None and id_.scheme_id == "SEPA":
            return str(id_.value)
    return None


def _allowance_charge_fields(item: Any) -> dict[str, Any]:
    return {
        "amount": _require(_val(item.amount), "AllowanceCharge/Amount"),
        "base_amount": _val(item.base_amount),
        "percentage": _val(item.multiplier_factor_numeric),
        "reason": _val(_first(item.allowance_charge_reason)),
        "reason_code": _val(item.allowance_charge_reason_code),
    }


def _line(line: Any, *, invoice: bool) -> InvoiceLine:
    quantity = line.invoiced_quantity if invoice else line.credited_quantity
    quantity = _require(quantity, "BT-129 quantity")
    item = _require(line.item, "Item")
    tax_category = _first(item.classified_tax_category)
    price = line.price
    period = _first(line.invoice_period)
    order_ref = _first(line.order_line_reference)
    object_ref = next(
        (
            ref
            for ref in line.document_reference
            if _val(ref.document_type_code) == "130"
        ),
        None,
    )
    standard = item.standard_item_identification
    sellers = item.sellers_item_identification
    buyers = item.buyers_item_identification

    allowances: list[LineAllowance] = []
    charges: list[LineCharge] = []
    for entry in line.allowance_charge:
        fields = _allowance_charge_fields(entry)
        if _val(entry.charge_indicator):
            charges.append(_read(LineCharge, **fields))
        else:
            allowances.append(_read(LineAllowance, **fields))

    gross_price: Decimal | None = None
    price_discount: Decimal | None = None
    if price is not None and (price_allowance := _first(price.allowance_charge)):
        price_discount = _val(price_allowance.amount)
        gross_price = _val(price_allowance.base_amount)

    object_id, object_id_scheme = _id_and_scheme(object_ref.id if object_ref else None)
    standard_item_id, standard_item_scheme = _id_and_scheme(
        standard.id if standard else None
    )
    return _read(
        InvoiceLine,
        id=_val(line.id),
        note=_val(_first(line.note)),
        object_id=object_id,
        object_id_scheme=object_id_scheme,
        quantity=_require(quantity.value, "quantity"),
        unit=_require(_text(quantity.unit_code), "BT-130 unit code"),
        net_amount=_require(_val(line.line_extension_amount), "BT-131"),
        order_line_reference=_val(order_ref.line_id) if order_ref else None,
        accounting_reference=_val(line.accounting_cost),
        period=(
            _read(Period, start=_date(period.start_date), end=_date(period.end_date))
            if period and (period.start_date or period.end_date)
            else None
        ),
        allowances=allowances,
        charges=charges,
        unit_price=_require(
            _val(price.price_amount) if price else None, "BT-146 price"
        ),
        price_base_quantity=_val(price.base_quantity) if price else None,
        price_base_unit=(
            _text(price.base_quantity.unit_code)
            if price is not None and price.base_quantity is not None
            else None
        ),
        gross_price=gross_price,
        price_discount=price_discount,
        vat_category=_require(
            _val(tax_category.id) if tax_category else None, "BT-151"
        ),
        vat_rate=_val(tax_category.percent) if tax_category else None,
        name=_require(_val(item.name), "BT-153 item name"),
        description=_val(_first(item.description)),
        sellers_item_id=_val(sellers.id) if sellers else None,
        buyers_item_id=_val(buyers.id) if buyers else None,
        standard_item_id=standard_item_id,
        standard_item_scheme=standard_item_scheme,
        classifications=[
            _read(
                ItemClassification,
                code=code.value,
                scheme=_text(code.list_id),
                scheme_version=_text(code.list_version_id),
            )
            for classification in item.commodity_classification
            if (code := classification.item_classification_code) is not None
            and _text(code.value) is not None
        ],
        origin_country=(
            _val(item.origin_country.identification_code)
            if item.origin_country
            else None
        ),
        attributes=[
            _read(ItemAttribute, name=_val(prop.name), value=_val(prop.value))
            for prop in item.additional_item_property
        ],
    )


def _vat_breakdown(doc: Invoice | CreditNote, currency: str) -> list[VatBreakdownEntry]:
    entries = []
    for total in doc.tax_total:
        for subtotal in total.tax_subtotal:
            category = _require(subtotal.tax_category, "TaxSubtotal/TaxCategory")
            entries.append(
                _read(
                    VatBreakdownEntry,
                    category=_require(_val(category.id), "BT-118"),
                    rate=_val(category.percent),
                    taxable_amount=_val(subtotal.taxable_amount),
                    tax_amount=_val(subtotal.tax_amount),
                    exemption_reason_code=_val(category.tax_exemption_reason_code),
                    exemption_reason=_val(_first(category.tax_exemption_reason)),
                )
            )
    return entries


def _totals(
    doc: Invoice | CreditNote, currency: str, tax_currency: str | None
) -> Totals:
    monetary = _require(doc.legal_monetary_total, "LegalMonetaryTotal")
    vat_total: Decimal | None = None
    vat_total_tax_currency: Decimal | None = None
    for total in doc.tax_total:
        amount = total.tax_amount
        if amount is None:
            continue
        # Not exclusive: issuers do set BT-6 equal to BT-5, and then the single
        # TaxTotal is both BT-110 and BT-111 (BR-53 asks only that a TaxAmount
        # in the accounting currency exists). Reading it as BT-110 alone made
        # `validate` report a spurious fatal BR-53 on documents ANAF accepted.
        if amount.currency_id == currency:
            vat_total = amount.value
        if tax_currency and amount.currency_id == tax_currency:
            vat_total_tax_currency = amount.value
    return _read(
        Totals,
        lines_total=_val(monetary.line_extension_amount),
        allowance_total=_val(monetary.allowance_total_amount),
        charge_total=_val(monetary.charge_total_amount),
        tax_exclusive=_val(monetary.tax_exclusive_amount),
        vat_total=vat_total,
        vat_total_tax_currency=vat_total_tax_currency,
        tax_inclusive=_val(monetary.tax_inclusive_amount),
        prepaid=_val(monetary.prepaid_amount),
        rounding=_val(monetary.payable_rounding_amount),
        payable=_val(monetary.payable_amount),
    )
