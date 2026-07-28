"""Bidirectional flat models for CIUS-RO electronic invoices.

One semantic model — EN 16931's — covers both UBL document types:
:class:`InvoiceDocument` authors and views an ``Invoice`` or a ``CreditNote``
(:attr:`~InvoiceDocument.kind` picks the render target). The same models are
produced by :func:`~.read.read_invoice` and consumed by :func:`~.build.build_invoice`
/ :func:`~.build.render_invoice`, mirroring the e-Transport flat models.

Validation is two-tier:

- **Construction** enforces what a single model can know unconditionally: field
  formats and lengths (the ``BR-RO-L*`` limits), closed code lists (``BR-CL-*``),
  decimal budgets (``BR-DEC-*``), and local consistency (a period needs a start or
  an end, a VAT category pins its rate shape, ...). Data violating these is
  rejected by ANAF with certainty, so failing fast is data hygiene.
- :func:`~.rules.validate` runs the cross-aggregate EN 16931 / CIUS-RO rule set
  (totals arithmetic, VAT breakdown consistency, regime-dependent identifier
  requirements) and returns a findings report instead of raising.

Authoring and reading are the same models but *not* the same contract. Refusing
to build an invalid document is data hygiene; refusing to *read* one ANAF already
accepted is a bug — so :func:`~.read.read_invoice` validates through the
:data:`_DERIVED_CONTEXT` marker, which turns the consistency and sign checks
into no-ops while leaving coercion, defaults and normalisation in place. The
first tier above stays fatal in both directions — code lists, format patterns,
lengths, decimal budgets all mirror rules ANAF enforces fatally, so they cannot
fire on an accepted document; when one does, the mirrors have drifted, which is
the tripwire :attr:`~anafpy.efactura.models.DownloadedMessage.view` documents.

Totals and the VAT breakdown are **computed by default** from the lines,
allowances and charges (correct by construction); explicit values may be supplied
— e.g. when reproducing an upstream document — and are then checked against the
computed ones by :func:`~.rules.validate`.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
    model_validator,
)

from ._codelists import (
    COUNTRY_CODES,
    CURRENCY_CODES,
    ELECTRONIC_ADDRESS_SCHEMES,
    ICD_SCHEMES,
    ITEM_CLASSIFICATION_SCHEMES,
    MIME_CODES,
    NOTE_SUBJECT_CODES,
    OBJECT_ID_SCHEMES,
    PAYMENT_MEANS_CODES,
    UNIT_CODES,
    VAT_EXEMPTION_CODES,
)
from .codes import (
    BUCHAREST_SECTORS,
    CREDIT_NOTE_TYPE_CODES,
    INVOICE_TYPE_CODES,
    RO_COUNTY_CODES,
    DocumentKind,
    InvoiceTypeCode,
    VatCategory,
    VatPointDateCode,
)

__all__ = [
    "Contact",
    "CreditTransfer",
    "DeliveryInformation",
    "DirectDebit",
    "DocumentAllowance",
    "DocumentCharge",
    "ElectronicAddress",
    "InvoiceDocument",
    "InvoiceLine",
    "ItemAttribute",
    "ItemClassification",
    "LineAllowance",
    "LineCharge",
    "Note",
    "Party",
    "Payee",
    "PaymentCard",
    "PaymentInstructions",
    "Period",
    "PostalAddress",
    "PrecedingInvoice",
    "Seller",
    "SupportingDocument",
    "TaxRepresentative",
    "Totals",
    "VatBreakdownEntry",
]

_CENT = Decimal("0.01")


def round2(value: Decimal) -> Decimal:
    """EN 16931 Annex-B rounding: two decimals, half away from zero."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _member_by_name(enum_cls: type[Enum]) -> Callable[[object], object]:
    """Accept an enum member NAME ('STANDARD') or case-folded value ('s') in
    addition to what pydantic's own enum validation takes; other values pass
    through untouched."""

    def coerce(value: object) -> object:
        if isinstance(value, str):
            key = value.strip().upper().replace(" ", "_").replace("-", "_")
            if key in enum_cls.__members__:
                return enum_cls[key]
            if key in {str(member.value) for member in enum_cls}:
                return key
        return value

    return coerce


def _in_codelist(codes: frozenset[str], label: str) -> Callable[[str], str]:
    def check(value: str) -> str:
        if value not in codes:
            raise ValueError(f"{value!r} is not on the {label} code list")
        return value

    return check


#: Validation context marking a value the caller did **not** author: one
#: :func:`~.read.read_invoice` translated off the wire, or one this module
#: derived from a document that was (:meth:`InvoiceDocument.compute_totals`,
#: :meth:`~InvoiceDocument.compute_vat_breakdown`).
#:
#: Every check it disables is one whose whole job is to stop *us* emitting an
#: invalid document: the non-negativity rules, the contact free-text shapes, the
#: per-category rate and exemption-reason consistency, and the cross-field
#: "X requires Y" pairs. Neither kind of value is a place to enforce them. A
#: received document already carries ANAF's verdict, so re-judging it can only
#: lose data — one rejected optional field would make the whole invoice
#: unreadable. And a *derived* value is this module's own output: raising there
#: turns a caller's data problem into a raw pydantic error thrown from inside a
#: function documented never to raise (which is exactly how the BR-*-10
#: exemption reason went wrong, DESIGN.md §4) — and would make a read document
#: unrenderable, breaking the bidirectional contract.
#:
#: Coercion, defaults and normalisation still run, as do the closed code lists
#: (see the module docstring).
_DERIVED_CONTEXT = {"derived": True}


def _derived(info: ValidationInfo) -> bool:
    """Whether validation is running under :data:`_DERIVED_CONTEXT`."""
    return bool((info.context or {}).get("derived"))


def vat_group_key(
    category: VatCategory, rate: Decimal | None
) -> tuple[VatCategory, Decimal | None]:
    """The ``(category, rate)`` key the VAT breakdown (BG-23) groups by.

    Rates are compared numerically (``19`` and ``19.00`` are one group), and
    category O is keyed without a rate at all: BR-O-05..07 say it carries none,
    so an issuer's explicit ``0`` and an absent rate mean the same thing. Both
    spellings occur in one document — a line with no ``cbc:Percent`` under a
    subtotal that has one — and keying them apart splits the group in two.
    """
    if category is VatCategory.NOT_SUBJECT:
        return category, None
    return category, None if rate is None else rate.normalize()


def _not_negative(value: Decimal, info: ValidationInfo) -> Decimal:
    """Authoring-only non-negativity: an allowance is a positive amount under a
    false charge indicator, not a negative charge."""
    if value < 0 and not _derived(info):
        raise ValueError("must not be negative")
    return value


def _positive(value: Decimal, info: ValidationInfo) -> Decimal:
    """Authoring-only positivity (BT-149's base quantity)."""
    if value <= 0 and not _derived(info):
        raise ValueError("must be greater than zero")
    return value


_NonNegative = AfterValidator(_not_negative)


# Closed-list string types (the BR-CL-* rules), enforced at construction.
_Currency = Annotated[
    str, AfterValidator(_in_codelist(CURRENCY_CODES, "ISO 4217 currency"))
]
_Country = Annotated[
    str, AfterValidator(_in_codelist(COUNTRY_CODES, "ISO 3166 country"))
]
_UnitCode = Annotated[
    str, AfterValidator(_in_codelist(UNIT_CODES, "UN/ECE Rec 20/21 unit"))
]
_IcdScheme = Annotated[
    str,
    AfterValidator(_in_codelist(ICD_SCHEMES | {"SEPA"}, "ISO 6523 ICD scheme")),
]
_EasScheme = Annotated[
    str,
    AfterValidator(_in_codelist(ELECTRONIC_ADDRESS_SCHEMES, "EAS address scheme")),
]
_ObjectScheme = Annotated[
    str, AfterValidator(_in_codelist(OBJECT_ID_SCHEMES, "UNTDID 1153 scheme"))
]
_ClassificationScheme = Annotated[
    str,
    AfterValidator(
        _in_codelist(ITEM_CLASSIFICATION_SCHEMES, "UNTDID 7143 classification scheme")
    ),
]
_PaymentMeansCode = Annotated[
    str,
    AfterValidator(_in_codelist(PAYMENT_MEANS_CODES, "UNTDID 4461 payment means")),
]
_MimeCode = Annotated[
    str, AfterValidator(_in_codelist(MIME_CODES, "EN 16931 attachment MIME"))
]
_ExemptionCode = Annotated[
    str, AfterValidator(_in_codelist(VAT_EXEMPTION_CODES, "VATEX exemption reason"))
]
_NoteSubjectCode = Annotated[
    str, AfterValidator(_in_codelist(NOTE_SUBJECT_CODES, "UNCL 4451 note subject"))
]

# Amounts carry at most two decimals (the BR-DEC-* budget); prices and quantities
# are unbudgeted by EN 16931 and stay plain Decimals.
_Money = Annotated[Decimal, Field(decimal_places=2)]
_NonNegativeMoney = Annotated[Decimal, Field(decimal_places=2), _NonNegative]
_Rate = Annotated[
    Decimal, Field(description="Percentage, e.g. 19 for 19%."), _NonNegative
]

_VatCategory = Annotated[VatCategory, BeforeValidator(_member_by_name(VatCategory))]

#: VAT categories whose rate is fixed at 0 (BR-Z/E/AE/IC/G-05..07); a ``None``
#: rate on them is filled with 0 at construction.
_ZERO_RATE_CATEGORIES = frozenset(
    {
        VatCategory.ZERO_RATED,
        VatCategory.EXEMPT,
        VatCategory.REVERSE_CHARGE,
        VatCategory.INTRA_COMMUNITY,
        VatCategory.EXPORT,
    }
)
#: VAT categories whose breakdown must carry an exemption reason (BR-E/AE/IC/G/O-10).
_EXEMPTION_REASON_CATEGORIES = _ZERO_RATE_CATEGORIES - {VatCategory.ZERO_RATED} | {
    VatCategory.NOT_SUBJECT
}

# Contact shapes (BT-42/43, BT-57/58). Deliberately permissive: no e-Factura rule
# constrains the address beyond its 100-char length. The alphanumerics-only
# RO-EMAIL-REGEX this once mirrored belongs to the *e-Transport* Schematron —
# where it is a declared-but-never-referenced `let`, so ANAF enforces it in
# neither service — and ANAF accepts filings whose contact carries `_`, `-` or
# `+`. What remains is authoring hygiene only, refusing what is unambiguously
# malformed: a missing/duplicated `@`, whitespace, an empty side, or a
# leading/trailing dot on either side. Since ANAF validates neither BT-42 nor
# BT-43, real filings do carry two addresses in one element or a stray `-` for a
# phone number — so reading skips both checks rather than lose the invoice.
_EMAIL = re.compile(r"^[^\s@.](?:[^\s@]*[^\s@.])?@[^\s@.](?:[^\s@]*[^\s@.])?$")


def _valid_email(value: str, info: ValidationInfo) -> str:
    if not _EMAIL.match(value) and not _derived(info):
        raise ValueError(f"{value!r} is not a plausible email address")
    return value


def _valid_telephone(value: str, info: ValidationInfo) -> str:
    if sum(char.isdigit() for char in value) < 3 and not _derived(info):
        raise ValueError("a telephone number needs at least 3 digits")
    return value


def _check_vat_rate_shape(
    category: VatCategory, rate: Decimal | None, *, required: bool, derived: bool
) -> Decimal | None:
    """The per-category VAT rate shape shared by lines, document-level
    allowances/charges and breakdown entries (BR-S/Z/E/AE/IC/G/O-05..09).

    Returns the effective rate: a ``None`` rate on a fixed-zero category is
    filled with 0 rather than rejected. When ``derived``, the value's own rate is
    returned as-is instead of being judged.
    """
    if category is VatCategory.NOT_SUBJECT:
        # BR-O-05/06/07: category O takes no rate. Reading keeps whatever the
        # issuer sent (some send an explicit zero); authoring reads that same
        # redundant zero as "no rate" and refuses anything else.
        if derived:
            return rate
        if rate is None or rate == 0:
            return None
        raise ValueError("VAT category O (not subject to VAT) takes no rate")
    if category in _ZERO_RATE_CATEGORIES:
        if rate is None:
            # Filled on the derived path too, on purpose: a wire line with no
            # cbc:Percent must land in the same (category, 0) breakdown group
            # as a subtotal that spells the fixed rate explicitly.
            return Decimal(0)
        if rate != 0 and not derived:
            raise ValueError(f"VAT category {category.value} requires a 0% rate")
        return rate
    if rate is None:
        if required and not derived:
            raise ValueError(f"VAT category {category.value} requires a rate")
        return None
    if category is VatCategory.STANDARD and rate == 0 and not derived:
        raise ValueError("VAT category S (standard) requires a rate above zero")
    return rate


class Contact(BaseModel):
    """A contact point (BG-6 seller / BG-9 buyer)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)  # BT-41/56
    telephone: Annotated[str, AfterValidator(_valid_telephone)] | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-42/57
    email: Annotated[str, AfterValidator(_valid_email)] | None = Field(
        default=None, max_length=100
    )  # BT-43/58


class PostalAddress(BaseModel):
    """A postal address (BG-5/8/12/15).

    CIUS-RO requires the street and city everywhere an address appears
    (BR-RO-080/090/140/150/180/200); the county (``CountrySubentity``) is
    required for Romanian addresses and must be an ISO 3166-2:RO code
    (BR-RO-110), with Bucharest city names drawn from the SECTOR list
    (BR-RO-100) — ``"sector 3"`` is normalised to ``"SECTOR3"``.
    """

    street: str = Field(min_length=1, max_length=150)  # BT-35/50/64/75
    additional_street: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-36/51/65/76
    address_line: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-162..165
    city: str = Field(min_length=1, max_length=50)  # BT-37/52/66/77
    postal_zone: str | None = Field(
        default=None, min_length=1, max_length=20
    )  # BT-38/53/67/78
    county: str | None = Field(
        default=None,
        min_length=1,
        description="CountrySubentity (BT-39/54/68/79); for country RO an "
        "ISO 3166-2:RO code such as 'RO-B' or 'RO-CJ'.",
    )
    country: _Country  # BT-40/55/69/80

    @model_validator(mode="after")
    def _romanian_subdivisions(self, info: ValidationInfo) -> PostalAddress:
        if self.country != "RO" or _derived(info):
            # Reading keeps the issuer's own spelling, so a round-trip stays
            # byte-stable and an off-list county never costs the whole document.
            return self
        if self.county not in RO_COUNTY_CODES:
            raise ValueError(
                "a Romanian address requires an ISO 3166-2:RO county code "
                f"('RO-B', 'RO-CJ', ...), got {self.county!r}"
            )
        if self.county == "RO-B":
            sector = self.city.upper().replace(" ", "")
            if sector not in BUCHAREST_SECTORS:
                raise ValueError(
                    "a Bucharest (RO-B) address takes its sector as the city: "
                    "'SECTOR1' ... 'SECTOR6'"
                )
            self.city = sector
        return self


class ElectronicAddress(BaseModel):
    """An electronic delivery address (BT-34/49) with its mandatory scheme
    (BR-62/63), e.g. ``ElectronicAddress(address="0000000000000", scheme="0088")``."""

    address: str = Field(min_length=1)
    scheme: _EasScheme


class PartyIdentifier(BaseModel):
    """A party identifier (BT-29/46/60); the scheme, when given, is an ISO 6523
    ICD code (BR-CL-10)."""

    id: str = Field(min_length=1)
    scheme: _IcdScheme | None = None


class Party(BaseModel):
    """A buyer (BG-7); also the base of :class:`Seller` (BG-4).

    ``name`` is the legal name (BT-27/44) and the address is mandatory
    (BR-08/10). The VAT identifier must carry its ISO 3166 country prefix
    (BR-CO-09; Greece may use ``EL``, and the rule's own list also admits
    ``1A`` for Kosovo — the one non-alphabetic prefix).
    """

    name: str = Field(min_length=1, max_length=200)  # BT-27/44
    trading_name: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-28/45
    identifiers: list[PartyIdentifier] = []  # BT-29/46
    legal_registration_id: str | None = Field(default=None, min_length=1)  # BT-30/47
    legal_registration_scheme: _IcdScheme | None = None
    vat_id: str | None = Field(
        default=None, pattern=r"^(?:[A-Z]{2}|1A)", min_length=3
    )  # BT-31/48
    tax_registration_id: str | None = Field(
        default=None,
        min_length=1,
        description="Tax registration identifier — the CompanyID of a "
        "PartyTaxScheme whose scheme marker is not 'VAT'. On the seller it is "
        "BT-32, e.g. the plain CUI of a seller not registered for VAT. EN 16931 "
        "gives the buyer no BT-32 counterpart, but CIUS-RO reads the same slot "
        "for the buyer (BR-RO-120 accepts it without a VAT-scheme filter), which "
        "is how RO issuers identify a buyer below the VAT-registration "
        "threshold. Distinct from vat_id (BT-31/48), which carries its country "
        "prefix.",
    )
    tax_registration_scheme: str | None = Field(
        default=None,
        min_length=1,
        description="The scheme marker written alongside tax_registration_id "
        "(TaxScheme/ID). Unconstrained by the code lists — any non-'VAT' value "
        "does the job; the reader keeps the source document's own marker. Left "
        "unset, the renderer writes 'FC' for the seller and '!VAT' for the "
        "buyer, each side's market convention.",
    )
    electronic_address: ElectronicAddress | None = None  # BT-34/49
    address: PostalAddress  # BG-5/8
    contact: Contact | None = None  # BG-6/9

    @model_validator(mode="after")
    def _scheme_needs_id(self, info: ValidationInfo) -> Party:
        if _derived(info):
            return self
        if self.legal_registration_scheme and self.legal_registration_id is None:
            raise ValueError(
                "legal_registration_scheme is set without a legal_registration_id"
            )
        if self.tax_registration_scheme and self.tax_registration_id is None:
            raise ValueError(
                "tax_registration_scheme is set without a tax_registration_id"
            )
        return self


class Seller(Party):
    """The seller (BG-4): a :class:`Party` plus the seller-only terms."""

    additional_legal_info: str | None = Field(
        default=None, min_length=1, max_length=1000
    )  # BT-33


class Payee(BaseModel):
    """The payee (BG-10), when different from the seller (BR-17)."""

    name: str = Field(min_length=1, max_length=200)  # BT-59
    identifier: PartyIdentifier | None = None  # BT-60
    legal_registration_id: str | None = Field(default=None, min_length=1)  # BT-61
    legal_registration_scheme: _IcdScheme | None = None


class TaxRepresentative(BaseModel):
    """The seller's tax representative (BG-11); the VAT identifier (BT-63) and
    postal address (BG-12) are mandatory (BR-56/19)."""

    name: str = Field(min_length=1, max_length=200)  # BT-62
    vat_id: str = Field(pattern=r"^(?:[A-Z]{2}|1A)", min_length=3)  # BT-63
    address: PostalAddress  # BG-12


class Period(BaseModel):
    """An invoicing (BG-14) or line (BG-26) period: at least one bound
    (BR-CO-19/20), end not before start (BR-29/30)."""

    start: dt.date | None = None  # BT-73/134
    end: dt.date | None = None  # BT-74/135

    @model_validator(mode="after")
    def _bounds(self, info: ValidationInfo) -> Period:
        if _derived(info):
            return self
        if self.start is None and self.end is None:
            raise ValueError("a period needs a start date, an end date, or both")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("the period end date precedes its start date")
        return self


class DeliveryInformation(BaseModel):
    """Delivery details (BG-13): recipient (BT-70), location (BT-71), actual
    delivery date (BT-72) and address (BG-15)."""

    recipient_name: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-70
    location_id: str | None = Field(default=None, min_length=1)  # BT-71
    location_scheme: _IcdScheme | None = None
    date: dt.date | None = None  # BT-72
    address: PostalAddress | None = None  # BG-15

    @model_validator(mode="after")
    def _address_needs_county(self, info: ValidationInfo) -> DeliveryInformation:
        # BR-RO-211: unlike the party addresses, a delivery address requires the
        # country subdivision regardless of country.
        if _derived(info):
            return self
        if self.address is not None and self.address.county is None:
            raise ValueError("a delivery address requires the county (BT-79)")
        return self


class CreditTransfer(BaseModel):
    """A credit-transfer account (BG-17); the account identifier is mandatory
    (BR-50)."""

    account_id: str = Field(min_length=1, description="IBAN or account (BT-84).")
    account_name: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-85
    service_provider_id: str | None = Field(
        default=None, min_length=1, description="BIC or provider id (BT-86)."
    )


class PaymentCard(BaseModel):
    """Payment card information (BG-18). Card-security standards allow at most
    the first 6 and last 4 digits of the account number (BR-51, a warning)."""

    number: str = Field(min_length=1)  # BT-87
    holder_name: str | None = Field(default=None, min_length=1, max_length=200)  # BT-88


class DirectDebit(BaseModel):
    """Direct-debit terms (BG-19)."""

    mandate_reference: str | None = Field(default=None, min_length=1)  # BT-89
    creditor_id: str | None = Field(default=None, min_length=1)  # BT-90
    debited_account_id: str | None = Field(default=None, min_length=1)  # BT-91


class PaymentInstructions(BaseModel):
    """Payment instructions (BG-16); the means code (BT-81) is mandatory
    (BR-49) and drawn from UNTDID 4461 — e.g. ``"30"`` credit transfer,
    ``"58"`` SEPA credit transfer, ``"42"`` bank account payment."""

    means_code: _PaymentMeansCode  # BT-81
    means_text: str | None = Field(default=None, min_length=1, max_length=100)  # BT-82
    remittance_information: str | None = Field(
        default=None, min_length=1, max_length=140
    )  # BT-83
    credit_transfers: list[CreditTransfer] = []  # BG-17
    card: PaymentCard | None = None  # BG-18
    direct_debit: DirectDebit | None = None  # BG-19


class _AllowanceChargeBase(BaseModel):
    """Common shape of allowances and charges: a reason (text or code) is
    mandatory (BR-33/38/42/44), amounts carry two decimals (BR-DEC)."""

    amount: _NonNegativeMoney  # BT-92/99/136/141
    base_amount: _NonNegativeMoney | None = None  # BT-93/100/137/142
    percentage: _Rate | None = None  # BT-94/101/138/143
    reason: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-97/104/139/144
    reason_code: str | None = Field(default=None, min_length=1)  # BT-98/105/140/145

    @model_validator(mode="after")
    def _reason_required(self, info: ValidationInfo) -> _AllowanceChargeBase:
        if self.reason is None and self.reason_code is None and not _derived(info):
            raise ValueError("an allowance/charge needs a reason or a reason code")
        return self


class _DocumentAllowanceChargeBase(_AllowanceChargeBase):
    """Document-level allowances/charges additionally carry a VAT category
    (BR-32/37) whose rate follows the category's shape (BR-*-06/07)."""

    vat_category: _VatCategory  # BT-95/102
    vat_rate: _Rate | None = None  # BT-96/103

    @model_validator(mode="after")
    def _rate_shape(self, info: ValidationInfo) -> _DocumentAllowanceChargeBase:
        self.vat_rate = _check_vat_rate_shape(
            self.vat_category,
            self.vat_rate,
            required=True,
            derived=_derived(info),
        )
        return self


class DocumentAllowance(_DocumentAllowanceChargeBase):
    """A document-level allowance (BG-20)."""


class DocumentCharge(_DocumentAllowanceChargeBase):
    """A document-level charge (BG-21)."""


class LineAllowance(_AllowanceChargeBase):
    """An invoice-line allowance (BG-27)."""


class LineCharge(_AllowanceChargeBase):
    """An invoice-line charge (BG-28)."""


class ItemAttribute(BaseModel):
    """An item attribute (BG-32): name and value are both required (BR-54)."""

    name: str = Field(min_length=1, max_length=50)  # BT-160
    value: str = Field(min_length=1, max_length=100)  # BT-161


class ItemClassification(BaseModel):
    """An item classification (BT-158); the scheme is mandatory (BR-65)."""

    code: str = Field(min_length=1)
    scheme: _ClassificationScheme
    scheme_version: str | None = None


class InvoiceLine(BaseModel):
    """One invoice / credit-note line (BG-25) with its item and price flattened in.

    ``net_amount`` (BT-131) is computed from quantity x price and the line
    allowances/charges when omitted; supply it explicitly to reproduce an
    upstream document's own rounding.
    """

    id: str | None = Field(
        default=None,
        min_length=1,
        description="Line identifier (BT-126); filled with the 1-based position "
        "when omitted.",
    )
    note: str | None = Field(default=None, min_length=1, max_length=300)  # BT-127
    object_id: str | None = Field(default=None, min_length=1)  # BT-128
    object_id_scheme: _ObjectScheme | None = None
    quantity: Decimal  # BT-129
    unit: _UnitCode  # BT-130
    net_amount: _Money | None = None  # BT-131
    order_line_reference: str | None = Field(default=None, min_length=1)  # BT-132
    accounting_reference: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-133
    period: Period | None = None  # BG-26
    allowances: list[LineAllowance] = []  # BG-27
    charges: list[LineCharge] = []  # BG-28
    # BT-146 carries no sign constraint: CIUS-RO 1.0.9 comments BR-27 out of the
    # UBL binding ("to correct problems regarding negative values for item net
    # price"), and Romanian practice does file a storno as a type-380 invoice
    # with negative values rather than as a credit note.
    unit_price: Decimal  # BT-146
    price_base_quantity: Annotated[Decimal, AfterValidator(_positive)] | None = (
        None  # BT-149
    )
    price_base_unit: _UnitCode | None = None  # BT-150
    gross_price: Annotated[Decimal, _NonNegative] | None = None  # BT-148 (BR-28)
    price_discount: Annotated[Decimal, _NonNegative] | None = None  # BT-147
    vat_category: _VatCategory  # BT-151 (BR-CO-04)
    vat_rate: _Rate | None = None  # BT-152
    name: str = Field(min_length=1, max_length=100)  # BT-153
    description: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-154
    sellers_item_id: str | None = Field(default=None, min_length=1)  # BT-155
    buyers_item_id: str | None = Field(default=None, min_length=1)  # BT-156
    standard_item_id: str | None = Field(default=None, min_length=1)  # BT-157
    standard_item_scheme: _IcdScheme | None = None
    classifications: list[ItemClassification] = []  # BT-158
    origin_country: _Country | None = None  # BT-159
    attributes: list[ItemAttribute] = Field(default=[], max_length=50)  # BG-32

    @model_validator(mode="after")
    def _shape(self, info: ValidationInfo) -> InvoiceLine:
        derived = _derived(info)
        self.vat_rate = _check_vat_rate_shape(
            self.vat_category, self.vat_rate, required=True, derived=derived
        )
        if derived:
            return self
        # BR-64: the standard item identifier requires its scheme.
        if self.standard_item_id is not None and self.standard_item_scheme is None:
            raise ValueError("standard_item_id (BT-157) requires its scheme (BR-64)")
        if self.object_id_scheme is not None and self.object_id is None:
            raise ValueError("object_id_scheme is set without an object_id")
        return self

    @property
    def effective_net_amount(self) -> Decimal:
        """BT-131: the explicit net amount, else quantity x unit price (per base
        quantity) minus line allowances plus line charges, rounded to 2."""
        if self.net_amount is not None:
            return self.net_amount
        base = self.price_base_quantity or Decimal(1)
        amount = self.quantity * self.unit_price / base
        amount -= sum((a.amount for a in self.allowances), Decimal(0))
        amount += sum((c.amount for c in self.charges), Decimal(0))
        return round2(amount)


class VatBreakdownEntry(BaseModel):
    """One VAT breakdown group (BG-23), keyed by category + rate.

    Amounts left ``None`` are computed from the lines and document-level
    allowances/charges of the same category and rate. Exemption reasons cannot be
    computed: categories E/AE/K/G/O require one (BR-E/AE/IC/G/O-10), which is the
    main reason to pass explicit entries when authoring an exempt invoice. An entry
    written by hand must carry it — that is data hygiene, enforced here; an entry
    :meth:`InvoiceDocument.compute_vat_breakdown` derived has nowhere to get it, so
    it is built without one and :func:`~.rules.validate` reports the missing reason
    as a fatal ``BR-*-10`` finding.
    """

    category: _VatCategory  # BT-118
    rate: _Rate | None = None  # BT-119
    taxable_amount: _Money | None = None  # BT-116
    tax_amount: _Money | None = None  # BT-117
    exemption_reason_code: _ExemptionCode | None = None  # BT-121
    exemption_reason: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-120

    @model_validator(mode="after")
    def _shape(self, info: ValidationInfo) -> VatBreakdownEntry:
        derived = _derived(info)
        self.rate = _check_vat_rate_shape(
            self.category, self.rate, required=True, derived=derived
        )
        if derived:
            return self
        zero_tax = self.category in _ZERO_RATE_CATEGORIES | {VatCategory.NOT_SUBJECT}
        if zero_tax and self.tax_amount:
            raise ValueError(
                f"VAT category {self.category.value} carries a zero tax amount"
            )
        has_reason = self.exemption_reason or self.exemption_reason_code
        if self.category in _EXEMPTION_REASON_CATEGORIES and not has_reason:
            raise ValueError(
                f"VAT category {self.category.value} requires an exemption reason "
                "text or code (BT-120/121)"
            )
        if self.category not in _EXEMPTION_REASON_CATEGORIES and has_reason:
            raise ValueError(
                f"VAT category {self.category.value} takes no exemption reason"
            )
        return self


class Totals(BaseModel):
    """The document totals (BG-22). Every member is optional: whatever is left
    ``None`` is computed (see :meth:`InvoiceDocument.effective_totals`); whatever
    is supplied is preserved and checked by :func:`~.rules.validate`.

    No member is sign-constrained. EN 16931 and CIUS-RO put no such rule on any
    of them, and Romanian practice files a *storno* as a type-380 invoice with
    negative values throughout, so a negative BT-110 is ordinary inbox content.
    Requiring otherwise also made a read storno unrenderable — the computed
    totals are derived from the very amounts that make them negative.
    """

    lines_total: _Money | None = None  # BT-106
    allowance_total: _Money | None = None  # BT-107
    charge_total: _Money | None = None  # BT-108
    tax_exclusive: _Money | None = None  # BT-109
    vat_total: _Money | None = None  # BT-110
    vat_total_tax_currency: _Money | None = None  # BT-111
    tax_inclusive: _Money | None = None  # BT-112
    prepaid: _Money | None = None  # BT-113
    rounding: _Money | None = None  # BT-114
    payable: _Money | None = None  # BT-115


class PrecedingInvoice(BaseModel):
    """A preceding invoice reference (BG-3); the number is mandatory (BR-55).
    CIUS-RO requires at least one on credit notes referencing the corrected
    invoice in practice, and caps them at 500 (BR-RO-A500)."""

    number: str = Field(min_length=1, max_length=200)  # BT-25
    issue_date: dt.date | None = None  # BT-26


class SupportingDocument(BaseModel):
    """An additional supporting document (BG-24); the reference is mandatory
    (BR-52). Embedded content requires its MIME code and filename."""

    reference: str = Field(min_length=1, max_length=200)  # BT-122
    description: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-123
    url: str | None = Field(default=None, min_length=1, max_length=200)  # BT-124
    content: bytes | None = None  # BT-125
    mime_code: _MimeCode | None = None
    filename: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def _embedded_needs_metadata(self, info: ValidationInfo) -> SupportingDocument:
        if _derived(info):
            return self
        if self.content is not None and (self.mime_code is None or not self.filename):
            raise ValueError("embedded content requires mime_code and filename")
        return self


class Note(BaseModel):
    """An invoice note (BG-1): free text (BT-22) with an optional UNCL 4451
    subject qualifier (BT-21); on the wire the two ride one ``cbc:Note`` as
    ``#CODE#text``."""

    text: str = Field(min_length=1, max_length=300)  # BT-22
    subject_code: _NoteSubjectCode | None = None  # BT-21


class InvoiceDocument(BaseModel):
    """A CIUS-RO electronic invoice or credit note, flat and bidirectional.

    Author one with the business fields and let the totals and VAT breakdown be
    computed; or obtain one from wire XML via :func:`~.read.read_invoice` /
    :func:`~.read.parse_invoice`, with every wire amount preserved. Render with
    :func:`~.build.render_invoice`; check the full EN 16931 + CIUS-RO rule set
    with :func:`~.rules.validate`.
    """

    kind: Annotated[DocumentKind, BeforeValidator(_member_by_name(DocumentKind))] = (
        DocumentKind.INVOICE
    )
    number: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"[0-9]",  # BR-RO-010: at least one numeric character
        description="Invoice number (BT-1).",
    )
    issue_date: dt.date  # BT-2
    type_code: (
        Annotated[InvoiceTypeCode, BeforeValidator(_member_by_name(InvoiceTypeCode))]
        | None
    ) = Field(
        default=None,
        description="BT-3; defaults to 380 for an invoice, 381 for a credit note.",
    )
    currency: _Currency  # BT-5
    tax_currency: _Currency | None = None  # BT-6
    vat_point_date: dt.date | None = None  # BT-7
    vat_point_date_code: (
        Annotated[VatPointDateCode, BeforeValidator(_member_by_name(VatPointDateCode))]
        | None
    ) = None  # BT-8
    due_date: dt.date | None = None  # BT-9
    buyer_reference: str | None = Field(default=None, min_length=1)  # BT-10
    project_reference: str | None = Field(default=None, min_length=1)  # BT-11
    contract_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-12
    order_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-13
    sales_order_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-14
    receiving_advice_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-15
    despatch_advice_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-16
    tender_or_lot_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-17
    invoiced_object_id: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # BT-18
    invoiced_object_scheme: _ObjectScheme | None = None
    accounting_reference: str | None = Field(
        default=None, min_length=1, max_length=100
    )  # BT-19
    payment_terms: str | None = Field(
        default=None, min_length=1, max_length=300
    )  # BT-20
    notes: list[Note] = Field(default=[], max_length=20)  # BG-1 (BR-RO-A020)
    invoicing_period: Period | None = None  # BG-14
    preceding_invoices: list[PrecedingInvoice] = Field(
        default=[], max_length=500
    )  # BG-3 (BR-RO-A500)
    seller: Seller  # BG-4
    buyer: Party  # BG-7
    payee: Payee | None = None  # BG-10
    tax_representative: TaxRepresentative | None = None  # BG-11
    delivery: DeliveryInformation | None = None  # BG-13
    payment_instructions: PaymentInstructions | None = None  # BG-16
    allowances: list[DocumentAllowance] = []  # BG-20
    charges: list[DocumentCharge] = []  # BG-21
    supporting_documents: list[SupportingDocument] = Field(
        default=[], max_length=50
    )  # BG-24 (BR-RO-A051)
    lines: list[InvoiceLine] = Field(min_length=1)  # BG-25 (BR-16)
    vat_breakdown: list[VatBreakdownEntry] = []  # BG-23
    totals: Totals | None = None  # BG-22

    @model_validator(mode="after")
    def _shape(self, info: ValidationInfo) -> InvoiceDocument:
        if self.type_code is None:
            self.type_code = (
                InvoiceTypeCode.COMMERCIAL_INVOICE
                if self.kind is DocumentKind.INVOICE
                else InvoiceTypeCode.CREDIT_NOTE
            )
        if _derived(info):
            return self
        allowed = (
            INVOICE_TYPE_CODES
            if self.kind is DocumentKind.INVOICE
            else CREDIT_NOTE_TYPE_CODES
        )
        if self.type_code not in allowed:
            raise ValueError(
                f"type_code {self.type_code.value} is not valid on a "
                f"{self.kind.value.replace('_', ' ')} (BR-RO-020 allows "
                f"{sorted(code.value for code in allowed)})"
            )
        # BR-CO-03: the VAT point date and its code are mutually exclusive.
        if self.vat_point_date is not None and self.vat_point_date_code is not None:
            raise ValueError(
                "vat_point_date (BT-7) and vat_point_date_code (BT-8) are "
                "mutually exclusive (BR-CO-03)"
            )
        # BR-RO-030: a non-RON invoice accounts its VAT in RON.
        if self.currency != "RON" and self.tax_currency != "RON":
            raise ValueError(
                "when the invoice currency is not RON, tax_currency must be "
                "'RON' (BR-RO-030)"
            )
        if self.invoiced_object_scheme and self.invoiced_object_id is None:
            raise ValueError("invoiced_object_scheme is set without an id")
        # UBL's cac:OrderReference cannot carry BT-14 without BT-13: its cbc:ID
        # is schema-mandatory.
        if self.sales_order_reference and self.order_reference is None:
            raise ValueError(
                "sales_order_reference (BT-14) requires order_reference (BT-13)"
            )
        return self

    # --- computed totals & VAT breakdown ------------------------------------

    def _group_amounts(self) -> dict[tuple[VatCategory, Decimal | None], Decimal]:
        """Net amount per (category, rate) group: line nets minus document
        allowances plus document charges (the BR-S/Z/E/AE/IC/G/O-08 sums)."""
        groups: dict[tuple[VatCategory, Decimal | None], Decimal] = {}

        def add(category: VatCategory, rate: Decimal | None, amount: Decimal) -> None:
            key = vat_group_key(category, rate)
            groups[key] = groups.get(key, Decimal(0)) + amount

        for line in self.lines:
            add(line.vat_category, line.vat_rate, line.effective_net_amount)
        for allowance in self.allowances:
            add(allowance.vat_category, allowance.vat_rate, -allowance.amount)
        for charge in self.charges:
            add(charge.vat_category, charge.vat_rate, charge.amount)
        return groups

    def compute_vat_breakdown(self) -> list[VatBreakdownEntry]:
        """The VAT breakdown (BG-23) computed from lines, allowances and charges:
        one entry per (category, rate), tax = taxable x rate rounded to 2
        (BR-CO-17), zero for the exempt-style categories. Exemption reasons are
        carried over from matching explicit :attr:`vat_breakdown` entries."""
        explicit = {
            vat_group_key(entry.category, entry.rate): entry
            for entry in self.vat_breakdown
        }
        entries = []
        for key, amount in sorted(
            self._group_amounts().items(),
            key=lambda item: (item[0][0].value, item[0][1] or Decimal(0)),
        ):
            category, rate = key
            taxable = round2(amount)
            taxes_apply = category not in _ZERO_RATE_CATEGORIES and category not in (
                VatCategory.NOT_SUBJECT,
            )
            tax = (
                round2(taxable * rate / 100)
                if taxes_apply and rate
                else Decimal("0.00")
            )
            match = explicit.get(key)
            entries.append(
                # Built through the derived context: this entry is our output,
                # not the caller's input, so nothing here judges it. An
                # exempt-style group with no matching explicit entry has no
                # reason to carry, and that is rules.validate()'s BR-*-10
                # finding to report, not a crash from inside compute_totals().
                VatBreakdownEntry.model_validate(
                    {
                        "category": category,
                        "rate": rate,
                        "taxable_amount": taxable,
                        "tax_amount": tax,
                        "exemption_reason": match.exemption_reason if match else None,
                        "exemption_reason_code": (
                            match.exemption_reason_code if match else None
                        ),
                    },
                    context=_DERIVED_CONTEXT,
                )
            )
        return entries

    def effective_vat_breakdown(self) -> list[VatBreakdownEntry]:
        """The breakdown to render: the computed one when no explicit entries were
        given; otherwise the explicit entries with any ``None`` amounts filled
        from the matching computed group."""
        computed = self.compute_vat_breakdown()
        if not self.vat_breakdown:
            return computed
        computed_map = {
            vat_group_key(entry.category, entry.rate): entry for entry in computed
        }
        merged = []
        for entry in self.vat_breakdown:
            match = computed_map.get(vat_group_key(entry.category, entry.rate))
            update: dict[str, Decimal | None] = {}
            if entry.taxable_amount is None and match is not None:
                update["taxable_amount"] = match.taxable_amount
            if entry.tax_amount is None and match is not None:
                update["tax_amount"] = match.tax_amount
            merged.append(entry.model_copy(update=update) if update else entry)
        return merged

    def compute_totals(self) -> Totals:
        """The document totals (BG-22) computed per BR-CO-10..16.

        ``prepaid`` and ``rounding`` are never computed (they are facts, not
        sums) and are read from the explicit :attr:`totals`;
        ``vat_total_tax_currency`` (BT-111) needs an exchange rate this library
        does not know, so it also stays explicit-only.
        """
        explicit = self.totals or Totals()
        lines_total = round2(
            sum((line.effective_net_amount for line in self.lines), Decimal(0))
        )
        allowance_total = (
            round2(sum((a.amount for a in self.allowances), Decimal(0)))
            if self.allowances
            else None
        )
        charge_total = (
            round2(sum((c.amount for c in self.charges), Decimal(0)))
            if self.charges
            else None
        )
        tax_exclusive = (
            lines_total - (allowance_total or Decimal(0)) + (charge_total or Decimal(0))
        )
        vat_total = round2(
            sum(
                (
                    entry.tax_amount or Decimal(0)
                    for entry in self.effective_vat_breakdown()
                ),
                Decimal(0),
            )
        )
        tax_inclusive = tax_exclusive + vat_total
        payable = (
            tax_inclusive
            - (explicit.prepaid or Decimal(0))
            + (explicit.rounding or Decimal(0))
        )
        # Derived context, like the breakdown entries above: these are sums of
        # the caller's own amounts, and this method must never raise.
        return Totals.model_validate(
            {
                "lines_total": lines_total,
                "allowance_total": allowance_total,
                "charge_total": charge_total,
                "tax_exclusive": tax_exclusive,
                "vat_total": vat_total,
                "vat_total_tax_currency": explicit.vat_total_tax_currency,
                "tax_inclusive": tax_inclusive,
                "prepaid": explicit.prepaid,
                "rounding": explicit.rounding,
                "payable": payable,
            },
            context=_DERIVED_CONTEXT,
        )

    def effective_totals(self) -> Totals:
        """The totals to render: each member's explicit value when supplied, the
        computed value otherwise."""
        computed = self.compute_totals()
        if self.totals is None:
            return computed
        merged = {
            name: (
                explicit
                if (explicit := getattr(self.totals, name)) is not None
                else getattr(computed, name)
            )
            for name in Totals.model_fields
        }
        return Totals.model_validate(merged, context=_DERIVED_CONTEXT)
