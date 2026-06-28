"""Shared transport concerns: environment + per-service base URLs.

Both services are reached over OAuth2 on the **same host** ``api.anaf.ro``; they differ
only by **path prefix** (``/FCTEL/rest`` vs ``/ETRANSPORT/ws/v1``). See
``docs/anaf-reference/{efactura,etransport}/api.md``.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum

__all__ = [
    "OAUTH_HOST",
    "Environment",
    "Service",
    "is_empty_result_message",
    "service_base_url",
]

#: OAuth2 API host for both services (the cert-direct host ``webserviceapl.anaf.ro`` is
#: intentionally not used by anafpy).
OAUTH_HOST = "https://api.anaf.ro"


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
)


def is_empty_result_message(text: str) -> bool:
    """True when an ANAF list ``eroare`` string denotes *no results* (empty window),
    not a genuine error (bad CIF/interval). Matched accent-insensitively."""
    normalized = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    ).casefold()
    return any(marker in normalized for marker in _EMPTY_RESULT_MARKERS)
