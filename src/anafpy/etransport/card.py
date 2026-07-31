"""UIT presentation artifacts: the driver card and the detail document.

An e-Transport filing yields a UIT, and the code then has to travel — to the
driver, who must carry it, and often to the partner company. ANAF issues no
document for this, so :class:`UitCard` gathers what a filing already knows and
:mod:`anafpy.etransport.cardpdf` renders two PDFs from it:

- **the card**, one page at a phone's own aspect ratio (90x195mm), so the driver
  opens it full-screen and the phone *is* the document — the code set large, a
  QR carrying the bare UIT, and the plates and dates a roadside check asks for;
- **the detail document**, A4, carrying the whole filing for the partner company
  or the caller's own file.

Both are **informative**: they are generated locally, are not issued by ANAF,
and say so on their face. The QR encodes the raw 16-character UIT and nothing
else — there is no official ANAF QR format, so it is a scan-to-copy convenience
observed on the cards Romanian invoicing software already produces.

Rendering needs the ``anafpy[cards]`` extra; :func:`load_cardpdf` reports its
absence as an :class:`~anafpy.exceptions.AnafConfigError` rather than an
``ImportError``. :meth:`UitCard.summary_text` needs nothing and is the paste-
into-a-chat fallback for phones whose PDF viewer will not select text.
"""

from __future__ import annotations

import datetime as dt
import importlib
from typing import TYPE_CHECKING, Protocol, cast

from pydantic import BaseModel, Field

from ..exceptions import AnafConfigError
from .labels import label_for
from .models import FlatTransport, UploadResult, _Uit

if TYPE_CHECKING:
    from .schema.schema_etr_v2_20230126 import CodTipOperatiuneType

__all__ = ["CardRenderModule", "UitCard", "load_cardpdf", "partner_label"]

# Which noun names the commercial partner, by ANAF operation code: inbound
# operations buy from a supplier, outbound ones sell to a customer, and a
# domestic transport says neither.
_INBOUND = {10, 12, 14, 40, 60}
_OUTBOUND = {20, 22, 24, 50, 70}


def partner_label(operation: CodTipOperatiuneType) -> str:
    """``Furnizor`` / ``Client`` / ``Partener``, by transport direction."""
    match operation.value:
        case value if value in _INBOUND:
            return "Furnizor"
        case value if value in _OUTBOUND:
            return "Client"
        case _:
            return "Partener"


class UitCard(BaseModel):
    """A filing plus the identifiers ANAF returned for it, ready to render.

    ``transport`` is the declaration itself; everything else is what the upload
    and a later ``info`` lookup add. The optional fields are genuinely optional:
    a card rendered straight after upload has no ``uit_expiry`` yet, and prints
    the transport date alone rather than inventing a validity window.
    """

    uit: _Uit
    transport: FlatTransport
    uit_expiry: dt.date | None = Field(
        default=None,
        description="Expiry ANAF reports as data_exp_uit; never computed locally.",
    )
    declarant_name: str | None = Field(
        default=None, description="Declarant's registered name."
    )
    declarant_code: str | None = Field(
        default=None,
        description="Declarant's fiscal code as it should read on the document, "
        "verbatim — a prefix is never added or stripped.",
    )
    filed_on: dt.date | None = None
    upload_id: str | None = Field(
        default=None, description="ANAF's index_incarcare for the upload."
    )
    anaf_state: str | None = Field(
        default=None, description="Processing state, e.g. 'ok'."
    )
    notes: list[str] = Field(
        default=[],
        description="The caller's own observations, printed on the detail "
        "document only. Boilerplate belongs nowhere near this.",
    )

    @classmethod
    def from_upload(
        cls,
        transport: FlatTransport,
        result: UploadResult,
        *,
        uit_expiry: dt.date | None = None,
        declarant_name: str | None = None,
        declarant_code: str | None = None,
        filed_on: dt.date | None = None,
        anaf_state: str | None = None,
        notes: list[str] | None = None,
    ) -> UitCard:
        """Build from an accepted upload, carrying its UIT and upload index.

        ``uit_expiry`` is not among them by accident: ``upload`` does not report
        it, and only a later ``info`` lookup does.
        """
        if not result.uit:
            raise AnafConfigError(
                "the upload carries no UIT — it was rejected, or the response "
                "predates acceptance; nothing to put on a card"
            )
        return cls(
            uit=result.uit,
            transport=transport,
            upload_id=result.upload_id,
            uit_expiry=uit_expiry,
            declarant_name=declarant_name,
            declarant_code=declarant_code,
            filed_on=filed_on,
            anaf_state=anaf_state,
            notes=notes or [],
        )

    def is_expired(self, today: dt.date | None = None) -> bool:
        """Whether the UIT's validity has lapsed. False when ANAF's expiry is
        unknown — an absent date is not evidence of expiry."""
        if self.uit_expiry is None:
            return False
        return self.uit_expiry < (today or dt.date.today())

    def summary_text(self) -> str:
        """The card's facts as plain text, for pasting into a chat message.

        The UIT is alone on the first line so that copying the whole block, or
        just its first line, both yield a usable code. This is the fallback for
        viewers that will not select text in a PDF.
        """
        vehicle = self.transport.vehicle
        plates = " + ".join(
            p for p in (vehicle.plate, vehicle.trailer1, vehicle.trailer2) if p
        )
        lines = [
            self.uit,
            f"Vehicul {plates}",
            f"Transport {vehicle.transport_date:%d.%m.%Y}",
        ]
        if self.uit_expiry is not None:
            lines[-1] += f" · UIT valabil până la {self.uit_expiry:%d.%m.%Y}"
        operation = self.transport.operation_type
        lines.append(f"{operation.value} — {label_for(operation)}")
        return "\n".join(lines)


class CardRenderModule(Protocol):
    """Typed shape of the optional :mod:`anafpy.etransport.cardpdf` module."""

    def render_card(self, card: UitCard, *, today: dt.date | None = ...) -> bytes: ...

    def render_details(
        self, card: UitCard, *, today: dt.date | None = ...
    ) -> bytes: ...


def load_cardpdf() -> CardRenderModule:
    """Load the optional fpdf2-backed renderer with an install hint."""
    try:
        module = importlib.import_module(".cardpdf", __package__)
    except ModuleNotFoundError as exc:
        raise AnafConfigError(
            "rendering UIT cards needs the anafpy[cards] extra — install it "
            "with `pip install 'anafpy[cards]'`"
        ) from exc
    return cast(CardRenderModule, module)
