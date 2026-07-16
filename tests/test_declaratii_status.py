"""StareD112 status client: page parsing and wire behaviour (respx-mocked).

The HTML fixtures under ``tests/fixtures/stared112/`` are live captures from
2026-07-16 (the same ones vendored under
``docs/anaf-reference/_sources/stared112/``), so the parser is exercised on
ANAF's real markup: numeric entities, the ``<thead>`` with cell tags but no
row tag, nested layout tables, and a row whose recipisa link has lapsed.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import httpx
import pytest
import respx

from anafpy.declaratii.status import (
    DeclarationState,
    DeclarationStatusClient,
    _parse_status_page,
)
from anafpy.exceptions import AnafConfigError, AnafResponseError, AnafTransportError

FIXTURES = Path(__file__).parent / "fixtures" / "stared112"

STATUS_URL = "https://www.anaf.ro/StareD112/vizualizareStare.do"
RECEIPT_URL = "https://www.anaf.ro/StareD112/ObtineRecipisa"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="iso-8859-1")


# --- parsing ------------------------------------------------------------------------


def test_parse_found_page() -> None:
    result = _parse_status_page(_fixture("result-found.html"), queried_cui="99999909")
    assert result.found is True
    assert result.cui == "99999909"
    assert result.period_start == datetime.date(2026, 4, 15)
    assert result.period_end == datetime.date(2026, 7, 16)
    assert len(result.documents) == 4

    first = result.documents[0]
    assert first.index == "1100000001"
    assert first.form == "F4109"
    assert first.state is DeclarationState.VALID
    assert first.state_text == "Documentul este valid"
    assert first.registration == "INTERNT-1100000001-2026 din 16.07.2026"
    assert first.upload_date == datetime.date(2026, 7, 16)
    assert first.receipt_available is True


def test_parse_found_page_receipt_lapsed() -> None:
    # The oldest row (filed 2026-04-18, ~90 days before the capture) has no
    # recipisa link — the ~60-day window has lapsed — but keeps its status.
    result = _parse_status_page(_fixture("result-found.html"), queried_cui="99999909")
    oldest = result.document("1100000004")
    assert oldest is not None
    assert oldest.state is DeclarationState.VALID
    assert oldest.receipt_available is False


def test_parse_not_found_page() -> None:
    result = _parse_status_page(
        _fixture("result-notfound.html"), queried_cui="99999909"
    )
    assert result.found is False
    assert result.cui == "99999909"
    assert result.documents == []
    assert "3 months" in result.message


def test_parse_invalid_input_page_raises() -> None:
    with pytest.raises(AnafResponseError, match="index valid"):
        _parse_status_page(_fixture("result-invalid-input.html"), queried_cui="1")


def test_parse_unrecognised_page_raises() -> None:
    with pytest.raises(AnafResponseError, match="unrecognised"):
        _parse_status_page("<html><body>mentenanta</body></html>", queried_cui="1")


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("In prelucrare.", DeclarationState.PROCESSING),
        (
            "Fişierul depus nu este un document valid.",
            DeclarationState.NOT_VALID,
        ),
        ("Documentul are erori de validare.", DeclarationState.VALIDATION_ERRORS),
        ("Documentul este valid", DeclarationState.VALID),
        ("ceva nou", DeclarationState.UNKNOWN),
    ],
)
def test_state_classification(text: str, state: DeclarationState) -> None:
    page = _fixture("result-found.html").replace("Documentul este valid<br>", text, 1)
    result = _parse_status_page(page, queried_cui="99999909")
    assert result.documents[0].state is state
    assert result.documents[0].state_text == text.strip()


# --- check_status wire ----------------------------------------------------------------


@respx.mock
async def test_check_status_posts_form_and_parses() -> None:
    route = respx.post(STATUS_URL).mock(
        return_value=httpx.Response(
            200,
            text=_fixture("result-found.html"),
            headers={"Content-Type": "text/html;charset=ISO-8859-1"},
        )
    )
    async with DeclarationStatusClient() as client:
        result = await client.check_status(1100000001, "RO 99999909")
    assert result.found is True
    sent = route.calls.last.request
    assert sent.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert dict(httpx.QueryParams(sent.content.decode())) == {
        "ghiseu": "N",
        "id": "1100000001",
        "cui": "99999909",
    }


@respx.mock
async def test_check_status_counter_filing_sets_ghiseu() -> None:
    route = respx.post(STATUS_URL).mock(
        return_value=httpx.Response(200, text=_fixture("result-notfound.html"))
    )
    async with DeclarationStatusClient() as client:
        result = await client.check_status("555", "99999909", filed_at_counter=True)
    assert result.found is False
    assert b"ghiseu=Y" in route.calls.last.request.content


async def test_check_status_rejects_non_numeric_input() -> None:
    async with DeclarationStatusClient() as client:
        with pytest.raises(AnafConfigError, match="index"):
            await client.check_status("12 34", "99999909")
        with pytest.raises(AnafConfigError, match="cui"):
            await client.check_status("1100000001", "not-a-cui")


@respx.mock
async def test_check_status_network_error_raises_transport() -> None:
    respx.post(STATUS_URL).mock(side_effect=httpx.ConnectError("boom"))
    async with DeclarationStatusClient() as client:
        with pytest.raises(AnafTransportError):
            await client.check_status("1100000001", "99999909")


@respx.mock
async def test_check_status_http_error_raises() -> None:
    respx.post(STATUS_URL).mock(return_value=httpx.Response(503, text="mentenanta"))
    async with DeclarationStatusClient() as client:
        with pytest.raises(AnafResponseError):
            await client.check_status("1100000001", "99999909")


# --- download_receipt wire ------------------------------------------------------------


@respx.mock
async def test_download_receipt_returns_pdf() -> None:
    route = respx.get(RECEIPT_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"%PDF-1.4 fake",
            headers={"Content-Type": "application/pdf"},
        )
    )
    async with DeclarationStatusClient() as client:
        pdf = await client.download_receipt(1100000001)
    assert pdf == b"%PDF-1.4 fake"
    assert (
        httpx.QueryParams(route.calls.last.request.url.query)["numefisier"]
        == "1100000001.pdf"
    )


@respx.mock
async def test_download_receipt_empty_body_is_not_available() -> None:
    # Live-confirmed 2026-07-16: an unknown/expired index answers HTTP 200 with
    # an empty application/pdf body — a business "not available", never raised.
    respx.get(RECEIPT_URL).mock(
        return_value=httpx.Response(
            200, content=b"", headers={"Content-Type": "application/pdf"}
        )
    )
    async with DeclarationStatusClient() as client:
        assert await client.download_receipt("9999999999") is None


@respx.mock
async def test_download_receipt_non_pdf_raises() -> None:
    respx.get(RECEIPT_URL).mock(
        return_value=httpx.Response(200, text="<html>eroare</html>")
    )
    async with DeclarationStatusClient() as client:
        with pytest.raises(AnafResponseError, match="PDF"):
            await client.download_receipt("1100000001")
