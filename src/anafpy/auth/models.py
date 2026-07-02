"""Token model.

ANAF access tokens are JWTs valid 90 days; refresh tokens 365 days. Refresh **rotates**
the refresh token (a new access *and* refresh token come back), so both are persisted.
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["TokenSet"]

# Fallback lifetimes (s) if a JWT `exp` can't be read. Source: official OAuth PDF.
_ACCESS_TTL = 90 * 24 * 3600
_REFRESH_TTL = 365 * 24 * 3600


def _jwt_exp(token: str) -> float | None:
    """Best-effort read of a JWT's ``exp`` claim (epoch seconds), without verifying.

    Signature verification is ANAF's job server-side; here we only read ``exp`` to
    schedule refresh. Returns ``None`` for non-JWT or unparseable tokens.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_b64 = parts[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # pad to a multiple of 4
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except (binascii.Error, ValueError):
        return None
    exp = payload.get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


class TokenSet(BaseModel):
    """An access/refresh token pair plus computed expiry timestamps."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    obtained_at: float = Field(default_factory=time.time)
    access_expires_at: float | None = None
    refresh_expires_at: float | None = None

    @classmethod
    def from_token_response(
        cls, data: dict[str, Any], *, obtained_at: float | None = None
    ) -> TokenSet:
        """Build from ANAF's JSON token response (`access_token`, `refresh_token`)."""
        now = obtained_at if obtained_at is not None else time.time()
        access = str(data["access_token"])
        refresh = str(data["refresh_token"])
        # Prefer the JWT `exp`; else `expires_in`, then the documented 90-day TTL.
        access_exp = _jwt_exp(access)
        if access_exp is None:
            expires_in = data.get("expires_in")
            access_exp = now + float(expires_in) if expires_in else now + _ACCESS_TTL
        return cls(
            access_token=access,
            refresh_token=refresh,
            token_type=str(data.get("token_type", "Bearer")),
            obtained_at=now,
            access_expires_at=access_exp,
            # Same preference for the refresh token: its JWT `exp`, else the
            # documented 365-day TTL.
            refresh_expires_at=_jwt_exp(refresh) or now + _REFRESH_TTL,
        )

    def access_expired(self, *, leeway: float = 300.0) -> bool:
        """True if the access token is expired (or within ``leeway`` seconds of it)."""
        if self.access_expires_at is None:
            return False
        return time.time() >= (self.access_expires_at - leeway)

    def refresh_expired(self) -> bool:
        """True if the refresh token has likely expired (re-auth required)."""
        if self.refresh_expires_at is None:
            return False
        return time.time() >= self.refresh_expires_at
