"""Async client for the RO e-Transport web services (``ETRANSPORT/ws/v1``).

Design mirrors ``anafpy.efactura.client`` with three key differences:
1. Upload path embeds ``standard``, ``cif``, and ``versiune`` as path segments
   (``POST /upload/ETRANSP/{cif}/{versiune}``), not query params; body is
   ``application/xml`` (e-Factura uses ``text/plain``).
2. Status uses a **path param** (``GET stareMesaj/{id_incarcare}``), not a query param.
3. **No download step** — the UIT code is returned in the upload response; state is
   tracked via ``lista`` / ``stareMesaj``.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_result,
    stop_after_delay,
    wait_exponential_jitter,
)

from .._transport.base import (
    Environment,
    Service,
    is_empty_result_message,
    service_base_url,
)
from ..auth.provider import AnafAuth, TokenProvider
from ..exceptions import (
    AnafConfigError,
    AnafRateLimitError,
    AnafResponseError,
    AnafTransportError,
)
from .models import (
    InfoItem,
    InfoList,
    MessageState,
    MessageStatus,
    Notification,
    UploadResult,
)

__all__ = ["ETransportClient"]

_STANDARD = "ETRANSP"
_XML_BODY_HEADERS = {"Content-Type": "application/xml"}


def _local(tag: str) -> str:
    """Strip any ``{namespace}`` prefix from an ElementTree tag."""
    return tag.rsplit("}", 1)[-1]


def _header_errors(root: ET.Element) -> list[str]:
    """Collect ``errorMessage`` values from ``<Errors>`` children of an ANAF header."""
    errors: list[str] = []
    for child in root.iter():
        if _local(child.tag) == "Errors":
            message = child.get("errorMessage")
            if message:
                errors.append(message)
    return errors


def _as_text(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


class ETransportClient:
    """Talks to ANAF e-Transport over OAuth2.

    Construct with an authenticated :class:`~anafpy.auth.provider.TokenProvider`; the
    client owns an ``httpx.AsyncClient`` (unless one is injected) and should be used as
    an async context manager so it is closed cleanly.
    """

    def __init__(
        self,
        provider: TokenProvider,
        *,
        environment: Environment = Environment.PROD,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = service_base_url(Service.ETRANSPORT, environment)
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(auth=AnafAuth(provider), timeout=timeout)

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
        if self._owns_http:
            await self._http.aclose()

    # -- transport -------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}/{path}"
        try:
            response = await self._http.request(
                method, url, params=params, content=content, headers=headers
            )
        except httpx.HTTPError as exc:
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc
        self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        body = _as_text(response.content)
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            retry_after = response.headers.get("Retry-After")
            raise AnafRateLimitError(
                retry_after=float(retry_after) if retry_after else None, body=body
            )
        raise AnafResponseError(
            f"ANAF returned HTTP {response.status_code}",
            status_code=response.status_code,
            body=body,
        )

    # -- operations ------------------------------------------------------------------

    async def upload(
        self,
        xml: str | bytes,
        *,
        cif: str,
        version: int = 2,
    ) -> UploadResult:
        """Submit a transport declaration XML for processing.

        Returns an :class:`UploadResult` whose ``upload_id`` feeds ``get_status`` and
        ``uit`` is the transport declaration code returned on acceptance.  A document
        rejected at submission comes back with ``accepted is False`` and ``errors``
        populated — not as an exception.
        """
        body = xml.encode("utf-8") if isinstance(xml, str) else xml
        path = f"upload/{_STANDARD}/{cif}/{version}"
        response = await self._request(
            "POST", path, content=body, headers=_XML_BODY_HEADERS
        )
        return self._parse_upload(response.content)

    @staticmethod
    def _parse_upload(body: bytes) -> UploadResult:
        root = ET.fromstring(body)
        upload_id = root.get("index_incarcare")
        uit = root.get("uit")
        errors = _header_errors(root)
        if upload_id is None and not errors:
            errors = [f"unrecognised upload response: {_as_text(body)[:200]}"]
        return UploadResult(upload_id=upload_id, uit=uit, errors=errors, raw=body)

    async def get_status(self, upload_id: str) -> MessageStatus:
        """Poll the processing state for an ``upload_id`` (``index_incarcare``)."""
        response = await self._request("GET", f"stareMesaj/{upload_id}")
        return self._parse_status(response.content)

    @staticmethod
    def _parse_status(body: bytes) -> MessageStatus:
        root = ET.fromstring(body)
        errors = _header_errors(root)
        raw_state = root.get("stare")
        if raw_state is None:
            if errors:
                return MessageStatus(
                    state=MessageState.REJECTED, errors=errors, raw=body
                )
            raise AnafResponseError(
                f"stareMesaj response missing `stare`: {_as_text(body)[:200]}",
                status_code=200,
                body=_as_text(body),
            )
        state = MessageState.from_raw(raw_state)
        return MessageStatus(state=state, errors=errors, raw=body)

    def list_notifications(self, *, days: int, cif: str) -> AsyncIterator[Notification]:
        """Iterate transport notifications from the last ``days`` (1-60) for ``cif``.

        Yields each :class:`Notification`; an empty window yields nothing. The
        ``lista`` endpoint is not paginated, so this is a single request under the hood.

        Consume with ``async for``. Raises :class:`AnafConfigError` for a bad ``days``
        (eagerly), and :class:`AnafResponseError` if ANAF reports a genuine list error
        (a benign "no notifications" note yields an empty iterator instead).
        """
        if not 1 <= days <= 60:
            raise AnafConfigError("list_notifications: `days` must be between 1 and 60")
        return self._iter_notifications(days, cif)

    async def _iter_notifications(
        self, days: int, cif: str
    ) -> AsyncIterator[Notification]:
        response = await self._request("GET", f"lista/{days}/{cif}")
        for notification in self._parse_notifications(response.content):
            yield notification

    @staticmethod
    def _parse_notifications(body: bytes) -> list[Notification]:
        """Parse a ``lista`` response to notifications.

        Raises :class:`AnafResponseError` when ANAF's ``eroare`` is a real error; a
        benign "no notifications" note returns an empty list.
        """
        data = json.loads(body)
        if isinstance(data, list):
            raw_items = data
        else:
            raw_items = (
                data.get("found")
                or data.get("notificari")
                or data.get("declaratii")
                or []
            )
            error = data.get("eroare") or data.get("error")
            if not raw_items and error is not None:
                if is_empty_result_message(str(error)):
                    return []
                raise AnafResponseError(
                    f"ANAF e-Transport list error: {error}",
                    status_code=200,
                    body=_as_text(body),
                )
        return [Notification.model_validate(item) for item in raw_items]

    async def info(
        self,
        *,
        cui_op: str,
        cui_decl: str | None = None,
        uit: str | None = None,
        ref_decl: str | None = None,
    ) -> InfoList:
        """Look up active notifications where ``cui_op`` is the transport organizer."""
        params: dict[str, str] = {"cui_op": cui_op}
        if cui_decl is not None:
            params["cui_decl"] = cui_decl
        if uit is not None:
            params["uit"] = uit
        if ref_decl is not None:
            params["ref_decl"] = ref_decl
        response = await self._request("GET", "info", params=params)
        return self._parse_info(response.content)

    @staticmethod
    def _parse_info(body: bytes) -> InfoList:
        data = json.loads(body)
        if isinstance(data, list):
            raw_items = data
            error = None
        else:
            raw_items = (
                data.get("found") or data.get("items") or data.get("notificari") or []
            )
            error = data.get("eroare") or data.get("error")
        items = [InfoItem.model_validate(item) for item in raw_items]
        return InfoList(
            items=items,
            error=str(error) if error is not None else None,
            raw=body,
        )

    async def upload_and_wait(
        self,
        xml: str | bytes,
        *,
        cif: str,
        version: int = 2,
        timeout: float = 300.0,
        initial_wait: float = 2.0,
        max_wait: float = 30.0,
    ) -> MessageStatus:
        """Upload, then poll ``get_status`` until a terminal state or ``timeout``.

        Raises :class:`TimeoutError` if the declaration is still processing when the
        budget is exhausted. A ``nok`` or rejected result is returned, not raised.
        """
        result = await self.upload(xml, cif=cif, version=version)
        if not result.accepted or result.upload_id is None:
            return MessageStatus(
                state=MessageState.REJECTED, errors=result.errors, raw=result.raw
            )
        upload_id = result.upload_id

        last: MessageStatus | None = None
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_result(lambda s: s.is_processing),
                wait=wait_exponential_jitter(initial=initial_wait, max=max_wait),
                stop=stop_after_delay(timeout),
                reraise=True,
            ):
                with attempt:
                    last = await self.get_status(upload_id)
                if not attempt.retry_state.outcome.failed:  # type: ignore[union-attr]
                    attempt.retry_state.set_result(last)
        except RetryError as exc:
            raise TimeoutError(
                f"e-Transport upload {upload_id} still processing after {timeout}s"
            ) from exc
        assert last is not None
        return last
