"""Shared transport layer (environment, per-service base URLs)."""

from __future__ import annotations

from .base import OAUTH_HOST, Environment, Service, service_base_url

__all__ = ["OAUTH_HOST", "Environment", "Service", "service_base_url"]
