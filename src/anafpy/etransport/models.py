"""Value types returned by :class:`anafpy.etransport.client.ETransportClient`.

Key differences from e-Factura:
- ``UploadResult`` carries both ``upload_id`` (``index_incarcare``) **and** ``uit``
  (the transport declaration code returned at upload time — no separate download step).
- ``MessageStatus`` has no ``download_id``; the UIT is already in ``UploadResult``.
- ``NotificationList`` mirrors the richer JSON returned by ``lista/{zile}/{cif}``.
- ``InfoList`` / ``InfoItem`` cover the transporter-lookup endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "InfoItem",
    "InfoList",
    "Location",
    "MessageState",
    "MessageStatus",
    "Notification",
    "NotificationList",
    "NotificationMessage",
    "UploadResult",
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


@dataclass(slots=True)
class UploadResult:
    """Outcome of ``POST /upload/ETRANSP/{cif}/{versiune}``.

    ``upload_id`` (``index_incarcare``) feeds ``get_status``; ``uit`` is the transport
    declaration code available immediately on acceptance; there is no separate download.
    """

    upload_id: str | None
    uit: str | None = None
    errors: list[str] = field(default_factory=list)
    raw: bytes = b""

    @property
    def accepted(self) -> bool:
        return self.upload_id is not None


@dataclass(slots=True)
class MessageStatus:
    """Outcome of ``GET stareMesaj/{id_incarcare}``."""

    state: MessageState
    errors: list[str] = field(default_factory=list)
    raw: bytes = b""

    @property
    def is_processing(self) -> bool:
        return self.state is MessageState.PROCESSING

    @property
    def is_terminal(self) -> bool:
        return self.state in (MessageState.OK, MessageState.NOK)


@dataclass(slots=True)
class NotificationMessage:
    """One entry in a notification's ``mesaje`` array (tip ERR|WARN|INFO)."""

    tip: str | None
    mesaj: str | None

    @classmethod
    def from_json(cls, obj: dict[str, object]) -> NotificationMessage:
        def s(k: str) -> str | None:
            v = obj.get(k)
            return None if v is None else str(v)

        return cls(tip=s("tip"), mesaj=s("mesaj"))


@dataclass(slots=True)
class Notification:
    """One entry from ``GET lista/{zile}/{cif}``."""

    tip: str | None  # NOT / COR / DEL / CON / MVH
    stare: str | None  # OK / ERR
    uit: str | None
    cod_decl: str | None
    ref_decl: str | None
    post_avarie: str | None
    sursa: str | None  # A = API, I = web app
    id_incarcare: str | None
    data_creare: str | None
    data_modif: str | None
    tip_op: str | None  # 10/12/14/20/22/24/30/40/50/60/70
    data_transp: str | None
    pc_tara: str | None
    pc_cod: str | None
    pc_den: str | None
    tr_tara: str | None
    tr_cod: str | None
    tr_den: str | None
    nr_veh: str | None
    nr_rem1: str | None
    nr_rem2: str | None
    nr_linii: str | None
    gr_tot_neta: str | None
    gr_tot_bruta: str | None
    val_tot: str | None
    mesaje: list[NotificationMessage] = field(default_factory=list)

    @classmethod
    def from_json(cls, obj: dict[str, object]) -> Notification:
        def s(k: str) -> str | None:
            v = obj.get(k)
            return None if v is None else str(v)

        raw_mesaje = obj.get("mesaje")
        mesaje = [
            NotificationMessage.from_json(m)
            for m in (raw_mesaje if isinstance(raw_mesaje, list) else [])
        ]
        return cls(
            tip=s("tip"),
            stare=s("stare"),
            uit=s("uit"),
            cod_decl=s("cod_decl"),
            ref_decl=s("ref_decl"),
            post_avarie=s("post_avarie"),
            sursa=s("sursa"),
            id_incarcare=s("id_incarcare"),
            data_creare=s("data_creare"),
            data_modif=s("data_modif"),
            tip_op=s("tip_op"),
            data_transp=s("data_transp"),
            pc_tara=s("pc_tara"),
            pc_cod=s("pc_cod"),
            pc_den=s("pc_den"),
            tr_tara=s("tr_tara"),
            tr_cod=s("tr_cod"),
            tr_den=s("tr_den"),
            nr_veh=s("nr_veh"),
            nr_rem1=s("nr_rem1"),
            nr_rem2=s("nr_rem2"),
            nr_linii=s("nr_linii"),
            gr_tot_neta=s("gr_tot_neta"),
            gr_tot_bruta=s("gr_tot_bruta"),
            val_tot=s("val_tot"),
            mesaje=mesaje,
        )


@dataclass(slots=True)
class NotificationList:
    """Response from ``GET lista/{zile}/{cif}``."""

    notifications: list[Notification] = field(default_factory=list)
    error: str | None = None
    raw: bytes = b""


@dataclass(slots=True)
class Location:
    """A ``loc_start`` or ``loc_final`` from an ``info`` record."""

    tip_loc: str | None  # PTF = border point / BV = customs / ADR = national address
    judet: str | None
    localitate: str | None
    strada: str | None
    numar: str | None

    @classmethod
    def from_json(cls, obj: dict[str, object]) -> Location:
        def s(k: str) -> str | None:
            v = obj.get(k)
            return None if v is None else str(v)

        return cls(
            tip_loc=s("tip_loc"),
            judet=s("judet"),
            localitate=s("localitate"),
            strada=s("strada"),
            numar=s("numar"),
        )


@dataclass(slots=True)
class InfoItem:
    """One record from ``GET info?cui_op=...``."""

    uit: str | None
    cod_decl: str | None
    den_decl: str | None
    ref_decl: str | None
    data_transp: str | None
    data_exp_uit: str | None
    tr_tara: str | None
    tr_cod: str | None
    tr_den: str | None
    nr_veh: str | None
    nr_rem1: str | None
    nr_rem2: str | None
    loc_start: Location | None = None
    loc_final: Location | None = None

    @classmethod
    def from_json(cls, obj: dict[str, object]) -> InfoItem:
        def s(k: str) -> str | None:
            v = obj.get(k)
            return None if v is None else str(v)

        loc_s = obj.get("loc_start")
        loc_f = obj.get("loc_final")
        return cls(
            uit=s("uit"),
            cod_decl=s("cod_decl"),
            den_decl=s("den_decl"),
            ref_decl=s("ref_decl"),
            data_transp=s("data_transp"),
            data_exp_uit=s("data_exp_uit"),
            tr_tara=s("tr_tara"),
            tr_cod=s("tr_cod"),
            tr_den=s("tr_den"),
            nr_veh=s("nr_veh"),
            nr_rem1=s("nr_rem1"),
            nr_rem2=s("nr_rem2"),
            loc_start=Location.from_json(loc_s) if isinstance(loc_s, dict) else None,
            loc_final=Location.from_json(loc_f) if isinstance(loc_f, dict) else None,
        )


@dataclass(slots=True)
class InfoList:
    """Response from ``GET info?cui_op=...``."""

    items: list[InfoItem] = field(default_factory=list)
    error: str | None = None
    raw: bytes = b""
