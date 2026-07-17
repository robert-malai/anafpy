"""Shared lifecycle and network-error translation for ANAF HTTP clients."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

from ..exceptions import AnafConfigError, AnafTransportError

__all__ = ["HttpClientBase"]


class HttpClientBase:
    """Own or accept one ``httpx.AsyncClient`` for an ANAF service.

    Service base URLs always end in ``/`` and callers use relative request
    paths. An owned client is constructed with the resolved service URL. An
    injected client is never mutated: one with a non-empty ``base_url`` is
    accepted as-is (the intentional test/proxy seam), while one with an
    empty ``base_url`` raises :class:`~anafpy.exceptions.AnafConfigError`
    at construction — silently stamping a service URL onto a caller-owned
    object would mis-route a second client sharing it.
    """

    def __init__(
        self,
        *,
        http: httpx.AsyncClient | None,
        base_url: str,
        timeout: float,
        auth: httpx.Auth | None = None,
        follow_redirects: bool = False,
        limits: httpx.Limits | None = None,
    ) -> None:
        resolved_base_url = f"{base_url.rstrip('/')}/"
        self._owns_http = http is None
        if http is None:
            kwargs: dict[str, Any] = {
                "base_url": resolved_base_url,
                "timeout": timeout,
                "follow_redirects": follow_redirects,
            }
            if auth is not None:
                kwargs["auth"] = auth
            if limits is not None:
                kwargs["limits"] = limits
            self._http = httpx.AsyncClient(**kwargs)
        else:
            if not str(http.base_url):
                raise AnafConfigError(
                    "the injected httpx client must be constructed with a "
                    f"base_url compatible with {resolved_base_url} — anafpy "
                    "sends relative paths and will not adopt or modify an "
                    "injected client's base_url"
                )
            self._http = http

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close only clients constructed by this instance."""
        if self._owns_http:
            await self._http.aclose()

    async def _request_http(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Issue one request and translate httpx network failures."""
        try:
            return await self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc
