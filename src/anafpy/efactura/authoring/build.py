"""Compose a flat :class:`~.models.InvoiceDocument` into UBL wire XML.

:func:`build_invoice` produces the generated UBL model (``Invoice`` or
``CreditNote`` per the document's :attr:`~.models.InvoiceDocument.kind`);
:func:`render_invoice` serializes it to upload-ready bytes, running
:func:`~.rules.validate` first unless explicitly skipped.

Syntax-mapping notes (the EN 16931 UBL binding's quirks, mirrored by
:mod:`.read`):

- BT-21/22 ride one ``cbc:Note`` as ``#SUBJECTCODE#text``.
- BT-8 (VAT point date code) rides ``cac:InvoicePeriod/cbc:DescriptionCode``.
- BT-32 (seller tax registration) is a second ``cac:PartyTaxScheme`` whose
  ``TaxScheme/ID`` is not ``VAT`` (rendered as ``FC``).
- BT-90 (bank-assigned creditor id) is a ``cac:PartyIdentification`` with
  ``schemeID="SEPA"`` on the payee (or the seller when there is no payee).
- On a credit note, BT-9 (due date) rides ``cac:PaymentMeans`` and BT-11
  (project reference) an ``AdditionalDocumentReference`` with type code 50.
- UBL requires ``cac:CardAccount/cbc:NetworkID``, which EN 16931 does not
  model; it is rendered as ``ZZZ`` and dropped on read.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Literal, overload

from xsdata.models.datatype import XmlDate

from ..ubl.common import ubl_common_aggregate_components_2_1 as cac
from ..ubl.common import ubl_common_basic_components_2_1 as cbc
from ..ubl.maindoc.ubl_credit_note_2_1 import CreditNote
from ..ubl.maindoc.ubl_invoice_2_1 import Invoice
from .codes import CIUS_RO_CUSTOMIZATION_ID, DocumentKind, VatCategory
from .models import (
    DeliveryInformation,
    InvoiceDocument,
    InvoiceLine,
    Note,
    Party,
    PostalAddress,
    Seller,
    Totals,
    VatBreakdownEntry,
    _AllowanceChargeBase,
    _DocumentAllowanceChargeBase,
    round2,
)
from .rules import InvoiceValidationError, validate

__all__ = ["build_invoice", "render_invoice"]

#: TaxScheme/ID marking the seller tax registration identifier (BT-32); any
#: non-``VAT`` value distinguishes it, ``FC`` is the CEN examples' convention.
_FISCAL_SCHEME = "FC"
VAT = "VAT"


def render_invoice(
    document: InvoiceDocument, *, skip_validation: bool = False
) -> bytes:
    """Compose and serialize a document to upload-ready UTF-8 XML bytes.

    Runs :func:`~.rules.validate` first and raises
    :class:`~.rules.InvoiceValidationError` on fatal findings; pass
    ``skip_validation=True`` to render regardless (e.g. to reproduce a faulty
    upstream document byte-for-byte for ANAF's own validator to judge).
    """
    from xsdata_pydantic.bindings import XmlSerializer

    if not skip_validation:
        report = validate(document)
        if not report.ok:
            raise InvoiceValidationError(report)
    model = build_invoice(document)
    return XmlSerializer().render(model).encode("utf-8")


def build_invoice(document: InvoiceDocument) -> Invoice | CreditNote:
    """Compose the flat document into its generated UBL model.

    Pure translation — no validation, no defaulting beyond what the flat model
    already computed (line ids, totals, VAT breakdown).
    """
    doc = document
    currency = doc.currency
    is_invoice = doc.kind is DocumentKind.INVOICE
    totals = doc.effective_totals()
    breakdown = doc.effective_vat_breakdown()

    common: dict[str, Any] = {
        "customization_id": cbc.CustomizationId(value=CIUS_RO_CUSTOMIZATION_ID),
        "id": cbc.Id(value=doc.number),
        "issue_date": cbc.IssueDate(value=_xml_date(doc.issue_date)),
        "note": [cbc.Note(value=_note_text(note)) for note in doc.notes],
        "tax_point_date": (
            cbc.TaxPointDate(value=_xml_date(doc.vat_point_date))
            if doc.vat_point_date
            else None
        ),
        "document_currency_code": cbc.DocumentCurrencyCode(value=currency),
        "tax_currency_code": (
            cbc.TaxCurrencyCode(value=doc.tax_currency) if doc.tax_currency else None
        ),
        "accounting_cost": (
            cbc.AccountingCost(value=doc.accounting_reference)
            if doc.accounting_reference
            else None
        ),
        "buyer_reference": (
            cbc.BuyerReference(value=doc.buyer_reference)
            if doc.buyer_reference
            else None
        ),
        "invoice_period": _invoice_period(doc),
        "order_reference": (
            cac.OrderReference(
                id=cbc.Id(value=doc.order_reference),
                sales_order_id=(
                    cbc.SalesOrderId(value=doc.sales_order_reference)
                    if doc.sales_order_reference
                    else None
                ),
            )
            if doc.order_reference
            else None
        ),
        "billing_reference": [
            cac.BillingReference(
                invoice_document_reference=cac.InvoiceDocumentReference(
                    id=cbc.Id(value=ref.number),
                    issue_date=(
                        cbc.IssueDate(value=_xml_date(ref.issue_date))
                        if ref.issue_date
                        else None
                    ),
                )
            )
            for ref in doc.preceding_invoices
        ],
        "despatch_document_reference": _doc_reference(
            cac.DespatchDocumentReference, doc.despatch_advice_reference
        ),
        "receipt_document_reference": _doc_reference(
            cac.ReceiptDocumentReference, doc.receiving_advice_reference
        ),
        "originator_document_reference": _doc_reference(
            cac.OriginatorDocumentReference, doc.tender_or_lot_reference
        ),
        "contract_document_reference": _doc_reference(
            cac.ContractDocumentReference, doc.contract_reference
        ),
        "additional_document_reference": _additional_references(doc, is_invoice),
        "accounting_supplier_party": cac.AccountingSupplierParty(
            party=_party(doc.seller, sepa_creditor=_seller_sepa_creditor(doc))
        ),
        "accounting_customer_party": cac.AccountingCustomerParty(
            party=_party(doc.buyer)
        ),
        "payee_party": _payee(doc),
        "tax_representative_party": _tax_representative(doc),
        "delivery": _delivery(doc.delivery),
        "payment_means": _payment_means(doc),
        "payment_terms": (
            [cac.PaymentTerms(note=[cbc.Note(value=doc.payment_terms)])]
            if doc.payment_terms
            else []
        ),
        "allowance_charge": [
            _document_allowance_charge(item, charge=False, currency=currency)
            for item in doc.allowances
        ]
        + [
            _document_allowance_charge(item, charge=True, currency=currency)
            for item in doc.charges
        ],
        "tax_total": _tax_totals(doc, totals, breakdown),
        "legal_monetary_total": _monetary_total(totals, currency),
    }

    if is_invoice:
        return Invoice(
            **common,
            due_date=(
                cbc.DueDate(value=_xml_date(doc.due_date)) if doc.due_date else None
            ),
            invoice_type_code=cbc.InvoiceTypeCode(value=str(doc.type_code)),
            project_reference=(
                [cac.ProjectReference(id=cbc.Id(value=doc.project_reference))]
                if doc.project_reference
                else []
            ),
            invoice_line=[
                _line(line, index, currency, invoice=True)
                for index, line in enumerate(doc.lines, start=1)
            ],
        )
    return CreditNote(
        **common,
        credit_note_type_code=cbc.CreditNoteTypeCode(value=str(doc.type_code)),
        credit_note_line=[
            _line(line, index, currency, invoice=False)
            for index, line in enumerate(doc.lines, start=1)
        ],
    )


# --- helpers ------------------------------------------------------------------


def _xml_date(value: dt.date) -> XmlDate:
    return XmlDate(value.year, value.month, value.day)


def _money(value: Decimal, currency: str) -> dict[str, Any]:
    return {"value": round2(value), "currency_id": currency}


def _note_text(note: Note) -> str:
    if note.subject_code:
        return f"#{note.subject_code}#{note.text}"
    return note.text


def _doc_reference(cls: type[Any], reference: str | None) -> list[Any]:
    return [cls(id=cbc.Id(value=reference))] if reference else []


def _invoice_period(doc: InvoiceDocument) -> list[cac.InvoicePeriod]:
    period = doc.invoicing_period
    if period is None and doc.vat_point_date_code is None:
        return []
    return [
        cac.InvoicePeriod(
            start_date=(
                cbc.StartDate(value=_xml_date(period.start))
                if period and period.start
                else None
            ),
            end_date=(
                cbc.EndDate(value=_xml_date(period.end))
                if period and period.end
                else None
            ),
            description_code=(
                [cbc.DescriptionCode(value=str(doc.vat_point_date_code))]
                if doc.vat_point_date_code
                else []
            ),
        )
    ]


def _additional_references(
    doc: InvoiceDocument, is_invoice: bool
) -> list[cac.AdditionalDocumentReference]:
    references = []
    if doc.invoiced_object_id:
        references.append(
            cac.AdditionalDocumentReference(
                id=cbc.Id(
                    value=doc.invoiced_object_id,
                    scheme_id=doc.invoiced_object_scheme,
                ),
                document_type_code=cbc.DocumentTypeCode(value="130"),
            )
        )
    if not is_invoice and doc.project_reference:
        references.append(
            cac.AdditionalDocumentReference(
                id=cbc.Id(value=doc.project_reference),
                document_type_code=cbc.DocumentTypeCode(value="50"),
            )
        )
    for item in doc.supporting_documents:
        attachment = None
        if item.url or item.content is not None:
            attachment = cac.Attachment(
                embedded_document_binary_object=(
                    cbc.EmbeddedDocumentBinaryObject(
                        value=item.content,
                        mime_code=item.mime_code,
                        filename=item.filename,
                    )
                    # mime_code is model-guaranteed alongside content; the check
                    # here narrows the Optional for the schema-required attr.
                    if item.content is not None and item.mime_code is not None
                    else None
                ),
                external_reference=(
                    cac.ExternalReference(uri=cbc.Uri(value=item.url))
                    if item.url
                    else None
                ),
            )
        references.append(
            cac.AdditionalDocumentReference(
                id=cbc.Id(value=item.reference),
                document_description=(
                    [cbc.DocumentDescription(value=item.description)]
                    if item.description
                    else []
                ),
                attachment=attachment,
            )
        )
    return references


def _address(address: PostalAddress, cls: type[Any] = cac.PostalAddress) -> Any:
    # cac.PostalAddress and cac.Address (the delivery location's type) share the
    # same field surface; ``cls`` picks the element.
    return cls(
        street_name=cbc.StreetName(value=address.street),
        additional_street_name=(
            cbc.AdditionalStreetName(value=address.additional_street)
            if address.additional_street
            else None
        ),
        address_line=(
            [cac.AddressLine(line=cbc.Line(value=address.address_line))]
            if address.address_line
            else []
        ),
        city_name=cbc.CityName(value=address.city),
        postal_zone=(
            cbc.PostalZone(value=address.postal_zone) if address.postal_zone else None
        ),
        country_subentity=(
            cbc.CountrySubentity(value=address.county) if address.county else None
        ),
        country=cac.Country(
            identification_code=cbc.IdentificationCode(value=address.country)
        ),
    )


def _seller_sepa_creditor(doc: InvoiceDocument) -> str | None:
    """BT-90 rides the payee's SEPA-schemed identification, falling back to the
    seller's when the invoice has no payee."""
    instructions = doc.payment_instructions
    if instructions is None or instructions.direct_debit is None:
        return None
    if doc.payee is not None:
        return None
    return instructions.direct_debit.creditor_id


def _party(party: Party, *, sepa_creditor: str | None = None) -> cac.Party:
    tax_schemes = []
    if party.vat_id:
        tax_schemes.append(
            cac.PartyTaxScheme(
                company_id=cbc.CompanyId(value=party.vat_id),
                tax_scheme=cac.TaxScheme(id=cbc.Id(value=VAT)),
            )
        )
    if isinstance(party, Seller) and party.tax_registration_id:
        tax_schemes.append(
            cac.PartyTaxScheme(
                company_id=cbc.CompanyId(value=party.tax_registration_id),
                tax_scheme=cac.TaxScheme(id=cbc.Id(value=_FISCAL_SCHEME)),
            )
        )
    identifications = [
        cac.PartyIdentification(
            id=cbc.Id(value=identifier.id, scheme_id=identifier.scheme)
        )
        for identifier in party.identifiers
    ]
    if sepa_creditor:
        identifications.append(
            cac.PartyIdentification(id=cbc.Id(value=sepa_creditor, scheme_id="SEPA"))
        )
    legal_form = party.additional_legal_info if isinstance(party, Seller) else None
    return cac.Party(
        endpoint_id=(
            cbc.EndpointId(
                value=party.electronic_address.address,
                scheme_id=party.electronic_address.scheme,
            )
            if party.electronic_address
            else None
        ),
        party_identification=identifications,
        party_name=(
            [cac.PartyName(name=cbc.Name(value=party.trading_name))]
            if party.trading_name
            else []
        ),
        postal_address=_address(party.address),
        party_tax_scheme=tax_schemes,
        party_legal_entity=[
            cac.PartyLegalEntity(
                registration_name=cbc.RegistrationName(value=party.name),
                company_id=(
                    cbc.CompanyId(
                        value=party.legal_registration_id,
                        scheme_id=party.legal_registration_scheme,
                    )
                    if party.legal_registration_id
                    else None
                ),
                company_legal_form=(
                    cbc.CompanyLegalForm(value=legal_form) if legal_form else None
                ),
            )
        ],
        contact=(
            cac.Contact(
                name=(
                    cbc.Name(value=party.contact.name) if party.contact.name else None
                ),
                telephone=(
                    cbc.Telephone(value=party.contact.telephone)
                    if party.contact.telephone
                    else None
                ),
                electronic_mail=(
                    cbc.ElectronicMail(value=party.contact.email)
                    if party.contact.email
                    else None
                ),
            )
            if party.contact
            else None
        ),
    )


def _payee(doc: InvoiceDocument) -> cac.PayeeParty | None:
    payee = doc.payee
    if payee is None:
        return None
    instructions = doc.payment_instructions
    creditor = (
        instructions.direct_debit.creditor_id
        if instructions and instructions.direct_debit
        else None
    )
    identifications = []
    if payee.identifier:
        identifications.append(
            cac.PartyIdentification(
                id=cbc.Id(value=payee.identifier.id, scheme_id=payee.identifier.scheme)
            )
        )
    if creditor:
        identifications.append(
            cac.PartyIdentification(id=cbc.Id(value=creditor, scheme_id="SEPA"))
        )
    return cac.PayeeParty(
        party_identification=identifications,
        party_name=[cac.PartyName(name=cbc.Name(value=payee.name))],
        party_legal_entity=(
            [
                cac.PartyLegalEntity(
                    company_id=cbc.CompanyId(
                        value=payee.legal_registration_id,
                        scheme_id=payee.legal_registration_scheme,
                    )
                )
            ]
            if payee.legal_registration_id
            else []
        ),
    )


def _tax_representative(doc: InvoiceDocument) -> cac.TaxRepresentativeParty | None:
    representative = doc.tax_representative
    if representative is None:
        return None
    return cac.TaxRepresentativeParty(
        party_name=[cac.PartyName(name=cbc.Name(value=representative.name))],
        postal_address=_address(representative.address),
        party_tax_scheme=[
            cac.PartyTaxScheme(
                company_id=cbc.CompanyId(value=representative.vat_id),
                tax_scheme=cac.TaxScheme(id=cbc.Id(value=VAT)),
            )
        ],
    )


def _delivery(delivery: DeliveryInformation | None) -> list[cac.Delivery]:
    if delivery is None:
        return []
    return [
        cac.Delivery(
            actual_delivery_date=(
                cbc.ActualDeliveryDate(value=_xml_date(delivery.date))
                if delivery.date
                else None
            ),
            delivery_location=(
                cac.DeliveryLocation(
                    id=(
                        cbc.Id(
                            value=delivery.location_id,
                            scheme_id=delivery.location_scheme,
                        )
                        if delivery.location_id
                        else None
                    ),
                    address=(
                        _address(delivery.address, cac.Address)
                        if delivery.address
                        else None
                    ),
                )
                if delivery.location_id or delivery.address
                else None
            ),
            delivery_party=(
                cac.DeliveryParty(
                    party_name=[
                        cac.PartyName(name=cbc.Name(value=delivery.recipient_name))
                    ]
                )
                if delivery.recipient_name
                else None
            ),
        )
    ]


def _payment_means(doc: InvoiceDocument) -> list[cac.PaymentMeans]:
    instructions = doc.payment_instructions
    due_date = (
        cbc.PaymentDueDate(value=_xml_date(doc.due_date))
        if doc.kind is DocumentKind.CREDIT_NOTE and doc.due_date
        else None
    )
    if instructions is None:
        # A credit note's due date (BT-9) has no carrier but PaymentMeans, whose
        # means code is schema-mandatory (BR-49): 4461 code 1 = not defined.
        if due_date is not None:
            return [
                cac.PaymentMeans(
                    payment_means_code=cbc.PaymentMeansCode(value="1"),
                    payment_due_date=due_date,
                )
            ]
        return []
    accounts: list[cac.PayeeFinancialAccount | None] = [
        cac.PayeeFinancialAccount(
            id=cbc.Id(value=transfer.account_id),
            name=(
                cbc.Name(value=transfer.account_name) if transfer.account_name else None
            ),
            financial_institution_branch=(
                cac.FinancialInstitutionBranch(
                    id=cbc.Id(value=transfer.service_provider_id)
                )
                if transfer.service_provider_id
                else None
            ),
        )
        for transfer in instructions.credit_transfers
    ] or [None]

    means = []
    for index, account in enumerate(accounts):
        first = index == 0
        means.append(
            cac.PaymentMeans(
                payment_means_code=cbc.PaymentMeansCode(
                    value=instructions.means_code,
                    name=instructions.means_text if first else None,
                ),
                payment_due_date=due_date if first else None,
                payment_id=(
                    [cbc.PaymentId(value=instructions.remittance_information)]
                    if first and instructions.remittance_information
                    else []
                ),
                card_account=(
                    cac.CardAccount(
                        primary_account_number_id=cbc.PrimaryAccountNumberId(
                            value=instructions.card.number
                        ),
                        # UBL requires NetworkID; EN 16931 has no such term.
                        network_id=cbc.NetworkId(value="ZZZ"),
                        holder_name=(
                            cbc.HolderName(value=instructions.card.holder_name)
                            if instructions.card.holder_name
                            else None
                        ),
                    )
                    if first and instructions.card
                    else None
                ),
                payee_financial_account=account,
                payment_mandate=(
                    cac.PaymentMandate(
                        id=(
                            cbc.Id(value=instructions.direct_debit.mandate_reference)
                            if instructions.direct_debit.mandate_reference
                            else None
                        ),
                        payer_financial_account=(
                            cac.PayerFinancialAccount(
                                id=cbc.Id(
                                    value=instructions.direct_debit.debited_account_id
                                )
                            )
                            if instructions.direct_debit.debited_account_id
                            else None
                        ),
                    )
                    if first and instructions.direct_debit
                    else None
                ),
            )
        )
    return means


def _tax_category(
    category: VatCategory,
    rate: Decimal | None,
    *,
    cls: type[Any],
    exemption_code: str | None = None,
    exemption_reason: str | None = None,
) -> Any:
    return cls(
        id=cbc.Id(value=str(category)),
        percent=cbc.Percent(value=rate) if rate is not None else None,
        tax_exemption_reason_code=(
            cbc.TaxExemptionReasonCode(value=exemption_code) if exemption_code else None
        ),
        tax_exemption_reason=(
            [cbc.TaxExemptionReason(value=exemption_reason)] if exemption_reason else []
        ),
        tax_scheme=cac.TaxScheme(id=cbc.Id(value=VAT)),
    )


def _allowance_charge_fields(
    item: _AllowanceChargeBase, *, charge: bool, currency: str
) -> dict[str, Any]:
    return {
        "charge_indicator": cbc.ChargeIndicator(value=charge),
        "allowance_charge_reason_code": (
            cbc.AllowanceChargeReasonCode(value=item.reason_code)
            if item.reason_code
            else None
        ),
        "allowance_charge_reason": (
            [cbc.AllowanceChargeReason(value=item.reason)] if item.reason else []
        ),
        "multiplier_factor_numeric": (
            cbc.MultiplierFactorNumeric(value=item.percentage)
            if item.percentage is not None
            else None
        ),
        "amount": cbc.Amount(**_money(item.amount, currency)),
        "base_amount": (
            cbc.BaseAmount(**_money(item.base_amount, currency))
            if item.base_amount is not None
            else None
        ),
    }


def _document_allowance_charge(
    item: _DocumentAllowanceChargeBase, *, charge: bool, currency: str
) -> cac.AllowanceCharge:
    return cac.AllowanceCharge(
        **_allowance_charge_fields(item, charge=charge, currency=currency),
        tax_category=[
            _tax_category(item.vat_category, item.vat_rate, cls=cac.TaxCategory)
        ],
    )


def _tax_totals(
    doc: InvoiceDocument, totals: Totals, breakdown: list[VatBreakdownEntry]
) -> list[cac.TaxTotal]:
    vat_total = totals.vat_total or Decimal(0)
    tax_totals = [
        cac.TaxTotal(
            tax_amount=cbc.TaxAmount(**_money(vat_total, doc.currency)),
            tax_subtotal=[
                cac.TaxSubtotal(
                    taxable_amount=cbc.TaxableAmount(
                        **_money(entry.taxable_amount or Decimal(0), doc.currency)
                    ),
                    tax_amount=cbc.TaxAmount(
                        **_money(entry.tax_amount or Decimal(0), doc.currency)
                    ),
                    tax_category=_tax_category(
                        entry.category,
                        entry.rate,
                        cls=cac.TaxCategory,
                        exemption_code=entry.exemption_reason_code,
                        exemption_reason=entry.exemption_reason,
                    ),
                )
                for entry in breakdown
            ],
        )
    ]
    if (
        doc.tax_currency
        and doc.tax_currency != doc.currency
        and totals.vat_total_tax_currency is not None
    ):
        tax_totals.append(
            cac.TaxTotal(
                tax_amount=cbc.TaxAmount(
                    **_money(totals.vat_total_tax_currency, doc.tax_currency)
                )
            )
        )
    return tax_totals


def _monetary_total(totals: Totals, currency: str) -> cac.LegalMonetaryTotal:
    def amount(cls: type[Any], value: Decimal | None) -> Any:
        return cls(**_money(value, currency)) if value is not None else None

    return cac.LegalMonetaryTotal(
        line_extension_amount=amount(cbc.LineExtensionAmount, totals.lines_total),
        tax_exclusive_amount=amount(cbc.TaxExclusiveAmount, totals.tax_exclusive),
        tax_inclusive_amount=amount(cbc.TaxInclusiveAmount, totals.tax_inclusive),
        allowance_total_amount=amount(cbc.AllowanceTotalAmount, totals.allowance_total),
        charge_total_amount=amount(cbc.ChargeTotalAmount, totals.charge_total),
        prepaid_amount=amount(cbc.PrepaidAmount, totals.prepaid),
        payable_rounding_amount=amount(cbc.PayableRoundingAmount, totals.rounding),
        payable_amount=amount(cbc.PayableAmount, totals.payable),
    )


@overload
def _line(
    line: InvoiceLine, position: int, currency: str, *, invoice: Literal[True]
) -> cac.InvoiceLine: ...
@overload
def _line(
    line: InvoiceLine, position: int, currency: str, *, invoice: Literal[False]
) -> cac.CreditNoteLine: ...
def _line(
    line: InvoiceLine, position: int, currency: str, *, invoice: bool
) -> cac.InvoiceLine | cac.CreditNoteLine:
    price_allowance = []
    if line.gross_price is not None or line.price_discount is not None:
        discount = line.price_discount
        if discount is None and line.gross_price is not None:
            discount = line.gross_price - line.unit_price
        price_allowance.append(
            cac.AllowanceCharge(
                charge_indicator=cbc.ChargeIndicator(value=False),
                amount=cbc.Amount(**_money(discount or Decimal(0), currency)),
                base_amount=(
                    cbc.BaseAmount(**_money(line.gross_price, currency))
                    if line.gross_price is not None
                    else None
                ),
            )
        )
    fields: dict[str, Any] = {
        "id": cbc.Id(value=line.id or str(position)),
        "note": [cbc.Note(value=line.note)] if line.note else [],
        "line_extension_amount": cbc.LineExtensionAmount(
            **_money(line.effective_net_amount, currency)
        ),
        "accounting_cost": (
            cbc.AccountingCost(value=line.accounting_reference)
            if line.accounting_reference
            else None
        ),
        "invoice_period": (
            [
                cac.InvoicePeriod(
                    start_date=(
                        cbc.StartDate(value=_xml_date(line.period.start))
                        if line.period.start
                        else None
                    ),
                    end_date=(
                        cbc.EndDate(value=_xml_date(line.period.end))
                        if line.period.end
                        else None
                    ),
                )
            ]
            if line.period
            else []
        ),
        "order_line_reference": (
            [
                cac.OrderLineReference(
                    line_id=cbc.LineId(value=line.order_line_reference)
                )
            ]
            if line.order_line_reference
            else []
        ),
        "document_reference": (
            [
                cac.DocumentReference(
                    id=cbc.Id(value=line.object_id, scheme_id=line.object_id_scheme),
                    document_type_code=cbc.DocumentTypeCode(value="130"),
                )
            ]
            if line.object_id
            else []
        ),
        "allowance_charge": [
            cac.AllowanceCharge(
                **_allowance_charge_fields(item, charge=False, currency=currency)
            )
            for item in line.allowances
        ]
        + [
            cac.AllowanceCharge(
                **_allowance_charge_fields(item, charge=True, currency=currency)
            )
            for item in line.charges
        ],
        "item": cac.Item(
            description=(
                [cbc.Description(value=line.description)] if line.description else []
            ),
            name=cbc.Name(value=line.name),
            buyers_item_identification=(
                cac.BuyersItemIdentification(id=cbc.Id(value=line.buyers_item_id))
                if line.buyers_item_id
                else None
            ),
            sellers_item_identification=(
                cac.SellersItemIdentification(id=cbc.Id(value=line.sellers_item_id))
                if line.sellers_item_id
                else None
            ),
            standard_item_identification=(
                cac.StandardItemIdentification(
                    id=cbc.Id(
                        value=line.standard_item_id,
                        scheme_id=line.standard_item_scheme,
                    )
                )
                if line.standard_item_id
                else None
            ),
            origin_country=(
                cac.OriginCountry(
                    identification_code=cbc.IdentificationCode(
                        value=line.origin_country
                    )
                )
                if line.origin_country
                else None
            ),
            commodity_classification=[
                cac.CommodityClassification(
                    item_classification_code=cbc.ItemClassificationCode(
                        value=classification.code,
                        list_id=classification.scheme,
                        list_version_id=classification.scheme_version,
                    )
                )
                for classification in line.classifications
            ],
            classified_tax_category=[
                _tax_category(
                    line.vat_category, line.vat_rate, cls=cac.ClassifiedTaxCategory
                )
            ],
            additional_item_property=[
                cac.AdditionalItemProperty(
                    name=cbc.Name(value=attribute.name),
                    value=cbc.Value(value=attribute.value),
                )
                for attribute in line.attributes
            ],
        ),
        "price": cac.Price(
            price_amount=cbc.PriceAmount(value=line.unit_price, currency_id=currency),
            base_quantity=(
                cbc.BaseQuantity(
                    value=line.price_base_quantity,
                    unit_code=line.price_base_unit or line.unit,
                )
                if line.price_base_quantity is not None
                else None
            ),
            allowance_charge=price_allowance,
        ),
    }
    if invoice:
        return cac.InvoiceLine(
            invoiced_quantity=cbc.InvoicedQuantity(
                value=line.quantity, unit_code=line.unit
            ),
            **fields,
        )
    return cac.CreditNoteLine(
        credited_quantity=cbc.CreditedQuantity(
            value=line.quantity, unit_code=line.unit
        ),
        **fields,
    )
