"""Token lifecycle: hand out a valid access token, refreshing transparently.

``TokenProvider`` is the batteries-included implementation over a ``TokenStore``.
``AnafAuth`` plugs it into httpx so every request carries a Bearer token and a 401
triggers a single refresh-and-retry.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from contextlib import asynccontextmanager

import httpx

from ..exceptions import AnafAuthError, AnafConfigError
from .models import TokenSet
from .oauth import refresh_tokens
from .store import TokenStore

__all__ = ["AnafAuth", "TokenProvider"]


class TokenProvider:
    """Provides valid access tokens, refreshing and persisting as needed.

    The ``TokenStore`` is the single source of truth: the provider keeps no token
    state of its own. Every operation reads the freshest persisted set under the
    lock, so a login or a refresh-token rotation performed by another process
    sharing the store (the CLI, a second server) is picked up on the next call.
    """

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
        self._lock = asyncio.Lock()

    @property
    def _client(self) -> httpx.AsyncClient:
        # Lazily built so a provider that never refreshes never opens a client;
        # ``aclose`` resets it, so a later use transparently gets a fresh one.
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    @asynccontextmanager
    async def _authenticated(self) -> AsyncIterator[TokenSet]:
        # Scopes a single operation: serialize refreshes and hand the operation
        # the freshest persisted token set. Tokens must not outlive the block —
        # holding them across operations would reintroduce a stale cache.
        # Store I/O is synchronous (keyring can block briefly) — accepted for a
        # local single-user process; refreshes happen ~once per 90 days.
        async with self._lock:
            tokens = self._store.load()
            if tokens is None:
                raise AnafAuthError("not authenticated — run `anafpy auth login`")
            yield tokens

    async def access_token(self) -> str:
        """Return a currently-valid access token, refreshing if expired."""
        async with self._authenticated() as tokens:
            if tokens.access_expired():
                tokens = await self._refresh(tokens)
            return tokens.access_token

    async def force_refresh(self, *, stale: str | None = None) -> str:
        """Refresh unconditionally (used after a 401); return the new access token.

        Pass the access token the failing request carried as ``stale``: when it has
        already been replaced (a concurrent request or another process refreshed
        first), the current token is returned without burning another rotation.
        """
        async with self._authenticated() as tokens:
            if stale is not None and tokens.access_token != stale:
                return tokens.access_token
            return (await self._refresh(tokens)).access_token

    async def _refresh(self, tokens: TokenSet) -> TokenSet:
        if tokens.refresh_expired():
            raise AnafAuthError("refresh token expired — run `anafpy auth login`")
        new = await refresh_tokens(
            self._client,
            client_id=self._client_id,
            client_secret=self._client_secret,
            refresh_token=tokens.refresh_token,
        )
        self._store.save(new)  # persist the rotated refresh token
        return new

    @property
    def tokens(self) -> TokenSet | None:
        """The persisted token set, if authenticated (read-only snapshot)."""
        return self._store.load()

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
