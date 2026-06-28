"""Async client for the RO e-Factura web services (``FCTEL/rest``).

Design (see ``DESIGN.md`` §4): discrete 1:1 methods are the primary surface and do **no
transport retry** — a single call, one result-or-raise — so a non-idempotent ``upload``
is never silently repeated. ``upload_and_wait`` is the only place that loops, polling
the processing state with ``tenacity``. HTTP/auth failures raise; business outcomes
(``nok``, upload rejections) are returned as values.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
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

from .._transport.base import Environment, Service, service_base_url
from ..auth.provider import AnafAuth, TokenProvider
from ..exceptions import AnafRateLimitError, AnafResponseError, AnafTransportError
from .models import (
    DownloadedMessage,
    Filter,
    MessageList,
    MessageListItem,
    MessageState,
    MessageStatus,
    TransformStandard,
    UploadResult,
    UploadStandard,
)

__all__ = ["EFacturaClient"]

# ANAF wants the XML payload as a raw text/plain body (per the API PDF), despite it
# being XML.
_XML_BODY_HEADERS = {"Content-Type": "text/plain"}


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


class EFacturaClient:
    """Talks to ANAF e-Factura over OAuth2.

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
        self._base_url = service_base_url(Service.EFACTURA, environment)
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
        except httpx.HTTPError as exc:  # connect/read/timeout/etc.
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
        standard: UploadStandard = UploadStandard.UBL,
        extern: bool = False,
        autofactura: bool = False,
        executare: bool = False,
        b2c: bool = False,
    ) -> UploadResult:
        """Submit an invoice/credit-note/message XML for processing.

        Returns an :class:`UploadResult` whose ``upload_id`` feeds ``get_status``. A
        document rejected at submission comes back with ``accepted is False`` and
        ``errors`` populated — not as an exception.
        """
        params = {"standard": standard.value, "cif": cif}
        if extern:
            params["extern"] = "DA"
        if autofactura:
            params["autofactura"] = "DA"
        if executare:
            params["executare"] = "DA"
        body = xml.encode("utf-8") if isinstance(xml, str) else xml
        path = "uploadb2c" if b2c else "upload"
        response = await self._request(
            "POST", path, params=params, content=body, headers=_XML_BODY_HEADERS
        )
        return self._parse_upload(response.content)

    @staticmethod
    def _parse_upload(body: bytes) -> UploadResult:
        root = ET.fromstring(body)
        upload_id = root.get("index_incarcare") or root.get("index_descarcare")
        errors = _header_errors(root)
        if upload_id is None and not errors:
            # Be explicit rather than silently returning an empty result.
            errors = [f"unrecognised upload response: {_as_text(body)[:200]}"]
        return UploadResult(upload_id=upload_id, errors=errors, raw=body)

    async def get_status(self, upload_id: str) -> MessageStatus:
        """Poll the processing state for an ``upload_id`` (``index_incarcare``)."""
        response = await self._request(
            "GET", "stareMesaj", params={"id_incarcare": upload_id}
        )
        return self._parse_status(response.content)

    @staticmethod
    def _parse_status(body: bytes) -> MessageStatus:
        root = ET.fromstring(body)
        errors = _header_errors(root)
        raw_state = root.get("stare")
        if raw_state is None:
            # No `stare` but errors present => rejected at upload time.
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
        download_id = root.get("id_descarcare")
        return MessageStatus(
            state=state, download_id=download_id, errors=errors, raw=body
        )

    async def download(self, message_id: str) -> DownloadedMessage:
        """Download the ZIP (signed invoice/errors + MF signature) for a message id."""
        response = await self._request("GET", "descarcare", params={"id": message_id})
        return DownloadedMessage.from_zip(response.content)

    async def list_messages(
        self, *, days: int, cif: str, filter: Filter | None = None
    ) -> MessageList:
        """List messages from the last ``days`` (1-60) for ``cif``."""
        params = {"zile": str(days), "cif": cif}
        if filter is not None:
            params["filtru"] = filter.value
        response = await self._request("GET", "listaMesajeFactura", params=params)
        return self._parse_list(response.content)

    async def list_messages_paged(
        self,
        *,
        start_ms: int,
        end_ms: int,
        cif: str,
        page: int = 1,
        filter: Filter | None = None,
    ) -> MessageList:
        """List messages in a time range (unix-millisecond bounds), one page."""
        params = {
            "startTime": str(start_ms),
            "endTime": str(end_ms),
            "cif": cif,
            "pagina": str(page),
        }
        if filter is not None:
            params["filtru"] = filter.value
        response = await self._request(
            "GET", "listaMesajePaginatieFactura", params=params
        )
        return self._parse_list(response.content)

    @staticmethod
    def _parse_list(body: bytes) -> MessageList:
        data = json.loads(body)
        raw_messages = data.get("mesaje") or []
        messages = [MessageListItem.from_json(m) for m in raw_messages]
        error = data.get("eroare")
        return MessageList(
            messages=messages,
            error=str(error) if error is not None else None,
            raw=body,
        )

    async def to_pdf(
        self,
        xml: str | bytes,
        *,
        standard: TransformStandard = TransformStandard.INVOICE,
        validate: bool = True,
    ) -> bytes:
        """Render invoice XML to a PDF (``transformare``). ``validate=False`` skips
        ANAF's validation (it then does not guarantee the PDF)."""
        body = xml.encode("utf-8") if isinstance(xml, str) else xml
        path = f"transformare/{standard.value}"
        if not validate:
            path += "/DA"
        response = await self._request(
            "POST", path, content=body, headers=_XML_BODY_HEADERS
        )
        return response.content

    async def upload_and_wait(
        self,
        xml: str | bytes,
        *,
        cif: str,
        standard: UploadStandard = UploadStandard.UBL,
        timeout: float = 300.0,
        initial_wait: float = 2.0,
        max_wait: float = 30.0,
        **upload_kwargs: bool,
    ) -> MessageStatus:
        """Upload, then poll ``get_status`` until a terminal state or ``timeout``.

        Raises :class:`TimeoutError` if the document is still processing when the budget
        is exhausted. A ``nok`` result is returned, not raised.
        """
        result = await self.upload(xml, cif=cif, standard=standard, **upload_kwargs)
        if not result.accepted or result.upload_id is None:
            return MessageStatus(
                state=MessageState.REJECTED, errors=result.errors, raw=result.raw
            )
        upload_id = result.upload_id

        # Only the processing state is retried; any HTTP/auth exception propagates
        # immediately (reraise=True), keeping the "single transparent call" contract.
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
                # set_result drives the result-based retry; it must run after the
                # `with` block so the attempt's outcome is recorded first.
                if not attempt.retry_state.outcome.failed:  # type: ignore[union-attr]
                    attempt.retry_state.set_result(last)
        except RetryError as exc:
            raise TimeoutError(
                f"e-Factura upload {upload_id} still processing after {timeout}s"
            ) from exc
        assert last is not None
        return last
