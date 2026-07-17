"""Shared lifecycle and network-error translation for ANAF HTTP clients."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

from ..exceptions import AnafTransportError

__all__ = ["HttpClientBase"]


class HttpClientBase:
    """Own or adopt one ``httpx.AsyncClient`` for an ANAF service.

    Service base URLs always end in ``/`` and callers use relative request
    paths. An injected client with an empty ``base_url`` adopts the service
    URL; a non-empty one is preserved as an intentional test/proxy seam.
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
            self._http = http
            if not str(self._http.base_url):
                self._http.base_url = httpx.URL(resolved_base_url)

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
