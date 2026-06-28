"""Value types returned by :class:`anafpy.efactura.client.EFacturaClient`.

These are deliberately small, transport-facing types. Business outcomes (an upload
rejected at submission, a ``nok`` status) are represented here as *values*, never
exceptions — see :mod:`anafpy.exceptions` for the error half of the hybrid model.

The richer document models (``Invoice``/``CreditNote``) are the generated UBL types;
``DownloadedMessage`` preserves the raw signed bytes and parses them lazily.
"""

from __future__ import annotations

import io
import zipfile
from enum import StrEnum
from functools import cached_property
from typing import Annotated, cast

from pydantic import BaseModel, BeforeValidator, ConfigDict

from .ubl.maindoc import CreditNote, Invoice

__all__ = [
    "DownloadedMessage",
    "Filter",
    "MessageList",
    "MessageListItem",
    "MessageState",
    "MessageStatus",
    "TransformStandard",
    "UploadResult",
    "UploadStandard",
]

# Coerce any non-None JSON value to str; mirrors the defensive s() helper previously
# used in from_json classmethods (ANAF occasionally returns numeric ids as numbers).
_StrNone = Annotated[str | None, BeforeValidator(lambda v: None if v is None else str(v))]


class UploadStandard(StrEnum):
    """``standard`` query param for ``/upload`` (the document kind being submitted)."""

    UBL = "UBL"  # invoice
    CN = "CN"  # credit note
    CII = "CII"
    RASP = "RASP"  # buyer -> issuer message


class TransformStandard(StrEnum):
    """``std`` path segment for ``/validare`` and ``/transformare``."""

    INVOICE = "FACT1"
    CREDIT_NOTE = "FCN"


class Filter(StrEnum):
    """``filtru`` query param for the message-list endpoints."""

    ERRORS = "E"  # ERORI FACTURA
    SENT = "T"  # FACTURA TRIMISA
    RECEIVED = "P"  # FACTURA PRIMITA
    BUYER_MESSAGE = "R"  # MESAJ CUMPARATOR


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
    """Outcome of ``/upload``.

    ``upload_id`` (``index_incarcare``) is set when ANAF accepted the document for
    processing; ``errors`` carries any messages when it was rejected at submission.
    """

    upload_id: str | None
    errors: list[str] = []
    raw: bytes = b""

    @property
    def accepted(self) -> bool:
        return self.upload_id is not None


class MessageStatus(BaseModel):
    """Outcome of ``stareMesaj``."""

    state: MessageState
    download_id: str | None = None
    errors: list[str] = []
    raw: bytes = b""

    @property
    def is_processing(self) -> bool:
        return self.state is MessageState.PROCESSING

    @property
    def is_terminal(self) -> bool:
        return self.state in (MessageState.OK, MessageState.NOK)


class MessageListItem(BaseModel):
    """One entry from a message-list response."""

    id: _StrNone = None
    id_solicitare: _StrNone = None
    tip: _StrNone = None
    data_creare: _StrNone = None
    cif: _StrNone = None
    cif_emitent: _StrNone = None
    cif_beneficiar: _StrNone = None
    detalii: _StrNone = None


class MessageList(BaseModel):
    """A page of messages. ``error`` holds ANAF's informational note (e.g. "no
    messages in interval") when the list is empty."""

    messages: list[MessageListItem] = []
    error: str | None = None
    raw: bytes = b""


class DownloadedMessage(BaseModel):
    """A ``descarcare`` ZIP, with raw bytes preserved.

    The signed invoice/errors XML and the MF signature are the legally meaningful
    artifacts and are kept verbatim; ``document`` parses the content member lazily.
    """

    model_config = ConfigDict(ignored_types=(cached_property,))

    raw_zip: bytes
    content_xml: bytes | None = None
    signature_xml: bytes | None = None

    @classmethod
    def from_zip(cls, raw_zip: bytes) -> DownloadedMessage:
        content: bytes | None = None
        signature: bytes | None = None
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                data = zf.read(name)
                if "semnatura" in name.lower():
                    signature = data
                else:
                    content = data
        return cls(raw_zip=raw_zip, content_xml=content, signature_xml=signature)

    @cached_property
    def document(self) -> Invoice | CreditNote | None:
        """Parse the content member into its UBL model, or ``None`` if it is not a UBL
        document (e.g. a ``nok`` errors file)."""
        if self.content_xml is None:
            return None
        # Imported here to keep import-time cost off the hot path for raw-bytes users.
        from xsdata.exceptions import ParserError
        from xsdata_pydantic.bindings import XmlParser

        parser = XmlParser()
        for model in (Invoice, CreditNote):
            try:
                parsed = parser.from_bytes(self.content_xml, model)
            except (ParserError, ValueError):
                continue
            return cast("Invoice | CreditNote", parsed)
        return None
