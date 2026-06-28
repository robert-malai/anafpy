"""Curated, flat, skill-friendly models — the LLM authoring surface (``DESIGN.md`` §7).

These are deliberately *not* the generated UBL / e-Transport models: those have huge,
awkward JSON Schemas (wrapper objects, ``currencyID`` everywhere, reconciling totals) an
LLM authors wrong. Here we expose a small flat shape for the common case, plus a locked
**XML pass-through** escape hatch (``UblXmlInput`` / ``EtransportXmlInput``) for
existing ERP- or user-produced documents. The structured full UBL model stays
library-only.

Mapping to the wire format lives in :mod:`anafpy.mcp.mapping`; the value types the tools
*return* (previews, validation summaries) live here too.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..validation import ValidationFinding

__all__ = [
    "EtransportXmlInput",
    "FlatInvoice",
    "FlatInvoiceLine",
    "FlatParty",
    "FlatTransport",
    "FlatTransportDocument",
    "FlatTransportGood",
    "FlatTransportLocation",
    "FlatTransportPartner",
    "FlatTransportVehicle",
    "InvoiceInput",
    "InvoicePreview",
    "PreparedSubmission",
    "SubmitResult",
    "TransportInput",
    "TransportPreview",
    "UblXmlInput",
]

# CIUS-RO 1.0.1 customization marker required on every RO e-Factura UBL document.
CIUS_RO = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"


# --- e-Factura flat authoring surface ----------------------------------------------


class FlatParty(BaseModel):
    """A seller or buyer, flattened from the UBL ``Party`` tree."""

    name: str = Field(description="Registered legal name.")
    vat_id: str | None = Field(
        default=None,
        description="VAT identifier including country prefix, e.g. 'RO1234567'. "
        "Required for the seller and for VAT-registered buyers.",
    )
    company_id: str | None = Field(
        default=None,
        description="Legal registration id (CUI / Trade Register no.) when different "
        "from the VAT id.",
    )
    country: str = Field(
        default="RO", description="ISO 3166-1 alpha-2 country code, e.g. 'RO'."
    )
    county: str | None = Field(
        default=None,
        description="Country subdivision code (BT). For Romania use 'RO-<county>', "
        "e.g. 'RO-B' for Bucharest, 'RO-CJ' for Cluj.",
    )
    city: str = Field(description="City / locality name.")
    address: str = Field(description="Street name and number (main address line).")
    postal_zone: str | None = Field(default=None, description="Postal code.")


class FlatInvoiceLine(BaseModel):
    """One invoice line."""

    description: str = Field(description="Item name / description.")
    quantity: Decimal = Field(description="Invoiced quantity.")
    unit_code: str = Field(
        default="C62",
        description="UN/ECE Rec 20 unit code; 'C62' = unit/piece, 'HUR' = hour, "
        "'KGM' = kilogram, 'MTR' = metre.",
    )
    unit_price: Decimal = Field(description="Net price per unit, excluding VAT.")
    vat_category: str = Field(
        default="S",
        description="UNCL5305 VAT category code: 'S' standard rate, 'Z' zero rate, "
        "'E' exempt, 'AE' reverse charge, 'O' out of scope.",
    )
    vat_rate: Decimal = Field(
        default=Decimal(0),
        description="VAT rate as a percentage, e.g. 19 or 9. Use 0 for Z/E/AE/O.",
    )


class FlatInvoice(BaseModel):
    """A flat invoice the model can author for the common CIUS-RO case.

    Totals (line amounts, VAT subtotals, payable) are computed during mapping — do not
    supply them. For documents this shape can't express (allowances, multiple payment
    means, ...), use :class:`UblXmlInput` to pass existing UBL XML through instead.
    """

    kind: Literal["flat"] = "flat"
    invoice_number: str = Field(description="Invoice number (BT-1).")
    issue_date: str = Field(description="Issue date, ISO 'YYYY-MM-DD'.")
    due_date: str | None = Field(
        default=None, description="Payment due date, ISO 'YYYY-MM-DD'."
    )
    currency: str = Field(default="RON", description="ISO 4217 document currency code.")
    invoice_type_code: str = Field(
        default="380",
        description="UNCL1001 invoice type; '380' commercial invoice, '381' credit "
        "note, '389' self-billed.",
    )
    seller: FlatParty
    buyer: FlatParty
    lines: list[FlatInvoiceLine] = Field(min_length=1)
    note: str | None = Field(default=None, description="Free-text document note.")


class UblXmlInput(BaseModel):
    """Escape hatch: pass an *existing* UBL invoice/credit-note as XML.

    Use for ERP-generated or user-supplied UBL — it is parsed and Schematron-validated,
    then filed verbatim. Exactly one of ``xml`` / ``path`` must be set.
    """

    kind: Literal["ubl_xml"] = "ubl_xml"
    xml: str | None = Field(default=None, description="The UBL document as XML text.")
    path: str | None = Field(
        default=None, description="Filesystem path to a UBL XML file."
    )


InvoiceInput = Annotated[FlatInvoice | UblXmlInput, Field(discriminator="kind")]


# --- e-Transport flat authoring surface --------------------------------------------


class FlatTransportPartner(BaseModel):
    """Commercial partner (supplier/buyer/beneficiary depending on operation type)."""

    name: str = Field(description="Partner name.")
    country: str = Field(default="RO", description="ISO 3166-1 alpha-2 country code.")
    code: str | None = Field(
        default=None, description="Fiscal code / CUI (without country prefix)."
    )


class FlatTransportVehicle(BaseModel):
    """Vehicle and carrier details."""

    plate: str = Field(description="Vehicle registration plate (nr_vehicul).")
    trailer1: str | None = Field(default=None, description="First trailer plate.")
    trailer2: str | None = Field(default=None, description="Second trailer plate.")
    carrier_name: str = Field(description="Transport organiser name.")
    carrier_country: str = Field(default="RO", description="Carrier country code.")
    carrier_code: str | None = Field(default=None, description="Carrier fiscal code.")
    transport_date: str = Field(description="Transport date, ISO 'YYYY-MM-DD'.")


class FlatTransportLocation(BaseModel):
    """A national address used as the start or end of the road route."""

    county_code: str = Field(
        description="Numeric county code (cod_judet), 1-52, e.g. '40' for Bucharest, "
        "'12' for Cluj."
    )
    locality: str = Field(description="Locality name.")
    street: str = Field(description="Street name.")
    number: str | None = Field(default=None, description="Street number.")
    postal_code: str | None = Field(default=None, description="Postal code.")
    other: str | None = Field(default=None, description="Other address details.")


class FlatTransportGood(BaseModel):
    """One transported-goods line."""

    operation_scope: str = Field(
        description="Operation-scope code (cod_scop_operatiune), e.g. '101' "
        "intra-community delivery, '201' acquisition, '301' import."
    )
    name: str = Field(description="Goods description (denumire_marfa).")
    quantity: Decimal = Field(description="Quantity (cantitate).")
    unit_code: str = Field(description="Measure-unit code (cod_unitate_masura).")
    gross_weight: Decimal = Field(description="Gross weight in kg (greutate_bruta).")
    net_weight: Decimal | None = Field(
        default=None, description="Net weight in kg (greutate_neta)."
    )
    tariff_code: str | None = Field(
        default=None, description="NC/tariff code (cod_tarifar)."
    )
    value_ron: Decimal | None = Field(
        default=None, description="Value in RON excluding VAT (valoare_lei_fara_tva)."
    )


class FlatTransportDocument(BaseModel):
    """A transport document reference."""

    doc_type: str = Field(
        description="Document-type code (tip_document): '10' CMR, '20' invoice, "
        "'30' delivery note, '9999' other."
    )
    number: str | None = Field(default=None, description="Document number.")
    date: str = Field(description="Document date, ISO 'YYYY-MM-DD'.")
    note: str | None = Field(default=None, description="Observations.")


class FlatTransport(BaseModel):
    """A flat e-Transport declaration for the common road-transport case."""

    kind: Literal["flat"] = "flat"
    operation_type: str = Field(
        description="Operation-type code (cod_tip_operatiune): '10' AIC delivery, "
        "'20' AIC acquisition, '30' import, '40' export, '50' intra-community "
        "transit, '60' national trade, '70' other."
    )
    declarant_ref: str | None = Field(
        default=None, description="Declarant's own reference (ref_declarant)."
    )
    partner: FlatTransportPartner
    vehicle: FlatTransportVehicle
    start_location: FlatTransportLocation
    end_location: FlatTransportLocation
    goods: list[FlatTransportGood] = Field(min_length=1)
    documents: list[FlatTransportDocument] = Field(default_factory=list)


class EtransportXmlInput(BaseModel):
    """Escape hatch: pass an *existing* e-Transport declaration as XML."""

    kind: Literal["etransport_xml"] = "etransport_xml"
    xml: str | None = Field(default=None, description="The declaration as XML text.")
    path: str | None = Field(
        default=None, description="Path to a declaration XML file."
    )


TransportInput = Annotated[
    FlatTransport | EtransportXmlInput, Field(discriminator="kind")
]


# --- tool return value types -------------------------------------------------------


class InvoicePreview(BaseModel):
    """Human-readable summary of an invoice about to be filed."""

    invoice_number: str
    issue_date: str
    currency: str
    seller_name: str
    buyer_name: str
    line_count: int
    total_without_vat: Decimal
    total_vat: Decimal
    total_with_vat: Decimal


class TransportPreview(BaseModel):
    """Human-readable summary of an e-Transport declaration about to be filed."""

    operation_type: str
    partner_name: str
    vehicle_plate: str
    transport_date: str
    goods_count: int
    total_gross_weight: Decimal


class PreparedSubmission(BaseModel):
    """Result of a ``prepare`` step: preview + local validation + confirmation token.

    ``confirmation_token`` is ``None`` when local validation failed — fix the findings
    and prepare again. When present, pass it (with the *same* document) to the matching
    ``submit`` tool to file.
    """

    valid: bool
    findings: list[ValidationFinding] = []
    validation_available: bool = True
    confirmation_token: str | None = None
    invoice_preview: InvoicePreview | None = None
    transport_preview: TransportPreview | None = None
    message: str = ""


class SubmitResult(BaseModel):
    """Result of a ``submit`` step."""

    accepted: bool
    upload_id: str | None = None
    uit: str | None = None
    errors: list[str] = []
    message: str = ""
