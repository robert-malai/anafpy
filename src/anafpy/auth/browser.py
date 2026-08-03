"""The browser-login choreography shared by the CLI and the MCP server.

Both interactive front-ends — ``anafpy auth login`` and the MCP server's
confirm-gated ``auth_login`` tool — run the same security-critical sequence:
a fresh OAuth ``state`` per attempt, the callback listener bound **before** the
browser opens (with a cached certificate/session the redirect can arrive within
a second, and ANAF's codes expire in ~60s), the code exchange, and the save to
the token store. :func:`browser_login` is that sequence's single home; nothing
past its two gates raises for a flow outcome — every way an attempt can end is
a member of the :data:`BrowserLoginOutcome` union, and each front-end translates
those into its own interaction model (interactive prints and paste fallbacks;
a structured tool result). :func:`finish_login` is the exchange-and-save tail,
also used on its own by the CLI's paste paths, which capture the code without a
listener.
"""

from __future__ import annotations

import asyncio
import secrets
import ssl
import webbrowser
from collections.abc import Callable

import httpx2
from pydantic import BaseModel

from ..exceptions import AnafAuthError, AnafConfigError, AnafTransportError
from .callback import CallbackListener
from .models import TokenSet
from .oauth import build_authorize_url, exchange_code
from .store import TokenStore

__all__ = [
    "AuthorizationDenied",
    "BrowserLoginOutcome",
    "BrowserNotOpened",
    "CallbackTimedOut",
    "ExchangeFailed",
    "ListenerUnavailable",
    "LoginCompleted",
    "browser_login",
    "finish_login",
]


class LoginCompleted(BaseModel):
    """The code was exchanged and the tokens saved to the store."""

    tokens: TokenSet


class ListenerUnavailable(BaseModel):
    """The callback port could not be bound; the browser was **not** opened.

    ``authorize_url`` and ``state`` let a front-end continue the same attempt
    without a listener (open the browser itself, then capture by paste).
    """

    error: str
    authorize_url: str
    state: str


class BrowserNotOpened(BaseModel):
    """No browser could be opened and ``require_browser`` was set.

    The listener is already closed; ``authorize_url``/``state`` describe the
    attempt for reporting or a paste continuation.
    """

    authorize_url: str
    state: str


class AuthorizationDenied(BaseModel):
    """ANAF redirected with an OAuth error — usually a cancelled certificate step."""

    error: str


class CallbackTimedOut(BaseModel):
    """No redirect arrived within ``timeout``.

    The browser's address bar still holds the redirect after a late
    authorization, so a paste continuation with the same ``state`` remains
    possible.
    """

    authorize_url: str
    state: str
    timeout: float


class ExchangeFailed(BaseModel):
    """The token endpoint refused the code or was unreachable (codes expire ~60s)."""

    error: str


type BrowserLoginOutcome = (
    LoginCompleted
    | ListenerUnavailable
    | BrowserNotOpened
    | AuthorizationDenied
    | CallbackTimedOut
    | ExchangeFailed
)
"""Every way one browser-login attempt can end. Closed — ``match`` with
``assert_never``."""


async def finish_login(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    store: TokenStore,
) -> TokenSet:
    """Exchange a captured authorization code and persist the tokens.

    The tail of every login: shared by :func:`browser_login` and the CLI's
    paste paths, so the exchange parameters and the save cannot drift apart.

    Raises:
        AnafAuthError: if the token endpoint refuses the code.
        AnafTransportError: if the token endpoint is unreachable.
    """
    async with httpx2.AsyncClient(timeout=30.0) as http:
        tokens = await exchange_code(
            http,
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
    store.save(tokens)
    return tokens


async def browser_login(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    store: TokenStore,
    *,
    timeout: float = 180.0,
    ssl_context: ssl.SSLContext | None = None,
    require_browser: bool = False,
    open_browser: Callable[[str], bool] | None = None,
) -> BrowserLoginOutcome:
    """Run one listener-based OAuth login attempt end to end.

    Args:
        timeout: how long to wait for the redirect once the browser is open.
        ssl_context: TLS for the callback listener (``None`` serves plain HTTP —
            only correct behind an external TLS terminator or an ``http://``
            redirect URI).
        require_browser: end the attempt with :class:`BrowserNotOpened` when no
            browser opens — for an unattended front-end with nobody watching a
            printed URL. The default keeps waiting: an interactive caller shows
            ``authorize_url`` for the user to visit by hand.
        open_browser: replaces ``webbrowser.open`` — an interactive front-end
            wraps it to narrate what is about to happen.

    Returns:
        A :data:`BrowserLoginOutcome`; nothing here raises for a flow outcome.
    """
    # A per-attempt OAuth `state`: the redirect must echo it back, so a forged
    # redirect cannot inject someone else's authorization code (login CSRF).
    state = secrets.token_urlsafe(16)
    url = build_authorize_url(client_id, redirect_uri, state=state)
    # Bind BEFORE the browser opens: with a cached certificate/session the
    # redirect can arrive within a second (ANAF's codes expire in ~60s).
    try:
        listener = CallbackListener(
            redirect_uri, ssl_context=ssl_context, expected_state=state
        )
    except AnafConfigError as exc:
        return ListenerUnavailable(error=str(exc), authorize_url=url, state=state)
    with listener:
        opener = webbrowser.open if open_browser is None else open_browser
        # Both the opener (spawns a subprocess) and the wait block — keep them
        # off the event loop.
        opened = await asyncio.to_thread(opener, url)
        if require_browser and not opened:
            return BrowserNotOpened(authorize_url=url, state=state)
        try:
            code = await asyncio.to_thread(listener.wait, timeout)
        except AnafAuthError as exc:
            return AuthorizationDenied(error=str(exc))
    if code is None:
        return CallbackTimedOut(authorize_url=url, state=state, timeout=timeout)
    try:
        tokens = await finish_login(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
            store=store,
        )
    except (AnafAuthError, AnafTransportError) as exc:
        return ExchangeFailed(error=str(exc))
    return LoginCompleted(tokens=tokens)
