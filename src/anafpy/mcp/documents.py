"""Resolve XML pass-through inputs and project them to read views (``DESIGN.md`` §7).

The filing tools take a *complete* document; this module turns an ``xml`` / ``path``
input into bytes and — for the ``prepare`` preview — parses those bytes into the
client-layer flat read view. Nothing is composed here: the bytes are filed verbatim, and
parsing is best-effort (an unparseable document yields ``None``, not an error).
"""

from __future__ import annotations

from pathlib import Path

from ..efactura.models import (
    FlatInvoice,
    UploadStandard,
    parse_ubl_document,
    read_flat_invoice,
)
from ..efactura.ubl.maindoc import CreditNote
from ..etransport.models import (
    FlatTransport,
    parse_etransport_document,
    read_flat_transport,
)
from ..exceptions import AnafConfigError
from .models import EtransportXmlInput, UblXmlInput

__all__ = ["invoice_view", "resolve_xml", "transport_view", "upload_standard"]


def resolve_xml(document: UblXmlInput | EtransportXmlInput) -> bytes:
    """Read an XML pass-through input to UTF-8 bytes ready to upload.

    Raises :class:`AnafConfigError` when neither or both of ``xml`` / ``path`` are set.
    """
    if document.xml and document.path:
        raise AnafConfigError("set only one of `xml` / `path`, not both")
    if document.xml:
        return document.xml.encode("utf-8")
    if document.path:
        return Path(document.path).expanduser().read_bytes()
    raise AnafConfigError("one of `xml` / `path` is required")


def upload_standard(xml: bytes) -> UploadStandard:
    """The ``standard`` upload param for e-Factura XML: ``CN`` for a credit note,
    else ``UBL``. Unparseable bytes default to ``UBL`` (ANAF rejects them anyway)."""
    doc = parse_ubl_document(xml)
    return UploadStandard.CN if isinstance(doc, CreditNote) else UploadStandard.UBL


def invoice_view(xml: bytes) -> FlatInvoice | None:
    """Easy-to-read projection of e-Factura XML, or ``None`` if it does not parse."""
    doc = parse_ubl_document(xml)
    return read_flat_invoice(doc) if doc is not None else None


def transport_view(xml: bytes) -> FlatTransport | None:
    """Easy-to-read projection of e-Transport XML, or ``None`` if it does not parse."""
    doc = parse_etransport_document(xml)
    return read_flat_transport(doc) if doc is not None else None
