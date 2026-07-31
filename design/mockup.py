"""Visual mockups for the UIT presentation artifacts.

Throwaway design exploration — NOT the future renderer. Run with:

    uv run --with segno --with fpdf2 --with fonttools python design/mockup.py

Two deliverables, both PDF:

- ``uit-card.pdf`` — the driver card, sized to a phone display (90x195mm, the
  phone's own 19.5:9), every value real selectable text, QR drawn as vectors.
- ``partner-pdf.pdf`` — the A4 document for the partner company.

macOS system fonts (Arial, Menlo) stand in for the OFL Noto faces the real
`anafpy[cards]` extra would bundle. All data is fictional — it mirrors the
*shape* of a real AIC filing (Hungarian supplier, Bulgarian carrier) without
carrying anyone's real CIF or UIT.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

import segno
from fpdf import FPDF

HERE = Path(__file__).parent

INK = (27, 31, 42)
ACCENT = (29, 78, 216)
SLATE = (51, 65, 85)
GRAY = (107, 114, 128)
RED = (185, 28, 28)
LIGHT_GRAY = (243, 244, 246)
LIGHT_RED = (254, 226, 226)
RULE = (229, 231, 235)

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MENLO = "/System/Library/Fonts/Menlo.ttc"

# --- fictional sample filing -------------------------------------------------
# The UIT prints solid, never grouped in fours — both real-world references
# print it as one run.
UIT = "9T5R204811730587"
OPERATION = ("10", "AIC", "Achiziție intracomunitară")
# Fiscal codes print verbatim, with no country name bolted on: a foreign VAT
# number already carries its country prefix. A Romanian code does NOT, which is
# why `country` stays a field of its own for the formal PDF.
DECLARANT = ("SC EXEMPLU AGRO SRL", "RO12345678")
DECLARANT_SEAT = "Sat Exemplu, com. Exemplu, jud. Timiș, Calea Exemplu nr. 10, 307315"
PARTNER = ("EXAMPLE FEED KFT", "HU11223344")
PARTNER_COUNTRY = "Ungaria (HU)"
CARRIER = ("EXPRES TRANS EOOD", "BG99887766")
CARRIER_COUNTRY = "Bulgaria (BG)"
PLATE, TRAILER, TRAILER2 = "CB1234AB", "CB5678CD", "CB9012EF"
TRANSPORT_DATE = "01.08.2026"
VALID_FROM, VALID_TO = "01.08.2026", "15.08.2026"
UPLOAD_ID = "12345678901"
FILED_ON = "31.07.2026"
ROUTE_START = "Punct de trecere a frontierei GIURGIU (cod 9) — dinspre Ruse, Bulgaria"
ROUTE_END = "Exemplu, jud. Timiș — Calea Exemplu nr. 10"
GOODS = [
    ["1", "Bicarbonat de sodiu, saci 25 kg", "Comercializare", "28363000",
     "22.050,00 KGM", "22.050,00", "22.350,00", "49.810,95"],
]
GOODS_TOTAL = ["", "TOTAL — 1 linie", "", "", "", "22.050,00", "22.350,00",
               "49.810,95"]
# ANAF's TipDocumentType is CMR (10) / Factură (20) / Aviz de însoțire a
# mărfii (30) / Altele (9999) — a filing need not carry a CMR, so the section
# renders whatever types are present rather than assuming one.
DOCUMENTS = [
    ("CMR", "2026-EX/000343", "01.08.2026", ""),
    ("Factură", "INV-2026-114", "31.07.2026", ""),
]
# Observations are the CALLER's, never boilerplate: facts specific to this
# filing that the structured fields cannot carry.
SAMPLE_NOTES = [
    "Greutatea brută de 22.350 kg este cea comunicată de expeditor cu "
    "mențiunea „cca.” — dacă bonul de cântar indică o valoare diferită, "
    "declarația se corectează printr-o notificare de corecție a UIT.",
    "Marfa se încarcă în zona industrială Devnya (Bulgaria) și se descarcă la "
    "sediul declarantului.",
]

# Which noun names the commercial partner, by ANAF operation code: inbound
# operations buy from a supplier, outbound ones sell to a customer.
PARTNER_LABEL = {
    "10": "Furnizor", "12": "Furnizor", "14": "Furnizor", "40": "Furnizor",
    "60": "Furnizor",
    "20": "Client", "22": "Client", "24": "Client", "50": "Client",
    "70": "Client",
    "30": "Partener",
}


def menlo_bold_ttf() -> str:
    """Menlo ships as a .ttc collection, which fpdf2 won't load; extract the
    bold face once. The real extra would just bundle Noto Sans Mono."""
    out = Path(tempfile.gettempdir()) / "anafpy-mockup-Menlo-Bold.ttf"
    if not out.exists():
        from fontTools.ttLib import TTFont

        for i in range(4):
            f = TTFont(MENLO, fontNumber=i)
            name = f["name"].getDebugName(2) or ""
            if "bold" in name.lower():
                f.save(out)
                break
    return str(out)


class Cell(NamedTuple):
    """One bordered fact: a grey caption band over a value (+ optional sub)."""

    caption: str
    value: str
    sub: str = ""
    mono: bool = False
    value_size: float = 46
    color: tuple[int, int, int] = INK
    band: tuple[int, int, int] = LIGHT_GRAY


def render_card_pdf(
    path: Path,
    *,
    expired: bool = False,
    trailers: tuple[str, ...] = (TRAILER,),
    size_px: tuple[int, int] = (1080, 2340),
) -> None:
    """The driver card: one page at the phone's own aspect ratio.

    Every fact lives in a bordered cell with a caption band — the treatment the
    plate and dates already used, extended to the parties so the card reads as
    one continuous table rather than a table plus loose text.

    Coordinates stay in a 1080-wide pixel space and convert on the way out, so
    the design can be reasoned about in screen terms.
    """
    page_w_pt = 90 / 25.4 * 72  # 90mm wide
    k = page_w_pt / size_px[0]

    def p(v: float) -> float:
        return v * k

    pdf = FPDF(unit="pt", format=(page_w_pt, p(size_px[1])))
    pdf.set_auto_page_break(False)
    pdf.add_font("NS", "", ARIAL)
    pdf.add_font("NS", "B", ARIAL_B)
    pdf.add_font("Mono", "B", menlo_bold_ttf())
    pdf.add_page()

    W, M = size_px[0], 64
    content_w = W - 2 * M

    def text_at(
        x: float, y: float, w: float, txt: str, fam: str, style: str,
        size: float, color: tuple[int, int, int], align: str = "L",
    ) -> None:
        pdf.set_font(fam, style, p(size))
        pdf.set_text_color(*color)
        pdf.set_xy(p(x), p(y))
        pdf.cell(p(w), p(size * 1.16), txt, align=align)

    def fit(fam: str, style: str, txt: str, width_px: float, start: float) -> float:
        size = start
        while size > 16:
            pdf.set_font(fam, style, p(size))
            if pdf.get_string_width(txt) <= p(width_px):
                break
            size -= 2
        return size

    def table_row(y: float, cells: list[Cell], h: float) -> float:
        w = content_w / len(cells)
        band_h = 44.0
        for i, c in enumerate(cells):
            x = M + i * w
            pdf.set_fill_color(*c.band)
            pdf.rect(p(x), p(y), p(w), p(band_h), style="F")
            pdf.set_draw_color(*RULE)
            pdf.set_line_width(p(2))
            pdf.rect(p(x), p(y), p(w), p(h))
            text_at(x, y + 7, w, c.caption, "NS", "B", 26,
                    RED if c.band == LIGHT_RED else GRAY, align="C")
            fam, style = ("Mono", "B") if c.mono else ("NS", "B")
            vs = fit(fam, style, c.value, w - 40, c.value_size)
            sub_h = 44.0 if c.sub else 0.0
            vy = y + band_h + max(4, (h - band_h - vs - sub_h) / 2)
            text_at(x, vy, w, c.value, fam, style, vs, c.color, align="C")
            if c.sub:
                text_at(x, vy + vs + 6, w, c.sub, "Mono", "B", 38, SLATE,
                        align="C")
        return y + h

    y = 132.0
    text_at(M, y, content_w, "RO e-Transport", "NS", "B", 50, INK)
    text_at(M, y + 8, content_w, f"{OPERATION[1]} ({OPERATION[0]})", "NS", "",
            34, GRAY, align="R")
    y += 78
    pdf.set_fill_color(*ACCENT)
    pdf.rect(p(M), p(y), p(content_w), p(5), style="F")
    y += 44

    if expired:
        pdf.set_fill_color(*RED)
        pdf.rect(p(0), p(y), p(W), p(66), style="F")
        text_at(M, y + 14, content_w, "EXPIRAT — UIT-ul nu mai este valabil",
                "NS", "B", 34, (255, 255, 255), align="C")
        y += 86

    uit_size = fit("Mono", "B", UIT, content_w, 104)
    text_at(M, y, content_w, UIT, "Mono", "B", uit_size,
            GRAY if expired else ACCENT, align="C")
    y += uit_size + 24

    # Build the table first: the QR then takes whatever vertical space is left,
    # so a card with more plates gives up QR rather than crowding the footer.
    vehicle = Cell("VEHICUL", PLATE, mono=True, value_size=98)
    date = Cell("DATA TRANSPORT", TRANSPORT_DATE, mono=True, value_size=98)
    validity = Cell("UIT VALABIL PÂNĂ LA" if not expired else "A EXPIRAT LA",
                    VALID_TO, mono=True, value_size=98,
                    color=RED if expired else INK,
                    band=LIGHT_RED if expired else LIGHT_GRAY)

    def trailer_cell(i: int, plate: str) -> Cell:
        caption = "REMORCĂ" if len(trailers) == 1 else f"REMORCĂ {i + 1}"
        return Cell(caption, plate, mono=True, value_size=98)

    # Every plate is a peer, so every plate gets its own cell at full size —
    # three across would fit-shrink them all back to ~57px, and folding the
    # second trailer into a sub-line would rank it below the first, which the
    # law does not.
    match [trailer_cell(i, t) for i, t in enumerate(trailers)]:
        case []:
            rows = [[vehicle]]
        case [one]:
            rows = [[vehicle, one]]
        case [*many]:
            rows = [[vehicle], many]
    rows.append([date, validity])
    table_h = 140 * len(rows) + 112 + 150 * 3

    footer_top = size_px[1] - 145
    qr_px = max(560, min(860, footer_top - 40 - table_h - y - 70))

    # The QR as vector rectangles — crisp at any zoom, unlike an embedded
    # raster. Quiet zone cut to 2 modules: the page is white all round, so it
    # supplies the rest, and the same footprint buys bigger modules.
    border = 2
    matrix = list(segno.make(UIT, error="h").matrix)
    modules = len(matrix) + 2 * border
    m = qr_px / modules
    x0 = (W - qr_px) / 2
    pdf.set_fill_color(0, 0, 0)
    for r, row in enumerate(matrix):
        for c, dark in enumerate(row):
            if dark:
                pdf.rect(p(x0 + (c + border) * m), p(y + (r + border) * m),
                         p(m) + 0.05, p(m) + 0.05, style="F")
    y += qr_px + 20
    text_at(M, y, content_w, "Scanează pentru codul UIT", "NS", "", 28, GRAY,
            align="C")
    y += 50

    for row in rows:
        y = table_row(y, row, 140)
    y = table_row(y, [
        Cell("TIP OPERAȚIUNE", f"{OPERATION[0]} — {OPERATION[2]}"),
    ], 112)
    for caption, (name, code) in (
        ("DECLARANT", DECLARANT),
        (PARTNER_LABEL[OPERATION[0]].upper(), PARTNER),
        ("TRANSPORTATOR", CARRIER),
    ):
        y = table_row(y, [Cell(caption, name, sub=code)], 150)

    # Two lines, substance first: the filing identifiers carry weight, the
    # disclaimer is fine print. "Document informativ" already says the card is
    # not proof, so the separate "face dovada doar declarația..." sentence was
    # saying it twice.
    fy = footer_top
    pdf.set_fill_color(*RULE)
    pdf.rect(p(M), p(fy), p(content_w), p(2), style="F")
    fy += 23
    for line, color in (
        (f"Depusă {FILED_ON} · index încărcare {UPLOAD_ID}", SLATE),
        ("Document informativ, generat local cu anafpy — nu este emis de ANAF.",
         GRAY),
    ):
        text_at(M, fy, content_w, line, "NS", "",
                fit("NS", "", line, content_w, 27), color)
        fy += 37
    pdf.output(str(path))


class DetailsPDF(FPDF):
    """A4 details document with a running footer identifying the filing."""

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("NS", "", 7.5)
        self.set_text_color(*GRAY)
        self.cell(140, 4, f"UIT {UIT} · {DECLARANT[0]}, {DECLARANT[1]} · "
                          f"depusă {FILED_ON}")
        self.cell(40, 4, f"Pagina {self.page_no()} din {{nb}}", align="R")


def render_details_pdf(path: Path, *, notes: Sequence[str] = ()) -> None:
    """The full filing, for the partner company or the caller's own file.

    ``notes`` is the caller's own observations; the section is omitted entirely
    when there are none. The two unbounded sections — the goods table, then the
    notes — sit at the end, so a long one spills onto page 2 while everything
    identifying the filing stays together on page 1.
    """
    pdf = DetailsPDF(format="A4")
    pdf.add_font("NS", "", ARIAL)
    pdf.add_font("NS", "B", ARIAL_B)
    pdf.add_font("Mono", "B", menlo_bold_ttf())
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    L, CW = 15, 180

    def section(title: str) -> None:
        pdf.ln(3)
        pdf.set_fill_color(*SLATE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("NS", "B", 8.5)
        pdf.cell(CW, 6, f"  {title.upper()}", fill=True, new_x="LMARGIN",
                 new_y="NEXT")
        pdf.ln(1.5)
        pdf.set_text_color(*INK)

    def kv(label: str, value: str, mono: bool = False) -> None:
        pdf.set_font("NS", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(38, 5.4, f"  {label}")
        pdf.set_font("Mono" if mono else "NS", "B", 9 if mono else 9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CW - 38, 5.4, value, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(L, 13)
    pdf.set_font("NS", "B", 17)
    pdf.set_text_color(*INK)
    pdf.cell(112, 9, "DECLARAȚIE RO e-TRANSPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(L)
    pdf.set_font("NS", "", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(112, 5, "Sistem național de monitorizare a transporturilor "
                     "de bunuri · ANAF", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(L + 112, 13)
    pdf.set_font("NS", "", 7.5)
    pdf.cell(68, 4, "COD UIT", align="R")
    pdf.set_xy(L + 112, 17.5)
    pdf.set_font("Mono", "B", 13)
    pdf.set_text_color(*ACCENT)
    pdf.cell(68, 7, UIT, align="R")
    pdf.set_y(29)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(L, pdf.get_y(), L + CW, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(2)

    section("Identificare declarație")
    kv("Declarant", f"{DECLARANT[0]} · {DECLARANT[1]}")
    kv("Sediu", DECLARANT_SEAT)
    kv("Tip operațiune", f"{OPERATION[1]} (cod {OPERATION[0]}) — {OPERATION[2]}")
    kv("Cod UIT", UIT, mono=True)
    kv("Index încărcare", UPLOAD_ID)
    kv("Data depunerii", FILED_ON)
    kv("Stare ANAF", "OK — prelucrare finalizată, fără erori")
    kv("Valabilitate UIT", f"{VALID_FROM} – {VALID_TO} (15 zile calendaristice)")

    section(f"{PARTNER_LABEL[OPERATION[0]]} (partener comercial)")
    kv("Denumire", PARTNER[0])
    kv("Cod fiscal", PARTNER[1])
    kv("Țara", PARTNER_COUNTRY)

    section("Date transport")
    kv("Transportator", f"{CARRIER[0]} · {CARRIER[1]}")
    kv("Țara transportator", CARRIER_COUNTRY)
    kv("Nr. vehicul", PLATE, mono=True)
    kv("Nr. remorcă 1", TRAILER, mono=True)
    kv("Data transportului", TRANSPORT_DATE)
    kv("Loc start traseu", ROUTE_START)
    kv("Loc final traseu", ROUTE_END)

    section("Documente de transport")
    for label, number, date, note in DOCUMENTS:
        value = f"nr. {number} din {date}" if number else f"din {date}"
        kv(label, f"{value} — {note}" if note else value)

    section("Bunuri transportate")
    widths = [7, 47, 24, 18, 26, 19, 19, 20]
    headers = ["#", "Denumire marfă", "Scop", "Cod NC", "Cantitate", "Net (kg)",
               "Brut (kg)", "Valoare RON"]
    numeric = {"Cantitate", "Net (kg)", "Brut (kg)", "Valoare RON"}
    pdf.set_font("NS", "B", 7.5)
    pdf.set_fill_color(*SLATE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(*RULE)
    for w, h in zip(widths, headers):
        pdf.cell(w, 6, f" {h}", border=0, fill=True,
                 align="R" if h in numeric else "L")
    pdf.ln()
    pdf.set_text_color(*INK)
    pdf.set_font("NS", "", 8)
    for row in GOODS:
        for w, cellv, h in zip(widths, row, headers):
            pdf.cell(w, 6.4, f" {cellv}", border="B",
                     align="R" if h in numeric else "L")
        pdf.ln()
    pdf.set_font("NS", "B", 8)
    pdf.set_fill_color(*LIGHT_GRAY)
    for w, cellv, h in zip(widths, GOODS_TOTAL, headers):
        pdf.cell(w, 6.4, f" {cellv}", border=0, fill=True,
                 align="R" if h in numeric else "L")
    pdf.ln()

    if notes:
        section("Observații")
        pdf.set_font("NS", "", 8.5)
        pdf.set_text_color(*INK)
        for note in notes:
            pdf.multi_cell(CW, 4.6, f"  •  {note}", new_x="LMARGIN",
                           new_y="NEXT")
            pdf.ln(0.8)

    pdf.ln(4)
    pdf.set_font("NS", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(CW, 4, "Document informativ generat local cu anafpy — nu "
                          "este emis de ANAF. Face dovada doar declarația "
                          "înregistrată în sistemul e-Transport.")
    pdf.output(str(path))


if __name__ == "__main__":
    render_card_pdf(HERE / "uit-card.pdf")
    render_card_pdf(HERE / "uit-card-expired.pdf", expired=True)
    render_card_pdf(HERE / "uit-card-no-trailer.pdf", trailers=())
    render_card_pdf(HERE / "uit-card-two-trailers.pdf",
                    trailers=(TRAILER, TRAILER2))
    render_details_pdf(HERE / "uit-details.pdf")
    render_details_pdf(HERE / "uit-details-notes.pdf", notes=SAMPLE_NOTES)
    print("done")
