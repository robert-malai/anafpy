"""Live smoke test against BNR's real exchange-rate feed (opt-in).

BNR needs no credentials, so this runs anywhere — but it hits the real
``curs.bnr.ro``, so it is not part of the default suite:

    ANAFPY_LIVE=1 uv run pytest -q -m live

Its job is the **drift tripwire** for the one wire contract this client has.
That contract has already broken once: the files used to live at
``www.bnr.ro/nbrfxrates.xml``, which today answers a 302 to the site homepage.
A move like that is silent in a workflow instruction and loud here.

Read-only, and assertions are structural — rates change daily, so nothing here
pins a number.
"""

from __future__ import annotations

import datetime
import os
from decimal import Decimal

import pytest

from anafpy.bnr import BnrClient
from anafpy.bnr.client import BNR_FX_HOST

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]

#: BNR has quoted the euro every banking day since the archive begins.
_ALWAYS_QUOTED = "EUR"


async def test_bnr_feed_still_serves_the_documented_shape() -> None:
    """The current file parses, carries EUR, and is dated a real banking day."""
    async with BnrClient() as client:
        rates = await client.get_rates()
    assert rates.source_url == f"{BNR_FX_HOST}/nbrfxrates.xml"
    assert rates.base_currency == "RON"
    assert (rate := rates.rate(_ALWAYS_QUOTED)) is not None
    # A sanity band, not a prediction: the leu has never been near either edge.
    assert Decimal(1) < rate.lei_per_unit < Decimal(100)
    # Published per banking day, so today or a few days back — never the future.
    today = datetime.datetime.now(datetime.UTC).date()
    assert rates.date <= today
    assert (today - rates.date).days <= 10


async def test_the_multiplier_currencies_still_carry_a_multiplier() -> None:
    """The factor-of-100 trap is a live wire fact, not an assumption."""
    async with BnrClient() as client:
        rates = await client.get_rates()
    scaled = [rate for rate in rates.rates.values() if rate.multiplier != 1]
    assert scaled, "no multiplier-carrying currency — re-check the feed's shape"
    assert all(rate.multiplier == 100 for rate in scaled)
    assert {"HUF", "JPY"} <= {rate.currency for rate in scaled}


async def test_the_archive_still_answers_a_past_date() -> None:
    """The year archive path, and the resolution to the latest day on or before."""
    async with BnrClient() as client:
        # A Saturday: BNR published nothing on it, so this must resolve back.
        rates = await client.get_rates("2026-01-10")
    assert rates.date < datetime.date(2026, 1, 10)
    assert rates.rate(_ALWAYS_QUOTED) is not None
