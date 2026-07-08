"""anafpy — typed Python clients for ANAF e-Factura, e-Transport, and the public
no-auth services (registries, financial statements)."""

from __future__ import annotations

from .exceptions import (
    AnafAuthError,
    AnafConfigError,
    AnafError,
    AnafRateLimitError,
    AnafResponseError,
    AnafTransportError,
)

__version__ = "0.2.0"

__all__ = [
    "AnafAuthError",
    "AnafConfigError",
    "AnafError",
    "AnafRateLimitError",
    "AnafResponseError",
    "AnafTransportError",
    "__version__",
]
