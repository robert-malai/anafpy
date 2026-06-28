"""Exception hierarchy for anafpy.

Per the design: exceptions are raised for transport / auth / programming errors.
*Business* outcomes (e.g. an e-Factura ``nok`` rejection with its BR-RO findings) are
returned as typed values, never raised.
"""

from __future__ import annotations

__all__ = [
    "AnafAuthError",
    "AnafConfigError",
    "AnafError",
    "AnafRateLimitError",
    "AnafResponseError",
    "AnafTransportError",
]


class AnafError(Exception):
    """Base class for every error raised by anafpy."""


class AnafConfigError(AnafError):
    """Invalid or missing configuration (credentials, paths, parameters)."""


class AnafAuthError(AnafError):
    """OAuth/authentication failure (bad credentials, expired refresh token, ...)."""


class AnafTransportError(AnafError):
    """A network-level failure talking to ANAF (connection, timeout, ...)."""


class AnafResponseError(AnafTransportError):
    """ANAF returned a non-success HTTP status.

    Attributes:
        status_code: the HTTP status code.
        body: the (decoded) response body, if any, for diagnostics.
    """

    def __init__(
        self, message: str, *, status_code: int, body: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AnafRateLimitError(AnafResponseError):
    """HTTP 429 — ANAF's rate limit (1000 req/min) was exceeded.

    The client does not auto-retry; it surfaces ``retry_after`` (seconds) so the
    caller can decide how to back off.
    """

    def __init__(
        self,
        message: str = "ANAF rate limit exceeded (429)",
        *,
        retry_after: float | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message, status_code=429, body=body)
        self.retry_after = retry_after
