"""The ``auth_login`` tool — ANAF's OAuth browser login, driven by the server.

The certificate step structurally needs the user's browser, but the server is
just as host-side as the CLI — a local stdio process on the machine that has the
browser and the token store (DESIGN.md §3) — so it can run the same bootstrap:
bind the callback listener (per-attempt ephemeral self-signed TLS, per-attempt
OAuth ``state``), open the browser, wait for the redirect, exchange the code,
and save the tokens to the shared store. The long-lived
:class:`~anafpy.auth.TokenProvider` re-reads that store on its next call, so a
fresh login takes effect with no restart. The human gates are unchanged:
``confirm=true`` (the model relays the user's explicit ask) plus the
certificate/PIN step itself, entirely between the user, their browser, and
their token.

Deliberately NOT here: paste mode (an authorization code must never transit the
model's context, and ANAF's ~60s code expiry cannot span a model turn) and any
credential parameter (client id/secret come only from
:class:`~anafpy.mcp.config.ServerConfig`). One attempt per call; every failure
after the confirm/config gates is a returned ``logged_in: false`` value with
guidance — ``spv_login``'s contract — and ``anafpy auth login`` in a terminal
stays the fallback (it also keeps the paste and user-supplied-TLS options).
"""

from __future__ import annotations

import asyncio
import secrets
import urllib.parse
import webbrowser
from inspect import cleandoc

import httpx2
from mcp.server import MCPServer

from ..auth import (
    CallbackListener,
    build_authorize_url,
    ephemeral_server_context,
    exchange_code,
)
from ..exceptions import AnafAuthError, AnafConfigError, AnafTransportError
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
        # A per-attempt OAuth `state`: the redirect must echo it back, so a
        # forged redirect cannot inject someone else's code (login CSRF).
        state = secrets.token_urlsafe(16)
        url = build_authorize_url(config.client_id, config.redirect_uri, state=state)
        parsed = urllib.parse.urlparse(config.redirect_uri)
        ssl_context = (
            ephemeral_server_context(parsed.hostname or "localhost")
            if parsed.scheme == "https"
            else None
        )
        # Bind BEFORE the browser opens: with a cached certificate/session the
        # redirect can arrive within a second (ANAF's codes expire in ~60s).
        try:
            listener = CallbackListener(
                config.redirect_uri, ssl_context=ssl_context, expected_state=state
            )
        except AnafConfigError as exc:
            return {
                "logged_in": False,
                "detail": str(exc),
                "next_step": "the callback port could not be bound (another "
                "login in progress, or the port is taken) — retry with the "
                f"user's go-ahead; {_CLI_FALLBACK}",
            }
        with listener:
            if not webbrowser.open(url):
                return {
                    "logged_in": False,
                    "detail": "no browser could be opened on this machine",
                    "authorize_url": url,
                    "next_step": f"{_CLI_FALLBACK} — it prints the URL to "
                    "visit by hand",
                }
            try:
                code = await asyncio.to_thread(listener.wait, timeout)
            except AnafAuthError as exc:
                return {
                    "logged_in": False,
                    "detail": str(exc),
                    "next_step": "ANAF reported the authorization as failed — "
                    "usually the user cancelled the certificate step; ask "
                    "what they saw, then retry with their go-ahead",
                }
        if code is None:
            return {
                "logged_in": False,
                "detail": f"no callback arrived within {timeout:.0f}s",
                "authorize_url": url,
                "next_step": "ask whether the browser opened and which page "
                "the user reached, then retry with their go-ahead; "
                f"{_CLI_FALLBACK}",
            }
        try:
            async with httpx2.AsyncClient(timeout=30.0) as http:
                tokens = await exchange_code(
                    http,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    code=code,
                    redirect_uri=config.redirect_uri,
                )
        except (AnafAuthError, AnafTransportError) as exc:
            return {
                "logged_in": False,
                "detail": f"the code exchange failed: {exc}",
                "next_step": "ANAF's codes expire in ~60 seconds — with the "
                "user's go-ahead call auth_login again for a fresh attempt",
            }
        # The shared store is the single source of truth: the long-lived
        # provider re-reads it on its next call, so no restart is needed.
        token_store(config).save(tokens)
        return {
            "logged_in": True,
            "status": ctx.auth_status().model_dump(mode="json"),
            "next_step": "authenticated — the e-Factura / e-Transport tools "
            "work immediately; the session refreshes headlessly for about a "
            "year",
        }
