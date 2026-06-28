"""Curated flat models ⇄ wire XML (``DESIGN.md`` §4, §7).

The only hand-written serialization piece in the package: turn a :class:`FlatInvoice`
into a CIUS-RO UBL :class:`Invoice` (computing all totals) and a :class:`FlatTransport`
into an e-Transport :class:`ETransport`, then render with ``xsdata-pydantic``. The XML
pass-through inputs are read and returned as-is (still parsed/validated downstream).

This covers the common case only. Anything richer (allowances, multiple payment means,
exotic tax handling) is authored as UBL XML upstream and passed through.
"""

from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlSerializer

from ..efactura.ubl.common import ubl_common_aggregate_components_2_1 as agg
from ..efactura.ubl.common import ubl_common_basic_components_2_1 as cbc
from ..efactura.ubl.maindoc import Invoice
from ..etransport.schema import schema_etr_v2_20230126 as etr
from ..exceptions import AnafConfigError
from .models import (
    CIUS_RO,
    EtransportXmlInput,
    FlatInvoice,
    FlatParty,
    FlatTransport,
    FlatTransportLocation,
    InvoiceInput,
    InvoicePreview,
    TransportInput,
    TransportPreview,
    UblXmlInput,
)

__all__ = [
    "build_invoice_xml",
    "build_transport_xml",
    "flat_invoice_to_ubl",
    "flat_transport_to_etransport",
    "invoice_preview",
    "transport_preview",
]

_VAT = "VAT"
_TWO_DP = Decimal("0.01")


def _q2(value: Decimal) -> Decimal:
    """Round to 2 decimals, half-up (the EN 16931 rounding rule for amounts)."""
    return value.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


# --- e-Factura: FlatInvoice -> UBL Invoice -----------------------------------------


def _party(p: FlatParty) -> agg.Party:
    legal_id = p.company_id or p.vat_id
    party = agg.Party(
        party_name=[agg.PartyName(name=cbc.Name(value=p.name))],
        postal_address=agg.PostalAddress(
            street_name=cbc.StreetName(value=p.address),
            city_name=cbc.CityName(value=p.city),
            postal_zone=cbc.PostalZone(value=p.postal_zone) if p.postal_zone else None,
            country_subentity=(
                cbc.CountrySubentity(value=p.county) if p.county else None
            ),
            country=agg.Country(
                identification_code=cbc.IdentificationCode(value=p.country)
            ),
        ),
        party_legal_entity=[
            agg.PartyLegalEntity(
                registration_name=cbc.RegistrationName(value=p.name),
                company_id=cbc.CompanyId(value=legal_id) if legal_id else None,
            )
        ],
    )
    if p.vat_id:
        party.endpoint_id = cbc.EndpointId(value=p.vat_id, scheme_id="9959")
        party.party_tax_scheme = [
            agg.PartyTaxScheme(
                company_id=cbc.CompanyId(value=p.vat_id),
                tax_scheme=agg.TaxScheme(id=cbc.Id(value=_VAT)),
            )
        ]
    return party


def flat_invoice_to_ubl(inv: FlatInvoice) -> Invoice:
    """Build a CIUS-RO UBL :class:`Invoice` from a :class:`FlatInvoice`.

    All monetary totals — line extension amounts, VAT subtotals grouped by category and
    rate, and the legal monetary total — are computed here from the line inputs.
    """
    currency = inv.currency

    lines: list[agg.InvoiceLine] = []
    # Group taxable base + tax per (category, rate) for the document-level TaxTotal.
    by_cat: OrderedDict[tuple[str, Decimal], list[Decimal]] = OrderedDict()
    line_total = Decimal(0)

    for index, line in enumerate(inv.lines, start=1):
        net = _q2(line.quantity * line.unit_price)
        line_total += net
        key = (line.vat_category, line.vat_rate)
        by_cat.setdefault(key, []).append(net)
        tax_category = agg.ClassifiedTaxCategory(
            id=cbc.Id(value=line.vat_category),
            percent=cbc.Percent(value=line.vat_rate),
            tax_scheme=agg.TaxScheme(id=cbc.Id(value=_VAT)),
        )
        lines.append(
            agg.InvoiceLine(
                id=cbc.Id(value=str(index)),
                invoiced_quantity=cbc.InvoicedQuantity(
                    value=line.quantity, unit_code=line.unit_code
                ),
                line_extension_amount=cbc.LineExtensionAmount(
                    value=net, currency_id=currency
                ),
                item=agg.Item(
                    name=cbc.Name(value=line.description),
                    classified_tax_category=[tax_category],
                ),
                price=agg.Price(
                    price_amount=cbc.PriceAmount(
                        value=line.unit_price, currency_id=currency
                    )
                ),
            )
        )

    subtotals: list[agg.TaxSubtotal] = []
    tax_total_amount = Decimal(0)
    for (category, rate), nets in by_cat.items():
        taxable = _q2(sum(nets, Decimal(0)))
        tax = _q2(taxable * rate / Decimal(100))
        tax_total_amount += tax
        subtotals.append(
            agg.TaxSubtotal(
                taxable_amount=cbc.TaxableAmount(value=taxable, currency_id=currency),
                tax_amount=cbc.TaxAmount(value=tax, currency_id=currency),
                tax_category=agg.TaxCategory(
                    id=cbc.Id(value=category),
                    percent=cbc.Percent(value=rate),
                    tax_scheme=agg.TaxScheme(id=cbc.Id(value=_VAT)),
                ),
            )
        )

    line_total = _q2(line_total)
    tax_total_amount = _q2(tax_total_amount)
    payable = _q2(line_total + tax_total_amount)

    invoice = Invoice(
        customization_id=cbc.CustomizationId(value=CIUS_RO),
        id=cbc.Id(value=inv.invoice_number),
        issue_date=cbc.IssueDate(value=XmlDate.from_string(inv.issue_date)),
        invoice_type_code=cbc.InvoiceTypeCode(value=inv.invoice_type_code),
        document_currency_code=cbc.DocumentCurrencyCode(value=currency),
        accounting_supplier_party=agg.AccountingSupplierParty(party=_party(inv.seller)),
        accounting_customer_party=agg.AccountingCustomerParty(party=_party(inv.buyer)),
        tax_total=[
            agg.TaxTotal(
                tax_amount=cbc.TaxAmount(value=tax_total_amount, currency_id=currency),
                tax_subtotal=subtotals,
            )
        ],
        legal_monetary_total=agg.LegalMonetaryTotal(
            line_extension_amount=cbc.LineExtensionAmount(
                value=line_total, currency_id=currency
            ),
            tax_exclusive_amount=cbc.TaxExclusiveAmount(
                value=line_total, currency_id=currency
            ),
            tax_inclusive_amount=cbc.TaxInclusiveAmount(
                value=payable, currency_id=currency
            ),
            payable_amount=cbc.PayableAmount(value=payable, currency_id=currency),
        ),
        invoice_line=lines,
    )
    if inv.due_date:
        invoice.due_date = cbc.DueDate(value=XmlDate.from_string(inv.due_date))
    if inv.note:
        invoice.note = [cbc.Note(value=inv.note)]
    return invoice


def invoice_preview(inv: FlatInvoice) -> InvoicePreview:
    """Compute a preview (totals) for a flat invoice without building full UBL."""
    line_total = Decimal(0)
    tax_total = Decimal(0)
    for line in inv.lines:
        net = _q2(line.quantity * line.unit_price)
        line_total += net
        tax_total += _q2(net * line.vat_rate / Decimal(100))
    line_total = _q2(line_total)
    tax_total = _q2(tax_total)
    return InvoicePreview(
        invoice_number=inv.invoice_number,
        issue_date=inv.issue_date,
        currency=inv.currency,
        seller_name=inv.seller.name,
        buyer_name=inv.buyer.name,
        line_count=len(inv.lines),
        total_without_vat=line_total,
        total_vat=tax_total,
        total_with_vat=_q2(line_total + tax_total),
    )


def _read_xml_input(xml: str | None, path: str | None, *, label: str) -> bytes:
    if xml and path:
        raise AnafConfigError(f"{label}: set only one of `xml` / `path`, not both")
    if xml:
        return xml.encode("utf-8")
    if path:
        return Path(path).expanduser().read_bytes()
    raise AnafConfigError(f"{label}: one of `xml` / `path` is required")


def build_invoice_xml(document: InvoiceInput) -> bytes:
    """Resolve an invoice input to UTF-8 XML bytes ready to upload."""
    if isinstance(document, UblXmlInput):
        return _read_xml_input(document.xml, document.path, label="ubl_xml")
    xml = XmlSerializer().render(flat_invoice_to_ubl(document))
    return xml.encode("utf-8")


# --- e-Transport: FlatTransport -> ETransport --------------------------------------


def _route(loc: FlatTransportLocation) -> etr.LocTraseuRutierType:
    return etr.LocTraseuRutierType(
        locatie=etr.LocatieType(
            cod_judet=etr.CodJudetType(int(loc.county_code)),
            denumire_localitate=loc.locality,
            denumire_strada=loc.street,
            numar=loc.number,
            cod_postal=loc.postal_code,
            alte_info=loc.other,
        )
    )


def flat_transport_to_etransport(t: FlatTransport, *, cif: str) -> etr.ETransport:
    """Build an e-Transport :class:`ETransport` from a :class:`FlatTransport`.

    ``cif`` is the declarant's fiscal code (without country prefix); it becomes the
    document-root ``cod_declarant``.
    """
    goods = [
        etr.BunuriTransportateType(
            cod_scop_operatiune=etr.CodScopOperatiuneType(int(g.operation_scope)),
            cod_tarifar=g.tariff_code,
            denumire_marfa=g.name,
            cantitate=str(g.quantity),
            cod_unitate_masura=g.unit_code,
            greutate_neta=str(g.net_weight) if g.net_weight is not None else None,
            greutate_bruta=str(g.gross_weight),
            valoare_lei_fara_tva=(
                str(g.value_ron) if g.value_ron is not None else None
            ),
        )
        for g in t.goods
    ]
    documents = [
        etr.DocumenteTransportType(
            tip_document=etr.TipDocumentType(int(d.doc_type)),
            numar_document=d.number,
            data_document=XmlDate.from_string(d.date),
            observatii=d.note,
        )
        for d in t.documents
    ]
    notificare = etr.NotificareType(
        bunuri_transportate=goods,
        partener_comercial=etr.PartenerComercialType(
            cod_tara=etr.CodTaraType(t.partner.country),
            cod=t.partner.code,
            denumire=t.partner.name,
        ),
        date_transport=etr.DateTransportType(
            nr_vehicul=t.vehicle.plate,
            nr_remorca1=t.vehicle.trailer1,
            nr_remorca2=t.vehicle.trailer2,
            cod_tara_org_transport=etr.CodTaraType(t.vehicle.carrier_country),
            cod_org_transport=t.vehicle.carrier_code,
            denumire_org_transport=t.vehicle.carrier_name,
            data_transport=XmlDate.from_string(t.vehicle.transport_date),
        ),
        loc_start_traseu_rutier=_route(t.start_location),
        loc_final_traseu_rutier=_route(t.end_location),
        documente_transport=documents,
        cod_tip_operatiune=etr.CodTipOperatiuneType(int(t.operation_type)),
    )
    return etr.ETransport(
        notificare=notificare,
        cod_declarant=cif,
        ref_declarant=t.declarant_ref,
    )


def transport_preview(t: FlatTransport) -> TransportPreview:
    """Compute a preview for a flat transport declaration."""
    gross = sum((g.gross_weight for g in t.goods), Decimal(0))
    return TransportPreview(
        operation_type=t.operation_type,
        partner_name=t.partner.name,
        vehicle_plate=t.vehicle.plate,
        transport_date=t.vehicle.transport_date,
        goods_count=len(t.goods),
        total_gross_weight=gross,
    )


def build_transport_xml(document: TransportInput, *, cif: str) -> bytes:
    """Resolve a transport input to UTF-8 XML bytes ready to upload."""
    if isinstance(document, EtransportXmlInput):
        return _read_xml_input(document.xml, document.path, label="etransport_xml")
    xml = XmlSerializer().render(flat_transport_to_etransport(document, cif=cif))
    return xml.encode("utf-8")
