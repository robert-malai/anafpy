"""Exception hierarchy for anafpy.

Per the design: exceptions are raised for transport / auth / programming errors.
*Business* outcomes (e.g. an e-Factura ``nok`` rejection with its BR-RO findings) are
returned as typed values, never raised.
"""

from __future__ import annotations

__all__ = [
    "AnafAuthError",
    "AnafConfigError",
    "AnafDownloadExpiredError",
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


class AnafDownloadExpiredError(AnafResponseError):
    """The message left ANAF's 60-day download window — it can never be fetched.

    ``descarcare`` answers **HTTP 200** with the JSON note ``{"eroare":
    "Fisierul nu mai poate fi descarcat pentru ca a trecut perioada de 60 de
    zile in care este disponibil", …}`` (see
    ``docs/anaf-reference/efactura/api.md`` §4.1). This is **terminal**: the file
    is gone from the SPV, no retry can ever succeed, and a caller may safely stop
    asking for this id for good.

    Reachable in normal operation, not only through caller error: ``listaMesaje``
    and ``descarcare`` anchor their 60 days differently, so ANAF *lists* messages
    it then refuses to hand over. A first sync — or one catching up after a gap —
    with a 60-day lookback walks into the boundary band.

    Only the recognised wording raises this; every other non-ZIP ``descarcare``
    body (unknown id, malformed request) stays a plain
    :class:`AnafResponseError`, which is worth retrying or fixing.

    Attributes:
        message_id: the ``descarcare`` id that can no longer be downloaded, or
            ``None`` if the raiser had none to hand.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 200,
        body: str | None = None,
        message_id: str | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.message_id = message_id


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
