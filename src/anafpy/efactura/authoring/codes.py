"""Hand-curated codes for the CIUS-RO invoice models.

The big closed lists (currencies, countries, units, ...) are generated into
:mod:`._codelists`; this module carries the small, semantically-named subsets the
CIUS-RO Schematron restricts beyond the base UNTDID/ISO lists, plus the Romanian
sub-national code lists that exist only in the RO rules.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "BUCHAREST_SECTORS",
    "CIUS_RO_CUSTOMIZATION_ID",
    "CREDIT_NOTE_TYPE_CODES",
    "INVOICE_TYPE_CODES",
    "RO_COUNTY_CODES",
    "DocumentKind",
    "InvoiceTypeCode",
    "VatCategory",
    "VatPointDateCode",
]

#: BT-24 specification identifier the RO Schematron pins exactly (BR-RO-001).
CIUS_RO_CUSTOMIZATION_ID = (
    "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
)


class DocumentKind(StrEnum):
    """Which UBL document a :class:`~.models.InvoiceDocument` renders to."""

    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"


class InvoiceTypeCode(StrEnum):
    """BT-3 document type codes CIUS-RO admits (BR-RO-020, UNTDID 1001 subset).

    ``CREDIT_NOTE`` (381) is the only code valid on a UBL CreditNote; the other
    four are valid on a UBL Invoice.
    """

    COMMERCIAL_INVOICE = "380"
    CREDIT_NOTE = "381"
    CORRECTED_INVOICE = "384"
    SELF_BILLED_INVOICE = "389"
    ACCOUNTING_INVOICE = "751"  # invoice — information for accounting purposes


#: BT-3 codes valid per document kind (BR-RO-020).
INVOICE_TYPE_CODES = frozenset(
    {
        InvoiceTypeCode.COMMERCIAL_INVOICE,
        InvoiceTypeCode.CORRECTED_INVOICE,
        InvoiceTypeCode.SELF_BILLED_INVOICE,
        InvoiceTypeCode.ACCOUNTING_INVOICE,
    }
)
CREDIT_NOTE_TYPE_CODES = frozenset({InvoiceTypeCode.CREDIT_NOTE})


class VatCategory(StrEnum):
    """BT-95/102/118/151 VAT category codes (UNCL 5305, EN16931 subset).

    ``SPLIT_PAYMENT`` (B) is on the list but only valid on domestic Italian
    invoices (BR-B-01) — a CIUS-RO filing using it is rejected.
    """

    STANDARD = "S"
    ZERO_RATED = "Z"
    EXEMPT = "E"
    REVERSE_CHARGE = "AE"
    INTRA_COMMUNITY = "K"  # intra-community supply of goods/services
    EXPORT = "G"  # export outside the EU
    NOT_SUBJECT = "O"  # services outside the scope of VAT
    IGIC = "L"  # Canary Islands general indirect tax
    IPSI = "M"  # Ceuta / Melilla tax
    SPLIT_PAYMENT = "B"


class VatPointDateCode(StrEnum):
    """BT-8 VAT point date codes (UNTDID 2005 restricted by BR-RO-040)."""

    ISSUE_DATE = "3"
    DELIVERY_DATE = "35"
    PAYMENT_DATE = "432"


#: ISO 3166-2:RO county codes (BR-RO-110): the CountrySubentity values accepted
#: when the address country is RO.
RO_COUNTY_CODES = frozenset(
    {
        "RO-AB", "RO-AG", "RO-AR", "RO-B", "RO-BC", "RO-BH", "RO-BN", "RO-BR",
        "RO-BT", "RO-BV", "RO-BZ", "RO-CJ", "RO-CL", "RO-CS", "RO-CT", "RO-CV",
        "RO-DB", "RO-DJ", "RO-GJ", "RO-GL", "RO-GR", "RO-HD", "RO-HR", "RO-IF",
        "RO-IL", "RO-IS", "RO-MH", "RO-MM", "RO-MS", "RO-NT", "RO-OT", "RO-PH",
        "RO-SB", "RO-SJ", "RO-SM", "RO-SV", "RO-TL", "RO-TM", "RO-TR", "RO-VL",
        "RO-VN", "RO-VS",
    }
)  # fmt: skip

#: City names required inside Bucharest (county RO-B), exactly as the RO
#: Schematron spells them (BR-RO-100).
BUCHAREST_SECTORS = frozenset(
    {"SECTOR1", "SECTOR2", "SECTOR3", "SECTOR4", "SECTOR5", "SECTOR6"}
)
