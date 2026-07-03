"""Runtime context shared by the MCP tools.

Holds the long-lived :class:`TokenProvider` and the clients, built from a
:class:`ServerConfig`. Clients are created lazily on first use and closed on shutdown.
The public-services client needs no auth (and ignores the configured environment —
the public host has no test/prod split), so it — and the server as a whole — works
even when no OAuth credentials are configured; only the authenticated clients then
fail, with a :class:`~anafpy.exceptions.AnafConfigError` saying how to enable them.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from ..auth import FileTokenStore, TokenProvider
from ..efactura.client import EFacturaClient
from ..etransport.client import ETransportClient
from ..exceptions import AnafConfigError
from ..public.client import PublicClient
from .config import ServerConfig
from .tokens import TokenLedger

__all__ = ["AppContext", "AuthStatus"]

_NO_CREDENTIALS = (
    "no OAuth credentials configured — set ANAFPY_CLIENT_ID and "
    "ANAFPY_CLIENT_SECRET (then run `anafpy auth login` once) to enable the "
    "e-Factura / e-Transport tools; the public anaf_* lookups work without them"
)


class AuthStatus(BaseModel):
    """Read-only snapshot of the stored ANAF session."""

    authenticated: bool
    environment: str
    credentials_configured: bool = True
    access_token_valid: bool = False
    access_expires_in_days: float | None = None
    refresh_expires_in_days: float | None = None
    needs_login: bool = False
    message: str = ""


class AppContext:
    """Owns auth + clients for the lifetime of the server process."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._provider: TokenProvider | None = None
        if config.client_id is not None and config.client_secret is not None:
            self._provider = TokenProvider(
                client_id=config.client_id,
                client_secret=config.client_secret,
                store=FileTokenStore(config.store_path),
            )
        self._efactura: EFacturaClient | None = None
        self._etransport: ETransportClient | None = None
        self._public: PublicClient | None = None
        #: Redeemed confirmation tokens (single-use gate for the submit tools).
        self.token_ledger = TokenLedger()

    @property
    def provider(self) -> TokenProvider:
        if self._provider is None:
            raise AnafConfigError(_NO_CREDENTIALS)
        return self._provider

    def efactura(self) -> EFacturaClient:
        if self._efactura is None:
            self._efactura = EFacturaClient(
                self.provider, environment=self.config.environment
            )
        return self._efactura

    def etransport(self) -> ETransportClient:
        if self._etransport is None:
            self._etransport = ETransportClient(
                self.provider, environment=self.config.environment
            )
        return self._etransport

    def public(self) -> PublicClient:
        if self._public is None:
            self._public = PublicClient()
        return self._public

    def auth_status(self) -> AuthStatus:
        """Report whether a usable ANAF session is present (read-only)."""
        env = self.config.environment.value
        if self._provider is None:
            return AuthStatus(
                authenticated=False,
                environment=env,
                credentials_configured=False,
                needs_login=True,
                message=_NO_CREDENTIALS,
            )
        tokens = self._provider.tokens
        if tokens is None:
            return AuthStatus(
                authenticated=False,
                environment=env,
                needs_login=True,
                message="not authenticated — run `anafpy auth login`",
            )
        now = time.time()
        access_days = (tokens.access_expires_at - now) / 86400.0
        refresh_days = (tokens.refresh_expires_at - now) / 86400.0
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
        if self._provider is not None:
            await self._provider.aclose()
