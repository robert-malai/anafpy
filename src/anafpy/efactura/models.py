"""Value types returned by :class:`anafpy.efactura.client.EFacturaClient`.

These are deliberately small, transport-facing types. Business outcomes (an upload
rejected at submission, a ``nok`` status) are represented here as *values*, never
exceptions — see :mod:`anafpy.exceptions` for the error half of the hybrid model.

The richer document models (``Invoice``/``CreditNote``) are the generated UBL types;
``DownloadedMessage`` preserves the raw signed bytes and parses them lazily — its
``view`` tier is the flat :class:`~anafpy.efactura.authoring.InvoiceDocument`
from :mod:`anafpy.efactura.authoring`.
"""

from __future__ import annotations

import io
import re
import zipfile
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, cast

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from .ubl.maindoc import CreditNote, Invoice

if TYPE_CHECKING:
    from .authoring import InvoiceDocument

__all__ = [
    "DownloadedMessage",
    "Filter",
    "MessageListItem",
    "MessageState",
    "MessageStatus",
    "SignatureValidationResult",
    "UploadResult",
    "UploadStandard",
    "parse_ubl_document",
]

# Coerce any non-None JSON value to str; mirrors the defensive s() helper previously
# used in from_json classmethods (ANAF occasionally returns numeric ids as numbers).
_StrNone = Annotated[
    str | None, BeforeValidator(lambda v: None if v is None else str(v))
]


class UploadStandard(StrEnum):
    """``standard`` query param for ``/upload`` (the document kind being submitted)."""

    UBL = "UBL"  # invoice
    CN = "CN"  # credit note
    CII = "CII"
    RASP = "RASP"  # buyer -> issuer message


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
        return self.state is not MessageState.PROCESSING


class SignatureValidationResult(BaseModel):
    """Outcome of ``POST /api/validate/signature`` (MF signature over an invoice).

    Both outcomes are HTTP 200 with a prose ``msg``; ``valid`` reflects which of the
    two documented wordings ANAF answered with. A failed validation is a *business*
    outcome — never an exception.
    """

    valid: bool
    message: str
    raw: bytes = b""


# The list endpoints never emit cif_emitent/cif_beneficiar as JSON keys despite
# ANAF's API PDF listing them as response fields (live-confirmed in production
# 2026-07-06; the swagger Mesaj schema agrees) — the CIFs ride only inside the
# free-text `detalii`, in these known wordings.
_DETAILS_INVOICE = re.compile(r"emisa de cif_emitent=(\d+) pentru cif_beneficiar=(\d+)")
# Self-billing: the buyer transmits the invoice on the supplier's behalf, so the
# "in numele" party is the seller. Whitespace is \s+ — production shows a double
# space before "ca autofactura".
_DETAILS_SELF_BILLED = re.compile(
    r"transmisa de cif=(\d+)\s+ca autofactura in numele cif=(\d+)"
)


class MessageListItem(BaseModel):
    """One entry from a message-list response.

    Descriptive field names, with ANAF's wire names kept as validation aliases
    (``data_creare`` -> ``created_at``, ...); values are read verbatim.
    ``populate_by_name`` lets callers also construct by the field names.

    ``sender_cif``/``receiver_cif`` are documented by ANAF's API PDF but never sent
    on the wire; when absent they are extracted (best-effort) from the ``details``
    prose, staying ``None`` for wordings that carry no CIFs (``ERORI FACTURA``,
    buyer messages).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: _StrNone = None
    request_id: _StrNone = Field(default=None, alias="id_solicitare")
    message_type: _StrNone = Field(default=None, alias="tip")
    created_at: _StrNone = Field(default=None, alias="data_creare")
    cif: _StrNone = None
    sender_cif: _StrNone = Field(default=None, alias="cif_emitent")
    receiver_cif: _StrNone = Field(default=None, alias="cif_beneficiar")
    details: _StrNone = Field(default=None, alias="detalii")

    @model_validator(mode="after")
    def _fill_cifs_from_details(self) -> MessageListItem:
        """Best-effort ``sender_cif``/``receiver_cif`` extraction from ``details``.

        Wire values win: runs only when both fields are unset, so if ANAF ever
        starts emitting the documented keys the aliases take precedence. Never
        raises — an unrecognised wording just leaves the fields ``None``.
        """
        if self.sender_cif is not None or self.receiver_cif is not None:
            return self
        if not self.details:
            return self
        if match := _DETAILS_INVOICE.search(self.details):
            self.sender_cif, self.receiver_cif = match.groups()
        elif match := _DETAILS_SELF_BILLED.search(self.details):
            # Swapped on purpose: the transmitter is the buyer, the seller is the
            # "in numele" party — sender_cif keeps its cif_emitent (seller) meaning.
            self.receiver_cif, self.sender_cif = match.groups()
        return self


def parse_ubl_document(xml: bytes) -> Invoice | CreditNote | None:
    """Parse e-Factura wire XML into its UBL model.

    Returns an :class:`Invoice` or :class:`CreditNote`, or ``None`` when the bytes are
    not a parseable UBL document (e.g. a ``nok`` errors file). Never raises.
    """
    # Imported here to keep import-time cost off the hot path for raw-bytes users.
    from xsdata.exceptions import ParserError
    from xsdata_pydantic.bindings import XmlParser

    parser = XmlParser()
    for model in (Invoice, CreditNote):
        try:
            parsed = parser.from_bytes(xml, model)
        except (ParserError, ValueError):
            continue
        return cast("Invoice | CreditNote", parsed)
    return None


class DownloadedMessage(BaseModel):
    """A ``descarcare`` ZIP, with raw bytes preserved.

    Three read tiers, cheapest first: ``raw_zip`` / ``content_xml`` (the legally
    meaningful, archived bytes), ``document`` (the full generated UBL model), and
    ``view`` (the flat :class:`~anafpy.efactura.authoring.InvoiceDocument`
    projection — full-fidelity, and renderable back via the authoring package).
    The latter two parse lazily; tier 1 stays authoritative.
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
        return parse_ubl_document(self.content_xml)

    @cached_property
    def view(self) -> InvoiceDocument | None:
        """The flat :class:`~anafpy.efactura.authoring.InvoiceDocument` projection
        of :attr:`document`.

        ``None`` when the content is not a parseable UBL invoice/credit-note (a
        ``nok`` errors file, a buyer message) **or** when the strict authoring
        reader cannot represent it — never an exception. Every inbox document
        passed ANAF's validation at filing, whose rules the authoring models
        mirror, so a ``None`` on parseable UBL signals rule drift: fall back to
        :attr:`document` / :attr:`content_xml` and consider re-vendoring the
        CIUS-RO code lists.
        """
        # Imported lazily: authoring.read imports this module for
        # parse_ubl_document.
        from .authoring import read_invoice

        doc = self.document
        if doc is None:
            return None
        try:
            return read_invoice(doc)
        except ValueError:  # includes pydantic.ValidationError
            return None
