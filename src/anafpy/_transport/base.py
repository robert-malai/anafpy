"""Shared transport concerns: environment + per-service base URLs.

Both services are reached over OAuth2 on the **same host** ``api.anaf.ro``; they differ
only by **path prefix** (``/FCTEL/rest`` vs ``/ETRANSPORT/ws/v1``). See
``docs/anaf-reference/{efactura,etransport}/api.md``.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["OAUTH_HOST", "Environment", "Service", "service_base_url"]

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
