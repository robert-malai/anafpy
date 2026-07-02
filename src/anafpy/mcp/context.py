"""Runtime context shared by the MCP tools.

Holds the long-lived :class:`TokenProvider` and the clients, built from a
:class:`ServerConfig`. Clients are created lazily on first use and closed on shutdown.
The public-services client needs no auth (and ignores the configured environment —
the public host has no test/prod split).
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from ..auth import FileTokenStore, TokenProvider
from ..efactura.client import EFacturaClient
from ..etransport.client import ETransportClient
from ..public.client import PublicClient
from .config import ServerConfig
from .tokens import TokenLedger

__all__ = ["AppContext", "AuthStatus"]


class AuthStatus(BaseModel):
    """Read-only snapshot of the stored ANAF session."""

    authenticated: bool
    environment: str
    access_token_valid: bool = False
    access_expires_in_days: float | None = None
    refresh_expires_in_days: float | None = None
    needs_login: bool = False
    message: str = ""


class AppContext:
    """Owns auth + clients for the lifetime of the server process."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._store = FileTokenStore(config.store_path)
        self._provider = TokenProvider(
            client_id=config.client_id,
            client_secret=config.client_secret,
            store=self._store,
        )
        self._efactura: EFacturaClient | None = None
        self._etransport: ETransportClient | None = None
        self._public: PublicClient | None = None
        #: Redeemed confirmation tokens (single-use gate for the submit tools).
        self.token_ledger = TokenLedger()

    @property
    def provider(self) -> TokenProvider:
        return self._provider

    def efactura(self) -> EFacturaClient:
        if self._efactura is None:
            self._efactura = EFacturaClient(
                self._provider, environment=self.config.environment
            )
        return self._efactura

    def etransport(self) -> ETransportClient:
        if self._etransport is None:
            self._etransport = ETransportClient(
                self._provider, environment=self.config.environment
            )
        return self._etransport

    def public(self) -> PublicClient:
        if self._public is None:
            self._public = PublicClient()
        return self._public

    def auth_status(self) -> AuthStatus:
        """Report whether a usable ANAF session is present (read-only)."""
        env = self.config.environment.value
        tokens = self._provider.tokens
        if tokens is None:
            return AuthStatus(
                authenticated=False,
                environment=env,
                needs_login=True,
                message="not authenticated — run `anafpy auth login`",
            )
        now = time.time()
        access_days = (
            (tokens.access_expires_at - now) / 86400.0
            if tokens.access_expires_at is not None
            else None
        )
        refresh_days = (
            (tokens.refresh_expires_at - now) / 86400.0
            if tokens.refresh_expires_at is not None
            else None
        )
        refresh_dead = tokens.refresh_expired()
        if refresh_dead:
            message = "refresh token expired — run `anafpy auth login`"
        elif tokens.access_expired():
            message = "access token expired; it will refresh headlessly on next call"
        else:
            message = "authenticated"
        return AuthStatus(
            authenticated=not refresh_dead,
            environment=env,
            access_token_valid=not tokens.access_expired(),
            access_expires_in_days=access_days,
            refresh_expires_in_days=refresh_days,
            needs_login=refresh_dead,
            message=message,
        )

    async def aclose(self) -> None:
        if self._efactura is not None:
            await self._efactura.aclose()
        if self._etransport is not None:
            await self._etransport.aclose()
        if self._public is not None:
            await self._public.aclose()
        await self._provider.aclose()
