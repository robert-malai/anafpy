"""Tests for the OAuth2 auth module (mocked with respx — no real network)."""

from __future__ import annotations

import base64
import json
import time

import httpx
import pytest
import respx

from anafpy.auth import (
    MemoryTokenStore,
    TokenProvider,
    TokenSet,
    build_authorize_url,
    exchange_code,
    refresh_tokens,
)
from anafpy.auth.oauth import TOKEN_URL
from anafpy.exceptions import AnafAuthError


def _make_jwt(exp: float) -> str:
    """A structurally-valid (unsigned) JWT carrying an `exp` claim."""

    def seg(obj: dict[str, object]) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{seg({'alg': 'RS512'})}.{seg({'exp': int(exp)})}.sig"


def _token_response(access_exp: float, refresh: str = "refresh-2") -> dict[str, str]:
    return {
        "access_token": _make_jwt(access_exp),
        "refresh_token": refresh,
        "token_type": "Bearer",
    }


# --- TokenSet -------------------------------------------------------------------------


def test_tokenset_reads_jwt_exp() -> None:
    exp = time.time() + 90 * 86400
    tokens = TokenSet.from_token_response(_token_response(exp))
    assert tokens.access_expires_at == pytest.approx(exp, abs=1)
    assert not tokens.access_expired()
    assert tokens.refresh_expires_at is not None  # 365-day fallback


def test_tokenset_reads_refresh_jwt_exp() -> None:
    refresh_exp = time.time() + 200 * 86400
    tokens = TokenSet.from_token_response(
        _token_response(time.time() + 90 * 86400, refresh=_make_jwt(refresh_exp))
    )
    assert tokens.refresh_expires_at == pytest.approx(refresh_exp, abs=1)


def test_tokenset_access_expired_with_leeway() -> None:
    tokens = TokenSet.from_token_response(_token_response(time.time() + 100))
    assert tokens.access_expired(leeway=300) is True
    assert tokens.access_expired(leeway=10) is False


def test_authorize_url_contains_required_params() -> None:
    url = build_authorize_url("CID", "https://localhost:9002/callback")
    assert url.startswith("https://logincert.anaf.ro/anaf-oauth2/v1/authorize?")
    assert "response_type=code" in url
    assert "token_content_type=jwt" in url
    assert "client_id=CID" in url


# --- exchange / refresh ---------------------------------------------------------------


@respx.mock
async def test_exchange_code_uses_basic_auth_and_jwt_param() -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response(time.time() + 90 * 86400))
    )
    async with httpx.AsyncClient() as http:
        tokens = await exchange_code(
            http,
            client_id="CID",
            client_secret="SECRET",
            code="abc",
            redirect_uri="https://localhost:9002/callback",
        )
    assert tokens.token_type == "Bearer"
    req = route.calls.last.request
    assert req.headers["Authorization"].startswith("Basic ")
    body = req.content.decode()
    assert "grant_type=authorization_code" in body
    assert "token_content_type=jwt" in body


@respx.mock
async def test_refresh_rotates_refresh_token() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json=_token_response(time.time() + 90 * 86400, refresh="rotated")
        )
    )
    async with httpx.AsyncClient() as http:
        tokens = await refresh_tokens(
            http, client_id="CID", client_secret="SECRET", refresh_token="old"
        )
    assert tokens.refresh_token == "rotated"


@respx.mock
async def test_token_error_raises_auth_error() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            400, json={"error": "invalid_client", "error_description": "bad"}
        )
    )
    async with httpx.AsyncClient() as http:
        with pytest.raises(AnafAuthError, match="bad"):
            await refresh_tokens(
                http, client_id="x", client_secret="y", refresh_token="z"
            )


# --- TokenProvider --------------------------------------------------------------------


@respx.mock
async def test_provider_refreshes_expired_access_token_and_persists() -> None:
    expired = TokenSet.from_token_response(
        _token_response(time.time() - 10, refresh="r1")
    )
    store = MemoryTokenStore(expired)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json=_token_response(time.time() + 90 * 86400, refresh="r2")
        )
    )
    async with httpx.AsyncClient() as http:
        provider = TokenProvider(
            client_id="CID", client_secret="SECRET", store=store, http=http
        )
        token = await provider.access_token()
    assert token  # a fresh access token
    # rotated refresh token was persisted back to the store
    saved = store.load()
    assert saved is not None and saved.refresh_token == "r2"


@respx.mock
async def test_provider_adopts_tokens_rotated_by_another_process() -> None:
    # The CLI (or a second server) refreshed and saved a new set to the shared
    # store; the provider must adopt it, not refresh with its stale refresh token.
    expired = TokenSet.from_token_response(
        _token_response(time.time() - 10, refresh="r1")
    )
    store = MemoryTokenStore(expired)
    provider = TokenProvider(client_id="CID", client_secret="SECRET", store=store)
    rotated = TokenSet.from_token_response(
        _token_response(time.time() + 90 * 86400, refresh="r2")
    )
    store.save(rotated)

    token = await provider.access_token()
    assert token == rotated.access_token
    assert not respx.calls  # no refresh round-trip


@respx.mock
async def test_provider_refreshes_with_the_rotated_refresh_token() -> None:
    # Both the adopted set and ours are expired: refresh must use the store's
    # (newest) refresh token, not the invalidated in-memory one.
    expired = TokenSet.from_token_response(
        _token_response(time.time() - 10, refresh="r1")
    )
    store = MemoryTokenStore(expired)
    provider = TokenProvider(client_id="CID", client_secret="SECRET", store=store)
    store.save(
        TokenSet.from_token_response(_token_response(time.time() - 5, refresh="r2"))
    )
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json=_token_response(time.time() + 90 * 86400, refresh="r3")
        )
    )

    await provider.access_token()
    assert "refresh_token=r2" in route.calls.last.request.content.decode()


@respx.mock
async def test_force_refresh_skips_when_stale_token_was_already_replaced() -> None:
    current = TokenSet.from_token_response(
        _token_response(time.time() + 90 * 86400, refresh="r1")
    )
    provider = TokenProvider(
        client_id="CID", client_secret="SECRET", store=MemoryTokenStore(current)
    )

    token = await provider.force_refresh(stale="an-older-access-token")
    assert token == current.access_token
    assert not respx.calls  # no second rotation burnt


async def test_provider_without_tokens_raises() -> None:
    provider = TokenProvider(
        client_id="CID", client_secret="SECRET", store=MemoryTokenStore(None)
    )
    with pytest.raises(AnafAuthError, match="auth login"):
        await provider.access_token()


async def test_provider_adopts_login_made_after_construction() -> None:
    # `anafpy auth login` ran while the provider (e.g. the MCP server) was already
    # up: tokens landing in the store afterwards must be picked up — no restart.
    store = MemoryTokenStore(None)
    provider = TokenProvider(client_id="CID", client_secret="SECRET", store=store)
    with pytest.raises(AnafAuthError, match="auth login"):
        await provider.access_token()

    fresh = TokenSet.from_token_response(
        _token_response(time.time() + 90 * 86400, refresh="r1")
    )
    store.save(fresh)
    assert await provider.access_token() == fresh.access_token
    assert provider.tokens is not None  # visible to auth_status as well
