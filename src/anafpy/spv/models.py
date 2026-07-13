"""Value types for the SPV web services (``webserviced.anaf.ro/SPVWS2/rest``).

Everything here mirrors the vendored ClientSPV documentation
(``docs/anaf-reference/spv/api.md``): the inbox message shapes (§2), the
``cerere`` report nomenclature with its per-type parameter requirements (§4),
and the fixed ``motiv`` list for income certificates (§4.2). Per the repo's
hybrid error model, these are *values*; the Romanian ``eroare`` texts become
:class:`~anafpy.exceptions.AnafResponseError` in the client, decorated with the
English hints from :func:`english_error_hint`.

``tip`` is an **open string** on the wire (live-observed values include a
trailing space: ``"DECLARATIE "``), so :class:`SpvMessage` keeps it verbatim
and offers :attr:`SpvMessage.kind` for trimmed comparisons.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from .._transport.base import ROMANIA_TZ, strip_accents

__all__ = [
    "INCOME_CERTIFICATE_REASONS",
    "REPORT_PARAMETER_WIRE_NAMES",
    "MessageList",
    "ReportRequest",
    "ReportRequestResult",
    "ReportType",
    "SpvDocument",
    "SpvEnvelope",
    "SpvMessage",
    "english_error_hint",
    "optional_parameters",
    "required_parameters",
]

# Coerce any non-None JSON value to str (ANAF returns ids both quoted and bare).
_StrNone = Annotated[
    str | None, BeforeValidator(lambda v: None if v is None else str(v))
]
_Str = Annotated[str, BeforeValidator(str)]


def _parse_message_datetime(value: object) -> object:
    """``data_creare`` arrives as ``dd.MM.yyyy HH:mm:ss`` (time added 06.11.2018);
    interpreted in Romania's timezone, ANAF's clock."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=ROMANIA_TZ)
        except ValueError:
            continue
    return value  # let pydantic report the shape error


class SpvMessage(BaseModel):
    """One inbox message from ``listaMesaje``."""

    model_config = ConfigDict(populate_by_name=True)

    id: _Str
    details: str = Field(validation_alias="detalii")
    cif: _Str
    created_at: Annotated[datetime, BeforeValidator(_parse_message_datetime)] = Field(
        validation_alias="data_creare"
    )
    #: The request this message answers (matches a ``cerere``'s ``id_solicitare``).
    request_id: _StrNone = Field(default=None, validation_alias="id_solicitare")
    #: Message type, verbatim from the wire — an open set (``RECIPISA``, ``PLATA``,
    #: ``RASPUNS SOLICITARE``, ``"DECLARATIE "``, ...); compare via :attr:`kind`.
    type_: str = Field(validation_alias="tip")

    @property
    def kind(self) -> str:
        """``type_`` normalised for comparison (trimmed — live-observed values
        carry trailing spaces)."""
        return self.type_.strip()


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item for item in (part.strip() for part in value.split(",")) if item]
    if isinstance(value, int):  # the relaxed serializer can emit a lone CUI bare
        return [str(value)]
    return value


class SpvEnvelope(BaseModel):
    """The identity stamp ANAF puts on every authenticated SPV response.

    ``cnp`` and ``certificate_serial`` identify the certificate the session was
    established with; ``title`` is the response's ``titlu``. All optional: the
    benign no-results ``listaMesaje`` shape carries no identity fields at all.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, validation_alias="titlu")
    #: Certificate holder's identifier.
    cnp: _StrNone = None
    certificate_serial: _StrNone = Field(default=None, validation_alias="serial")


class MessageList(SpvEnvelope):
    """Outcome of ``listaMesaje``.

    ``authorized_cuis`` (the wire's comma-separated ``cui``) is the certificate's
    **authorization inventory** — every CUI/CNP it may query; ``listaMesaje`` is
    the only endpoint that returns it. A benign "no messages in the window"
    answer yields empty ``messages`` with the note kept in ``note``.
    """

    messages: list[SpvMessage] = Field(default_factory=list, validation_alias="mesaje")
    authorized_cuis: Annotated[list[str], BeforeValidator(_split_csv)] = Field(
        default_factory=list, validation_alias="cui"
    )
    #: The benign no-results note, when ANAF answered with one.
    note: str | None = None


class SpvDocument(BaseModel):
    """A document downloaded via ``descarcare`` — usually a PDF."""

    message_id: str
    content: bytes
    media_type: str = "application/pdf"

    @property
    def is_pdf(self) -> bool:
        return self.content.startswith(b"%PDF")


class ReportRequestResult(SpvEnvelope):
    """Outcome of ``cerere`` — the request was **accepted**, not answered.

    The report itself arrives asynchronously as an inbox message whose
    ``request_id`` equals this ``request_id``; download it via ``descarcare``.
    (``cerere`` echoes the envelope's ``cnp``/``serial`` but, unlike
    ``listaMesaje``, no ``cui`` authorization list.)
    """

    request_id: _Str = Field(validation_alias="id_solicitare")
    #: Query parameters echoed back by ANAF.
    parameters: _StrNone = Field(default=None, validation_alias="parametri")


class ReportType(StrEnum):
    """``tip`` values accepted by ``cerere`` (vendored README, verbatim casing).

    Members are named after ANAF's own report names, per the repo convention
    for ANAF-code enums, and are declared ``(value, description)`` — the
    stdlib enum-with-attributes pattern. :attr:`description` is a one-line
    English rendering of the README's per-type explanation (api.md §4.1) so a
    caller choosing a report — the MCP model in particular — sees what each
    one is, not just the bare declaration code; timing and natural-/legal-
    person scope are folded in where the README states them, and parameter
    names are avoided (the library and the MCP tool spell them differently).
    A member declared without a description fails at import time.
    ``CAF`` is deliberately absent — the README states it is not yet
    requestable via the web service.
    """

    #: What the report returns, for callers choosing one.
    description: str

    def __new__(cls, value: str, description: str) -> Self:
        member = str.__new__(cls, value)
        member._value_ = value
        member.description = description
        return member

    D112CONTRIB = (
        "D112Contrib",
        "Social contributions declared by employers in D112 for the natural person",
    )
    OBLIGATII_DE_PLATA = (
        "Obligatii de plata",
        "Unpaid fiscal obligations at the end of the previous month",
    )
    NOTA_OBLIGATIILOR_DE_PLATA = (
        "Nota obligatiilor de plata",
        "Payment note usable at the treasury counter or for remote payment",
    )
    ISTORIC_SPATIU_VIRTUAL = (
        "Istoric Spatiu Virtual",
        "SPV activity history — profile changes and document downloads",
    )
    REGISTRU_INTRARI_IESIRI = (
        "Registru intrari-iesiri",
        "SPV activity history — the register of documents in and out",
    )
    BILANT_ANUAL = (
        "Bilant anual",
        "Annual financial statements for the selected year (the month is "
        "chosen automatically)",
    )
    D300 = ("D300", "VAT return (includes D305)")
    ISTORIC_DECLARATII = (
        "Istoric declaratii",
        "Every valid declaration filed for the selected year — the aggregate "
        "filing history (covers D100, D101, D102, D103, D112, D120, D130, "
        "D300, D301, D390, D394, D710, D205)",
    )
    D390 = (
        "D390",
        "Recapitulative statement of intra-community supplies and acquisitions",
    )
    D100 = (
        "D100",
        "State-budget payment obligations (includes valid D100 and D710)",
    )
    BILANT_SEMESTRIAL = (
        "Bilant semestrial",
        "Half-year financial reports for the selected year",
    )
    ISTORIC_BILANT = (
        "Istoric bilant",
        "History of filed financial statements and half-year reports (latest "
        "valid of each)",
    )
    D205 = (
        "D205",
        "Withholding-tax informative declaration, per income beneficiary",
    )
    D120 = ("D120", "Excise-duty return")
    D101 = ("D101", "Corporate income tax declaration")
    D130 = ("D130", "Domestic-crude-oil tax return")
    D112 = (
        "D112",
        "Social contributions, income tax and insured-persons declaration "
        "for the selected month",
    )
    DATE_IDENTIFICARE = (
        "DATE IDENTIFICARE",
        "The legal person's identification data in ANAF's records at generation time",
    )
    VECTOR_FISCAL = (
        "VECTOR FISCAL",
        "The legal person's fiscal vector at generation time",
    )
    SITUATIE_SINTETICA = (
        "Situatie Sintetica",
        "Debit situation for the previous month; only generated until the "
        "10th of the current month",
    )
    D208 = (
        "D208",
        "Real-estate-transfer withholding tax; half-yearly — month 6 for "
        "semester 1, month 12 for semester 2",
    )
    D301 = ("D301", "Special VAT return")
    INTEROGARI_BANCI = (
        "InterogariBanci",
        "Banks' queries to ANAF about the natural person's income",
    )
    FISA_ROL = (
        "Fisa Rol",
        "Taxpayer sheet from the local tax administration; an optional "
        "branch/working-point CUI narrows it",
    )
    D394 = (
        "D394",
        "Informative declaration on domestic supplies and acquisitions",
    )
    D392 = ("D392", "Informative declaration on goods deliveries and services")
    D393 = (
        "D393",
        "Informative declaration on international road passenger transport "
        "ticket income",
    )
    D180 = ("D180", "Certification note by an active fiscal consultant")
    D311 = (
        "D311",
        "VAT owed by taxpayers whose VAT registration code was cancelled",
    )
    D106 = ("D106", "Informative declaration on shareholder dividends")
    DUPLICAT_RECIPISA = (
        "Duplicat Recipisa",
        "Duplicate of an e-filing receipt named by its registration number, "
        "regenerated at request time",
    )
    ADEVERINTE_VENIT = (
        "Adeverinte Venit",
        "Income certificate for a natural person; the reason (printed on the "
        "certificate) must match ANAF's fixed list exactly",
    )
    D212 = (
        "D212",
        "Duplicate of the natural person's last filed single declaration "
        "(per chapter, latest rectifications)",
    )
    NECONCORDANTE_D112_CNP = (
        "NeconcordanteD112CNP",
        "Details of D112 vs REVISAL mismatches for the natural person",
    )
    NECONCORDANTE_D394 = (
        "NeconcordanteD394",
        "Details of D394 mismatches for the selected start..end month range",
    )


#: Accepted ``motiv`` values for ``Adeverinte Venit``, verbatim from the README
#: (which states the text is matched exactly; its own example uses lowercase
#: ``altele`` — until live-verified, this list is enforced as written).
INCOME_CERTIFICATE_REASONS: tuple[str, ...] = (
    "Sanatate",
    "Cresa",
    "Gradinita",
    "Scoala",
    "Liceu",
    "Facultate",
    "Alocatia pentru copiii nou nascuti",
    "Trusou nou nascuti",
    "Alocatia de stat pentru copii",
    "Indemnizatie ajutor stimulent pentru cresterea copilului",
    "Sprijin financiar acordat la constituirea familiei",
    "Alocatia pentru sustinerea familiei",
    "Alocatia familiala complementara",
    "Somaj si stimularea fortei de munca",
    "Ajutor social",
    "Pensie",
    "Stimulent de insertie",
    "Ajutoare pentru incalzirea locuintei",
    "Ajutoare financiare pentru persoane aflate in extrema dificultate",
    "Cheltuieli cu inmormantarea persoanelor din familiile beneficiare de "
    "ajutor social",
    "Ajutoare de urgenta in caz de calamitati naturale",
    "Indemnizatia Bugetul personal complementar pentru persoana cu handicap",
    "Alocatia de plasament",
    "Indemnizatia pentru insotitor",
    "Alocatia lunara de hrana pentru copiii cu handicap de tip HIV SIDA",
    "Ajutor anual pentru veteranii de razboi",
    "Institutie financiar bancara asigurare etc.",
    "Executor judecatoresc",
    "Autoritati straine",
    "Altele",
)


def required_parameters(type_: ReportType) -> tuple[str, ...]:
    """The parameters a :class:`ReportRequest` must carry for ``type_``
    (model-field names, not wire names).

    Groups per the vendored README's example calls (api.md §4.1 — the groupings
    are inferred from the examples; ANAF's own validation stays the authority
    on any discrepancy). The match is exhaustive over :class:`ReportType`, so
    ``mypy --strict`` flags an unclassified new member as a missing return.
    """
    match type_:
        case (
            ReportType.D112CONTRIB
            | ReportType.OBLIGATII_DE_PLATA
            | ReportType.NOTA_OBLIGATIILOR_DE_PLATA
            | ReportType.ISTORIC_SPATIU_VIRTUAL
            | ReportType.REGISTRU_INTRARI_IESIRI
            | ReportType.DATE_IDENTIFICARE
            | ReportType.VECTOR_FISCAL
            | ReportType.SITUATIE_SINTETICA
            | ReportType.INTEROGARI_BANCI
            | ReportType.ISTORIC_BILANT
            | ReportType.NECONCORDANTE_D112_CNP
            | ReportType.FISA_ROL
        ):
            return ("cui",)
        case (
            ReportType.BILANT_ANUAL
            | ReportType.ISTORIC_DECLARATII
            | ReportType.D205
            | ReportType.D120
            | ReportType.D130
            | ReportType.D101
            | ReportType.D392
            | ReportType.D393
            | ReportType.D106
            | ReportType.BILANT_SEMESTRIAL
            | ReportType.D212
        ):
            return ("cui", "year")
        case (
            ReportType.D300
            | ReportType.D390
            | ReportType.D100
            | ReportType.D112
            | ReportType.D208
            | ReportType.D394
            | ReportType.D301
            | ReportType.D180
            | ReportType.D311
        ):
            return ("cui", "year", "month")
        case ReportType.DUPLICAT_RECIPISA:
            return ("cui", "registration_number")
        case ReportType.ADEVERINTE_VENIT:
            return ("cui", "year", "reason")
        case ReportType.NECONCORDANTE_D394:
            return ("cui", "year", "start_month", "end_month")


def _allowed_parameters(type_: ReportType) -> frozenset[str]:
    allowed = frozenset(required_parameters(type_))
    if type_ is ReportType.FISA_ROL:
        return allowed | {"branch_cui"}
    return allowed


def optional_parameters(type_: ReportType) -> tuple[str, ...]:
    """The parameters ``type_`` accepts but does not require (model-field
    names) — today only ``Fisa Rol``'s optional ``branch_cui``.
    """
    return tuple(sorted(_allowed_parameters(type_) - set(required_parameters(type_))))


#: :class:`ReportRequest` model-field names -> ANAF's ``cerere`` wire names.
#: The single source of truth for the request's parameter surface:
#: :meth:`ReportRequest.wire_params` serializes from it, the per-type validator
#: derives its field list from it, and the MCP nomenclature advertises it. A
#: mismatch with the model's fields fails at import (guard below the class).
REPORT_PARAMETER_WIRE_NAMES: dict[str, str] = {
    "cui": "cui",
    "year": "an",
    "month": "luna",
    "reason": "motiv",
    "registration_number": "numar_inregistrare",
    "branch_cui": "cui_pui",
    "start_month": "lunai",
    "end_month": "lunas",
}


class ReportRequest(BaseModel):
    """A validated ``cerere`` — invalid parameter combinations fail here, before
    any wire call.

    Field names are English; :meth:`wire_params` produces ANAF's Romanian query
    names per :data:`REPORT_PARAMETER_WIRE_NAMES` (``an``, ``luna``, ``motiv``,
    ``numar_inregistrare``, ``cui_pui``, ``lunai``/``lunas``).
    """

    type_: ReportType
    #: The CUI (or CNP) the request is about.
    cui: str = Field(pattern=r"^\d{2,13}$")
    year: int | None = Field(default=None, ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    #: ``Adeverinte Venit`` only; one of :data:`INCOME_CERTIFICATE_REASONS`.
    reason: str | None = None
    #: ``Duplicat Recipisa`` only; e.g. ``INTERNT-140000000-2018``.
    registration_number: str | None = None
    #: ``Fisa Rol`` only (optional): the branch/working point CUI.
    branch_cui: str | None = Field(default=None, pattern=r"^\d{2,13}$")
    #: ``NeconcordanteD394`` only: first/last month of the period.
    start_month: int | None = Field(default=None, ge=1, le=12)
    end_month: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def _check_per_type_parameters(self) -> Self:
        required = required_parameters(self.type_)
        allowed = _allowed_parameters(self.type_)
        optional_fields = tuple(
            name for name in REPORT_PARAMETER_WIRE_NAMES if name != "cui"
        )
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise ValueError(
                f"report type {self.type_.value!r} requires {', '.join(required)} "
                f"(missing: {', '.join(missing)})"
            )
        extraneous = [
            name
            for name in optional_fields
            if name not in allowed and getattr(self, name) is not None
        ]
        if extraneous:
            raise ValueError(
                f"report type {self.type_.value!r} does not take "
                f"{', '.join(extraneous)} (accepted: {', '.join(sorted(allowed))})"
            )
        if self.type_ is ReportType.D208 and self.month not in (6, 12):
            raise ValueError(
                "D208 is half-yearly: month must be 6 (semester 1) or 12 (semester 2)"
            )
        if self.type_ is ReportType.ADEVERINTE_VENIT:
            assert self.reason is not None
            if self.reason not in INCOME_CERTIFICATE_REASONS:
                # Enumerate the accepted values: the caller (human or agent)
                # must map the stated purpose onto one of them, so the error
                # has to carry the list, not just point at it.
                raise ValueError(
                    f"reason {self.reason!r} is not in ANAF's fixed motiv list "
                    "for Adeverinte Venit (the text must match exactly); "
                    "accepted values: " + "; ".join(INCOME_CERTIFICATE_REASONS)
                )
        if (
            self.start_month is not None
            and self.end_month is not None
            and self.start_month > self.end_month
        ):
            raise ValueError("start_month cannot be after end_month")
        return self

    def wire_params(self) -> dict[str, str]:
        """The ``cerere`` query parameters, in ANAF's wire names."""
        params = {"tip": self.type_.value}
        for field, wire_name in REPORT_PARAMETER_WIRE_NAMES.items():
            if (value := getattr(self, field)) is not None:
                params[wire_name] = str(value)
        return params


# Import-time consistency guard: every request field must have a wire name and
# vice versa, or wire_params() would silently drop a parameter from the cerere.
if (
    _unmapped := (set(ReportRequest.model_fields) - {"type_"})
    ^ REPORT_PARAMETER_WIRE_NAMES.keys()
):
    raise RuntimeError(
        f"ReportRequest fields and REPORT_PARAMETER_WIRE_NAMES disagree on: "
        f"{sorted(_unmapped)}"
    )


#: (pattern, hint) pairs for :func:`english_error_hint`; matched accent- and
#: case-insensitively on the verbatim ``eroare`` text (patterns are spelled
#: unaccented and searched on the :func:`strip_accents`-folded text).
_ERROR_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"drept"),
        "the certificate has no SPV rights for this CUI/CNP or message — the "
        "authorized list is the `cui` field of listaMesaje",
    ),
    (
        re.compile(r"nu este corect"),
        "the CUI/CNP is not valid",
    ),
    (
        re.compile(r"obligatori"),
        "mandatory parameters are missing for this report type",
    ),
    (
        re.compile(r"inca nu poate fi solicitat"),
        "this report type is not yet available through the web service",
    ),
    (
        re.compile(r"\bcod\s*\d+"),
        "a technical error on ANAF's side — report the numeric code to "
        "spv.webservice@mfinante.ro",
    ),
)


def english_error_hint(eroare: str) -> str | None:
    """Best-effort English hint for a Romanian SPV ``eroare`` text, or ``None``.

    The verbatim Romanian text stays authoritative and is always surfaced
    alongside; this only orients non-Romanian-speaking callers.
    """
    folded = strip_accents(eroare)
    for pattern, hint in _ERROR_HINTS:
        if pattern.search(folded):
            return hint
    return None
