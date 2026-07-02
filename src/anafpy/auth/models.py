"""Token model.

ANAF access tokens are JWTs valid 90 days; refresh tokens 365 days. Refresh **rotates**
the refresh token (a new access *and* refresh token come back), so both are persisted.
Expiry timestamps are **computed from the JWTs themselves** (cached per instance), so
the persisted store can never drift from the tokens it holds.
"""

from __future__ import annotations

import time
from functools import cached_property
from typing import Any

import jwt
from pydantic import BaseModel, Field, computed_field

__all__ = ["TokenSet"]

# Fallback lifetimes (s) if a JWT `exp` can't be read. Source: official OAuth PDF.
_ACCESS_TTL = 90 * 24 * 3600
_REFRESH_TTL = 365 * 24 * 3600


def _jwt_exp(token: str) -> float | None:
    """Best-effort read of a JWT's ``exp`` claim (epoch seconds), without verifying.

    Signature verification is ANAF's job server-side; here we only read ``exp`` to
    schedule refresh. Returns ``None`` for non-JWT or unparseable tokens.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        return None
    exp = payload.get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


class TokenSet(BaseModel):
    """An access/refresh token pair; expiries are derived from the JWT ``exp`` claims.

    Instances are treated as immutable: refresh rotation builds a *new* ``TokenSet``
    via :meth:`from_token_response`, which is what makes the cached expiry properties
    safe.
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    obtained_at: float = Field(default_factory=time.time)
    # Lifetime (s) from the token response, used only if the access JWT has no `exp`.
    expires_in: float | None = None

    # Computed expiries are serialized into the store (for human inspection) but
    # ignored on load. The `type: ignore`s are pydantic's documented workaround for
    # mypy's blanket "decorators on top of @property" limitation.
    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def access_expires_at(self) -> float:
        """Access expiry (epoch s): JWT ``exp``, else ``expires_in``, else 90 days."""
        exp = _jwt_exp(self.access_token)
        if exp is not None:
            return exp
        if self.expires_in:
            return self.obtained_at + self.expires_in
        return self.obtained_at + _ACCESS_TTL

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def refresh_expires_at(self) -> float:
        """Refresh expiry (epoch s): JWT ``exp``, else the documented 365 days."""
        return _jwt_exp(self.refresh_token) or (self.obtained_at + _REFRESH_TTL)

    @classmethod
    def from_token_response(
        cls, data: dict[str, Any], *, obtained_at: float | None = None
    ) -> TokenSet:
        """Build from ANAF's JSON token response (`access_token`, `refresh_token`)."""
        expires_in = data.get("expires_in")
        return cls(
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]),
            token_type=str(data.get("token_type", "Bearer")),
            obtained_at=obtained_at if obtained_at is not None else time.time(),
            expires_in=float(expires_in) if expires_in else None,
        )

    def access_expired(self, *, leeway: float = 300.0) -> bool:
        """True if the access token is expired (or within ``leeway`` seconds of it)."""
        return time.time() >= (self.access_expires_at - leeway)

    def refresh_expired(self) -> bool:
        """True if the refresh token has likely expired (re-auth required)."""
        return time.time() >= self.refresh_expires_at
