"""Live smoke tests against ANAF's real public endpoints (opt-in).

The public services need no credentials, so these can run anywhere — but they hit
production ANAF, depend on its availability, and are paced at ANAF's 1 req/s rule,
so they are **not** part of the default suite. Run them explicitly:

    ANAFPY_LIVE=1 uv run pytest -q -m live

Their job is to re-confirm the wire shapes recorded in
docs/anaf-reference/public/api.md (compiled from instruction files + one round of
live probing); behavioural coverage lives in the respx suite (test_public_client.py).
Assertions are structural — registry *data* drifts over time, so nothing here pins a
company's current status beyond near-immutable facts.
"""

from __future__ import annotations

import os

import pytest

from anafpy.public import PublicClient

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]

# A large, stable, VAT-registered company (OMV Petrom) — the least likely CUI in
# Romania to churn registries between runs.
_STABLE_CUI = 1590082
_BILANT_YEAR = 2023


async def test_public_services_live_smoke() -> None:
    """One paced pass over every sync endpoint, sharing a client so the 1 req/s
    gate spans all calls."""
    async with PublicClient(min_request_interval=1.1) as client:
        taxpayers = await client.lookup_taxpayers([_STABLE_CUI])
        assert len(taxpayers.found) == 1
        record = taxpayers.found[0]
        assert record.cui == _STABLE_CUI
        assert record.name
        assert record.vat_registered is True
        assert record.fiscal_address is not None

        register = await client.lookup_efactura_register([_STABLE_CUI])
        # Registered or not, the CUI must land in exactly one of the two lists.
        in_found = any(e.cui == _STABLE_CUI for e in register.found)
        assert in_found or _STABLE_CUI in register.not_found

        farmers = await client.lookup_farmers([_STABLE_CUI])
        # Live note in the reference: unknown CUIs still arrive under `found`.
        assert farmers.found or farmers.not_found
        if farmers.found:
            assert farmers.found[0].registered is False

        cults = await client.lookup_cult_entities([_STABLE_CUI])
        assert cults.found or cults.not_found
        if cults.found:
            assert cults.found[0].registered is False

        statement = await client.get_financial_statement(_STABLE_CUI, _BILANT_YEAR)
        assert statement.cui == _STABLE_CUI
        assert statement.year == _BILANT_YEAR
        assert statement.indicators, "bilant returned no indicators"
