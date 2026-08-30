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
and say so on their face. Both also print a validity, from one of two places:
ANAF's ``data_exp_uit`` when the caller has one, and otherwise the statutory
window of :mod:`anafpy.etransport.validity` — resolved in one place,
:meth:`UitCard.validity`, and rendered so the two can never be confused.

The QR encodes the raw 16-character UIT and nothing else — there is no official
ANAF QR format, so it is a scan-to-copy convenience observed on the cards
Romanian invoicing software already produces.

Rendering needs the ``anafpy[cards]`` extra; :func:`load_cardpdf` reports its
absence as an :class:`~anafpy.exceptions.AnafConfigError` rather than an
``ImportError``. :meth:`UitCard.summary_text` needs nothing and is the paste-
into-a-chat fallback for phones whose PDF viewer will not select text.
"""

from __future__ import annotations

import datetime as dt
import importlib
from typing import TYPE_CHECKING, Literal, Protocol, cast

from pydantic import BaseModel, Field

from ..exceptions import AnafConfigError
from .labels import label_for
from .models import FlatTransport, UploadResult, _Uit
from .validity import statutory_first_expired_day, statutory_validity_days

if TYPE_CHECKING:
    from .schema.schema_etr_v2_20230126 import CodTipOperatiuneType

__all__ = [
    "CardRenderModule",
    "UitCard",
    "UitValidity",
    "load_cardpdf",
    "partner_label",
]

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


class UitValidity(BaseModel):
    """A UIT's window, resolved — and, as importantly, where it came from.

    ``source`` is what keeps the two apart: ``"anaf"`` when ``data_exp_uit`` was
    read back from the ``info`` endpoint, ``"statutory"`` when it was derived
    from the declared transport date because ANAF discloses that date only to
    the transport organizer. A derived window carries ``days`` — the count
    art. 11 gives that operation — so a caller can say *how* it was arrived at
    instead of presenting it as fact.
    """

    last_valid_day: dt.date = Field(
        description="The last day the UIT may be used, inclusive."
    )
    first_expired_day: dt.date = Field(
        description="The day it counts as expired — ANAF's data_exp_uit shape."
    )
    source: Literal["anaf", "statutory"]
    days: int | None = Field(
        default=None,
        description="Length of the statutory window in calendar days; None when "
        "the dates are ANAF's, which we do not second-guess by counting.",
    )
    expired: bool


class UitCard(BaseModel):
    """A filing plus the identifiers ANAF returned for it, ready to render.

    ``transport`` is the declaration itself; everything else is what the upload
    and a later ``info`` lookup add. The optional fields are genuinely optional:
    a card rendered straight after upload has no ``uit_expiry`` yet, and most
    never get one — ANAF serves ``data_exp_uit`` only to the transport
    organizer. :meth:`validity` is what fills the gap, from the statute rather
    than from ANAF, and says so.
    """

    uit: _Uit
    transport: FlatTransport
    uit_expiry: dt.date | None = Field(
        default=None,
        description="ANAF's data_exp_uit, verbatim: *the date from which the UIT "
        "is considered expired*, so the last day it may be used is the day "
        "before. Never computed locally — a derived window is `validity()`'s "
        "job, and is labelled as one.",
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

    @property
    def last_valid_day(self) -> dt.date | None:
        """The last day the UIT may still be used, or ``None`` when unknown.

        ANAF's ``data_exp_uit`` is defined as *"data incepand cu care UIT-ul este
        considerat expirat"* — the first **expired** day, not the last valid one
        (API PDF p. 4; the info swagger pairs ``data_transp`` 2024-06-24 with
        ``data_exp_uit`` 2024-06-29, i.e. the 5 calendar days of OUG 41/2022
        art. 11 counted from the transport date). Printing it under "valabil
        până la" would vouch for a day on which use is a contravention.
        """
        if self.uit_expiry is None:
            return None
        return self.uit_expiry - dt.timedelta(days=1)

    def validity(self, today: dt.date | None = None) -> UitValidity:
        """The window to show, and where its dates come from.

        ANAF's ``data_exp_uit`` wins whenever it was reported; otherwise the
        statutory window of :mod:`anafpy.etransport.validity` is derived from
        the declared transport date. So there is always a window — what varies
        is :attr:`UitValidity.source`, and everything that renders one is
        expected to say which it is looking at.
        """
        operation = self.transport.operation_type
        transport_date = self.transport.vehicle.transport_date
        source: Literal["anaf", "statutory"]
        days: int | None
        if (first_expired := self.uit_expiry) is not None:
            source, days = "anaf", None
        else:
            first_expired = statutory_first_expired_day(operation, transport_date)
            source, days = "statutory", statutory_validity_days(operation)
        return UitValidity(
            last_valid_day=first_expired - dt.timedelta(days=1),
            first_expired_day=first_expired,
            source=source,
            days=days,
            expired=first_expired <= (today or dt.date.today()),
        )

    def is_expired(self, today: dt.date | None = None) -> bool:
        """Whether the UIT's validity has lapsed, by the best date available.

        Expiry is inclusive of the first expired day itself — on that very date
        the UIT already counts as expired. With no ``uit_expiry`` reported this
        reads the statutory window rather than answering ``False``: ANAF not
        disclosing a date to a declarant who is not the transport organizer is
        not evidence that the UIT still lives.
        """
        return self.validity(today).expired

    def summary_text(self, today: dt.date | None = None) -> str:
        """The card's facts as plain text, for pasting into a chat message.

        The UIT is alone on the first line so that copying the whole block, or
        just its first line, both yield a usable code. This is the fallback for
        viewers that will not select text in a PDF.

        A derived window says so in the line itself and again in a closing note
        naming the rule — the reader has to be able to tell the estimate from
        ANAF's own date without knowing anafpy exists.
        """
        vehicle = self.transport.vehicle
        plates = " + ".join(
            p for p in (vehicle.plate, vehicle.trailer1, vehicle.trailer2) if p
        )
        window = self.validity(today)
        estimated = window.source == "statutory"
        validity = (
            f" · UIT valabil{' (estimat)' if estimated else ''} până la "
            f"{window.last_valid_day:%d.%m.%Y} inclusiv"
        )
        if window.expired:
            validity += " — PROBABIL EXPIRAT" if estimated else " — EXPIRAT"
        lines = [
            self.uit,
            f"Vehicul {plates}",
            f"Transport {vehicle.transport_date:%d.%m.%Y}{validity}",
        ]
        operation = self.transport.operation_type
        lines.append(f"{operation.value} — {label_for(operation)}")
        if estimated:
            lines.append(
                f"Valabilitate estimată: {window.days} zile calendaristice de la "
                "data transportului (OUG 41/2022 art. 11). ANAF comunică data "
                "expirării doar organizatorului transportului."
            )
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
