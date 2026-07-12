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

from .._transport.base import ROMANIA_TZ

__all__ = [
    "INCOME_CERTIFICATE_REASONS",
    "MessageList",
    "ReportRequest",
    "ReportRequestResult",
    "ReportType",
    "SpvDocument",
    "SpvEnvelope",
    "SpvMessage",
    "english_error_hint",
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

    Members are named after ANAF's own report names, per the repo convention for
    ANAF-code enums. ``CAF`` is deliberately absent — the README states it is not
    yet requestable via the web service.
    """

    D112CONTRIB = "D112Contrib"
    OBLIGATII_DE_PLATA = "Obligatii de plata"
    NOTA_OBLIGATIILOR_DE_PLATA = "Nota obligatiilor de plata"
    ISTORIC_SPATIU_VIRTUAL = "Istoric Spatiu Virtual"
    REGISTRU_INTRARI_IESIRI = "Registru intrari-iesiri"
    BILANT_ANUAL = "Bilant anual"
    D300 = "D300"
    ISTORIC_DECLARATII = "Istoric declaratii"
    D390 = "D390"
    D100 = "D100"
    BILANT_SEMESTRIAL = "Bilant semestrial"
    ISTORIC_BILANT = "Istoric bilant"
    D205 = "D205"
    D120 = "D120"
    D101 = "D101"
    D130 = "D130"
    D112 = "D112"
    DATE_IDENTIFICARE = "DATE IDENTIFICARE"
    VECTOR_FISCAL = "VECTOR FISCAL"
    SITUATIE_SINTETICA = "Situatie Sintetica"
    D208 = "D208"
    D301 = "D301"
    INTEROGARI_BANCI = "InterogariBanci"
    FISA_ROL = "Fisa Rol"
    D394 = "D394"
    D392 = "D392"
    D393 = "D393"
    D180 = "D180"
    D311 = "D311"
    D106 = "D106"
    DUPLICAT_RECIPISA = "Duplicat Recipisa"
    ADEVERINTE_VENIT = "Adeverinte Venit"
    D212 = "D212"
    NECONCORDANTE_D112_CNP = "NeconcordanteD112CNP"
    NECONCORDANTE_D394 = "NeconcordanteD394"


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


class ReportRequest(BaseModel):
    """A validated ``cerere`` — invalid parameter combinations fail here, before
    any wire call.

    Field names are English; :meth:`wire_params` produces ANAF's Romanian query
    names (``an``, ``luna``, ``motiv``, ``numar_inregistrare``, ``cui_pui``,
    ``lunai``/``lunas``).
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
        optional_fields = (
            "year",
            "month",
            "reason",
            "registration_number",
            "branch_cui",
            "start_month",
            "end_month",
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
        params = {"tip": self.type_.value, "cui": self.cui}
        wire_names = {
            "year": "an",
            "month": "luna",
            "reason": "motiv",
            "registration_number": "numar_inregistrare",
            "branch_cui": "cui_pui",
            "start_month": "lunai",
            "end_month": "lunas",
        }
        for field, wire_name in wire_names.items():
            if (value := getattr(self, field)) is not None:
                params[wire_name] = str(value)
        return params


#: (pattern, hint) pairs for :func:`english_error_hint`; matched accent- and
#: case-insensitively on the verbatim ``eroare`` text.
_ERROR_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"drept", re.IGNORECASE),
        "the certificate has no SPV rights for this CUI/CNP or message — the "
        "authorized list is the `cui` field of listaMesaje",
    ),
    (
        re.compile(r"nu este corect", re.IGNORECASE),
        "the CUI/CNP is not valid",
    ),
    (
        re.compile(r"obligatori", re.IGNORECASE),
        "mandatory parameters are missing for this report type",
    ),
    (
        re.compile(r"inca nu poate fi solicitat", re.IGNORECASE),
        "this report type is not yet available through the web service",
    ),
    (
        re.compile(r"\bcod\s*\d+", re.IGNORECASE),
        "a technical error on ANAF's side — report the numeric code to "
        "spv.webservice@mfinante.ro",
    ),
)


def english_error_hint(eroare: str) -> str | None:
    """Best-effort English hint for a Romanian SPV ``eroare`` text, or ``None``.

    The verbatim Romanian text stays authoritative and is always surfaced
    alongside; this only orients non-Romanian-speaking callers.
    """
    for pattern, hint in _ERROR_HINTS:
        if pattern.search(eroare):
            return hint
    return None
