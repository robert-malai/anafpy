"""Model-level tests for the SPV value types and the report nomenclature."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anafpy._transport.base import ROMANIA_TZ
from anafpy.spv import (
    INCOME_CERTIFICATE_REASONS,
    MessageList,
    ReportRequest,
    ReportType,
    english_error_hint,
    required_parameters,
)

# The vendored README's listaMesaje example (docs/anaf-reference/spv/api.md §2).
README_LISTING = {
    "titlu": "Lista Mesaje disponibile din ultimele 50 zile",
    "mesaje": [
        {
            "id": "100000000",
            "detalii": (
                "recipisa pentru CIF 8000000000, tip D112, numar_inregistrare "
                "INTERNT-130000000-2017/20-12-2017, perioada raportare 11.2017"
            ),
            "cif": "8000000000",
            "data_creare": "20.12.2017 12:00:00",
            "id_solicitare": None,
            "tip": "RECIPISA",
        }
    ],
    "cnp": "1111111111118",
    "cui": "8000000000,8000000001,8000000002",
    "serial": "xxxxxxxxxxxxxxxxxxx",
}


# --- message shapes -------------------------------------------------------------------


def test_message_list_parses_the_readme_example() -> None:
    listing = MessageList.model_validate(README_LISTING)
    assert listing.cnp == "1111111111118"
    assert listing.authorized_cuis == ["8000000000", "8000000001", "8000000002"]
    assert listing.certificate_serial == "xxxxxxxxxxxxxxxxxxx"
    (message,) = listing.messages
    assert message.id == "100000000"
    assert message.request_id is None
    assert message.created_at.year == 2017
    assert message.created_at.tzinfo is ROMANIA_TZ


def test_message_type_stays_verbatim_and_kind_trims() -> None:
    # Live-observed 2026-07-12: ANAF emits "DECLARATIE " with a trailing space.
    listing = MessageList.model_validate(
        {
            "mesaje": [
                {
                    "id": 886573489,  # bare number: coerced to str
                    "detalii": "depunere declaratie unica",
                    "cif": 1790127203156,
                    "data_creare": "25.05.2026 02:59:19",
                    "id_solicitare": 182990101,
                    "tip": "DECLARATIE ",
                }
            ]
        }
    )
    (message,) = listing.messages
    assert message.type_ == "DECLARATIE "
    assert message.kind == "DECLARATIE"
    assert message.id == "886573489"
    assert message.request_id == "182990101"


def test_authorized_cuis_accept_a_bare_numeric_cui() -> None:
    # The relaxed serializer that emits ids bare can do the same to a lone
    # `cui` — coerce instead of failing list[str] validation.
    listing = MessageList.model_validate({"titlu": "t", "cui": 8000000000})
    assert listing.authorized_cuis == ["8000000000"]


def test_message_date_only_form_is_accepted() -> None:
    # Pre-06.11.2018 shape (date without time) — parse rather than crash.
    listing = MessageList.model_validate(
        {
            "mesaje": [
                {
                    "id": "1",
                    "detalii": "x",
                    "cif": "123",
                    "data_creare": "20.12.2017",
                    "tip": "RECIPISA",
                }
            ]
        }
    )
    assert listing.messages[0].created_at.day == 20


# --- report nomenclature --------------------------------------------------------------


def test_required_parameters_per_group() -> None:
    assert required_parameters(ReportType.VECTOR_FISCAL) == ("cui",)
    assert required_parameters(ReportType.D101) == ("cui", "year")
    assert required_parameters(ReportType.D300) == ("cui", "year", "month")
    assert required_parameters(ReportType.DUPLICAT_RECIPISA) == (
        "cui",
        "registration_number",
    )
    assert required_parameters(ReportType.ADEVERINTE_VENIT) == ("cui", "year", "reason")
    assert required_parameters(ReportType.NECONCORDANTE_D394) == (
        "cui",
        "year",
        "start_month",
        "end_month",
    )


def test_every_report_type_has_a_description() -> None:
    # A member declared without a description fails at import (the enum's
    # __new__ requires one); this guards the content — real selection
    # guidance, not placeholders — and that the str value stays the wire tip.
    for type_ in ReportType:
        assert len(type_.description) > 10, type_
    assert ReportType.D300.description == "VAT return (includes D305)"
    # Value lookup still works despite the two-argument __new__ (mypy misreads
    # the enum call, hence the ignore).
    assert ReportType("D300") is ReportType.D300  # type: ignore[call-arg]
    assert str(ReportType.D300) == "D300"


def test_cui_only_report_accepts_cui_and_rejects_extras() -> None:
    request = ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="8000000000")
    assert request.wire_params() == {"tip": "VECTOR FISCAL", "cui": "8000000000"}
    with pytest.raises(ValidationError, match="does not take"):
        ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="8000000000", year=2025)


def test_missing_required_parameters_fail_before_the_wire() -> None:
    with pytest.raises(ValidationError, match="requires cui, year"):
        ReportRequest(type_=ReportType.D101, cui="8000000000")
    with pytest.raises(ValidationError, match="month"):
        ReportRequest(type_=ReportType.D300, cui="8000000000", year=2025)


def test_monthly_report_wire_params_use_anaf_names() -> None:
    request = ReportRequest(type_=ReportType.D394, cui="8000000000", year=2025, month=6)
    assert request.wire_params() == {
        "tip": "D394",
        "cui": "8000000000",
        "an": "2025",
        "luna": "6",
    }


def test_d208_is_half_yearly() -> None:
    with pytest.raises(ValidationError, match=r"6 .*or 12"):
        ReportRequest(type_=ReportType.D208, cui="8000000000", year=2025, month=5)
    ReportRequest(type_=ReportType.D208, cui="8000000000", year=2025, month=12)


def test_income_certificate_reason_is_matched_exactly() -> None:
    ReportRequest(
        type_=ReportType.ADEVERINTE_VENIT,
        cui="1111111111118",
        year=2025,
        reason="Altele",
    )
    # The error enumerates the accepted values so a caller (or agent) can map
    # the stated purpose onto one of them without a second lookup.
    with pytest.raises(ValidationError, match=r"motiv list.*accepted values: Sanatate"):
        ReportRequest(
            type_=ReportType.ADEVERINTE_VENIT,
            cui="1111111111118",
            year=2025,
            reason="altele",
        )
    assert "Altele" in INCOME_CERTIFICATE_REASONS


def test_neconcordante_d394_period_params() -> None:
    request = ReportRequest(
        type_=ReportType.NECONCORDANTE_D394,
        cui="8000000000",
        year=2025,
        start_month=1,
        end_month=8,
    )
    params = request.wire_params()
    assert params["lunai"] == "1"
    assert params["lunas"] == "8"
    with pytest.raises(ValidationError, match="start_month cannot be after"):
        ReportRequest(
            type_=ReportType.NECONCORDANTE_D394,
            cui="8000000000",
            year=2025,
            start_month=9,
            end_month=8,
        )


def test_fisa_rol_branch_cui_is_optional() -> None:
    ReportRequest(type_=ReportType.FISA_ROL, cui="8000000000")
    request = ReportRequest(
        type_=ReportType.FISA_ROL, cui="8000000000", branch_cui="8000000001"
    )
    assert request.wire_params()["cui_pui"] == "8000000001"
    with pytest.raises(ValidationError, match="does not take"):
        ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="8000000000", branch_cui="12")


def test_duplicat_recipisa_needs_registration_number() -> None:
    request = ReportRequest(
        type_=ReportType.DUPLICAT_RECIPISA,
        cui="8000000000",
        registration_number="INTERNT-140000000-2018",
    )
    assert request.wire_params()["numar_inregistrare"] == "INTERNT-140000000-2018"
    with pytest.raises(ValidationError, match="registration_number"):
        ReportRequest(type_=ReportType.DUPLICAT_RECIPISA, cui="8000000000")


# --- error hints ----------------------------------------------------------------------


def test_english_error_hints_cover_the_documented_categories() -> None:
    assert english_error_hint(
        "Nu veti drept sa solictati informatii despre CIF=8000000000"
    ) == (
        "the certificate has no SPV rights for this CUI/CNP or message — the "
        "authorized list is the `cui` field of listaMesaje"
    )
    assert english_error_hint("CUI-ul introdus= 8000000001 nu este corect. ")
    assert english_error_hint(
        "Pentru tip raport= D101 parametri cui si an sunt obligatorii"
    )
    assert english_error_hint("Tip raport= CAF inca nu poate fi solicitat prin WS")
    assert english_error_hint("Eroare transmitere cerere. Cod 057")
    assert english_error_hint("Nu exista mesaje in ultimele 5 zile") is None


def test_english_error_hints_match_diacritic_spellings() -> None:
    # The recorded wire errors are ASCII, but ANAF writes Romanian both ways —
    # matching folds accents, as the hints table promises.
    assert english_error_hint(
        "Tip raport= CAF încă nu poate fi solicitat prin WS"
    ) == english_error_hint("Tip raport= CAF inca nu poate fi solicitat prin WS")
