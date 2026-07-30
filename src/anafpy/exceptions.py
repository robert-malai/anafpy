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
    "AnafWafRejectionError",
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


class AnafWafRejectionError(AnafResponseError):
    """ANAF's web-application firewall refused the request *body*.

    The F5 fronting ANAF's hosts scans request bodies and answers its ``Request
    Rejected`` HTML page — **with HTTP 200** — when one matches an attack
    signature. Legitimate, ANAF-accepted invoices do: a relative path in
    ``xsi:schemaLocation`` reads as path traversal, ``;CP `` in an address reads
    as a shell command (see ``docs/anaf-reference/efactura/api.md`` §6). Raising
    keeps the block page from ever being mistaken for a result; it is ANAF's
    infrastructure refusing the call, not a verdict on the document.

    Attributes:
        support_id: the F5 incident id from the block page (quote it to ANAF),
            or ``None`` if the page carried none.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 200,
        body: str | None = None,
        support_id: str | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.support_id = support_id


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
