"""UIT card and detail document rendering.

Assertions are on the PDF's *text layer* and page geometry, never on pixels: the
point of choosing PDF over an image was that every value stays real text, so
that is what the tests hold the renderer to. A golden-image comparison would
also break on any font or fpdf2 update without telling us anything true.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from anafpy.etransport import (
    FlatTransport,
    FlatTransportDocument,
    FlatTransportVehicle,
    UitCard,
    UploadResult,
    load_cardpdf,
)
from anafpy.etransport.labels import COUNTY_LABELS, country_text, label_for
from anafpy.etransport.schema.schema_etr_v2_20230126 import CodJudetType
from anafpy.exceptions import AnafConfigError

# Fictional, and check-digit valid: the last two characters must be the last two
# digits of the ASCII sum of the first fourteen (BR-019), which `_Uit` enforces.
UIT = "9T5R204811730587"


def _transport(**overrides: object) -> FlatTransport:
    fields: dict[str, object] = {
        "operation_type": "AIC",
        "partner": {
            "name": "EXAMPLE FEED KFT",
            "country": "HU",
            "code": "HU11223344",
        },
        "vehicle": {
            "plate": "CB1234AB",
            "trailer1": "CB5678CD",
            "carrier_name": "EXPRES TRANS EOOD",
            "carrier_country": "BG",
            "carrier_code": "BG99887766",
            "transport_date": dt.date(2026, 8, 1),
        },
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
            }
        ],
        "documents": [
            {
                "doc_type": "CMR",
                "date": dt.date(2026, 8, 1),
                "number": "2026-EX/000343",
            }
        ],
    }
    fields.update(overrides)
    return FlatTransport.model_validate(fields)


def _card(**overrides: object) -> UitCard:
    fields: dict[str, object] = {
        "uit": UIT,
        "transport": _transport(),
        "uit_expiry": dt.date(2026, 8, 15),
        "declarant_name": "SC EXEMPLU AGRO SRL",
        "declarant_code": "RO12345678",
        "filed_on": dt.date(2026, 7, 31),
        "upload_id": "12345678901",
    }
    fields.update(overrides)
    return UitCard.model_validate(fields)


def _pages(pdf: bytes) -> list[str]:
    """The text of each page."""
    import io

    from pypdf import PdfReader

    return [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]


def _page_size_mm(pdf: bytes) -> tuple[float, float]:
    import io

    from pypdf import PdfReader

    box = PdfReader(io.BytesIO(pdf)).pages[0].mediabox
    return (float(box.width) / 72 * 25.4, float(box.height) / 72 * 25.4)


def test_card_is_phone_shaped() -> None:
    # 90x195mm is 19.5:9 — a viewer fitting the page to the screen fills it.
    width, height = _page_size_mm(load_cardpdf().render_card(_card()))
    assert (round(width), round(height)) == (90, 195)
    assert height / width == pytest.approx(19.5 / 9, abs=0.01)


def test_card_values_are_selectable_text() -> None:
    text = _pages(load_cardpdf().render_card(_card()))[0]
    # Everything a driver may need to read out or copy is real text.
    for expected in (
        UIT,
        "CB1234AB",
        "CB5678CD",
        "01.08.2026",
        "15.08.2026",
        "SC EXEMPLU AGRO SRL",
        "RO12345678",
        "EXAMPLE FEED KFT",
        "EXPRES TRANS EOOD",
    ):
        assert expected in text


def test_card_prints_the_uit_ungrouped() -> None:
    # Both real-world references print it as one run; grouping in fours would be
    # our invention, and a driver reading it aloud could introduce the spaces.
    text = _pages(load_cardpdf().render_card(_card()))[0]
    assert UIT in text
    assert " ".join(UIT[i : i + 4] for i in range(0, 16, 4)) not in text


def test_card_labels_the_partner_by_direction() -> None:
    render = load_cardpdf().render_card
    # Inbound buys from a supplier, outbound sells to a customer, TTN neither.
    assert "FURNIZOR" in _pages(render(_card()))[0]
    outbound = _card(transport=_transport(operation_type="LIC"))
    assert "CLIENT" in _pages(render(outbound))[0]
    domestic = _card(
        transport=_transport(
            operation_type="TTN",
            start_location={
                "address": {
                    "county": "CLUJ",
                    "locality": "Cluj-Napoca",
                    "street": "Str. Fabricii",
                }
            },
        )
    )
    assert "PARTENER" in _pages(render(domestic))[0]


@pytest.mark.parametrize(
    ("trailers", "present", "absent"),
    [
        ((None, None), ("VEHICUL",), ("REMORC",)),
        (("CB5678CD", None), ("VEHICUL", "REMORCĂ"), ("REMORCĂ 1",)),
        (("CB5678CD", "CB9012EF"), ("REMORCĂ 1", "REMORCĂ 2"), ()),
    ],
)
def test_card_adapts_to_the_trailer_count(
    trailers: tuple[str | None, str | None],
    present: tuple[str, ...],
    absent: tuple[str, ...],
) -> None:
    """Each plate is a peer with its own cell; the caption is numbered only when
    there are two, since numbering a lone trailer implies a second."""
    vehicle = FlatTransportVehicle.model_validate(
        {
            "plate": "CB1234AB",
            "trailer1": trailers[0],
            "trailer2": trailers[1],
            "carrier_name": "EXPRES TRANS EOOD",
            "carrier_country": "BG",
            "carrier_code": "BG99887766",
            "transport_date": dt.date(2026, 8, 1),
        }
    )
    text = _pages(
        load_cardpdf().render_card(_card(transport=_transport(vehicle=vehicle)))
    )[0]
    for expected in present:
        assert expected in text
    for missing in absent:
        assert missing not in text


def test_expired_card_says_so() -> None:
    render = load_cardpdf().render_card
    card = _card()
    live = _pages(render(card, today=dt.date(2026, 8, 1)))[0]
    assert "EXPIRAT" not in live
    assert "UIT VALABIL PÂNĂ LA" in live

    lapsed = _pages(render(card, today=dt.date(2026, 8, 20)))[0]
    assert "EXPIRAT — UIT-ul nu mai este valabil" in lapsed
    assert "A EXPIRAT LA" in lapsed


def test_unknown_expiry_is_never_invented() -> None:
    """ANAF owns that clock: with no data_exp_uit reported the card shows the
    transport date alone rather than a computed window."""
    card = _card(uit_expiry=None)
    assert card.is_expired(dt.date(2030, 1, 1)) is False
    text = _pages(load_cardpdf().render_card(card))[0]
    assert "DATA TRANSPORT" in text
    assert "VALABIL" not in text


def test_details_carries_the_whole_filing() -> None:
    card = _card(notes=["Greutatea brută este cea comunicată de expeditor."])
    text = _pages(load_cardpdf().render_details(card))[0]
    for expected in (
        "DECLARAȚIE RO e-TRANSPORT",
        UIT,
        "Achiziţie intracomunitară",  # ANAF's own spelling, quoted verbatim
        "Ungaria (HU)",
        "Punct de trecere a frontierei GIURGIU",
        "jud. Timiș",
        "CMR",
        "2026-EX/000343",
        "Bicarbonat de sodiu",
        "22.350,00",  # Romanian grouping: '.' thousands, ',' decimals
        "49.810,95",
        "OBSERVAȚII",
        "Greutatea brută",
    ):
        assert expected in text


def test_details_omits_the_notes_section_when_there_are_none() -> None:
    text = _pages(load_cardpdf().render_details(_card()))[0]
    assert "OBSERVAȚII" not in text


def test_details_labels_each_document_by_its_type() -> None:
    """A filing need not carry a CMR — ANAF's list is CMR / Factură / Aviz de
    însoțire a mărfii / Altele, and the section prints whichever is there."""
    transport = _transport(
        documents=[
            FlatTransportDocument.model_validate(
                {
                    "doc_type": "FACTURA",
                    "date": dt.date(2026, 7, 31),
                    "number": "INV-114",
                }
            ),
            FlatTransportDocument.model_validate(
                {
                    "doc_type": "ALTELE",
                    "date": dt.date(2026, 8, 1),
                    "note": "Certificat fitosanitar",
                }
            ),
        ]
    )
    text = _pages(load_cardpdf().render_details(_card(transport=transport)))[0]
    assert "Factura" in text
    assert "INV-114" in text
    assert "Altele" in text
    assert "Certificat fitosanitar" in text
    assert "CMR" not in text


def test_document_without_a_number_still_reads() -> None:
    # ANAF requires dataDocument but not numarDocument.
    transport = _transport(
        documents=[
            FlatTransportDocument.model_validate(
                {"doc_type": "CMR", "date": dt.date(2026, 8, 1)}
            )
        ]
    )
    text = _pages(load_cardpdf().render_details(_card(transport=transport)))[0]
    assert "din 01.08.2026" in text


def test_summary_text_leads_with_the_bare_uit() -> None:
    """The paste-into-a-chat fallback: copying the block, or just its first
    line, must both yield a usable code."""
    summary = _card().summary_text()
    assert summary.splitlines()[0] == UIT
    assert "CB1234AB + CB5678CD" in summary
    assert "15.08.2026" in summary


def test_from_upload_refuses_a_rejected_upload() -> None:
    transport = _transport()
    accepted = UitCard.from_upload(
        transport, UploadResult(upload_id="123", uit=UIT), filed_on=dt.date(2026, 7, 31)
    )
    assert accepted.uit == UIT
    assert accepted.upload_id == "123"

    with pytest.raises(AnafConfigError, match="carries no UIT"):
        UitCard.from_upload(transport, UploadResult(upload_id="123", uit=None))


def test_uit_check_digits_are_enforced() -> None:
    # A mistyped code must fail here rather than on a document a driver carries.
    with pytest.raises(ValueError, match="check digits"):
        _card(uit="9T5R204811730526")


def test_labels_cover_every_county() -> None:
    """A gap would silently print ANAF's ASCII member name (``BISTRITA_NASAUD``)
    on a document, so the map is held to the enum."""
    assert set(COUNTY_LABELS) == {member.name for member in CodJudetType}
    assert label_for(CodJudetType.BISTRITA_NASAUD) == "Bistrița-Năsăud"


def test_country_text_pairs_the_name_with_its_iso_code() -> None:
    from anafpy.etransport.schema.schema_etr_v2_20230126 import CodTaraType

    assert country_text(CodTaraType.UNGARIA) == "Ungaria (HU)"


# --- CLI ----------------------------------------------------------------------------


def _declaration_xml() -> bytes:
    from anafpy.etransport import render_etransport

    return render_etransport(_transport(), declarant_code="12345678")


def test_cli_renders_a_card_and_prints_the_message_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.cli.main import main

    xml = tmp_path / "declaration.xml"
    xml.write_bytes(_declaration_xml())
    out = tmp_path / "card.pdf"
    code = main(
        [
            "etransport",
            "card",
            str(xml),
            UIT,
            "-o",
            str(out),
            "--expiry",
            "2026-08-15",
            "--declarant",
            "SC EXEMPLU AGRO SRL",
            "--declarant-code",
            "RO12345678",
        ]
    )
    assert code == 0
    assert out.exists()
    printed = capsys.readouterr().out
    assert "✓ Rendered card" in printed
    # The paste-into-a-chat fallback is offered, not left to the user to retype.
    assert UIT in printed
    assert UIT in _pages(out.read_bytes())[0]


def test_cli_rejects_a_non_declaration_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A deletion notification carries a UIT but none of what a card prints."""
    from anafpy.cli.main import main
    from anafpy.etransport import FlatDeletion, render_etransport

    xml = tmp_path / "deletion.xml"
    xml.write_bytes(render_etransport(FlatDeletion(uit=UIT), declarant_code="12345678"))
    code = main(["etransport", "card", str(xml), UIT, "-o", str(tmp_path / "out.pdf")])
    assert code == 1
    assert "not a declaration" in capsys.readouterr().err


def test_cli_details_command_renders_the_a4_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.cli.main import main

    xml = tmp_path / "declaration.xml"
    xml.write_bytes(_declaration_xml())
    out = tmp_path / "details.pdf"
    assert (
        main(
            [
                "etransport",
                "details",
                str(xml),
                UIT,
                "-o",
                str(out),
                "--note",
                "O observație a expeditorului.",
            ]
        )
        == 0
    )
    width, height = _page_size_mm(out.read_bytes())
    assert (round(width), round(height)) == (210, 297)
    assert "O observație a expeditorului." in _pages(out.read_bytes())[0]
    assert "✓ Rendered detail document" in capsys.readouterr().out
