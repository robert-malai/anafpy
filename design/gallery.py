"""Render every state of the UIT card and detail document, for design review.

This drives the **shipped** renderer (:mod:`anafpy.etransport.cardpdf`) over a
fictional filing — it is a gallery, not a mockup. The pre-implementation mockup
this replaced carried its own copy of the layout, which was right while the
layout was still being argued about and wrong the moment a renderer existed:
two implementations mean the gallery can show a card the library never draws.

Run: ``uv run python design/gallery.py`` (needs the ``cards`` extra, which
``uv sync --all-extras`` installs). PDFs and PNGs land next to this file and are
git-ignored; ``README.md`` plus this script are the record.

Every combination the card has: three trailer shapes x four validity states,
plus the content edges that move the layout — long names, a filing with no
declarant identifiers, and a domestic TTN for the shorter statutory window.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

from anafpy.etransport import FlatTransport, UitCard, load_cardpdf

HERE = Path(__file__).resolve().parent

# A fixed "today" keeps the gallery reproducible: re-running it a fortnight
# later must not quietly turn a live card into an expired one.
TODAY = dt.date(2026, 9, 10)
LIVE_TRANSPORT = dt.date(2026, 9, 8)
STALE_TRANSPORT = dt.date(2026, 8, 10)
# ANAF's data_exp_uit for each, as art. 11 has it for an AIC: 15 calendar days
# counted from the transport date, so the first expired day is date + 15. The
# ANAF and estimated cards therefore carry the same dates — which is the point:
# what differs between them is what we are entitled to claim, not the arithmetic.
LIVE_EXPIRY = dt.date(2026, 9, 23)
STALE_EXPIRY = dt.date(2026, 8, 25)

UIT = "9T5R204811730587"

NOTES = [
    "Greutatea brută este cea din CMR; expeditorul a declarat-o ca aproximativă.",
    "Recepția se face la rampa 3, în intervalul 08:00-16:00.",
]


#: A goods table pushed along both of its unbounded axes: descriptions wider
#: than their column, and enough lines to run past the bottom margin.
LONG_GOODS_NAMES = (
    "Rafturi metalice paletizate STOW (uzate, demontate) - 12 stâlpi, 120 traverse",
    "Bicarbonat de sodiu, saci 25 kg",
    "Folie stretch manuala 500 mm x 300 m, 23 microni, bax 6 role",
)

LONG_GOODS = [
    {
        "operation_scope": "COMERCIALIZARE",
        "name": LONG_GOODS_NAMES[index % len(LONG_GOODS_NAMES)],
        # One line carries a quantity wider than its column, for the fit-shrink
        # the figure columns answer with — they have no word to break on.
        "quantity": Decimal("1234567890.00")
        if index == 1
        else Decimal("1000.00") * (index + 1),
        "unit_code": "KGM",
        "gross_weight": Decimal("1020.00") * (index + 1),
        "net_weight": Decimal("1000.00") * (index + 1),
        "tariff_code": "73084000",
        "value_ron": Decimal("1850.00") * (index + 1),
    }
    for index in range(14)
]


def transport(
    *,
    transport_date: dt.date = LIVE_TRANSPORT,
    trailers: tuple[str, ...] = ("CB5678CD",),
    **overrides: object,
) -> FlatTransport:
    """The sample filing: an intra-community acquisition (AIC, 15-day window).

    Fictional throughout — a Hungarian supplier and a Bulgarian carrier, no real
    CIF, VAT number or UIT — per the repo's no-personal-data rule.
    """
    vehicle: dict[str, object] = {
        "plate": "CB1234AB",
        "carrier_name": "EXPRES TRANS EOOD",
        "carrier_country": "BG",
        "carrier_code": "BG99887766",
        "transport_date": transport_date,
    }
    for index, plate in enumerate(trailers, start=1):
        vehicle[f"trailer{index}"] = plate
    fields: dict[str, object] = {
        "operation_type": "AIC",
        "partner": {
            "name": "EXAMPLE FEED KFT",
            "country": "HU",
            "code": "HU11223344",
        },
        "vehicle": vehicle,
        "start_location": {"border_point": "GIURGIU"},
        "end_location": {
            "address": {
                "county": "TIMIS",
                "locality": "Periam",
                "street": "Calea Exemplu",
                "number": "10",
            }
        },
        "goods": [
            {
                "operation_scope": "COMERCIALIZARE",
                "name": "Bicarbonat de sodiu, saci 25 kg",
                "quantity": Decimal("22050.00"),
                "unit_code": "KGM",
                "gross_weight": Decimal("22350.00"),
                "net_weight": Decimal("22050.00"),
                "tariff_code": "28363000",
                "value_ron": Decimal("49810.95"),
            },
            {
                "operation_scope": "COMERCIALIZARE",
                "name": "Acid citric monohidrat, saci 25 kg",
                "quantity": Decimal("2000.00"),
                "unit_code": "KGM",
                "gross_weight": Decimal("2060.00"),
                "net_weight": Decimal("2000.00"),
                "tariff_code": "29181400",
                "value_ron": Decimal("18400.00"),
            },
        ],
        "documents": [
            {
                "doc_type": "CMR",
                "date": transport_date,
                "number": "2026-EX/000343",
            },
            {
                "doc_type": "FACTURA",
                "date": transport_date - dt.timedelta(days=2),
                "number": "HU-2026-4471",
            },
        ],
    }
    fields.update(overrides)
    return FlatTransport.model_validate(fields)


def card(**overrides: object) -> UitCard:
    fields: dict[str, object] = {
        "uit": UIT,
        "transport": transport(),
        "declarant_name": "SC EXEMPLU AGRO SRL",
        "declarant_code": "RO12345678",
        "filed_on": dt.date(2026, 9, 7),
        "upload_id": "12345678901",
        "anaf_state": "ok",
    }
    fields.update(overrides)
    return UitCard.model_validate(fields)


#: The four validity states, as (transport date, ANAF's data_exp_uit or None).
#: ``None`` is the common case in the wild: ANAF serves data_exp_uit only on the
#: ``info`` endpoint, scoped to the transport organizer, so a declarant who is
#: not the carrier never reads it back and the card falls to the statutory
#: window — amber, captioned as an estimate.
STATES: dict[str, tuple[dt.date, dt.date | None]] = {
    "anaf": (LIVE_TRANSPORT, LIVE_EXPIRY),
    "anaf-expired": (STALE_TRANSPORT, STALE_EXPIRY),
    "estimated": (LIVE_TRANSPORT, None),
    "estimated-expired": (STALE_TRANSPORT, None),
}

#: The three plate shapes: the top row collapses to a full-width VEHICUL with no
#: trailer, pairs with one, and spills onto a second row with two.
SHAPES: dict[str, tuple[str, ...]] = {
    "no-trailer": (),
    "one-trailer": ("CB5678CD",),
    "two-trailers": ("CB5678CD", "CB9012EF"),
}


def main() -> None:
    cardpdf = load_cardpdf()
    written: list[Path] = []

    def write(name: str, pdf: bytes) -> None:
        path = HERE / f"{name}.pdf"
        path.write_bytes(pdf)
        written.append(path)

    # The full matrix: every plate shape in every validity state.
    for shape, trailers in SHAPES.items():
        for state, (date, expiry) in STATES.items():
            sample = card(
                transport=transport(transport_date=date, trailers=trailers),
                uit_expiry=expiry,
            )
            write(f"uit-card-{shape}-{state}", cardpdf.render_card(sample, today=TODAY))

    # A domestic TTN: the other statutory count, 5 days rather than 15.
    write(
        "uit-card-ttn-estimated",
        cardpdf.render_card(
            card(
                transport=transport(
                    operation_type="TTN",
                    trailers=(),
                    partner={
                        "name": "SC BENEFICIAR SRL",
                        "country": "RO",
                        "code": "RO87654321",
                    },
                    start_location={
                        "address": {
                            "county": "CLUJ",
                            "locality": "Cluj-Napoca",
                            "street": "Str. Depozitelor",
                            "number": "4",
                        }
                    },
                )
            ),
            today=TODAY,
        ),
    )

    # Names long enough to exercise the fit-shrink in the party cells.
    write(
        "uit-card-long-names-estimated",
        cardpdf.render_card(
            card(
                declarant_name="SOCIETATEA COMERCIALĂ EXEMPLU AGROINDUSTRIAL "
                "PRODCOM SRL",
                transport=transport(
                    partner={
                        "name": "TRANSPORTES Y LOGÍSTICA INTERNACIONAL "
                        "DEL MEDITERRÁNEO SL",
                        "country": "ES",
                        "code": "ESB12345678",
                    },
                ),
            ),
            today=TODAY,
        ),
    )

    # Everything optional omitted: no declarant, no upload index, no filing date,
    # so the party cells fall back to em dashes and the footer loses a line.
    write(
        "uit-card-minimal-estimated",
        cardpdf.render_card(
            UitCard(uit=UIT, transport=transport(trailers=())), today=TODAY
        ),
    )

    # The A4 document, which prints both dates and labels a derived window.
    details = {
        "uit-details": card(uit_expiry=LIVE_EXPIRY),
        "uit-details-notes": card(uit_expiry=LIVE_EXPIRY, notes=NOTES),
        "uit-details-estimated": card(),
        "uit-details-long-goods": card(
            uit_expiry=LIVE_EXPIRY, transport=transport(goods=LONG_GOODS)
        ),
        "uit-details-estimated-expired": card(
            transport=transport(transport_date=STALE_TRANSPORT)
        ),
    }
    for name, sample in details.items():
        write(name, cardpdf.render_details(sample, today=TODAY))

    # The card's plain-text twin — the message that travels with the PDF, and
    # the only path that works on a phone whose viewer will not select text.
    summaries = HERE / "summaries.txt"
    summaries.write_text(
        "\n\n".join(
            f"# {state}\n"
            + card(
                transport=transport(transport_date=date), uit_expiry=expiry
            ).summary_text(TODAY)
            for state, (date, expiry) in STATES.items()
        )
        + "\n",
        encoding="utf-8",
    )

    previews = _render_previews(written)
    print(f"{len(written)} PDFs, {previews} PNG previews, {summaries.name}")


def _render_previews(pdfs: list[Path]) -> int:
    """Raster previews, when poppler's pdftoppm is around. Viewing only."""
    if (pdftoppm := shutil.which("pdftoppm")) is None:
        print("pdftoppm not found — skipping PNG previews (brew install poppler)")
        return 0
    for pdf in pdfs:
        subprocess.run(
            [
                pdftoppm,
                "-png",
                "-r",
                "110",
                "-singlefile",
                str(pdf),
                f"{pdf.with_suffix('')}-preview",
            ],
            check=True,
        )
    return len(pdfs)


if __name__ == "__main__":
    main()
