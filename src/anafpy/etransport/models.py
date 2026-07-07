"""Value types returned by :class:`anafpy.etransport.client.ETransportClient`.

Key differences from e-Factura:
- **Responses are JSON**, not e-Factura's XML ``<header>`` (per the vendored swagger
  specs); the private ``_*Envelope`` models validate the wire shapes.
- ``UploadResult`` carries both ``upload_id`` (``index_incarcare``) **and** ``uit``
  (the transport declaration code returned at upload time — no separate download step).
- ``MessageStatus`` has no ``download_id``; the UIT is already in ``UploadResult``.
- ``Notification`` mirrors the richer JSON returned by ``lista/{zile}/{cif}``, and
  ``InfoList`` / ``InfoItem`` cover the transporter-lookup endpoint; both read ANAF's
  terse wire names via aliases and expose descriptive field names instead.
- **The flat models are bidirectional** — unlike e-Factura's read-only ``FlatInvoice``,
  the ``Flat*`` shapes here both *view* a parsed declaration
  (:func:`read_flat_transport`) and *author* one (:func:`build_etransport` /
  :func:`render_etransport`): e-Transport has no upstream authoring software the way
  invoicing does, and ANAF's XSD is small and fully enumerated, so anafpy translates
  the whole schema instead of passing XML through.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Annotated, Any, assert_never

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
    computed_field,
    model_validator,
)
from xsdata.models.datatype import XmlDate, XmlDateTime

from .._transport.base import ROMANIA_TZ
from ..exceptions import AnafConfigError
from .schema.schema_etr_v2_20230126 import (
    BunuriTransportateType,
    CodBirouVamalType,
    CodJudetType,
    CodPtfType,
    CodScopOperatiuneType,
    CodTaraType,
    CodTipOperatiuneType,
    ConfirmareType,
    CorectieType,
    DateTransportType,
    DeclPostAvarieType,
    DocumenteTransportType,
    ETransport,
    LocatieType,
    LocTraseuRutierType,
    ModifVehiculType,
    NotificareAnterioaraType,
    NotificareType,
    PartenerComercialType,
    TipConfirmareType,
    TipDocumentType,
)

__all__ = [
    "FlatConfirmation",
    "FlatDeletion",
    "FlatPriorNotification",
    "FlatSubmission",
    "FlatTransport",
    "FlatTransportAddress",
    "FlatTransportDocument",
    "FlatTransportGood",
    "FlatTransportLocation",
    "FlatTransportPartner",
    "FlatTransportVehicle",
    "FlatVehicleChange",
    "InfoItem",
    "InfoList",
    "Location",
    "MessageState",
    "MessageStatus",
    "Notification",
    "NotificationMessage",
    "UploadResult",
    "build_etransport",
    "parse_etransport_document",
    "read_flat_transport",
    "render_etransport",
]

# Coerce any non-None JSON value to str; mirrors the defensive s() helper previously
# used in from_json classmethods (ANAF occasionally returns numeric ids as numbers).
_StrNone = Annotated[
    str | None, BeforeValidator(lambda v: None if v is None else str(v))
]


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
    """Outcome of ``POST /upload/ETRANSP/{cif}/{versiune}``.

    ``upload_id`` (``index_incarcare``) feeds ``get_status``; ``uit`` is the transport
    declaration code available immediately on acceptance; there is no separate download.
    """

    upload_id: str | None
    uit: str | None = None
    errors: list[str] = []
    raw: bytes = b""

    @property
    def accepted(self) -> bool:
        return self.upload_id is not None


class MessageStatus(BaseModel):
    """Outcome of ``GET stareMesaj/{id_incarcare}``."""

    state: MessageState
    errors: list[str] = []
    raw: bytes = b""

    @property
    def is_processing(self) -> bool:
        return self.state is MessageState.PROCESSING

    @property
    def is_terminal(self) -> bool:
        return self.state is not MessageState.PROCESSING


class _AliasedReadModel(BaseModel):
    """Read view over ANAF's terse JSON: descriptive field names, with ANAF's wire
    names kept as validation aliases (``nr_veh`` -> ``plate``, ...). Values are read
    verbatim; ``populate_by_name`` lets callers also construct by the field names."""

    model_config = ConfigDict(populate_by_name=True)


class NotificationMessage(_AliasedReadModel):
    """One entry in a notification's ``mesaje`` array."""

    severity: _StrNone = Field(default=None, alias="tip")  # ERR / WARN / INFO
    message: _StrNone = Field(default=None, alias="mesaj")


class Notification(_AliasedReadModel):
    """One entry from ``GET lista/{zile}/{cif}``.

    Field names follow the flat-model vocabulary (``operation_type``, ``carrier_*``,
    ``plate``, ...); ANAF's wire names remain as aliases.
    """

    # NOT / COR / DEL / CON / MVH
    notification_type: _StrNone = Field(default=None, alias="tip")
    state: _StrNone = Field(default=None, alias="stare")  # OK / ERR
    uit: _StrNone = None
    declarant_code: _StrNone = Field(default=None, alias="cod_decl")
    declarant_ref: _StrNone = Field(default=None, alias="ref_decl")
    post_incident: _StrNone = Field(default=None, alias="post_avarie")  # D / N
    source: _StrNone = Field(default=None, alias="sursa")  # A = API, I = web app
    upload_id: _StrNone = Field(default=None, alias="id_incarcare")
    created_at: _StrNone = Field(default=None, alias="data_creare")
    modified_at: _StrNone = Field(default=None, alias="data_modif")
    operation_type: _StrNone = Field(default=None, alias="tip_op")  # 10/12/../70
    transport_date: _StrNone = Field(default=None, alias="data_transp")
    partner_country: _StrNone = Field(default=None, alias="pc_tara")
    partner_code: _StrNone = Field(default=None, alias="pc_cod")
    partner_name: _StrNone = Field(default=None, alias="pc_den")
    carrier_country: _StrNone = Field(default=None, alias="tr_tara")
    carrier_code: _StrNone = Field(default=None, alias="tr_cod")
    carrier_name: _StrNone = Field(default=None, alias="tr_den")
    plate: _StrNone = Field(default=None, alias="nr_veh")
    trailer1: _StrNone = Field(default=None, alias="nr_rem1")
    trailer2: _StrNone = Field(default=None, alias="nr_rem2")
    goods_count: _StrNone = Field(default=None, alias="nr_linii")
    total_net_weight: _StrNone = Field(default=None, alias="gr_tot_neta")
    total_gross_weight: _StrNone = Field(default=None, alias="gr_tot_bruta")
    total_value: _StrNone = Field(default=None, alias="val_tot")
    messages: list[NotificationMessage] = Field(default_factory=list, alias="mesaje")


class Location(_AliasedReadModel):
    """A ``loc_start`` or ``loc_final`` from an ``info`` record."""

    # PTF = border / BV = customs / ADR = national address
    location_type: _StrNone = Field(default=None, alias="tip_loc")
    full_address: _StrNone = Field(default=None, alias="adresa_completa")
    county: _StrNone = Field(default=None, alias="judet")
    locality: _StrNone = Field(default=None, alias="localitate")
    street: _StrNone = Field(default=None, alias="strada")
    number: _StrNone = Field(default=None, alias="numar")


class InfoItem(_AliasedReadModel):
    """One record from ``GET info?cui_op=...``."""

    id: _StrNone = None
    uit: _StrNone = None
    declarant_code: _StrNone = Field(default=None, alias="cod_decl")
    declarant_name: _StrNone = Field(default=None, alias="den_decl")
    declarant_ref: _StrNone = Field(default=None, alias="ref_decl")
    transport_date: _StrNone = Field(default=None, alias="data_transp")
    uit_expiry: _StrNone = Field(default=None, alias="data_exp_uit")
    carrier_country: _StrNone = Field(default=None, alias="tr_tara")
    carrier_code: _StrNone = Field(default=None, alias="tr_cod")
    carrier_name: _StrNone = Field(default=None, alias="tr_den")
    plate: _StrNone = Field(default=None, alias="nr_veh")
    trailer1: _StrNone = Field(default=None, alias="nr_rem1")
    trailer2: _StrNone = Field(default=None, alias="nr_rem2")
    start_location: Location | None = Field(default=None, alias="loc_start")
    end_location: Location | None = Field(default=None, alias="loc_final")


class InfoList(BaseModel):
    """Response from ``GET info?cui_op=...``.

    ``error`` carries ANAF's benign "no results" note (with ``items`` empty);
    genuine query errors are raised by the client, never returned here.
    """

    items: list[InfoItem] = []
    error: str | None = None
    raw: bytes = b""


# --- wire envelopes: JSON response shapes per the vendored swagger specs -------------
#
# e-Transport answers JSON (unlike e-Factura's XML ``<header>``): ``upload`` and
# ``stareMesaj`` return a flat object with an ``Errors[{errorMessage}]`` array, and
# ``lista`` wraps notifications in ``mesaje[]`` (plus ``serial``/``cui``/``titlu``,
# ignored). Validation-only shapes — not part of the public surface.


class _WireError(BaseModel):
    """One ``Errors[]`` entry."""

    error_message: _StrNone = Field(default=None, alias="errorMessage")


class _JsonEnvelope(BaseModel):
    """Base for e-Transport JSON responses: the shared ``Errors[]`` array."""

    errors: list[_WireError] = Field(default_factory=list, alias="Errors")

    @property
    def error_messages(self) -> list[str]:
        return [e.error_message for e in self.errors if e.error_message]


class _UploadEnvelope(_JsonEnvelope):
    """``upload`` response: ``index_incarcare`` + ``UIT`` on acceptance."""

    upload_index: _StrNone = Field(default=None, alias="index_incarcare")
    uit: _StrNone = Field(default=None, alias="UIT")


class _StatusEnvelope(_JsonEnvelope):
    """``stareMesaj`` response: ``stare`` (ok|nok) plus any ``Errors[]``."""

    state: _StrNone = Field(default=None, alias="stare")


class _ListaEnvelope(_JsonEnvelope):
    """``lista`` response: notifications under ``mesaje[]``."""

    messages: list[Notification] = Field(default_factory=list, alias="mesaje")


class _InfoEnvelope(_JsonEnvelope):
    """``info`` response object shape.

    Its no-results/error case rides a **top-level singular ``error`` string**
    (``{"error": "Nu exista informatii pentru aceasta solicitare", ...}`` —
    live-confirmed against TEST 2026-07-02), *not* the ``Errors[]`` array the other
    endpoints use; tolerate both here so ``info`` never masquerades a benign
    no-results as an unrecognised body. The client splits the collected messages
    like the list endpoints do: no-results is returned, real errors raise.
    """

    error: _StrNone = None

    @property
    def all_error_messages(self) -> list[str]:
        messages = list(self.error_messages)
        if self.error:
            messages.append(self.error)
        return messages


# --- flat models: e-Transport XSD <-> easy-to-read shapes ----------------------------
#
# Bidirectional, unlike e-Factura's read-only flat view: the same models render the
# preview of a parsed declaration (``read_flat_transport``) and author a new one
# (``build_etransport`` / ``render_etransport``). Enum-coded fields are typed with the
# generated XSD enums and accept either the ANAF code (``30``) or the member name
# (``"TTN"``, ``"CLUJ"``, ``"NADLAC"``); they serialize as the member name so previews
# stay human-readable. Their declared JSON schema is a plain string — pydantic's
# enum schema would list only the raw codes, which neither matches what validation
# accepts (names too) nor what serialization emits (names), and MCP clients validate
# tool output against it. The only structure not carried is the XSD's unused
# ``xs:any`` extension hooks.
#
# Field constraints mirror the XSD *tightened by ANAF's Schematron*
# (``docs/anaf-reference/_sources/eTransport-validation_v.2.0.2_12082024.sch``) where
# the Schematron rule is unconditional — a pure format or single-model consistency
# check (UIT check digits BR-019, gross >= net BR-020, no leading zero in the
# declarant code BR-002, ...): data violating those is rejected by ANAF with
# certainty, so failing fast at construction is a kindness, not a rule engine. The
# Schematron's *operation-type conditional* rules (partner country vs operation,
# purpose-code matrices, border-point/customs-office direction rules) are ANAF
# policy that changes across revisions; they stay ANAF's to enforce on upload —
# here they appear only as field descriptions so composing callers (the MCP model)
# know about them. Per docs/design.md §4/§5: no local rule engine, prepare never blocks.


def _member_or_value(enum_cls: type[Enum]) -> Callable[[object], object]:
    """Coerce an enum member NAME (case/space/dash-insensitive) or numeric string to
    something pydantic's own enum validation accepts; other values pass through."""

    def coerce(value: object) -> object:
        if isinstance(value, str):
            key = value.strip().upper().replace(" ", "_").replace("-", "_")
            if key in enum_cls.__members__:
                return enum_cls[key]
            if key.isdigit():
                return int(key)
        return value

    return coerce


_AS_NAME = PlainSerializer(lambda member: member.name, return_type=str)
_STR_SCHEMA = WithJsonSchema({"type": "string"})

_OperationType = Annotated[
    CodTipOperatiuneType,
    BeforeValidator(_member_or_value(CodTipOperatiuneType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(
        description="ANAF operation type: the sigla name ('TTN', 'AIC', 'LIC', "
        "'IMP', 'EXP', ...) or its numeric code (30, 10, 20, 40, 50, ...)."
    ),
]
_OperationScope = Annotated[
    CodScopOperatiuneType,
    BeforeValidator(_member_or_value(CodScopOperatiuneType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(
        description="Operation scope: member name ('COMERCIALIZARE', ...) or "
        "numeric code (101, ...). ANAF ties the accepted scopes to the operation "
        "type — TTN: COMERCIALIZARE, TRANSFER_INTRE_GESTIUNI, "
        "BUNURI_PUSE_LA_DISPOZITIA_CLIENTULUI or ALTELE; LIC: COMERCIALIZARE, "
        "GRATUITATI, OPERATIUNI_DE_LIVRARE_CU_INSTALARE, "
        "LEASING_FINANCIAR_OPERATIONAL, BUNURI_IN_GARANTIE or ALTELE; AIC: every "
        "scope except the TTN-only transfers and ACELASI_CU_OPERATIUNEA; every "
        "other operation type takes ACELASI_CU_OPERATIUNEA (9999)."
    ),
]
_County = Annotated[
    CodJudetType,
    BeforeValidator(_member_or_value(CodJudetType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(description="County: name ('CLUJ', 'MUNICIPIUL_BUCURESTI') or ANAF code."),
]


def _still_accepted_country(member: CodTaraType) -> CodTaraType:
    # The XSD still lists 'AN' (Netherlands Antilles) but ANAF's Schematron country
    # list (BR-CL-001/BR-CL-010) dropped it, so an 'AN' filing is rejected on upload.
    if member is CodTaraType.NETHERLANDS_ANTILLES:
        raise ValueError(
            "country 'AN' (Netherlands Antilles) is in the XSD but no longer "
            "accepted by ANAF; use the successor codes 'BQ', 'CW' or 'SX'"
        )
    return member


_Country = Annotated[
    CodTaraType,
    BeforeValidator(_member_or_value(CodTaraType)),
    AfterValidator(_still_accepted_country),
    _AS_NAME,
    _STR_SCHEMA,
    Field(description="Country: ISO-3166 alpha-2 code ('RO') or name ('ROMANIA')."),
]
_BorderPoint = Annotated[
    CodPtfType,
    BeforeValidator(_member_or_value(CodPtfType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(description="Border crossing point: name ('NADLAC', ...) or ANAF code."),
]
_CustomsOffice = Annotated[
    CodBirouVamalType,
    BeforeValidator(_member_or_value(CodBirouVamalType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(description="Customs office: name ('BVI_CLUJ_NAPOCA', ...) or ANAF code."),
]
_DocumentType = Annotated[
    TipDocumentType,
    BeforeValidator(_member_or_value(TipDocumentType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(
        description="Document type: 'CMR', 'FACTURA', 'AVIZ_DE_INSOTIRE_A_MARFII', "
        "'ALTELE' — or the ANAF code (10/20/30/9999)."
    ),
]
_ConfirmationType = Annotated[
    TipConfirmareType,
    BeforeValidator(_member_or_value(TipConfirmareType)),
    _AS_NAME,
    _STR_SCHEMA,
    Field(description="'CONFIRMAT' (10), 'CONFIRMAT_PARTIAL' (20) or 'INFIRMAT' (30)."),
]


def _clean_code(value: object) -> object:
    """Normalize a UIT / plate-style code: strip separators, uppercase."""
    if isinstance(value, str):
        return re.sub(r"[\s.-]", "", value).upper()
    return value


def _uit_check_digits(value: str) -> str:
    # BR-019 (also stated in the XSD's UitType note): the last 2 characters are the
    # last two digits of the sum of the ASCII codes of the first 14. A mismatch
    # means the code was mistyped, so fail before filing against a wrong UIT.
    expected = str(sum(ord(char) for char in value[:14]))[-2:]
    if value[14:] != expected:
        raise ValueError(
            f"UIT check digits {value[14:]!r} do not match the first 14 characters "
            f"(expected {expected!r}) — the code was mistyped or truncated"
        )
    return value


_Uit = Annotated[
    str,
    BeforeValidator(_clean_code),
    AfterValidator(_uit_check_digits),
    Field(
        pattern=r"^[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}$",
        description="The 16-character UIT code ANAF issued for the declaration.",
    ),
]
_Plate = Annotated[
    str,
    BeforeValidator(_clean_code),
    Field(pattern=r"^[0-9A-Z]{2,20}$", description="Vehicle registration plate."),
]
_TrailerPlate = Annotated[
    str,
    BeforeValidator(_clean_code),
    Field(pattern=r"^[0-9A-Z]{2,20}$", description="Trailer registration plate."),
]
# The XSD's 12.2 shape is 12 integer digits + 2 decimals; a max_digits budget would
# wrongly admit 13 integer digits when fewer decimals are used.
_Quantity = Annotated[Decimal, Field(gt=0, lt=Decimal(10**12), decimal_places=2)]


class FlatTransportPartner(BaseModel):
    """Commercial partner of the transport."""

    name: str = Field(min_length=1, max_length=200)
    country: _Country
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Partner fiscal code. For domestic transport (TTN) ANAF "
        "requires it: a valid Romanian code, or the literal 'PF' for a private "
        "individual whose code is unknown.",
    )


class FlatTransportVehicle(BaseModel):
    """Vehicle, carrier, and transport-date details."""

    plate: _Plate
    trailer1: _TrailerPlate | None = None
    trailer2: _TrailerPlate | None = None
    carrier_name: str = Field(min_length=1, max_length=200)
    carrier_country: _Country
    carrier_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Carrier fiscal code. When carrier_country is RO, ANAF "
        "requires a valid Romanian code ('PF' accepted for a private individual "
        "on domestic transport).",
    )
    transport_date: dt.date


class FlatTransportAddress(BaseModel):
    """A national address at one end of the road route."""

    # The Schematron (BR-214/BR-215) wants at least 2 characters here, one more
    # than the XSD's Str100.
    county: _County
    locality: str = Field(min_length=2, max_length=100)
    street: str = Field(min_length=2, max_length=100)
    number: str | None = Field(default=None, min_length=1, max_length=20)
    block: str | None = Field(default=None, min_length=1, max_length=30)
    entrance: str | None = Field(default=None, min_length=1, max_length=20)
    floor: str | None = Field(default=None, min_length=1, max_length=20)
    apartment: str | None = Field(default=None, min_length=1, max_length=20)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    other: str | None = Field(default=None, min_length=1, max_length=200)


class FlatTransportLocation(BaseModel):
    """One end of the road route: exactly one of ``border_point`` (PTF),
    ``customs_office`` (BV), or a national ``address``.

    Which one ANAF expects depends on the operation type: a domestic ``TTN`` uses
    addresses at both ends; inbound operations (AIC/LHI/SCI/IMP/DIN) start at a
    border point or customs office, outbound ones (LIC/LHE/SCE/EXP/DIE) end at
    one; a customs office is only valid at the start of an import (IMP) or the
    end of an export (EXP). ANAF validates all of that on upload.
    """

    border_point: _BorderPoint | None = None
    customs_office: _CustomsOffice | None = None
    address: FlatTransportAddress | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> FlatTransportLocation:
        set_count = sum(
            v is not None
            for v in (self.border_point, self.customs_office, self.address)
        )
        if set_count != 1:
            raise ValueError(
                "set exactly one of border_point / customs_office / address"
            )
        return self


class FlatTransportGood(BaseModel):
    """One transported-goods line."""

    operation_scope: _OperationScope
    name: str = Field(min_length=1, max_length=200)
    quantity: _Quantity
    unit_code: str = Field(
        pattern=r"^[0-9A-Z]{2,3}$",
        description="UN/ECE Rec 20/21 unit code, e.g. 'KGM' (kg), 'LTR', 'H87' "
        "(piece). ANAF validates against the full closed list — 'KG' or 'PCS' "
        "are not on it.",
    )
    gross_weight: _Quantity = Field(description="Gross weight in kg.")
    net_weight: _Quantity | None = Field(
        default=None,
        description="Net weight in kg. ANAF requires it for every operation type "
        "except DIN/DIE (60/70).",
    )
    tariff_code: str | None = Field(
        default=None,
        pattern=r"^([0-9]{4}|[0-9]{6}|[0-9]{8})$",
        description="NC tariff code (4, 6 or 8 digits). ANAF requires it for "
        "every operation type except DIN/DIE (60/70).",
    )
    value_ron: Decimal | None = Field(
        default=None,
        ge=0,
        lt=Decimal(10**12),
        decimal_places=2,
        description="Value in RON without VAT. ANAF requires it for every "
        "operation type except DIN/DIE (60/70).",
    )
    line_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Declarant's own reference for this line.",
    )

    @model_validator(mode="after")
    def _gross_covers_net(self) -> FlatTransportGood:
        # BR-020: a line's gross weight must be >= its net weight.
        if self.net_weight is not None and self.gross_weight < self.net_weight:
            raise ValueError(
                f"gross_weight ({self.gross_weight}) must be greater than or "
                f"equal to net_weight ({self.net_weight})"
            )
        return self


class FlatTransportDocument(BaseModel):
    """A transport document reference (CMR, invoice, ...)."""

    doc_type: _DocumentType
    date: dt.date
    number: str | None = Field(default=None, min_length=1, max_length=50)
    note: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def _other_needs_note(self) -> FlatTransportDocument:
        # BR-026: 'Altele' says nothing about the document, so ANAF wants the note
        # to say what it is.
        if self.doc_type is TipDocumentType.ALTELE and self.note is None:
            raise ValueError(
                "doc_type 'ALTELE' (9999) requires a note naming the document"
            )
        return self


class FlatPriorNotification(BaseModel):
    """A reference to a prior declaration (``notificareAnterioara``)."""

    uit: _Uit
    note: str | None = Field(default=None, min_length=1, max_length=200)
    declarant_ref: str | None = Field(default=None, min_length=1, max_length=50)


class _FlatSubmissionBase(BaseModel):
    """Root attributes shared by every flat e-Transport document."""

    # The Schematron's TIN regex (BR-002) forbids a leading zero, which the XSD's
    # CodDeclarantType pattern would allow.
    declarant_code: str | None = Field(
        default=None,
        pattern=r"^([1-9]\d{12}|[1-9]\d{1,9})$",
        description="Declarant CUI/CNP; filled from the upload CIF when omitted.",
    )
    declarant_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Declarant's own reference for this filing.",
    )
    post_incident: bool = Field(
        default=False,
        description="True only for a declaration filed post-incident (declPostAvarie).",
    )


class FlatTransport(_FlatSubmissionBase):
    """An e-Transport declaration in an easy-to-read shape.

    The same model authors a declaration (see :func:`build_etransport` /
    :func:`render_etransport`, or the client's ``upload_document``) and views a
    parsed one (:func:`read_flat_transport`). Set ``correction_of_uit`` to file it
    as a correction of an already-issued UIT.
    """

    operation_type: _OperationType
    correction_of_uit: _Uit | None = None
    partner: FlatTransportPartner
    vehicle: FlatTransportVehicle
    start_location: FlatTransportLocation
    end_location: FlatTransportLocation
    goods: list[FlatTransportGood] = Field(min_length=1)
    documents: list[FlatTransportDocument] = Field(min_length=1)
    prior_notifications: list[FlatPriorNotification] = Field(
        default=[],
        description="References to prior declarations. Only meaningful for the "
        "intra-community operations (AIC/LHI/SCI/LIC/LHE/SCE); ANAF rejects them "
        "for TTN, IMP, EXP, DIN and DIE.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def goods_count(self) -> int:
        return len(self.goods)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_gross_weight(self) -> Decimal:
        return sum((g.gross_weight for g in self.goods), Decimal(0))


class FlatDeletion(_FlatSubmissionBase):
    """Deletion (``stergere``) of an issued UIT."""

    uit: _Uit


class FlatConfirmation(_FlatSubmissionBase):
    """Confirmation (``confirmare``) of an issued UIT."""

    uit: _Uit
    confirmation_type: _ConfirmationType
    note: str | None = Field(default=None, min_length=1, max_length=200)


class FlatVehicleChange(_FlatSubmissionBase):
    """Vehicle change (``modifVehicul``) on an issued UIT."""

    uit: _Uit
    plate: _Plate
    trailer1: _TrailerPlate | None = None
    trailer2: _TrailerPlate | None = None
    changed_at: dt.datetime | None = Field(
        default=None,
        description="When the vehicle changed; defaults to now, Romania time.",
    )
    note: str | None = Field(default=None, min_length=1, max_length=200)


type FlatSubmission = (
    FlatTransport | FlatDeletion | FlatConfirmation | FlatVehicleChange
)
"""The four documents that can be filed with e-Transport."""


def parse_etransport_document(xml: bytes) -> ETransport | None:
    """Parse e-Transport wire XML into its :class:`ETransport` model, or ``None`` when
    the bytes are not a parseable declaration. Never raises on bad input."""
    from xsdata.exceptions import ParserError
    from xsdata_pydantic.bindings import XmlParser

    try:
        return XmlParser().from_bytes(xml, ETransport)
    except (ParserError, ValueError):
        return None


# --- read: parsed XSD models -> flat ------------------------------------------------


def read_flat_transport(doc: ETransport) -> FlatSubmission:
    """Translate a parsed :class:`ETransport` document to its flat model.

    Full translation: every XSD field maps onto the flat shape (only the schema's
    unused ``xs:any`` extension hooks are not carried). Raises :class:`ValueError`
    (or a pydantic ``ValidationError``) for a document that carries none of the four
    operations or otherwise cannot be represented.
    """
    root = _read_root(doc)
    if doc.notificare is not None:
        return _read_declaration(doc.notificare, root)
    if doc.stergere is not None:
        return FlatDeletion(uit=doc.stergere.uit, **root)
    if doc.confirmare is not None:
        return FlatConfirmation(
            uit=doc.confirmare.uit,
            confirmation_type=doc.confirmare.tip_confirmare,
            note=doc.confirmare.observatii,
            **root,
        )
    if doc.modif_vehicul is not None:
        change = doc.modif_vehicul
        return FlatVehicleChange(
            uit=change.uit,
            plate=change.nr_vehicul,
            trailer1=change.nr_remorca1,
            trailer2=change.nr_remorca2,
            changed_at=change.data_modificare.to_datetime(),
            note=change.observatii,
            **root,
        )
    raise ValueError(
        "eTransport document carries none of notificare / stergere / confirmare / "
        "modifVehicul"
    )


def _read_root(doc: ETransport) -> dict[str, Any]:
    return {
        "declarant_code": doc.cod_declarant,
        "declarant_ref": doc.ref_declarant,
        "post_incident": doc.decl_post_avarie is not None,
    }


def _read_declaration(notif: NotificareType, root: dict[str, Any]) -> FlatTransport:
    transport = notif.date_transport
    partner = notif.partener_comercial
    return FlatTransport(
        operation_type=notif.cod_tip_operatiune,
        correction_of_uit=notif.corectie.uit if notif.corectie is not None else None,
        partner=FlatTransportPartner(
            name=partner.denumire, country=partner.cod_tara, code=partner.cod
        ),
        vehicle=FlatTransportVehicle(
            plate=transport.nr_vehicul,
            trailer1=transport.nr_remorca1,
            trailer2=transport.nr_remorca2,
            carrier_name=transport.denumire_org_transport,
            carrier_country=transport.cod_tara_org_transport,
            carrier_code=transport.cod_org_transport,
            transport_date=transport.data_transport.to_date(),
        ),
        start_location=_read_route_point(notif.loc_start_traseu_rutier),
        end_location=_read_route_point(notif.loc_final_traseu_rutier),
        goods=[_read_good(g) for g in notif.bunuri_transportate],
        documents=[
            FlatTransportDocument(
                doc_type=d.tip_document,
                date=d.data_document.to_date(),
                number=d.numar_document,
                note=d.observatii,
            )
            for d in notif.documente_transport
        ],
        prior_notifications=[
            FlatPriorNotification(
                uit=p.uit, note=p.observatii, declarant_ref=p.ref_declarant
            )
            for p in notif.notificare_anterioara
        ],
        **root,
    )


def _read_route_point(point: LocTraseuRutierType) -> FlatTransportLocation:
    address = None
    if (loc := point.locatie) is not None:
        address = FlatTransportAddress(
            county=loc.cod_judet,
            locality=loc.denumire_localitate,
            street=loc.denumire_strada,
            number=loc.numar,
            block=loc.bloc,
            entrance=loc.scara,
            floor=loc.etaj,
            apartment=loc.apartament,
            postal_code=loc.cod_postal,
            other=loc.alte_info,
        )
    return FlatTransportLocation(
        border_point=point.cod_ptf,
        customs_office=point.cod_birou_vamal,
        address=address,
    )


def _read_good(good: BunuriTransportateType) -> FlatTransportGood:
    return FlatTransportGood(
        operation_scope=good.cod_scop_operatiune,
        name=good.denumire_marfa,
        quantity=_decimal(good.cantitate),
        unit_code=good.cod_unitate_masura,
        gross_weight=_decimal(good.greutate_bruta),
        net_weight=_decimal(good.greutate_neta) if good.greutate_neta else None,
        tariff_code=good.cod_tarifar,
        value_ron=(
            _decimal(good.valoare_lei_fara_tva) if good.valoare_lei_fara_tva else None
        ),
        line_ref=good.ref_declarant,
    )


def _decimal(value: str) -> Decimal:
    """Convert a wire numeric to :class:`Decimal`, raising :class:`ValueError`.

    The XML parser does not enforce the XSD numeric patterns, and a bare
    ``Decimal(...)`` raises ``decimal.InvalidOperation`` (an ``ArithmeticError``) —
    outside the ``ValueError`` contract :func:`read_flat_transport` documents.
    """
    try:
        return Decimal(value)
    except ArithmeticError as exc:
        raise ValueError(f"invalid numeric value in eTransport XML: {value!r}") from exc


# --- build: flat -> XSD models -> wire XML -------------------------------------------


def build_etransport(
    document: FlatSubmission, *, declarant_code: str | None = None
) -> ETransport:
    """Compose a flat document into the :class:`ETransport` wire model.

    ``cod_declarant`` comes from the model's ``declarant_code`` or the
    ``declarant_code`` argument (typically the upload CIF); setting both to
    different values raises :class:`AnafConfigError`, as does setting neither.
    """
    code = document.declarant_code or declarant_code
    if code is None:
        raise AnafConfigError(
            "declarant_code is required: set it on the document or pass it "
            "(typically the upload CIF)"
        )
    if (
        document.declarant_code is not None
        and declarant_code is not None
        and document.declarant_code != declarant_code
    ):
        raise AnafConfigError(
            f"declarant_code mismatch: document says "
            f"{document.declarant_code!r}, caller says {declarant_code!r}"
        )
    root = ETransport(
        cod_declarant=code,
        ref_declarant=document.declarant_ref,
        decl_post_avarie=DeclPostAvarieType.D if document.post_incident else None,
    )
    if isinstance(document, FlatTransport):
        root.notificare = _build_notificare(document)
    elif isinstance(document, FlatDeletion):
        root.stergere = CorectieType(uit=document.uit)
    elif isinstance(document, FlatConfirmation):
        root.confirmare = ConfirmareType(
            uit=document.uit,
            tip_confirmare=document.confirmation_type,
            observatii=document.note,
        )
    elif isinstance(document, FlatVehicleChange):
        # ANAF's documented dataModificare format is second-precision (BR-203).
        # The default is Romania *wall* time, kept naive so the rendered
        # xs:dateTime carries no offset; a caller-supplied value is used as-is.
        changed_at = (document.changed_at or _now_romania()).replace(microsecond=0)
        root.modif_vehicul = ModifVehiculType(
            uit=document.uit,
            nr_vehicul=document.plate,
            nr_remorca1=document.trailer1,
            nr_remorca2=document.trailer2,
            data_modificare=XmlDateTime.from_datetime(changed_at),
            observatii=document.note,
        )
    else:
        assert_never(document)
    return root


def render_etransport(
    document: FlatSubmission, *, declarant_code: str | None = None
) -> bytes:
    """Compose a flat document and serialize it to upload-ready UTF-8 XML bytes."""
    from xsdata_pydantic.bindings import XmlSerializer

    model = build_etransport(document, declarant_code=declarant_code)
    return XmlSerializer().render(model).encode("utf-8")


def _build_notificare(flat: FlatTransport) -> NotificareType:
    vehicle = flat.vehicle
    return NotificareType(
        cod_tip_operatiune=flat.operation_type,
        corectie=(
            CorectieType(uit=flat.correction_of_uit)
            if flat.correction_of_uit is not None
            else None
        ),
        bunuri_transportate=[_build_good(g) for g in flat.goods],
        partener_comercial=PartenerComercialType(
            cod_tara=flat.partner.country,
            cod=flat.partner.code,
            denumire=flat.partner.name,
        ),
        date_transport=DateTransportType(
            nr_vehicul=vehicle.plate,
            nr_remorca1=vehicle.trailer1,
            nr_remorca2=vehicle.trailer2,
            cod_tara_org_transport=vehicle.carrier_country,
            cod_org_transport=vehicle.carrier_code,
            denumire_org_transport=vehicle.carrier_name,
            data_transport=_xml_date(vehicle.transport_date),
        ),
        loc_start_traseu_rutier=_build_route_point(flat.start_location),
        loc_final_traseu_rutier=_build_route_point(flat.end_location),
        documente_transport=[
            DocumenteTransportType(
                tip_document=d.doc_type,
                numar_document=d.number,
                data_document=_xml_date(d.date),
                observatii=d.note,
            )
            for d in flat.documents
        ],
        notificare_anterioara=[
            NotificareAnterioaraType(
                uit=p.uit, observatii=p.note, ref_declarant=p.declarant_ref
            )
            for p in flat.prior_notifications
        ],
    )


def _build_route_point(point: FlatTransportLocation) -> LocTraseuRutierType:
    address = None
    if (a := point.address) is not None:
        address = LocatieType(
            cod_judet=a.county,
            denumire_localitate=a.locality,
            denumire_strada=a.street,
            numar=a.number,
            bloc=a.block,
            scara=a.entrance,
            etaj=a.floor,
            apartament=a.apartment,
            cod_postal=a.postal_code,
            alte_info=a.other,
        )
    return LocTraseuRutierType(
        locatie=address,
        cod_ptf=point.border_point,
        cod_birou_vamal=point.customs_office,
    )


def _build_good(good: FlatTransportGood) -> BunuriTransportateType:
    return BunuriTransportateType(
        cod_scop_operatiune=good.operation_scope,
        cod_tarifar=good.tariff_code,
        denumire_marfa=good.name,
        cantitate=_num(good.quantity),
        cod_unitate_masura=good.unit_code,
        greutate_neta=_num(good.net_weight) if good.net_weight is not None else None,
        greutate_bruta=_num(good.gross_weight),
        valoare_lei_fara_tva=(
            _num(good.value_ron) if good.value_ron is not None else None
        ),
        ref_declarant=good.line_ref,
    )


def _now_romania() -> dt.datetime:
    """Now as naive Romania wall time (ANAF's clock, offset-free on the wire)."""
    return dt.datetime.now(ROMANIA_TZ).replace(tzinfo=None)


def _num(value: Decimal) -> str:
    """Format a decimal per the XSD numeric pattern (at most two decimals)."""
    return str(value.quantize(Decimal("0.01")))


def _xml_date(value: dt.date) -> XmlDate:
    return XmlDate(value.year, value.month, value.day)
