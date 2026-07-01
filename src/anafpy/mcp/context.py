"""Runtime context shared by the MCP tools.

Holds the long-lived :class:`TokenProvider` and the two clients, built from a
:class:`ServerConfig`. Clients are created lazily on first use and closed on shutdown.
Validators come from the ``anafpy[validation]`` extra and degrade gracefully when it is
not installed — the ``validate``/``prepare`` tools then report that local pre-validation
is unavailable rather than failing.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from ..auth import FileTokenStore, TokenProvider
from ..efactura.client import EFacturaClient
from ..etransport.client import ETransportClient
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
        self._validators: dict[str, object] = {}
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

    def efactura_validator(self) -> object | None:
        return self._validator("efactura")

    def etransport_validator(self) -> object | None:
        return self._validator("etransport")

    def _validator(self, service: str) -> object | None:
        if service in self._validators:
            return self._validators[service]
        try:
            if service == "efactura":
                from ..efactura.validator import create_validator
            else:
                from ..etransport.validator import create_validator
            validator: object | None = create_validator()
        except (ImportError, ValueError):
            validator = None
        self._validators[service] = validator
        return validator

    async def aclose(self) -> None:
        if self._efactura is not None:
            await self._efactura.aclose()
        if self._etransport is not None:
            await self._etransport.aclose()
        await self._provider.aclose()
