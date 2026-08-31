"""fpdf2 + segno rendering of the UIT card and detail document.

Needs the ``anafpy[cards]`` extra; reach it through
:func:`anafpy.etransport.card.load_cardpdf`, which turns a missing extra into an
:class:`~anafpy.exceptions.AnafConfigError`.

Two page geometries, one visual language. The **card** is laid out in a
1080-wide pixel space and converted to points on the way out, so its proportions
can be reasoned about in phone-screen terms; every fact sits in a bordered cell
with a grey caption band, stacked flush into one continuous table. The **detail
document** is plain A4 in millimetres, section bars and label/value rows.

Two layout rules are load-bearing rather than cosmetic. Short codes sit two per
row, never three: at a third of the width they fit-shrink to about half the
size, which is the difference between a plate a driver can hold up and one an
inspector has to squint at. And the QR is sized *last*, from whatever vertical
space the table leaves — so a filing with a second trailer, or an expired
banner, gives up QR rather than crowding the page.

On the detail document the goods table is where the caller's prose meets a fixed
column, and an fpdf2 cell neither wraps nor clips: the free-text columns are
wrapped to their own width, the codes and figures beside them fit-shrink instead
(they carry no word to break on), and a row that would cross the bottom margin
moves to the next page with the column strip above it.

The bundled Noto faces are not decoration: fpdf2's built-in core fonts are
Latin-1 only, so ``ș`` and ``ț`` cannot be represented in them, and this is a
Romanian document.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple, cast

import segno
from fpdf import FPDF

from .card import UitCard, UitValidity, partner_label
from .labels import country_text, label_for
from .models import (
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
)

__all__ = ["render_card", "render_details"]

_FONTS = Path(__file__).resolve().parent / "_fonts"
_SANS = _FONTS / "NotoSans-Regular.ttf"
_SANS_BOLD = _FONTS / "NotoSans-Bold.ttf"
_MONO_BOLD = _FONTS / "NotoSansMono-Bold.ttf"

_INK = (27, 31, 42)
_ACCENT = (29, 78, 216)
_SLATE = (51, 65, 85)
_GRAY = (107, 114, 128)
_RED = (185, 28, 28)
_AMBER = (180, 83, 9)
_LIGHT_GRAY = (243, 244, 246)
_LIGHT_RED = (254, 226, 226)
_LIGHT_AMBER = (254, 243, 199)
_RULE = (229, 231, 235)
_WHITE = (255, 255, 255)

# 19.5:9 — iPhone X-and-later and most Samsung/Xiaomi flagships. A 20:9 Android
# letterboxes it by a hair, invisible against the white page.
_CARD_PX = (1080, 2340)
_CARD_WIDTH_MM = 90.0
_MARGIN = 64
_FOOTER_OFFSET = 145
_DISCLAIMER = "Document informativ, generat local cu anafpy — nu este emis de ANAF."

# A caption takes its colour from its band, so a cell states its own standing.
_CAPTION_COLOR = {_LIGHT_RED: _RED, _LIGHT_AMBER: _AMBER}

# The expiry cell's wording and colour, by (window source, expired). ANAF's
# dates get the plain caption and red when lapsed; a derived window says
# "estimat" and stays amber either way — it is our arithmetic, not a verdict.
_EXPIRY_STYLE = {
    ("anaf", False): ("UIT VALABIL PÂNĂ LA", _LIGHT_GRAY, _INK),
    ("anaf", True): ("A EXPIRAT LA", _LIGHT_RED, _RED),
    ("statutory", False): ("VALABIL (ESTIMAT) PÂNĂ LA", _LIGHT_AMBER, _INK),
    ("statutory", True): ("PROBABIL EXPIRAT DIN", _LIGHT_AMBER, _AMBER),
}


class _Cell(NamedTuple):
    """One bordered fact: a grey caption band over a value (+ optional sub)."""

    caption: str
    value: str
    sub: str = ""
    mono: bool = False
    value_size: float = 46
    color: tuple[int, int, int] = _INK
    band: tuple[int, int, int] = _LIGHT_GRAY


class _Column(NamedTuple):
    """One goods-table column: its width, its header, and how values sit in it.

    ``wrap`` marks the two free-text columns — the caller's (and ANAF's) prose,
    of no bounded length. Everything else is a code or a figure: short by
    construction, with no word to break on, so those fit-shrink instead.
    """

    width: float
    header: str
    align: str = "L"
    wrap: bool = False


# 180mm of content, in ANAF's own reading order for a goods line.
_GOODS_COLUMNS = (
    _Column(7.0, "#"),
    _Column(47.0, "Denumire marfă", wrap=True),
    _Column(24.0, "Scop", wrap=True),
    _Column(18.0, "Cod NC"),
    _Column(26.0, "Cantitate", align="R"),
    _Column(19.0, "Net (kg)", align="R"),
    _Column(19.0, "Brut (kg)", align="R"),
    _Column(20.0, "Valoare RON", align="R"),
)
_GOODS_LINE_H = 4.4
_GOODS_ROW_PAD = 2.0


def _amount(value: Decimal | None) -> str:
    """Romanian number formatting: '.' groups, ',' decimals."""
    if value is None:
        return "—"
    whole, _, frac = f"{value:,.2f}".partition(".")
    return f"{whole.replace(',', '.')},{frac}"


def _location_text(location: FlatTransportLocation) -> str:
    """One end of the route as a person reads it."""
    match location:
        case FlatTransportLocation(border_point=point) if point is not None:
            return (
                f"Punct de trecere a frontierei {label_for(point)} (cod {point.value})"
            )
        case FlatTransportLocation(customs_office=office) if office is not None:
            return f"Birou vamal {label_for(office)} (cod {office.value})"
        case FlatTransportLocation(address=address) if address is not None:
            street = " ".join(part for part in (address.street, address.number) if part)
            county = f"jud. {label_for(address.county)}"
            return ", ".join(
                part for part in (street, address.locality, county) if part
            )
        case _:  # pragma: no cover - the model admits exactly one of the three
            return "—"


def _document_text(document: FlatTransportDocument) -> tuple[str, str]:
    """A transport document as (label, value). ANAF requires the date but not
    the number, so a numberless document still reads properly."""
    value = (
        f"nr. {document.number} din {document.date:%d.%m.%Y}"
        if document.number
        else f"din {document.date:%d.%m.%Y}"
    )
    if document.note:
        value = f"{value} — {document.note}"
    return label_for(document.doc_type), value


class _Sheet:
    """An FPDF page drawn in the card's pixel space.

    Coordinates and font sizes are given in the 1080-wide design space and
    scaled on every call, so the layout reads the way it was designed.
    """

    def __init__(self, size_px: tuple[int, int]) -> None:
        self.width, self.height = size_px
        self.k = (_CARD_WIDTH_MM / 25.4 * 72) / self.width
        self.pdf = FPDF(unit="pt", format=(self.p(self.width), self.p(self.height)))
        self.pdf.set_auto_page_break(False)
        self.pdf.add_font("NS", "", str(_SANS))
        self.pdf.add_font("NS", "B", str(_SANS_BOLD))
        self.pdf.add_font("Mono", "B", str(_MONO_BOLD))
        self.pdf.add_page()

    def p(self, value: float) -> float:
        return value * self.k

    def text(
        self,
        x: float,
        y: float,
        width: float,
        txt: str,
        *,
        family: str = "NS",
        style: str = "",
        size: float = 27,
        color: tuple[int, int, int] = _INK,
        align: str = "L",
    ) -> None:
        self.pdf.set_font(family, style, self.p(size))
        self.pdf.set_text_color(*color)
        self.pdf.set_xy(self.p(x), self.p(y))
        self.pdf.cell(self.p(width), self.p(size * 1.16), txt, align=align)

    def fit(
        self, txt: str, width: float, start: float, *, family: str, style: str
    ) -> float:
        """The largest size at or below ``start`` that keeps ``txt`` on one line."""
        size = start
        while size > 16:
            self.pdf.set_font(family, style, self.p(size))
            if self.pdf.get_string_width(txt) <= self.p(width):
                break
            size -= 2
        return size

    def fill(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: tuple[int, int, int],
    ) -> None:
        self.pdf.set_fill_color(*color)
        self.pdf.rect(self.p(x), self.p(y), self.p(width), self.p(height), style="F")

    def outline(self, x: float, y: float, width: float, height: float) -> None:
        self.pdf.set_draw_color(*_RULE)
        self.pdf.set_line_width(self.p(2))
        self.pdf.rect(self.p(x), self.p(y), self.p(width), self.p(height))

    def qr(self, payload: str, x: float, y: float, size: float) -> None:
        """The QR as vector rectangles — crisp at any zoom, and no raster to
        embed. The quiet zone is 2 modules rather than the spec's 4: the page is
        white all round, so it supplies the rest, and the same footprint buys
        bigger, more scannable modules.
        """
        border = 2
        matrix = list(segno.make(payload, error="h").matrix)
        module = size / (len(matrix) + 2 * border)
        self.pdf.set_fill_color(0, 0, 0)
        for row_index, row in enumerate(matrix):
            for col_index, dark in enumerate(row):
                if dark:
                    self.pdf.rect(
                        self.p(x + (col_index + border) * module),
                        self.p(y + (row_index + border) * module),
                        self.p(module) + 0.05,
                        self.p(module) + 0.05,
                        style="F",
                    )

    def table_row(self, y: float, cells: list[_Cell], height: float) -> float:
        width = (self.width - 2 * _MARGIN) / len(cells)
        band = 44.0
        for index, cell in enumerate(cells):
            x = _MARGIN + index * width
            self.fill(x, y, width, band, cell.band)
            self.outline(x, y, width, height)
            self.text(
                x,
                y + 7,
                width,
                cell.caption,
                style="B",
                size=self.fit(cell.caption, width - 24, 26, family="NS", style="B"),
                color=_CAPTION_COLOR.get(cell.band, _GRAY),
                align="C",
            )
            family, style = ("Mono", "B") if cell.mono else ("NS", "B")
            size = self.fit(
                cell.value, width - 40, cell.value_size, family=family, style=style
            )
            sub_height = 44.0 if cell.sub else 0.0
            value_y = y + band + max(4, (height - band - size - sub_height) / 2)
            self.text(
                x,
                value_y,
                width,
                cell.value,
                family=family,
                style=style,
                size=size,
                color=cell.color,
                align="C",
            )
            if cell.sub:
                self.text(
                    x,
                    value_y + size + 6,
                    width,
                    cell.sub,
                    family="Mono",
                    style="B",
                    size=38,
                    color=_SLATE,
                    align="C",
                )
        return y + height


def render_card(card: UitCard, *, today: dt.date | None = None) -> bytes:
    """The driver card: one page at a phone's aspect ratio, text selectable."""
    sheet = _Sheet(_CARD_PX)
    width = sheet.width
    content = width - 2 * _MARGIN
    window = card.validity(today)
    expired = window.expired
    estimated = window.source == "statutory"
    transport = card.transport
    vehicle = transport.vehicle
    operation = transport.operation_type

    y = 132.0
    sheet.text(_MARGIN, y, content, "RO e-Transport", style="B", size=50)
    sheet.text(
        _MARGIN,
        y + 8,
        content,
        f"{operation.name} ({operation.value})",
        size=34,
        color=_GRAY,
        align="R",
    )
    y += 78
    sheet.fill(_MARGIN, y, content, 5, _ACCENT)
    y += 44

    if expired:
        # An estimated window states its own uncertainty: amber and "probabil",
        # because a red EXPIRAT is a verdict and only ANAF's date is one.
        sheet.fill(0, y, width, 66, _AMBER if estimated else _RED)
        sheet.text(
            _MARGIN,
            y + 14,
            content,
            "PROBABIL EXPIRAT — verificați valabilitatea"
            if estimated
            else "EXPIRAT — UIT-ul nu mai este valabil",
            style="B",
            size=34,
            color=_WHITE,
            align="C",
        )
        y += 86

    # The code alone, one solid run across the full width — no caption, since
    # nothing else on the card could be mistaken for it, and never grouped:
    # ANAF and the invoicing software that already prints these both set it
    # solid, so grouping would be our invention.
    size = sheet.fit(card.uit, content, 104, family="Mono", style="B")
    sheet.text(
        _MARGIN,
        y,
        content,
        card.uit,
        family="Mono",
        style="B",
        size=size,
        color=_GRAY if expired else _ACCENT,
        align="C",
    )
    y += size + 24

    rows = _card_rows(card, window)
    table_height = 140 * len(rows) + 112 + 150 * 3
    # The estimate's basis is a third footer line, and it buys its room from the
    # QR like every other variation on this page.
    footer_top = sheet.height - _FOOTER_OFFSET - (37 if estimated else 0)
    qr_size = max(560.0, min(860.0, footer_top - 40 - table_height - y - 70))

    sheet.qr(card.uit, (width - qr_size) / 2, y, qr_size)
    y += qr_size + 20
    sheet.text(
        _MARGIN,
        y,
        content,
        "Scanează pentru codul UIT",
        size=28,
        color=_GRAY,
        align="C",
    )
    y += 50

    for row in rows:
        y = sheet.table_row(y, row, 140)
    y = sheet.table_row(
        y,
        [_Cell("TIP OPERAȚIUNE", f"{operation.value} — {label_for(operation)}")],
        112,
    )
    parties = [
        ("DECLARANT", card.declarant_name, card.declarant_code),
        (
            partner_label(operation).upper(),
            transport.partner.name,
            transport.partner.code,
        ),
        ("TRANSPORTATOR", vehicle.carrier_name, vehicle.carrier_code),
    ]
    for caption, name, code in parties:
        y = sheet.table_row(y, [_Cell(caption, name or "—", sub=code or "")], 150)

    footer_y = footer_top
    sheet.fill(_MARGIN, footer_y, content, 2, _RULE)
    footer_y += 23
    for line, color in _card_footer_lines(card, window):
        size = sheet.fit(line, content, 27, family="NS", style="")
        sheet.text(_MARGIN, footer_y, content, line, size=size, color=color)
        footer_y += 37
    return bytes(sheet.pdf.output())


def _card_rows(card: UitCard, window: UitValidity) -> list[list[_Cell]]:
    """The plate and date rows.

    Every plate is a peer and gets its own cell at full size: three across
    would fit-shrink them all, and folding the second trailer into a sub-line
    would rank it below the first, which the law does not. With no trailer the
    top row collapses to a full-width VEHICUL, keeping the plate as the anchor
    and the dates side by side where they compare.
    """
    vehicle = card.transport.vehicle
    plate = _Cell("VEHICUL", vehicle.plate, mono=True, value_size=98)
    trailers = [t for t in (vehicle.trailer1, vehicle.trailer2) if t]
    match trailers:
        case []:
            rows = [[plate]]
        case [only]:
            rows = [[plate, _Cell("REMORCĂ", only, mono=True, value_size=98)]]
        case _:
            rows = [
                [plate],
                [
                    _Cell(f"REMORCĂ {index + 1}", value, mono=True, value_size=98)
                    for index, value in enumerate(trailers)
                ],
            ]

    date = _Cell(
        "DATA TRANSPORT",
        f"{vehicle.transport_date:%d.%m.%Y}",
        mono=True,
        value_size=98,
    )
    # A live card prints the last day the driver may actually use, an expired
    # one the day it lapsed — which is the shape ANAF's data_exp_uit already
    # has. A window ANAF never disclosed prints in amber under a caption that
    # calls it an estimate, so the two are never read as the same claim.
    caption, band, color = _EXPIRY_STYLE[window.source, window.expired]
    rows.append(
        [
            date,
            _Cell(
                caption,
                f"{window.first_expired_day:%d.%m.%Y}"
                if window.expired
                else f"{window.last_valid_day:%d.%m.%Y}",
                mono=True,
                value_size=98,
                color=color,
                band=band,
            ),
        ]
    )
    return rows


def _card_footer_lines(
    card: UitCard, window: UitValidity
) -> list[tuple[str, tuple[int, int, int]]]:
    """Substance first — the filing identifiers carry weight, the disclaimer is
    fine print. A derived window names the rule it was derived from, so the date
    above can be checked rather than trusted."""
    parts = []
    if card.filed_on is not None:
        parts.append(f"Depusă {card.filed_on:%d.%m.%Y}")
    if card.upload_id:
        parts.append(f"index încărcare {card.upload_id}")
    lines = [(_DISCLAIMER, _GRAY)]
    if window.source == "statutory":
        lines.insert(
            0,
            (
                f"Valabilitate estimată: {window.days} zile de la data "
                "transportului (OUG 41/2022).",
                _AMBER,
            ),
        )
    if parts:
        lines.insert(0, (" · ".join(parts), _SLATE))
    return lines


def render_details(card: UitCard, *, today: dt.date | None = None) -> bytes:
    """The A4 detail document: the whole filing, for the partner or the file."""
    transport = card.transport
    vehicle = transport.vehicle
    operation = transport.operation_type
    left, content_w = 15.0, 180.0

    pdf = FPDF(format="A4")
    pdf.add_font("NS", "", str(_SANS))
    pdf.add_font("NS", "B", str(_SANS_BOLD))
    pdf.add_font("Mono", "B", str(_MONO_BOLD))
    pdf.set_auto_page_break(auto=True, margin=20)

    def footer_text() -> str:
        who = " · ".join(
            part for part in (card.declarant_name, card.declarant_code) if part
        )
        return f"UIT {card.uit}" + (f" · {who}" if who else "")

    pdf.footer = lambda: _details_footer(pdf, footer_text())  # type: ignore[method-assign]
    pdf.add_page()

    def section(title: str) -> None:
        pdf.ln(3)
        pdf.set_fill_color(*_SLATE)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("NS", "B", 8.5)
        pdf.cell(
            content_w, 6, f"  {title.upper()}", fill=True, new_x="LMARGIN", new_y="NEXT"
        )
        pdf.ln(1.5)
        pdf.set_text_color(*_INK)

    def kv(label: str, value: str, mono: bool = False) -> None:
        # The label column is fixed, so a long label would run silently under
        # the value: step the label down until it fits instead.
        size = 9.0
        pdf.set_font("NS", "", size)
        while size > 6.5 and pdf.get_string_width(f"  {label} ") > 38:
            size -= 0.5
            pdf.set_font("NS", "", size)
        pdf.set_text_color(*_GRAY)
        pdf.cell(38, 5.4, f"  {label}")
        pdf.set_font("Mono" if mono else "NS", "B", 9 if mono else 9.5)
        pdf.set_text_color(*_INK)
        pdf.multi_cell(content_w - 38, 5.4, value, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(left, 13)
    pdf.set_font("NS", "B", 17)
    pdf.set_text_color(*_INK)
    pdf.cell(112, 9, "DECLARAȚIE RO e-TRANSPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(left)
    pdf.set_font("NS", "", 8.5)
    pdf.set_text_color(*_GRAY)
    pdf.cell(
        112,
        5,
        "Sistem național de monitorizare a transporturilor de bunuri · ANAF",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_xy(left + 112, 13)
    pdf.set_font("NS", "", 7.5)
    pdf.cell(68, 4, "COD UIT", align="R")
    pdf.set_xy(left + 112, 17.5)
    pdf.set_font("Mono", "B", 13)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(68, 7, card.uit, align="R")
    pdf.set_y(29)
    pdf.set_draw_color(*_ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(left, pdf.get_y(), left + content_w, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(2)

    section("Identificare declarație")
    who = " · ".join(
        part for part in (card.declarant_name, card.declarant_code) if part
    )
    if who:
        kv("Declarant", who)
    kv(
        "Tip operațiune",
        f"{operation.name} (cod {operation.value}) — {label_for(operation)}",
    )
    kv("Cod UIT", card.uit, mono=True)
    if card.upload_id:
        kv("Index încărcare", card.upload_id)
    if card.filed_on is not None:
        kv("Data depunerii", f"{card.filed_on:%d.%m.%Y}")
    if card.anaf_state:
        kv("Stare ANAF", card.anaf_state)
    # Both dates, each labelled: the last usable day for the reader, and the
    # first expired day — data_exp_uit's own shape — for the record. A derived
    # window says so in the label, gives the rule it was counted by, and never
    # borrows ANAF's plain "EXPIRAT".
    window = card.validity(today)
    validity = (
        f"până la {window.last_valid_day:%d.%m.%Y} inclusiv "
        f"(expirat începând cu {window.first_expired_day:%d.%m.%Y})"
    )
    if window.source == "statutory":
        # "ESTIMAT" opens the value rather than qualifying the label: it is the
        # first thing read either way, and the label column has no room for it.
        validity = (
            f"ESTIMAT — {validity}; {window.days} zile calendaristice de la data "
            "transportului (OUG 41/2022 art. 11). ANAF comunică data expirării "
            "doar organizatorului transportului."
        )
        if window.expired:
            validity += " PROBABIL EXPIRAT."
        kv("Valabilitate UIT", validity)
    else:
        if window.expired:
            validity += " — EXPIRAT"
        kv("Valabilitate UIT", validity)

    section(f"{partner_label(operation)} (partener comercial)")
    kv("Denumire", transport.partner.name)
    if transport.partner.code:
        kv("Cod fiscal", transport.partner.code)
    kv("Țara", country_text(transport.partner.country))

    section("Date transport")
    carrier = " · ".join(
        part for part in (vehicle.carrier_name, vehicle.carrier_code) if part
    )
    kv("Transportator", carrier)
    kv("Țara transportator", country_text(vehicle.carrier_country))
    kv("Nr. vehicul", vehicle.plate, mono=True)
    for index, trailer in enumerate(
        [t for t in (vehicle.trailer1, vehicle.trailer2) if t]
    ):
        kv(f"Nr. remorcă {index + 1}", trailer, mono=True)
    kv("Data transportului", f"{vehicle.transport_date:%d.%m.%Y}")
    kv("Loc start traseu", _location_text(transport.start_location))
    kv("Loc final traseu", _location_text(transport.end_location))

    section("Documente de transport")
    for document in transport.documents:
        kv(*_document_text(document))

    _details_goods(pdf, transport.goods, content_w)

    if card.notes:
        section("Observații")
        pdf.set_font("NS", "", 8.5)
        pdf.set_text_color(*_INK)
        for note in card.notes:
            pdf.multi_cell(
                content_w, 4.6, f"  •  {note}", new_x="LMARGIN", new_y="NEXT"
            )
            pdf.ln(0.8)

    pdf.ln(4)
    pdf.set_font("NS", "", 7.5)
    pdf.set_text_color(*_GRAY)
    pdf.multi_cell(content_w, 4, _DISCLAIMER)
    return bytes(pdf.output())


def _details_footer(pdf: FPDF, text: str) -> None:
    pdf.set_y(-14)
    pdf.set_font("NS", "", 7.5)
    pdf.set_text_color(*_GRAY)
    pdf.cell(140, 4, text)
    pdf.cell(40, 4, f"Pagina {pdf.page_no()}", align="R")


def _details_goods(pdf: FPDF, goods: list[FlatTransportGood], content_w: float) -> None:
    """The goods table, last because it is the only unbounded section: a long
    one spills onto page 2 while everything identifying the filing stays on
    page 1."""
    left = pdf.l_margin
    pdf.ln(3)
    pdf.set_fill_color(*_SLATE)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("NS", "B", 8.5)
    pdf.cell(
        content_w, 6, "  BUNURI TRANSPORTATE", fill=True, new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(1.5)
    _goods_header(pdf, left)

    net_total = Decimal(0)
    value_total = Decimal(0)
    for index, good in enumerate(goods, start=1):
        net_total += good.net_weight or Decimal(0)
        value_total += good.value_ron or Decimal(0)
        _goods_row(
            pdf,
            left,
            [
                str(index),
                good.name,
                label_for(good.operation_scope),
                good.tariff_code or "—",
                f"{_amount(good.quantity)} {good.unit_code}",
                _amount(good.net_weight),
                _amount(good.gross_weight),
                _amount(good.value_ron),
            ],
            rule=True,
        )

    line_word = "linie" if len(goods) == 1 else "linii"
    _goods_row(
        pdf,
        left,
        [
            "",
            f"TOTAL — {len(goods)} {line_word}",
            "",
            "",
            "",
            _amount(net_total),
            _amount(sum((g.gross_weight for g in goods), Decimal(0))),
            _amount(value_total),
        ],
        bold=True,
        fill=True,
    )


def _goods_header(pdf: FPDF, left: float) -> None:
    """The column strip — redrawn on every page the table reaches, so a row
    that lands overleaf is still read under its own headings."""
    pdf.set_x(left)
    pdf.set_font("NS", "B", 7.5)
    pdf.set_fill_color(*_SLATE)
    pdf.set_text_color(*_WHITE)
    for column in _GOODS_COLUMNS:
        pdf.cell(column.width, 6, f" {column.header}", fill=True, align=column.align)
    pdf.ln()


def _goods_row(
    pdf: FPDF,
    left: float,
    values: list[str],
    *,
    bold: bool = False,
    fill: bool = False,
    rule: bool = False,
) -> None:
    """One row, laid out line by line rather than as a strip of fpdf2 cells.

    A cell neither wraps nor clips, so a 70-character goods description used to
    print straight over the tariff code beside it. Here the free-text columns
    are wrapped to their own width first, the row takes the depth of the
    deepest of them, and a row that would cross the bottom margin moves to the
    next page whole, header and all.
    """
    style = "B" if bold else ""
    pdf.set_font("NS", style, 8)
    cells = [
        _wrapped(pdf, value, column.width) if column.wrap else [value]
        for column, value in zip(_GOODS_COLUMNS, values, strict=True)
    ]
    height = max(len(cell) for cell in cells) * _GOODS_LINE_H + _GOODS_ROW_PAD
    if pdf.get_y() + height > pdf.page_break_trigger:
        pdf.add_page()
        _goods_header(pdf, left)

    top = pdf.get_y()
    width = sum(column.width for column in _GOODS_COLUMNS)
    if fill:
        pdf.set_fill_color(*_LIGHT_GRAY)
        pdf.rect(left, top, width, height, style="F")
    pdf.set_text_color(*_INK)
    x = left
    for column, cell in zip(_GOODS_COLUMNS, cells, strict=True):
        for offset, line in enumerate(cell):
            _fit_font(pdf, f" {line} ", column.width, style=style)
            pdf.set_xy(x, top + _GOODS_ROW_PAD / 2 + offset * _GOODS_LINE_H)
            pdf.cell(column.width, _GOODS_LINE_H, f" {line}", align=column.align)
        x += column.width
    if rule:
        pdf.set_draw_color(*_RULE)
        pdf.line(left, top + height, left + width, top + height)
    pdf.set_xy(left, top + height)


def _wrapped(pdf: FPDF, text: str, width: float) -> list[str]:
    """``text`` broken into the lines it takes inside a ``width`` column, in the
    font already selected — fpdf2's own line breaking, asked for a measurement
    instead of a drawing, so what is measured is what will be drawn."""
    lines = cast(
        "list[str]",
        pdf.multi_cell(
            width - _GOODS_ROW_PAD,
            _GOODS_LINE_H,
            text,
            dry_run=True,
            output="LINES",
        ),
    )
    return lines or [""]


def _fit_font(pdf: FPDF, text: str, width: float, *, style: str = "") -> None:
    """Select the largest body size, down to 5.5pt, that keeps ``text`` inside
    ``width`` — the fallback for the columns that carry no word to break on."""
    size = 8.0
    pdf.set_font("NS", style, size)
    while size > 5.5 and pdf.get_string_width(text) > width:
        size -= 0.25
        pdf.set_font("NS", style, size)
