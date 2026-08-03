"""Shared transport concerns: environment, per-service base URLs, error raising.

Both OAuth services are reached on the **same host** ``api.anaf.ro``; they differ
only by **path prefix** (``/FCTEL/rest`` vs ``/ETRANSPORT/ws/v1``). See
``docs/anaf-reference/{efactura,etransport}/api.md``.

The unauthenticated public services (registries, financial statements) live on a
different host, ``webservicesp.anaf.ro``, with **no test/prod split** — so
:data:`PUBLIC_HOST` sits outside the :func:`service_base_url` scheme. See
``docs/anaf-reference/public/api.md``.

:func:`raise_for_status` and :func:`as_text` implement the error half of the hybrid
model shared by all clients: non-success HTTP raises (429 as
:class:`~anafpy.exceptions.AnafRateLimitError` with ``retry_after``); business
outcomes are the clients' job to return as values.
:func:`raise_for_waf_rejection` covers the case that is neither — ANAF's firewall
answering its block page *with HTTP 200*.
"""

from __future__ import annotations

import re
import time
import unicodedata
from datetime import datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Self
from zoneinfo import ZoneInfo

import httpx2

from ..exceptions import (
    AnafConfigError,
    AnafRateLimitError,
    AnafResponseError,
    AnafWafRejectionError,
)

__all__ = [
    "OAUTH_HOST",
    "PUBLIC_HOST",
    "ROMANIA_TZ",
    "DescribedStrEnum",
    "Environment",
    "Service",
    "as_text",
    "is_download_expired_message",
    "is_empty_result_message",
    "normalize_cui",
    "raise_for_status",
    "raise_for_waf_rejection",
    "request_moment_from_message",
    "retry_after_seconds",
    "service_base_url",
    "strip_accents",
]

#: ANAF's clock. "Today"/"now" *defaults* (a registry query's as-of date, a vehicle
#: change's timestamp) are ANAF-semantic values, so they are computed in Romania's
#: timezone rather than the machine's. Caller-supplied values are never converted.
ROMANIA_TZ = ZoneInfo("Europe/Bucharest")

#: OAuth2 API host for both services (the cert-direct host ``webserviceapl.anaf.ro`` is
#: intentionally not used by anafpy).
OAUTH_HOST = "https://api.anaf.ro"

#: Host of the unauthenticated public services (registries, financial statements).
#: Production only — ANAF exposes no TEST variant for these.
PUBLIC_HOST = "https://webservicesp.anaf.ro"


class DescribedStrEnum(StrEnum):
    """String enum whose members carry a required English description."""

    description: str

    def __new__(cls, value: str, description: str) -> Self:
        member = str.__new__(cls, value)
        member._value_ = value
        member.description = description
        return member


class Environment(StrEnum):
    """ANAF API environment."""

    TEST = "test"
    PROD = "prod"


class Service(StrEnum):
    """Path prefixes per ANAF service (under the OAuth host)."""

    EFACTURA = "FCTEL/rest"
    ETRANSPORT = "ETRANSPORT/ws/v1"


def service_base_url(service: Service, environment: Environment) -> str:
    """Return e.g. ``https://api.anaf.ro/test/FCTEL/rest``."""
    return f"{OAUTH_HOST}/{environment.value}/{service.value}"


def normalize_cui(value: str | int) -> str:
    """Return a fiscal code as digits, tolerating the Romanian ``RO`` prefix.

    The string form deliberately preserves leading zeroes. Service-specific
    callers may impose additional constraints (for example, public lookups
    convert to a positive integer).
    """
    text = str(value).strip().upper().removeprefix("RO").strip()
    if not text.isdigit():
        raise AnafConfigError(f"invalid CUI: {value!r} (digits expected)")
    return text


def retry_after_seconds(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header into seconds.

    RFC 9110 allows either a delay in seconds or an HTTP-date; an unparseable
    value yields ``None`` rather than masking the rate-limit error it decorates.
    """
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        delay = parsedate_to_datetime(value).timestamp() - time.time()
    except ValueError:
        return None
    return max(delay, 0.0)


def as_text(body: bytes) -> str:
    """Decode a response body for diagnostics (lossy — replacement characters)."""
    return body.decode("utf-8", errors="replace")


def raise_for_status(response: httpx2.Response) -> None:
    """Raise the anafpy error for a non-success response; a no-op on success.

    HTTP 429 raises :class:`~anafpy.exceptions.AnafRateLimitError` carrying
    ``retry_after``; anything else non-success raises
    :class:`~anafpy.exceptions.AnafResponseError`. No auto-backoff — per the
    design, the caller decides how to retry.
    """
    if response.is_success:
        return
    body = as_text(response.content)
    if response.status_code == httpx2.codes.TOO_MANY_REQUESTS:
        raise AnafRateLimitError(
            retry_after=retry_after_seconds(response.headers.get("Retry-After")),
            body=body,
        )
    raise AnafResponseError(
        f"ANAF returned HTTP {response.status_code}",
        status_code=response.status_code,
        body=body,
    )


#: The F5 block page's own wording — no ANAF payload contains it, on any host.
_WAF_REJECTION_MARKER = b"The requested URL was rejected"
_WAF_SUPPORT_ID = re.compile(rb"support ID is:\s*([\w-]+)", re.IGNORECASE)
#: Only the head of a body is scanned: the block page is ~250 bytes, while a
#: legitimate body can be a multi-megabyte ZIP.
_WAF_SCAN_BYTES = 4096


def raise_for_waf_rejection(response: httpx2.Response) -> None:
    """Raise when ANAF's firewall answered its block page instead of a payload.

    The page arrives as ``text/html`` **with HTTP 200** (live-confirmed
    2026-07-30 on ``transformare``), so nothing else in the stack would notice it
    — a caller would write an HTML file with a ``.pdf`` extension. A no-op on
    every real response; see :class:`~anafpy.exceptions.AnafWafRejectionError`.
    """
    head = response.content[:_WAF_SCAN_BYTES]
    if _WAF_REJECTION_MARKER not in head:
        return
    match = _WAF_SUPPORT_ID.search(head)
    support_id = match.group(1).decode() if match else None
    quoted = f" (support ID {support_id})" if support_id else ""
    raise AnafWafRejectionError(
        f"ANAF's firewall rejected the request body{quoted}: the content matched "
        "an attack signature. This is infrastructure refusing the call, not an "
        "ANAF verdict on the document.",
        status_code=response.status_code,
        body=as_text(head),
        support_id=support_id,
    )


#: Substrings (accent-stripped, casefolded) that mark an ANAF list ``eroare`` as a
#: benign "no results in this window" note rather than a real fault. ANAF overloads the
#: same ``eroare`` field for both, so the wording is the only signal; extend as needed.
_EMPTY_RESULT_MARKERS = (
    "nu exista mesaje",
    "nu sunt mesaje",
    "nu exista facturi",
    "nu exista notificari",
    "nu exista inregistrari",
    "nu exista date",
    "nu exista informatii",  # e-Transport `info` no-results (live-confirmed 2026-07-02)
)


def strip_accents(text: str) -> str:
    """``text`` casefolded with combining marks stripped — ANAF's Romanian wire
    texts arrive both with and without diacritics, so matching happens on the
    folded form."""
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    ).casefold()


def is_empty_result_message(text: str) -> bool:
    """True when an ANAF list ``eroare`` string denotes *no results* (empty window),
    not a genuine error (bad CIF/interval). Matched accent-insensitively."""
    normalized = strip_accents(text)
    return any(marker in normalized for marker in _EMPTY_RESULT_MARKERS)


#: The stable core (accent-stripped) of ANAF's "past the 60-day download window" note,
#: observed as ``"Fisierul nu mai poate fi descarcat pentru ca a trecut perioada de 60
#: de zile in care este disponibil"``. Deliberately just the clause that carries the
#: terminal meaning — ANAF rewords the rest — and deliberately *narrow*: recognising
#: this lets a caller stop retrying for good, so a false positive is worse than a miss.
_DOWNLOAD_EXPIRED_MARKER = "nu mai poate fi descarcat"


def is_download_expired_message(text: str) -> bool:
    """True when an ANAF ``eroare`` string says the file aged out of the 60-day
    download window — a *terminal* condition, not a transient one. Matched
    accent-insensitively, on whitespace-collapsed text."""
    return _DOWNLOAD_EXPIRED_MARKER in " ".join(strip_accents(text).split())


#: ANAF's own clock, as the e-Factura list endpoint's window faults quote it:
#: ``"endTime = 30-07-2026 15:15:28 nu poate in viitor fata de momentul requestului =
#: 30-07-2026 15:15:27"`` (field-observed 2026-07-30 — a one-second disagreement
#: between the caller's clock and ANAF's was enough to fail the whole listing).
#: The value is required: the swagger's own examples of the same faults state the
#: phrase *without* one (reference §3b), and a phrase with nothing to read is not a
#: correction. ``DD-MM-YYYY HH:MM:SS``, Romania wall time — never UTC, and never the
#: caller's zone.
_REQUEST_MOMENT = re.compile(
    r"momentul requestului\s*=\s*(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})"
)


def request_moment_from_message(text: str) -> datetime | None:
    """ANAF's clock at request time, parsed out of an ``eroare`` that quotes it.

    ``None`` when the note carries no such value — the caller then keeps whatever
    error handling it already had. Narrow like its siblings above: only the
    ``momentul requestului = <timestamp>`` form is read, and only as a
    :data:`ROMANIA_TZ` wall time, since reading it as UTC would shift a corrected
    window by the offset — three hours in summer.
    """
    match = _REQUEST_MOMENT.search(" ".join(strip_accents(text).split()))
    if match is None:
        return None
    try:
        moment = datetime.strptime(match.group(1), "%d-%m-%Y %H:%M:%S")
    except ValueError:  # a well-formed-looking but impossible date (32-13-2026)
        return None
    return moment.replace(tzinfo=ROMANIA_TZ)
