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
from functools import cached_property
from typing import Protocol, cast

from pydantic import BaseModel

from ..auth import FileTokenStore, KeyringTokenStore, TokenProvider, TokenStore
from ..declaratii import (
    DeclarationStatusClient,
    DeclarationUploadClient,
    DukIntegrator,
    default_duk_dir,
)
from ..efactura.client import EFacturaClient
from ..etransport.client import ETransportClient
from ..exceptions import AnafConfigError
from ..public.client import PublicClient
from ..spv import FileSessionStore, SpvClient, SpvSessionProvider
from .config import ServerConfig
from .gate import TokenLedger

__all__ = ["AppContext", "AuthStatus"]

_NO_CREDENTIALS = (
    "no OAuth credentials configured — set ANAFPY_CLIENT_ID and "
    "ANAFPY_CLIENT_SECRET (then run `anafpy auth login` once) to enable the "
    "e-Factura / e-Transport tools; the public anaf_* lookups work without them"
)

_NO_DUK = (
    "declaration tools need DUKIntegrator — call declaratie_duk_install (or "
    "run `anafpy duk install`) to provision the managed dist at "
    "~/.anafpy/duk-dist from ANAF's update feed, or set ANAFPY_DUK_DIR to an "
    "extracted dist/ folder"
)

#: The lazily-built clients that hold a connection, in the order shutdown closes
#: them. Each is a :func:`~functools.cached_property`, so its presence in the
#: instance ``__dict__`` is exactly "was it ever built?" — the others were never
#: touched and have nothing to close.
_LAZY_CLIENTS = (
    "efactura",
    "etransport",
    "public",
    "spv",
    "declaration_status",
    "declaration_upload",
)


class _AsyncCloseable(Protocol):
    """What :meth:`AppContext.aclose` needs of a built client."""

    async def aclose(self) -> None: ...


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
            # A keyring backend without a usable OS credential store fails loudly
            # here, at server start, rather than on the first authenticated call.
            store: TokenStore = (
                KeyringTokenStore()
                if config.store_backend == "keyring"
                else FileTokenStore(config.store_path)
            )
            self._provider = TokenProvider(
                client_id=config.client_id,
                client_secret=config.client_secret,
                store=store,
            )
        #: Redeemed confirmation tokens (single-use gate for the submit tools).
        self.token_ledger = TokenLedger()
        #: Same-day `cerere` dedupe for agent loops: canonical params -> the
        #: (request_id, date) an identical spv_cerere already got today. Guards
        #: an agent re-filing within one server process; deliberately in-memory
        #: (the library client is stateless by design — a repeat after a server
        #: restart is harmless).
        self.spv_request_log: dict[str, tuple[str, str]] = {}

    @property
    def provider(self) -> TokenProvider:
        if self._provider is None:
            raise AnafConfigError(_NO_CREDENTIALS)
        return self._provider

    @cached_property
    def efactura(self) -> EFacturaClient:
        return EFacturaClient(self.provider, environment=self.config.environment)

    @cached_property
    def etransport(self) -> ETransportClient:
        return ETransportClient(self.provider, environment=self.config.environment)

    @cached_property
    def public(self) -> PublicClient:
        return PublicClient()

    @cached_property
    def spv(self) -> SpvClient:
        """The SPV client over the persisted cookie session.

        The provider carries no bootstrapper: the certificate/2FA login is
        interactive and stays host-side (``anafpy spv login``), like the OAuth
        browser flow.
        """
        return SpvClient(
            SpvSessionProvider(store=FileSessionStore(self.config.spv_session_path))
        )

    @cached_property
    def duk(self) -> DukIntegrator:
        """The DUKIntegrator wrapper (validate / render); built lazily.

        Resolution: ``ANAFPY_DUK_DIR`` when configured, else the managed dist
        (``~/.anafpy/duk-dist``, provisioned by ``declaratie_duk_install``).
        A failed resolution is not cached — ``cached_property`` stores nothing
        when the getter raises, so the next call re-resolves and the tools pick
        a freshly installed dist up without a server restart.

        Raises:
            AnafConfigError: neither source is available, or the directory is
                not a DUKIntegrator install.
        """
        directory = self.config.duk_dir or default_duk_dir()
        if directory is None:
            raise AnafConfigError(_NO_DUK)
        return DukIntegrator(directory, java=self.config.duk_java)

    @cached_property
    def declaration_status(self) -> DeclarationStatusClient:
        """The StareD112 status client (public, no auth — needs no configuration)."""
        return DeclarationStatusClient()

    @cached_property
    def declaration_upload(self) -> DeclarationUploadClient:
        """The portal upload client, carrying the in-process APM session.

        Built without a bootstrapper: the certificate/2FA login stays in the
        ``declaratie_portal_login`` tool, which runs a per-attempt bootstrapper
        and installs the resulting cookie set here (``install_session``). The
        session is deliberately in-memory only — portal sessions die after ~10
        idle minutes, so unlike SPV's there is nothing worth persisting.
        """
        return DeclarationUploadClient()

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
        for name in _LAZY_CLIENTS:
            if (client := self.__dict__.get(name)) is not None:
                await cast(_AsyncCloseable, client).aclose()
        if self._provider is not None:
            await self._provider.aclose()
