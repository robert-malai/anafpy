"""Behavioural tests for the BNR exchange-rate client (respx-mocked, no network).

Fixture bodies reproduce the live shapes of ``curs.bnr.ro`` recorded on
2026-08-30: a ``<Cube date>`` per banking day, rates quoted in lei per unit, and
a ``multiplier`` attribute on the small-denomination currencies.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import httpx
import httpx2
import pytest
import respx

from anafpy.bnr import BnrClient, FxRate, FxRateSet
from anafpy.exceptions import (
    AnafConfigError,
    AnafResponseError,
    AnafTransportError,
)

BASE = "https://curs.bnr.ro"

# Friday 2026-08-28 — the last banking day before the Sunday the fixtures treat
# as "today"; the case the fallback exists for.
_FRIDAY = "2026-08-28"
_THURSDAY = "2026-08-27"


#: The two namespaces BNR serves at once: archives through 2025 use `http`,
#: 2026 onwards `https`. Parsing must not care which.
_NS_CURRENT = "https://www.bnr.ro/xsd"
_NS_ARCHIVE = "http://www.bnr.ro/xsd"


def _document(*days: str, namespace: str = _NS_CURRENT) -> bytes:
    cubes = "".join(
        f'<Cube date="{day}">'
        '<Rate currency="EUR">5.2584</Rate>'
        '<Rate currency="USD">4.5123</Rate>'
        '<Rate currency="HUF" multiplier="100">1.4430</Rate>'
        "</Cube>"
        for day in days
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<DataSet xmlns="{namespace}">'
        "<Header><Publisher>National Bank of Romania</Publisher>"
        f"<PublishingDate>{days[-1]}</PublishingDate>"
        "<MessageType>DR</MessageType></Header>"
        "<Body><Subject>Reference rates</Subject>"
        f"<OrigCurrency>RON</OrigCurrency>{cubes}</Body>"
        "</DataSet>"
    ).encode()


@pytest.fixture
def frozen_today(monkeypatch: pytest.MonkeyPatch) -> datetime.date:
    """Pin "today in Romania" to a Sunday, so the banking-day fallback is live."""
    sunday = datetime.date(2026, 8, 30)
    monkeypatch.setattr("anafpy.bnr.client._today", lambda: sunday)
    return sunday


def _client() -> BnrClient:
    """Cache off, so each test's route assertions count real requests."""
    return BnrClient(cache_ttl=0.0)


# --- fetching and resolving ------------------------------------------------


@respx.mock
async def test_current_rates_come_from_the_daily_file(
    frozen_today: datetime.date,
) -> None:
    route = respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    async with _client() as client:
        rates = await client.get_rates()
    assert route.called
    assert rates.date == datetime.date(2026, 8, 28)
    assert rates.base_currency == "RON"
    assert rates.source_url == f"{BASE}/nbrfxrates.xml"
    assert rates.currencies == ["EUR", "HUF", "USD"]


@respx.mock
async def test_weekend_reports_the_last_published_day_not_the_requested_one(
    frozen_today: datetime.date,
) -> None:
    """The whole point of the design: Friday's rate is never labelled Sunday's."""
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    async with _client() as client:
        rates = await client.get_rates("2026-08-30")
    assert rates.date == datetime.date(2026, 8, 28)


@respx.mock
async def test_recent_past_date_uses_the_ten_day_file(
    frozen_today: datetime.date,
) -> None:
    """A date the one-day file cannot answer falls to the 14 KB file, not the
    230 KB archive."""
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    ten_days = respx.get(f"{BASE}/nbrfxrates10days.xml").mock(
        return_value=httpx.Response(200, content=_document(_THURSDAY, _FRIDAY))
    )
    year = respx.get(f"{BASE}/files/xml/years/nbrfxrates2026.xml").mock(
        return_value=httpx.Response(200, content=_document(_THURSDAY))
    )
    async with _client() as client:
        rates = await client.get_rates(_THURSDAY)
    assert rates.date == datetime.date(2026, 8, 27)
    assert ten_days.called
    assert not year.called


@respx.mock
async def test_older_date_falls_through_to_the_year_archive(
    frozen_today: datetime.date,
) -> None:
    year = respx.get(f"{BASE}/files/xml/years/nbrfxrates2026.xml").mock(
        return_value=httpx.Response(200, content=_document("2026-03-10", "2026-03-11"))
    )
    async with _client() as client:
        rates = await client.get_rates("2026-03-10")
    assert year.called
    assert rates.date == datetime.date(2026, 3, 10)
    # The later cube in the same document must not win a request for an earlier day.
    assert rates.rates["EUR"].quoted == Decimal("5.2584")


@respx.mock
async def test_early_january_falls_back_to_the_previous_year(
    frozen_today: datetime.date,
) -> None:
    """2026's archive starts 2026-01-05 — a 2nd-of-January request predates it.

    The fallback crosses BNR's namespace boundary, so the previous year is
    served with the `http` namespace it really carries.
    """
    respx.get(f"{BASE}/files/xml/years/nbrfxrates2026.xml").mock(
        return_value=httpx.Response(200, content=_document("2026-01-05"))
    )
    previous = respx.get(f"{BASE}/files/xml/years/nbrfxrates2025.xml").mock(
        return_value=httpx.Response(
            200, content=_document("2025-12-31", namespace=_NS_ARCHIVE)
        )
    )
    async with _client() as client:
        rates = await client.get_rates("2026-01-02")
    assert previous.called
    assert rates.date == datetime.date(2025, 12, 31)


@respx.mock
async def test_no_rate_on_or_before_the_date_raises(
    frozen_today: datetime.date,
) -> None:
    for year in (2026, 2025):
        respx.get(f"{BASE}/files/xml/years/nbrfxrates{year}.xml").mock(
            return_value=httpx.Response(200, content=_document("2026-06-01"))
        )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="no reference rate on or before"):
            await client.get_rates("2026-01-02")


async def test_date_before_the_archive_raises_config_error() -> None:
    async with _client() as client:
        with pytest.raises(AnafConfigError, match="from 2005 onwards"):
            await client.get_rates("2004-12-31")


async def test_unparseable_date_raises_config_error() -> None:
    async with _client() as client:
        with pytest.raises(AnafConfigError, match="expected YYYY-MM-DD"):
            await client.get_rates("30-08-2026")


@respx.mock
async def test_both_bnr_namespaces_parse(frozen_today: datetime.date) -> None:
    """Matching is by local name: a namespace-bound model (anything generated
    from BNR's XSD) would parse one of these and reject the other."""
    for namespace in (_NS_CURRENT, _NS_ARCHIVE):
        respx.get(f"{BASE}/nbrfxrates.xml").mock(
            return_value=httpx.Response(
                200, content=_document(_FRIDAY, namespace=namespace)
            )
        )
        async with _client() as client:
            rates = await client.get_rates()
        assert rates.rate("EUR") is not None, namespace


# --- caching ---------------------------------------------------------------


@respx.mock
async def test_documents_are_cached_within_the_ttl(
    frozen_today: datetime.date,
) -> None:
    """BNR asks callers to store what they take — a second read must not refetch."""
    route = respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    async with BnrClient(cache_ttl=600.0) as client:
        await client.get_rates()
        await client.get_rates()
        await client.convert(10, "EUR")
    assert route.call_count == 1


@respx.mock
async def test_zero_ttl_disables_the_cache(frozen_today: datetime.date) -> None:
    route = respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    async with _client() as client:
        await client.get_rates()
        await client.get_rates()
    assert route.call_count == 2


# --- conversion ------------------------------------------------------------


def _rates() -> FxRateSet:
    return FxRateSet(
        date=datetime.date(2026, 8, 28),
        rates={
            "EUR": FxRate(currency="EUR", quoted=Decimal("5.2584")),
            "HUF": FxRate(currency="HUF", quoted=Decimal("1.4430"), multiplier=100),
        },
        source_url=f"{BASE}/nbrfxrates.xml",
    )


def test_conversion_rounds_to_two_decimals() -> None:
    # 1234.56 EUR * 5.2584 = 6491.8103... -> 6491.81
    conversion = _rates().convert("1234.56", "EUR")
    assert conversion.amount_ron == Decimal("6491.81")
    assert conversion.currency == "EUR"
    assert conversion.rate.quoted == Decimal("5.2584")


def test_an_exact_half_rounds_away_from_zero() -> None:
    """6.25 EUR * 5.2584 is exactly 32.865 — Romanian fiscal rounding takes it
    up. Python's default (banker's) would answer 32.86."""
    assert _rates().convert("6.25", "EUR").amount_ron == Decimal("32.87")


def test_multiplier_is_applied_not_dropped() -> None:
    """The factor-of-100 trap: 100 HUF = 1.4430 RON, so 250000 HUF is ~3607 RON."""
    conversion = _rates().convert(250_000, "HUF")
    assert conversion.amount_ron == Decimal("3607.50")
    assert conversion.rate.multiplier == 100
    assert conversion.rate.lei_per_unit == Decimal("0.014430")


def test_multiplier_precision_survives_the_intermediate() -> None:
    """Rounding once, at the end — a per-unit rate rounded first would lose this."""
    assert _rates().convert("1", "HUF").amount_ron == Decimal("0.01")


def test_base_currency_converts_one_for_one() -> None:
    conversion = _rates().convert("99.99", "ron")
    assert conversion.amount_ron == Decimal("99.99")
    assert conversion.rate.quoted == Decimal(1)


def test_currency_code_is_case_and_space_insensitive() -> None:
    assert _rates().convert(1, " eur ").amount_ron == Decimal("5.26")


def test_unquoted_currency_errors_with_the_quoted_list() -> None:
    with pytest.raises(AnafConfigError) as excinfo:
        _rates().convert(1, "XYZ")
    message = str(excinfo.value)
    assert "XYZ" in message
    assert "EUR" in message and "HUF" in message and "RON" in message


@respx.mock
async def test_client_convert_fetches_then_delegates(
    frozen_today: datetime.date,
) -> None:
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=_document(_FRIDAY))
    )
    async with _client() as client:
        conversion = await client.convert("100", "EUR")
    assert conversion.amount_ron == Decimal("525.84")


# --- malformed responses ---------------------------------------------------


@respx.mock
async def test_non_xml_body_raises_response_error(
    frozen_today: datetime.date,
) -> None:
    """The failure this whole module exists to make loud: the URL moved once
    already, and www.bnr.ro answers a redirect to an HTML homepage."""
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=b"<!doctype html><html>BNR</html>")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised BNR response"):
            await client.get_rates()


@respx.mock
async def test_non_numeric_rate_raises_rather_than_defaulting(
    frozen_today: datetime.date,
) -> None:
    body = _document(_FRIDAY).replace(b">5.2584<", b">n/a<")
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=body)
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="is not a number"):
            await client.get_rates()


@respx.mock
async def test_cube_without_a_date_raises(frozen_today: datetime.date) -> None:
    """`date` is required by BNR's XSD, so the generated model rejects this —
    the check is the schema's, not a hand-written one."""
    body = _document(_FRIDAY).replace(f'<Cube date="{_FRIDAY}">'.encode(), b"<Cube>")
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=body)
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised BNR response"):
            await client.get_rates()


@respx.mock
async def test_an_added_element_does_not_break_parsing(
    frozen_today: datetime.date,
) -> None:
    """Forward compatibility: something BNR adds must not take the client down,
    because the rates around it are still correct."""
    body = _document(_FRIDAY).replace(
        b"<OrigCurrency>RON</OrigCurrency>",
        b'<OrigCurrency>RON</OrigCurrency><SomethingNew flag="1">x</SomethingNew>',
    )
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(200, content=body)
    )
    async with _client() as client:
        rates = await client.get_rates()
    assert rates.rate("EUR") is not None


@respx.mock
async def test_an_unknown_namespace_raises_instead_of_parsing_empty(
    frozen_today: datetime.date,
) -> None:
    """The failure mode a lenient parser could hide: a namespace the generated
    models do not bind must be loud, never an empty rate set. The root element
    itself fails to match, so this raises before `_rate_sets`' empty-parse
    backstop — which stays as the guard for a partial shape change."""
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        return_value=httpx.Response(
            200, content=_document(_FRIDAY, namespace="https://example.invalid/xsd")
        )
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised BNR response"):
            await client.get_rates()


@respx.mock
async def test_http_error_raises_response_error(
    frozen_today: datetime.date,
) -> None:
    respx.get(f"{BASE}/nbrfxrates.xml").mock(return_value=httpx.Response(503))
    async with _client() as client:
        with pytest.raises(AnafResponseError):
            await client.get_rates()


@respx.mock
async def test_network_error_names_bnr_not_anaf(
    frozen_today: datetime.date,
) -> None:
    """A BNR outage must not report itself as an ANAF one."""
    respx.get(f"{BASE}/nbrfxrates.xml").mock(
        side_effect=httpx2.ConnectError("no route")
    )
    async with _client() as client:
        with pytest.raises(AnafTransportError, match="talking to BNR"):
            await client.get_rates()


# --- construction ----------------------------------------------------------


async def test_injected_client_without_base_url_is_rejected() -> None:
    with pytest.raises(AnafConfigError, match="base_url"):
        BnrClient(http=httpx2.AsyncClient())
