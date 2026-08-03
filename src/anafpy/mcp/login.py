"""The ``auth_login`` tool — ANAF's OAuth browser login, driven by the server.

The certificate step structurally needs the user's browser, but the server is
just as host-side as the CLI — a local stdio process on the machine that has the
browser and the token store (DESIGN.md §3) — so it runs the same bootstrap:
:func:`anafpy.auth.browser_login`, the choreography shared with
``anafpy auth login`` (per-attempt ephemeral self-signed TLS, per-attempt OAuth
``state``, listener bound before the browser opens, code exchange, save to the
shared store). The long-lived :class:`~anafpy.auth.TokenProvider` re-reads that
store on its next call, so a fresh login takes effect with no restart. The human
gates are unchanged: ``confirm=true`` (the model relays the user's explicit ask)
plus the certificate/PIN step itself, entirely between the user, their browser,
and their token.

This module maps the login outcomes onto the tool's contract. Deliberately NOT
here: paste mode (an authorization code must never transit the model's context,
and ANAF's ~60s code expiry cannot span a model turn) and any credential
parameter (client id/secret come only from
:class:`~anafpy.mcp.config.ServerConfig`). One attempt per call; every failure
after the confirm/config gates is a returned ``logged_in: false`` value with
guidance — ``spv_login``'s contract — and ``anafpy auth login`` in a terminal
stays the fallback (it also keeps the paste and user-supplied-TLS options).
"""

from __future__ import annotations

import urllib.parse
from inspect import cleandoc
from typing import assert_never

from mcp.server import MCPServer

from ..auth import (
    AuthorizationDenied,
    BrowserNotOpened,
    CallbackTimedOut,
    ExchangeFailed,
    ListenerUnavailable,
    LoginCompleted,
    browser_login,
    ephemeral_server_context,
)
from ..exceptions import AnafConfigError
from .artifacts import MUTATING
from .config import ServerConfig
from .context import AppContext, token_store

__all__ = ["register"]

_CLI_FALLBACK = "`anafpy auth login` in a terminal is the fallback"


def register(mcp: MCPServer, ctx: AppContext, config: ServerConfig) -> None:
    """Register the ``auth_login`` tool."""

    @mcp.tool(
        title="ANAF: Log in",
        annotations=MUTATING,
        description=cleandoc("""
            Run the one-time ANAF OAuth login in the user's browser — needed at
            first setup and again roughly yearly, when auth_status reports
            needs_login. OPENS THE USER'S BROWSER on ANAF's certificate login
            page — call it only when the user explicitly asked to log in (or
            approved doing so), and pass confirm=true to attest that.

            Before calling, tell the user what to expect, in order:
            - their browser opens on ANAF's page and asks for the qualified
              certificate (USB token plugged in; PIN if the device prompts —
              never via Claude)
            - then a "connection is not private" warning at localhost —
              expected (a one-time certificate of their own machine); they
              click Advanced -> Proceed to localhost (Firefox: Accept the Risk
              and Continue)
            - a page says the tab can be closed — done, nothing to copy.

            One attempt per call, waiting up to timeout_s (clamped 60-300s)
            for the browser round-trip. On failure, relay next_step and retry
            only with the user's go-ahead; `anafpy auth login` in a terminal
            is the equivalent fallback. On success the tokens are saved to the
            system store and every authenticated tool works immediately — no
            restart needed.
        """),
    )
    async def auth_login(
        confirm: bool = False, timeout_s: float = 180.0
    ) -> dict[str, object]:
        if not confirm:
            raise AnafConfigError(
                "auth_login opens the user's browser for ANAF's certificate "
                "step — get their explicit approval in the conversation, then "
                "call again with confirm=true"
            )
        if config.client_id is None or config.client_secret is None:
            raise AnafConfigError(
                "no OAuth credentials configured — the user sets the ANAF "
                "Client ID and Client Secret first (the extension's settings, "
                "or ANAFPY_CLIENT_ID / ANAFPY_CLIENT_SECRET), then auth_login "
                "can run"
            )
        timeout = min(max(timeout_s, 60.0), 300.0)
        parsed = urllib.parse.urlparse(config.redirect_uri)
        ssl_context = (
            ephemeral_server_context(parsed.hostname or "localhost")
            if parsed.scheme == "https"
            else None
        )
        # The shared store is the single source of truth: the long-lived
        # provider re-reads it on its next call, so no restart is needed.
        outcome = await browser_login(
            config.client_id,
            config.client_secret,
            config.redirect_uri,
            token_store(config),
            timeout=timeout,
            ssl_context=ssl_context,
            # Nobody watches a printed URL here — a browser that will not open
            # ends the attempt instead of waiting out the timeout.
            require_browser=True,
        )
        match outcome:
            case LoginCompleted():
                return {
                    "logged_in": True,
                    "status": ctx.auth_status().model_dump(mode="json"),
                    "next_step": "authenticated — the e-Factura / e-Transport "
                    "tools work immediately; the session refreshes headlessly "
                    "for about a year",
                }
            case ListenerUnavailable(error=error):
                return {
                    "logged_in": False,
                    "detail": error,
                    "next_step": "the callback port could not be bound "
                    "(another login in progress, or the port is taken) — retry "
                    f"with the user's go-ahead; {_CLI_FALLBACK}",
                }
            case BrowserNotOpened(authorize_url=url):
                return {
                    "logged_in": False,
                    "detail": "no browser could be opened on this machine",
                    "authorize_url": url,
                    "next_step": f"{_CLI_FALLBACK} — it prints the URL to "
                    "visit by hand",
                }
            case AuthorizationDenied(error=error):
                return {
                    "logged_in": False,
                    "detail": error,
                    "next_step": "ANAF reported the authorization as failed — "
                    "usually the user cancelled the certificate step; ask "
                    "what they saw, then retry with their go-ahead",
                }
            case CallbackTimedOut(authorize_url=url):
                return {
                    "logged_in": False,
                    "detail": f"no callback arrived within {timeout:.0f}s",
                    "authorize_url": url,
                    "next_step": "ask whether the browser opened and which "
                    "page the user reached, then retry with their go-ahead; "
                    f"{_CLI_FALLBACK}",
                }
            case ExchangeFailed(error=error):
                return {
                    "logged_in": False,
                    "detail": f"the code exchange failed: {error}",
                    "next_step": "ANAF's codes expire in ~60 seconds — with "
                    "the user's go-ahead call auth_login again for a fresh "
                    "attempt",
                }
            case _:
                assert_never(outcome)
