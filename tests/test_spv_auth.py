"""Unit tests for the SPV auth layer (provider + httpx auth flow)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from anafpy.exceptions import AnafAuthError, AnafConfigError, AnafResponseError
from anafpy.spv import (
    MemorySessionStore,
    SpvAuth,
    SpvSession,
    SpvSessionProvider,
)

BASE = "https://webserviced.anaf.ro/SPVWS2/rest"
HOST = "https://webserviced.anaf.ro"


class CountingStore(MemorySessionStore):
    """A MemorySessionStore that counts writes (save-if-changed assertions)."""

    def __init__(self, session: SpvSession | None = None) -> None:
        super().__init__(session)
        self.saves = 0

    def save(self, session: SpvSession) -> None:
        self.saves += 1
        super().save(session)


def _session(cookies: dict[str, str] | None = None) -> SpvSession:
    return SpvSession(
        cookies=cookies or {"MRHSession": "authenticated"},
        established_at=datetime(2026, 7, 1, tzinfo=UTC),
    )


# --- SpvSessionProvider ---------------------------------------------------------------


async def test_cookies_raise_without_a_stored_session() -> None:
    provider = SpvSessionProvider(store=MemorySessionStore())
    with pytest.raises(AnafAuthError, match="login"):
        await provider.cookies()


async def test_cookies_read_the_store_fresh_each_call() -> None:
    store = MemorySessionStore(_session())
    provider = SpvSessionProvider(store=store)
    assert await provider.cookies() == {"MRHSession": "authenticated"}
    store.save(_session({"MRHSession": "relogged"}))
    assert await provider.cookies() == {"MRHSession": "relogged"}


async def test_rotated_is_save_if_changed() -> None:
    store = CountingStore(_session())
    provider = SpvSessionProvider(store=store)
    await provider.rotated({"MRHSession": "authenticated"})  # unchanged
    assert store.saves == 0
    await provider.rotated({"MRHSession": "rotated"})
    assert store.saves == 1


async def test_rotated_preserves_the_established_timestamp() -> None:
    store = MemorySessionStore(_session())
    provider = SpvSessionProvider(store=store)
    await provider.rotated({"MRHSession": "rotated"})
    saved = store.load()
    assert saved is not None
    assert saved.established_at == datetime(2026, 7, 1, tzinfo=UTC)


async def test_login_without_a_bootstrapper_is_a_config_error() -> None:
    provider = SpvSessionProvider(store=MemorySessionStore())
    with pytest.raises(AnafConfigError, match="bootstrapper"):
        await provider.login()


async def test_login_saves_the_bootstrapped_session() -> None:
    fresh = _session({"MRHSession": "fresh"})

    class FakeBootstrapper:
        async def bootstrap(self) -> SpvSession:
            return fresh

    store = MemorySessionStore()
    provider = SpvSessionProvider(store=store, bootstrapper=FakeBootstrapper())
    assert provider.session is None
    assert await provider.login() is fresh
    assert provider.session == fresh


# --- SpvAuth --------------------------------------------------------------------------


def _client(session: SpvSession | None = None) -> httpx.AsyncClient:
    provider = SpvSessionProvider(
        store=MemorySessionStore(session if session is not None else _session())
    )
    return httpx.AsyncClient(auth=SpvAuth(provider))


def test_sync_usage_is_a_config_error() -> None:
    auth = SpvAuth(SpvSessionProvider(store=MemorySessionStore()))
    request = httpx.Request("GET", f"{BASE}/listaMesaje")
    with (
        pytest.raises(AnafConfigError, match="async-only"),
        httpx.Client(auth=auth) as client,
    ):
        client.send(request)


@respx.mock
async def test_hop_cookies_replace_the_stored_ones_on_the_next_request() -> None:
    # The nonce hop must carry the rotated cookie, not the stale Cookie header.
    api = respx.get(f"{BASE}/listaMesaje")
    api.side_effect = [
        httpx.Response(
            302,
            headers={
                "Location": f"{HOST}/my.policy_nonce?nonce=abc",
                "Set-Cookie": "MRHSession=revalidated;path=/;secure",
            },
        ),
        httpx.Response(200, json={"titlu": "ok"}),
    ]
    nonce = respx.get(f"{HOST}/my.policy_nonce").respond(
        302, headers={"Location": "/SPVWS2/rest/listaMesaje?zile=5"}
    )
    async with _client() as client:
        response = await client.get(f"{BASE}/listaMesaje", follow_redirects=False)
    assert response.status_code == 200
    assert "MRHSession=revalidated" in nonce.calls.last.request.headers["Cookie"]
    assert "MRHSession=revalidated" in api.calls.last.request.headers["Cookie"]


@respx.mock
async def test_endless_redirect_chain_is_bounded() -> None:
    respx.get(f"{HOST}/my.policy_nonce").respond(
        302, headers={"Location": f"{HOST}/my.policy_nonce?again=1"}
    )
    respx.get(f"{BASE}/listaMesaje").respond(
        302, headers={"Location": f"{HOST}/my.policy_nonce"}
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="exceeded"):
            await client.get(f"{BASE}/listaMesaje", follow_redirects=False)
