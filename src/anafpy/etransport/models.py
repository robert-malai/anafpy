"""Value types returned by :class:`anafpy.etransport.client.ETransportClient`.

Key differences from e-Factura:
- **Responses are JSON**, not e-Factura's XML ``<header>`` (per the vendored swagger
  specs); the private ``_*Envelope`` models validate the wire shapes.
- ``UploadResult`` carries both ``upload_id`` (``index_incarcare``) **and** ``uit``
  (the transport declaration code returned at upload time — no separate download step).
- ``MessageStatus`` has no ``download_id``; the UIT is already in ``UploadResult``.
- ``Notification`` mirrors the richer JSON returned by ``lista/{zile}/{cif}``.
- ``InfoList`` / ``InfoItem`` cover the transporter-lookup endpoint.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from .schema.schema_etr_v2_20230126 import ETransport

__all__ = [
    "FlatTransport",
    "FlatTransportDocument",
    "FlatTransportGood",
    "FlatTransportLocation",
    "FlatTransportPartner",
    "FlatTransportVehicle",
    "InfoItem",
    "InfoList",
    "Location",
    "MessageState",
    "MessageStatus",
    "Notification",
    "NotificationMessage",
    "UploadResult",
    "parse_etransport_document",
    "read_flat_transport",
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


class NotificationMessage(BaseModel):
    """One entry in a notification's ``mesaje`` array (tip ERR|WARN|INFO)."""

    tip: _StrNone = None
    mesaj: _StrNone = None


class Notification(BaseModel):
    """One entry from ``GET lista/{zile}/{cif}``."""

    tip: _StrNone = None  # NOT / COR / DEL / CON / MVH
    stare: _StrNone = None  # OK / ERR
    uit: _StrNone = None
    cod_decl: _StrNone = None
    ref_decl: _StrNone = None
    post_avarie: _StrNone = None
    sursa: _StrNone = None  # A = API, I = web app
    id_incarcare: _StrNone = None
    data_creare: _StrNone = None
    data_modif: _StrNone = None
    tip_op: _StrNone = None  # 10/12/14/20/22/24/30/40/50/60/70
    data_transp: _StrNone = None
    pc_tara: _StrNone = None
    pc_cod: _StrNone = None
    pc_den: _StrNone = None
    tr_tara: _StrNone = None
    tr_cod: _StrNone = None
    tr_den: _StrNone = None
    nr_veh: _StrNone = None
    nr_rem1: _StrNone = None
    nr_rem2: _StrNone = None
    nr_linii: _StrNone = None
    gr_tot_neta: _StrNone = None
    gr_tot_bruta: _StrNone = None
    val_tot: _StrNone = None
    mesaje: list[NotificationMessage] = []


class Location(BaseModel):
    """A ``loc_start`` or ``loc_final`` from an ``info`` record."""

    tip_loc: _StrNone = None  # PTF = border / BV = customs / ADR = national address
    adresa_completa: _StrNone = None
    judet: _StrNone = None
    localitate: _StrNone = None
    strada: _StrNone = None
    numar: _StrNone = None


class InfoItem(BaseModel):
    """One record from ``GET info?cui_op=...``."""

    id: _StrNone = None
    uit: _StrNone = None
    cod_decl: _StrNone = None
    den_decl: _StrNone = None
    ref_decl: _StrNone = None
    data_transp: _StrNone = None
    data_exp_uit: _StrNone = None
    tr_tara: _StrNone = None
    tr_cod: _StrNone = None
    tr_den: _StrNone = None
    nr_veh: _StrNone = None
    nr_rem1: _StrNone = None
    nr_rem2: _StrNone = None
    loc_start: Location | None = None
    loc_final: Location | None = None


class InfoList(BaseModel):
    """Response from ``GET info?cui_op=...``."""

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

    index_incarcare: _StrNone = None
    uit: _StrNone = Field(default=None, alias="UIT")


class _StatusEnvelope(_JsonEnvelope):
    """``stareMesaj`` response: ``stare`` (ok|nok) plus any ``Errors[]``."""

    stare: _StrNone = None


class _ListaEnvelope(_JsonEnvelope):
    """``lista`` response: notifications under ``mesaje[]``."""

    mesaje: list[Notification] = []


# --- flat read view: e-Transport XSD -> easy-to-read projection ---------------------
#
# Produced *from* a parsed declaration only (read direction); anafpy never composes the
# XSD from these. Used for the MCP ``prepare`` preview of a declaration about to be
# filed. Lossy: ``complete`` / ``dropped_fields`` mark anything the shape leaves out.


class FlatTransportPartner(BaseModel):
    """Commercial partner of the transport."""

    name: str | None = None
    country: str | None = None
    code: str | None = None


class FlatTransportVehicle(BaseModel):
    """Vehicle and carrier details."""

    plate: str | None = None
    trailer1: str | None = None
    trailer2: str | None = None
    carrier_name: str | None = None
    carrier_country: str | None = None
    carrier_code: str | None = None
    transport_date: str | None = None


class FlatTransportLocation(BaseModel):
    """A national address at the start or end of the road route."""

    county_code: str | None = None
    locality: str | None = None
    street: str | None = None
    number: str | None = None
    postal_code: str | None = None
    other: str | None = None


class FlatTransportGood(BaseModel):
    """One transported-goods line."""

    operation_scope: str | None = None
    name: str | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None
    gross_weight: Decimal | None = None
    net_weight: Decimal | None = None
    tariff_code: str | None = None
    value_ron: Decimal | None = None


class FlatTransportDocument(BaseModel):
    """A transport document reference."""

    doc_type: str | None = None
    number: str | None = None
    date: str | None = None
    note: str | None = None


class FlatTransport(BaseModel):
    """An e-Transport declaration flattened into an easy-to-read shape.

    A lossy projection of the ANAF XSD for display; ``complete`` is ``False`` (and
    ``dropped_fields`` names what) when the declaration carries structure this shape
    cannot represent.
    """

    operation_type: str | None = None
    declarant_code: str | None = None
    declarant_ref: str | None = None
    partner: FlatTransportPartner = FlatTransportPartner()
    vehicle: FlatTransportVehicle = FlatTransportVehicle()
    start_location: FlatTransportLocation = FlatTransportLocation()
    end_location: FlatTransportLocation = FlatTransportLocation()
    goods: list[FlatTransportGood] = []
    documents: list[FlatTransportDocument] = []
    goods_count: int = 0
    total_gross_weight: Decimal | None = None
    complete: bool = True
    dropped_fields: list[str] = []


def parse_etransport_document(xml: bytes) -> ETransport | None:
    """Parse e-Transport wire XML into its :class:`ETransport` model, or ``None`` when
    the bytes are not a parseable declaration. Never raises on bad input."""
    from xsdata.exceptions import ParserError
    from xsdata_pydantic.bindings import XmlParser

    try:
        return XmlParser().from_bytes(xml, ETransport)
    except (ParserError, ValueError):
        return None


def _enum_str(obj: Any) -> str | None:
    """Render an enum-or-scalar XSD value as text (codes are exposed as their value)."""
    if obj is None:
        return None
    value = getattr(obj, "value", obj)
    return None if value is None else str(value)


def _dec(value: Any) -> Decimal | None:
    """Parse a (string) XSD numeric into a ``Decimal``, tolerating bad input."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _read_location(route: Any) -> FlatTransportLocation:
    loc = getattr(route, "locatie", None) if route else None
    if loc is None:
        return FlatTransportLocation()
    return FlatTransportLocation(
        county_code=_enum_str(getattr(loc, "cod_judet", None)),
        locality=getattr(loc, "denumire_localitate", None),
        street=getattr(loc, "denumire_strada", None),
        number=getattr(loc, "numar", None),
        postal_code=getattr(loc, "cod_postal", None),
        other=getattr(loc, "alte_info", None),
    )


def _read_good(good: Any) -> FlatTransportGood:
    return FlatTransportGood(
        operation_scope=_enum_str(getattr(good, "cod_scop_operatiune", None)),
        name=getattr(good, "denumire_marfa", None),
        quantity=_dec(getattr(good, "cantitate", None)),
        unit_code=getattr(good, "cod_unitate_masura", None),
        gross_weight=_dec(getattr(good, "greutate_bruta", None)),
        net_weight=_dec(getattr(good, "greutate_neta", None)),
        tariff_code=getattr(good, "cod_tarifar", None),
        value_ron=_dec(getattr(good, "valoare_lei_fara_tva", None)),
    )


def read_flat_transport(doc: ETransport) -> FlatTransport:
    """Project a parsed :class:`ETransport` declaration to a :class:`FlatTransport`."""
    notif = getattr(doc, "notificare", None)
    if notif is None:
        return FlatTransport(
            declarant_code=getattr(doc, "cod_declarant", None),
            declarant_ref=getattr(doc, "ref_declarant", None),
            complete=False,
            dropped_fields=["notificare"],
        )

    transport = getattr(notif, "date_transport", None)
    partner = getattr(notif, "partener_comercial", None)
    goods = [_read_good(g) for g in getattr(notif, "bunuri_transportate", None) or []]
    documents = [
        FlatTransportDocument(
            doc_type=_enum_str(getattr(d, "tip_document", None)),
            number=getattr(d, "numar_document", None),
            date=_date_str(getattr(d, "data_document", None)),
            note=getattr(d, "observatii", None),
        )
        for d in getattr(notif, "documente_transport", None) or []
    ]
    weights = [g.gross_weight for g in goods if g.gross_weight is not None]
    return FlatTransport(
        operation_type=_enum_str(getattr(notif, "cod_tip_operatiune", None)),
        declarant_code=getattr(doc, "cod_declarant", None),
        declarant_ref=getattr(doc, "ref_declarant", None),
        partner=FlatTransportPartner(
            name=getattr(partner, "denumire", None),
            country=_enum_str(getattr(partner, "cod_tara", None)),
            code=getattr(partner, "cod", None),
        ),
        vehicle=FlatTransportVehicle(
            plate=getattr(transport, "nr_vehicul", None),
            trailer1=getattr(transport, "nr_remorca1", None),
            trailer2=getattr(transport, "nr_remorca2", None),
            carrier_name=getattr(transport, "denumire_org_transport", None),
            carrier_country=_enum_str(
                getattr(transport, "cod_tara_org_transport", None)
            ),
            carrier_code=getattr(transport, "cod_org_transport", None),
            transport_date=_date_str(getattr(transport, "data_transport", None)),
        ),
        start_location=_read_location(getattr(notif, "loc_start_traseu_rutier", None)),
        end_location=_read_location(getattr(notif, "loc_final_traseu_rutier", None)),
        goods=goods,
        documents=documents,
        goods_count=len(goods),
        total_gross_weight=sum(weights, Decimal(0)) if weights else None,
    )


def _date_str(obj: Any) -> str | None:
    """Render an ``XmlDate`` (or text date) as ISO text, or ``None``."""
    return None if obj is None else str(obj)
