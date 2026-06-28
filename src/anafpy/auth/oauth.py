"""ANAF OAuth2 endpoints and operations.

Verified against the official OAuth procedure PDF and a live probe (2026-06-28):
client auth is **HTTP Basic** (client_id:client_secret); ``token_content_type`` is
``jwt`` (query for /authorize, body for /token); refresh is **headless** (no
certificate). See ``docs/anaf-reference/oauth/authentication.md``.
"""

from __future__ import annotations

import urllib.parse

import httpx

from ..exceptions import AnafAuthError, AnafTransportError
from .models import TokenSet

__all__ = [
    "AUTHORIZE_URL",
    "REVOKE_URL",
    "TOKEN_URL",
    "build_authorize_url",
    "exchange_code",
    "refresh_tokens",
]

AUTHORIZE_URL = "https://logincert.anaf.ro/anaf-oauth2/v1/authorize"
TOKEN_URL = "https://logincert.anaf.ro/anaf-oauth2/v1/token"
REVOKE_URL = "https://logincert.anaf.ro/anaf-oauth2/v1/revoke"


def build_authorize_url(
    client_id: str, redirect_uri: str, *, state: str | None = None
) -> str:
    """Build the browser authorization URL (the cert step happens here)."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "token_content_type": "jwt",
    }
    if state is not None:
        params["state"] = state
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def _post_token(
    http: httpx.AsyncClient,
    client_id: str,
    client_secret: str,
    data: dict[str, str],
) -> TokenSet:
    data = {**data, "token_content_type": "jwt"}
    try:
        resp = await http.post(
            TOKEN_URL,
            data=data,
            auth=httpx.BasicAuth(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    except httpx.HTTPError as exc:  # connection/timeout
        raise AnafTransportError(f"token request failed: {exc}") from exc

    if resp.status_code != httpx.codes.OK:
        # ANAF returns OAuth error JSON, e.g. {"error":"invalid_grant", ...}.
        detail = resp.text
        try:
            payload = resp.json()
            detail = payload.get("error_description") or payload.get("error") or detail
        except ValueError:
            pass
        raise AnafAuthError(
            f"token endpoint returned HTTP {resp.status_code}: {detail}"
        )

    return TokenSet.from_token_response(resp.json())


async def exchange_code(
    http: httpx.AsyncClient,
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> TokenSet:
    """Exchange an authorization ``code`` for a token set (no certificate needed)."""
    return await _post_token(
        http,
        client_id,
        client_secret,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )


async def refresh_tokens(
    http: httpx.AsyncClient,
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> TokenSet:
    """Get a fresh token set from a refresh token (headless; rotates refresh token)."""
    return await _post_token(
        http,
        client_id,
        client_secret,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
