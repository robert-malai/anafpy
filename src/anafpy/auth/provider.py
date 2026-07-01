"""Token lifecycle: hand out a valid access token, refreshing transparently.

``TokenProvider`` is the batteries-included implementation over a ``TokenStore``.
``AnafAuth`` plugs it into httpx so every request carries a Bearer token and a 401
triggers a single refresh-and-retry.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import httpx

from ..exceptions import AnafAuthError, AnafConfigError
from .models import TokenSet
from .oauth import refresh_tokens
from .store import TokenStore

__all__ = ["AnafAuth", "TokenProvider"]


class TokenProvider:
    """Provides valid access tokens, refreshing and persisting as needed."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        store: TokenStore,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._store = store
        self._http = http
        self._owns_http = http is None
        self._tokens: TokenSet | None = store.load()
        self._lock = asyncio.Lock()

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def access_token(self) -> str:
        """Return a currently-valid access token, refreshing if expired."""
        async with self._lock:
            tokens = self._tokens
            if tokens is None:
                raise AnafAuthError("not authenticated — run `anafpy auth login`")
            if tokens.access_expired():
                tokens = await self._refresh_locked(tokens)
            return tokens.access_token

    async def force_refresh(self, *, stale: str | None = None) -> str:
        """Refresh unconditionally (used after a 401); return the new access token.

        Pass the access token the failing request carried as ``stale``: when it has
        already been replaced (a concurrent request refreshed first), the current
        token is returned without burning another refresh rotation.
        """
        async with self._lock:
            if self._tokens is None:
                raise AnafAuthError("not authenticated — run `anafpy auth login`")
            if stale is not None and self._tokens.access_token != stale:
                return self._tokens.access_token
            tokens = await self._refresh_locked(self._tokens)
            return tokens.access_token

    async def _refresh_locked(self, tokens: TokenSet) -> TokenSet:
        # ANAF rotates the refresh token on every refresh. Another process sharing
        # the store (CLI, a second server) may have rotated already — adopt the
        # stored set instead of refreshing with our now-invalidated refresh token.
        stored = self._store.load()
        if stored is not None and stored.refresh_token != tokens.refresh_token:
            self._tokens = stored
            if not stored.access_expired():
                return stored
            tokens = stored
        if tokens.refresh_expired():
            raise AnafAuthError("refresh token expired — run `anafpy auth login`")
        new = await refresh_tokens(
            await self._client(),
            client_id=self._client_id,
            client_secret=self._client_secret,
            refresh_token=tokens.refresh_token,
        )
        self._tokens = new
        self._store.save(new)  # persist rotated refresh token
        return new

    @property
    def tokens(self) -> TokenSet | None:
        """The current token set, if authenticated (read-only snapshot)."""
        return self._tokens

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None


class AnafAuth(httpx.Auth):
    """httpx auth flow: attach Bearer, and refresh-once on a 401."""

    def __init__(self, provider: TokenProvider) -> None:
        self._provider = provider

    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        raise AnafConfigError("anafpy auth is async-only; use an httpx.AsyncClient")
        yield request  # unreachable; makes this a generator to satisfy httpx.Auth

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        token = await self._provider.access_token()
        request.headers["Authorization"] = f"Bearer {token}"
        response = yield request
        if response.status_code == httpx.codes.UNAUTHORIZED:
            token = await self._provider.force_refresh(stale=token)
            request.headers["Authorization"] = f"Bearer {token}"
            yield request
