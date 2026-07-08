"""Wire-XML fixtures: build real UBL / e-Transport documents for the read-view tests.

anafpy never composes UBL from flat input, so the e-Factura fixtures build the
generated models directly (as a caller's invoicing software would) and serialize them
to the XML the clients / MCP tools consume. The e-Transport fixtures come in both
shapes: ``build_transport()`` builds the generated XSD models (external XML, as a TMS
would produce) and ``build_flat_transport()`` is its flat-model twin (the authoring
surface anafpy itself provides).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlSerializer

from anafpy.efactura import CreditNote, Invoice
from anafpy.efactura.ubl.common import ubl_common_aggregate_components_2_1 as agg
from anafpy.efactura.ubl.common import ubl_common_basic_components_2_1 as cbc
from anafpy.etransport import (
    FlatTransport,
    FlatTransportAddress,
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
    FlatTransportPartner,
    FlatTransportVehicle,
)
from anafpy.etransport.schema import schema_etr_v2_20230126 as etr

CIUS_RO = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
_CUR = "RON"


def _party(name: str, vat: str) -> agg.Party:
    return agg.Party(
        party_name=[agg.PartyName(name=cbc.Name(value=name))],
        postal_address=agg.PostalAddress(
            street_name=cbc.StreetName(value="Str A 1"),
            # RO-B requires a SECTOR city (BR-RO-100) — the strict authoring
            # reader behind DownloadedMessage.view enforces the same rule.
            city_name=cbc.CityName(value="SECTOR1"),
            country_subentity=cbc.CountrySubentity(value="RO-B"),
            country=agg.Country(identification_code=cbc.IdentificationCode(value="RO")),
        ),
        party_legal_entity=[
            agg.PartyLegalEntity(registration_name=cbc.RegistrationName(value=name))
        ],
        party_tax_scheme=[
            agg.PartyTaxScheme(
                company_id=cbc.CompanyId(value=vat),
                tax_scheme=agg.TaxScheme(id=cbc.Id(value="VAT")),
            )
        ],
    )


def _tax_total() -> agg.TaxTotal:
    return agg.TaxTotal(
        tax_amount=cbc.TaxAmount(value=Decimal("3.99"), currency_id=_CUR),
        tax_subtotal=[
            agg.TaxSubtotal(
                taxable_amount=cbc.TaxableAmount(
                    value=Decimal("21.00"), currency_id=_CUR
                ),
                tax_amount=cbc.TaxAmount(value=Decimal("3.99"), currency_id=_CUR),
                tax_category=agg.TaxCategory(
                    id=cbc.Id(value="S"),
                    percent=cbc.Percent(value=Decimal("19")),
                    tax_scheme=agg.TaxScheme(id=cbc.Id(value="VAT")),
                ),
            )
        ],
    )


def _monetary_total() -> agg.LegalMonetaryTotal:
    return agg.LegalMonetaryTotal(
        line_extension_amount=cbc.LineExtensionAmount(
            value=Decimal("21.00"), currency_id=_CUR
        ),
        tax_exclusive_amount=cbc.TaxExclusiveAmount(
            value=Decimal("21.00"), currency_id=_CUR
        ),
        tax_inclusive_amount=cbc.TaxInclusiveAmount(
            value=Decimal("24.99"), currency_id=_CUR
        ),
        payable_amount=cbc.PayableAmount(value=Decimal("24.99"), currency_id=_CUR),
    )


def _item() -> agg.Item:
    return agg.Item(
        name=cbc.Name(value="Widget"),
        classified_tax_category=[
            agg.ClassifiedTaxCategory(
                id=cbc.Id(value="S"),
                percent=cbc.Percent(value=Decimal("19")),
                tax_scheme=agg.TaxScheme(id=cbc.Id(value="VAT")),
            )
        ],
    )


def build_invoice(*, number: str = "INV-1") -> Invoice:
    """A one-line CIUS-RO invoice: net 21.00, 19% VAT 3.99, payable 24.99."""
    return Invoice(
        customization_id=cbc.CustomizationId(value=CIUS_RO),
        id=cbc.Id(value=number),
        issue_date=cbc.IssueDate(value=XmlDate(2026, 6, 28)),
        due_date=cbc.DueDate(value=XmlDate(2026, 7, 28)),
        invoice_type_code=cbc.InvoiceTypeCode(value="380"),
        document_currency_code=cbc.DocumentCurrencyCode(value=_CUR),
        accounting_supplier_party=agg.AccountingSupplierParty(
            party=_party("Seller", "RO1")
        ),
        accounting_customer_party=agg.AccountingCustomerParty(
            party=_party("Buyer", "RO2")
        ),
        tax_total=[_tax_total()],
        legal_monetary_total=_monetary_total(),
        invoice_line=[
            agg.InvoiceLine(
                id=cbc.Id(value="1"),
                invoiced_quantity=cbc.InvoicedQuantity(
                    value=Decimal("2"), unit_code="C62"
                ),
                line_extension_amount=cbc.LineExtensionAmount(
                    value=Decimal("21.00"), currency_id=_CUR
                ),
                item=_item(),
                price=agg.Price(
                    price_amount=cbc.PriceAmount(
                        value=Decimal("10.50"), currency_id=_CUR
                    )
                ),
            )
        ],
    )


def build_credit_note(*, number: str = "CN-1") -> CreditNote:
    """A minimal one-line CIUS-RO credit note (for document_type discrimination)."""
    return CreditNote(
        customization_id=cbc.CustomizationId(value=CIUS_RO),
        id=cbc.Id(value=number),
        issue_date=cbc.IssueDate(value=XmlDate(2026, 6, 28)),
        credit_note_type_code=cbc.CreditNoteTypeCode(value="381"),
        document_currency_code=cbc.DocumentCurrencyCode(value=_CUR),
        accounting_supplier_party=agg.AccountingSupplierParty(
            party=_party("Seller", "RO1")
        ),
        accounting_customer_party=agg.AccountingCustomerParty(
            party=_party("Buyer", "RO2")
        ),
        legal_monetary_total=_monetary_total(),
        credit_note_line=[
            agg.CreditNoteLine(
                id=cbc.Id(value="1"),
                credited_quantity=cbc.CreditedQuantity(
                    value=Decimal("2"), unit_code="C62"
                ),
                line_extension_amount=cbc.LineExtensionAmount(
                    value=Decimal("21.00"), currency_id=_CUR
                ),
                item=_item(),
                price=agg.Price(
                    price_amount=cbc.PriceAmount(
                        value=Decimal("10.50"), currency_id=_CUR
                    )
                ),
            )
        ],
    )


def invoice_xml(*, number: str = "INV-1") -> str:
    return XmlSerializer().render(build_invoice(number=number))


def credit_note_xml(*, number: str = "CN-1") -> str:
    return XmlSerializer().render(build_credit_note(number=number))


def build_transport() -> etr.ETransport:
    """A minimal road-transport declaration (gross weight 120 kg)."""
    return etr.ETransport(
        cod_declarant="123",
        notificare=etr.NotificareType(
            bunuri_transportate=[
                etr.BunuriTransportateType(
                    cod_scop_operatiune=etr.CodScopOperatiuneType(301),
                    denumire_marfa="Marfa",
                    cantitate="100",
                    cod_unitate_masura="KGM",
                    greutate_bruta="120",
                    greutate_neta="100",
                )
            ],
            partener_comercial=etr.PartenerComercialType(
                cod_tara=etr.CodTaraType("DE"),
                cod="DE9",
                denumire="Foreign GmbH",
            ),
            date_transport=etr.DateTransportType(
                nr_vehicul="B100XYZ",
                cod_tara_org_transport=etr.CodTaraType("RO"),
                denumire_org_transport="Carrier SRL",
                cod_org_transport="999",
                data_transport=XmlDate(2026, 6, 28),
            ),
            loc_start_traseu_rutier=etr.LocTraseuRutierType(
                locatie=etr.LocatieType(
                    cod_judet=etr.CodJudetType(40),
                    denumire_localitate="Bucuresti",
                    denumire_strada="Str A",
                    numar="1",
                )
            ),
            loc_final_traseu_rutier=etr.LocTraseuRutierType(
                locatie=etr.LocatieType(
                    cod_judet=etr.CodJudetType(12),
                    denumire_localitate="Cluj",
                    denumire_strada="Str B",
                )
            ),
            documente_transport=[
                etr.DocumenteTransportType(
                    tip_document=etr.TipDocumentType(20),
                    numar_document="FAC1",
                    data_document=XmlDate(2026, 6, 27),
                )
            ],
            cod_tip_operatiune=etr.CodTipOperatiuneType(30),
        ),
    )


def transport_xml() -> str:
    return XmlSerializer().render(build_transport())


def build_flat_transport() -> FlatTransport:
    """The flat-model twin of :func:`build_transport` (same declaration, authored)."""
    return FlatTransport(
        operation_type=etr.CodTipOperatiuneType.TTN,
        partner=FlatTransportPartner(
            name="Foreign GmbH", country=etr.CodTaraType.GERMANIA, code="DE9"
        ),
        vehicle=FlatTransportVehicle(
            plate="B100XYZ",
            carrier_name="Carrier SRL",
            carrier_country=etr.CodTaraType.ROMANIA,
            carrier_code="999",
            transport_date=dt.date(2026, 6, 28),
        ),
        start_location=FlatTransportLocation(
            address=FlatTransportAddress(
                county=etr.CodJudetType.MUNICIPIUL_BUCURESTI,
                locality="Bucuresti",
                street="Str A",
                number="1",
            )
        ),
        end_location=FlatTransportLocation(
            address=FlatTransportAddress(
                county=etr.CodJudetType.CLUJ, locality="Cluj", street="Str B"
            )
        ),
        goods=[
            FlatTransportGood(
                operation_scope=etr.CodScopOperatiuneType.GRATUITATI,
                name="Marfa",
                quantity=Decimal("100"),
                unit_code="KGM",
                gross_weight=Decimal("120"),
                net_weight=Decimal("100"),
            )
        ],
        documents=[
            FlatTransportDocument(
                doc_type=etr.TipDocumentType.FACTURA,
                date=dt.date(2026, 6, 27),
                number="FAC1",
            )
        ],
    )
