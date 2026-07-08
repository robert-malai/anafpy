"""Resolve XML pass-through inputs, project them to read views (``DESIGN.md`` §8).

The XML-taking tools (``efactura_validate``, ``efactura_prepare``,
``etransport_prepare``) take a *complete* document; this module turns an ``xml`` /
``path`` input into bytes and — for the ``prepare`` previews — parses those bytes
into the client-layer flat views. Nothing is composed here: the bytes go to ANAF
verbatim, and parsing is best-effort (an unparseable document yields ``None``,
not an error).
"""

from __future__ import annotations

from pathlib import Path

from ..efactura.authoring import InvoiceDocument, read_invoice
from ..efactura.models import UploadStandard, parse_ubl_document
from ..efactura.ubl.maindoc import CreditNote
from ..etransport.models import (
    FlatSubmission,
    parse_etransport_document,
    read_flat_transport,
)
from ..exceptions import AnafConfigError
from .models import EtransportXmlInput, UblXmlInput

__all__ = ["invoice_view", "resolve_xml", "transport_view", "upload_standard"]


def resolve_xml(document: UblXmlInput | EtransportXmlInput) -> bytes:
    """Read an XML pass-through input to UTF-8 bytes ready to upload.

    Raises :class:`AnafConfigError` when neither or both of ``xml`` / ``path`` are
    set, or when ``path`` cannot be read — stay in the AnafError hierarchy instead
    of leaking a raw OS error out of a tool.
    """
    if document.xml and document.path:
        raise AnafConfigError("set only one of `xml` / `path`, not both")
    if document.xml:
        return document.xml.encode("utf-8")
    if document.path:
        try:
            return Path(document.path).expanduser().read_bytes()
        except OSError as exc:
            raise AnafConfigError(
                f"cannot read XML file {document.path!r}: {exc}"
            ) from exc
    raise AnafConfigError("one of `xml` / `path` is required")


def upload_standard(xml: bytes) -> UploadStandard:
    """The ``standard`` upload param for e-Factura XML: ``CN`` for a credit note,
    else ``UBL``. Unparseable bytes default to ``UBL`` (ANAF rejects them anyway)."""
    doc = parse_ubl_document(xml)
    return UploadStandard.CN if isinstance(doc, CreditNote) else UploadStandard.UBL


def invoice_view(xml: bytes) -> InvoiceDocument | None:
    """Full-fidelity flat projection of e-Factura UBL, or ``None`` if it does not
    parse or the strict authoring reader cannot represent it.

    Used for the ``efactura_prepare`` preview; wire amounts land in the explicit
    fields, never recomputed. A ``None`` preview does not block the filing — the
    bytes go to ANAF verbatim either way.
    """
    doc = parse_ubl_document(xml)
    if doc is None:
        return None
    try:
        return read_invoice(doc)
    except ValueError:
        return None


def transport_view(xml: bytes) -> FlatSubmission | None:
    """Easy-to-read projection of e-Transport XML, or ``None`` if it does not parse.

    Translation is strict (a parseable document the flat models cannot represent
    yields ``None``, not a partial view); pydantic's ``ValidationError`` is a
    ``ValueError``, so one handler covers both failure shapes.
    """
    doc = parse_etransport_document(xml)
    if doc is None:
        return None
    try:
        return read_flat_transport(doc)
    except ValueError:
        return None
