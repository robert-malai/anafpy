"""Value types returned by :class:`anafpy.etransport.client.ETransportClient`.

Key differences from e-Factura:
- ``UploadResult`` carries both ``upload_id`` (``index_incarcare``) **and** ``uit``
  (the transport declaration code returned at upload time — no separate download step).
- ``MessageStatus`` has no ``download_id``; the UIT is already in ``UploadResult``.
- ``NotificationList`` mirrors the richer JSON returned by ``lista/{zile}/{cif}``.
- ``InfoList`` / ``InfoItem`` cover the transporter-lookup endpoint.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator

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

# Coerce any non-None JSON value to str; mirrors the defensive s() helper previously
# used in from_json classmethods (ANAF occasionally returns numeric ids as numbers).
_StrNone = Annotated[str | None, BeforeValidator(lambda v: None if v is None else str(v))]


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
        return self.state in (MessageState.OK, MessageState.NOK)


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


class NotificationList(BaseModel):
    """Response from ``GET lista/{zile}/{cif}``."""

    notifications: list[Notification] = []
    error: str | None = None
    raw: bytes = b""


class Location(BaseModel):
    """A ``loc_start`` or ``loc_final`` from an ``info`` record."""

    tip_loc: _StrNone = None  # PTF = border point / BV = customs / ADR = national address
    judet: _StrNone = None
    localitate: _StrNone = None
    strada: _StrNone = None
    numar: _StrNone = None


class InfoItem(BaseModel):
    """One record from ``GET info?cui_op=...``."""

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
