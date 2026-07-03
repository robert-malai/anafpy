"""Live smoke tests against ANAF's authenticated TEST endpoints (opt-in).

These need real credentials and a token store bootstrapped by ``anafpy auth login``,
so they are **not** part of the default suite. Provide ``ANAFPY_CLIENT_ID`` /
``ANAFPY_CLIENT_SECRET`` / ``ANAFPY_CIF`` (a repo-root ``.env`` is loaded by
conftest), then run explicitly:

    ANAFPY_LIVE=1 uv run pytest -q -m live tests/test_oauth_live.py

Their job is to re-confirm the swagger-derived wire shapes recorded in
docs/anaf-reference/{efactura,etransport}/api.md against the TEST environment —
read-only calls exclusively; nothing here uploads or files anything. Behavioural
coverage lives in the respx suites.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from anafpy._transport.base import Environment
from anafpy.auth import FileTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient
from anafpy.etransport import ETransportClient

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]

_HELLO_URL = "https://api.anaf.ro/TestOauth/jaxrs/hello"


def _store_path() -> Path:
    return Path(
        os.environ.get("ANAFPY_TOKEN_STORE", "~/.anafpy/tokens.json")
    ).expanduser()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set (see .env)")
    return value


@pytest.fixture
async def provider() -> AsyncIterator[TokenProvider]:
    client_id = _require("ANAFPY_CLIENT_ID")
    client_secret = _require("ANAFPY_CLIENT_SECRET")
    store = FileTokenStore(_store_path())
    if store.load() is None:
        pytest.skip("no token store — run `anafpy auth login` first")
    prov = TokenProvider(client_id=client_id, client_secret=client_secret, store=store)
    yield prov
    await prov.aclose()


@pytest.fixture
def cif() -> str:
    return _require("ANAFPY_CIF")


async def test_token_accepted_by_api_host(provider: TokenProvider) -> None:
    """The stored/refreshed token authenticates against api.anaf.ro (hello echo)."""
    token = await provider.access_token()
    async with httpx.AsyncClient(timeout=30.0) as http:
        response = await http.get(
            _HELLO_URL,
            params={"name": "anafpy-live"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert "anafpy-live" in response.text


async def test_efactura_test_list_messages_shape(
    provider: TokenProvider, cif: str
) -> None:
    """The paginated list parses cleanly: items with ids, or a benign empty window.

    Live-confirmed 2026-07-02: an empty window arrives as HTTP 200 with
    ``{"eroare": "Nu exista mesaje in intervalul selectat", ...}`` and must yield
    an empty iterator, not raise.
    """
    async with EFacturaClient(provider, environment=Environment.TEST) as client:
        messages = [m async for m in client.list_messages(cif=cif, days=60)]
    for message in messages:  # shape assertions only when the inbox has content
        assert message.id
        assert message.tip


async def test_etransport_test_list_notifications_shape(
    provider: TokenProvider, cif: str
) -> None:
    """The e-Transport ``lista`` endpoint parses cleanly (items or benign empty)."""
    async with ETransportClient(provider, environment=Environment.TEST) as client:
        notifications = [n async for n in client.list_notifications(days=60, cif=cif)]
    for notification in notifications:
        assert notification.uit or notification.notification_type
