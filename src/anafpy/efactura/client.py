"""Async client for the RO e-Factura web services (``FCTEL/rest``).

Design (see ``DESIGN.md`` §4): discrete 1:1 methods are the primary surface and
do **no transport retry** — a single call, one result-or-raise — so a non-idempotent
``upload`` is never silently repeated. ``upload_and_wait`` is the only place that
loops, polling the processing state with ``tenacity``. HTTP/auth failures raise;
business outcomes (``nok``, upload rejections) are returned as values.

Outbound documents arrive two ways: ``upload`` takes complete UBL XML exported by
the caller's invoicing software (the strongly recommended path when such software
exists — ANAF's SPV purges filed messages after ~60 days, so the upstream system
is what keeps the durable record), and ``upload_invoice`` composes one from the
flat authoring models (:mod:`anafpy.efactura.authoring`) for callers with no
upstream system, who then own archiving the signed downloads.

The stateless document services ``validare`` and ``transformare`` are **public,
no-auth, prod-only** and live on :class:`anafpy.public.client.PublicClient`
(``validate_invoice`` / ``render_invoice_pdf``); only the MF signature check
(``validate_signature``, on the OAuth host) stays here.
"""

from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_result,
    stop_after_delay,
    wait_exponential_jitter,
)

from .._transport.base import (
    OAUTH_HOST,
    Environment,
    Service,
    as_text,
    is_empty_result_message,
    raise_for_status,
    service_base_url,
)
from .._transport.http import HttpClientBase
from ..auth.provider import AnafAuth, TokenProvider
from ..exceptions import (
    AnafConfigError,
    AnafResponseError,
)
from .authoring import DocumentKind, InvoiceDocument, render_invoice
from .models import (
    DownloadedMessage,
    Filter,
    MessageListItem,
    MessageState,
    MessageStatus,
    SignatureValidationResult,
    UploadResult,
    UploadStandard,
)

__all__ = ["EFacturaClient"]

# ANAF wants the XML payload as a raw text/plain body (per the API PDF), despite it
# being XML.
_XML_BODY_HEADERS = {"Content-Type": "text/plain"}

# Defensive upper bound on pages walked by ``list_messages``: a server that never
# returns an empty/terminal page raises rather than silently truncating the list.
_MAX_LIST_PAGES = 10_000
# The paginated response's total-page field (per the vendored lista swagger); honoured
# only when present — the empty-page stop is the real terminator.
_PAGE_COUNT_KEY = "numar_total_pagini"


def _to_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _resolve_window(
    days: int | None, start: datetime | None, end: datetime | None
) -> tuple[int, int]:
    """Normalise the requested window to a ``(start_ms, end_ms)`` pair.

    Exactly one of ``days`` (1-60) or both ``start`` and ``end`` must be given.
    The range form mirrors ANAF's own documented rules for
    ``listaMesajePaginatieFactura`` (the lista swagger's error catalog): ``end``
    not before ``start``, ``end`` not in the future, and ``start`` at most 60
    days before the request — ANAF retains e-Factura messages for 60 days, so
    an older window can never match anything.
    """
    has_days = days is not None
    has_range = start is not None or end is not None
    if has_days and has_range:
        raise AnafConfigError(
            "list_messages: pass either `days` or `start`+`end`, not both"
        )
    if has_days:
        assert days is not None
        if not 1 <= days <= 60:
            raise AnafConfigError("list_messages: `days` must be between 1 and 60")
        end_ms = int(time.time() * 1000)
        return end_ms - days * 86_400_000, end_ms
    if start is not None and end is not None:
        start_ms, end_ms = _to_ms(start), _to_ms(end)
        now_ms = int(time.time() * 1000)
        if end_ms < start_ms:
            raise AnafConfigError("list_messages: `end` cannot be before `start`")
        if end_ms > now_ms:
            raise AnafConfigError("list_messages: `end` cannot be in the future")
        if start_ms < now_ms - 60 * 86_400_000:
            raise AnafConfigError(
                "list_messages: `start` cannot be older than 60 days — ANAF "
                "retains e-Factura messages for 60 days"
            )
        return start_ms, end_ms
    raise AnafConfigError("list_messages: pass `days` or both `start` and `end`")


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


def _parse_xml_header(body: bytes, operation: str) -> ET.Element:
    """Parse an XML ``<header>`` response body.

    A 200 body that is not XML at all (an HTML error page, a gateway response)
    raises :class:`AnafResponseError` — in the AnafError hierarchy, like every
    other unrecognised-shape path.
    """
    try:
        return ET.fromstring(body)
    except ET.ParseError as exc:
        raise AnafResponseError(
            f"unrecognised {operation} response: {as_text(body)[:200]}",
            status_code=200,
            body=as_text(body),
        ) from exc


class EFacturaClient(HttpClientBase):
    """Talks to ANAF e-Factura over OAuth2.

    Construct with an authenticated :class:`~anafpy.auth.provider.TokenProvider`; the
    client owns an ``httpx.AsyncClient`` (unless one is injected — it must then
    carry :class:`~anafpy.auth.oauth.AnafAuth`; an empty injected ``base_url``
    adopts this service's URL, while a non-empty one is preserved) and should
    be used as an async context manager so it is closed cleanly.
    """

    def __init__(
        self,
        provider: TokenProvider,
        *,
        environment: Environment = Environment.PROD,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            http=http,
            base_url=service_base_url(Service.EFACTURA, environment),
            timeout=timeout,
            auth=AnafAuth(provider),
        )

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
        response = await self._request_http(
            method, path, params=params, content=content, headers=headers
        )
        raise_for_status(response)
        return response

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
        root = _parse_xml_header(body, "upload")
        # `index_incarcare` is the only success attribute the upload swagger
        # documents; anything else falls through to the explicit-error path below.
        upload_id = root.get("index_incarcare")
        errors = _header_errors(root)
        if upload_id is None and not errors:
            # Be explicit rather than silently returning an empty result.
            errors = [f"unrecognised upload response: {as_text(body)[:200]}"]
        return UploadResult(upload_id=upload_id, errors=errors, raw=body)

    async def upload_invoice(
        self,
        document: InvoiceDocument,
        *,
        cif: str,
        skip_validation: bool = False,
        **upload_kwargs: bool,
    ) -> UploadResult:
        """Compose an authored :class:`~anafpy.efactura.authoring.InvoiceDocument`
        and submit it — filing without upstream invoicing software.

        Renders the flat document to CIUS-RO UBL (totals and the VAT breakdown are
        computed unless supplied explicitly) and uploads it with the ``standard``
        matching :attr:`~anafpy.efactura.authoring.InvoiceDocument.kind` (``UBL``
        for an invoice, ``CN`` for a credit note). The translated EN 16931 +
        CIUS-RO rule set runs first and raises
        :class:`~anafpy.efactura.authoring.InvoiceValidationError` on fatal
        findings; pass ``skip_validation=True`` to let ANAF be the only judge.
        Callers with ready-made XML from their invoicing software keep using
        :meth:`upload` — that path stays the recommendation when an upstream
        system exists.

        Extra boolean flags (``autofactura``, ``extern``, ``executare``, ``b2c``)
        pass through to :meth:`upload`.
        """
        xml = render_invoice(document, skip_validation=skip_validation)
        standard = (
            UploadStandard.CN
            if document.kind is DocumentKind.CREDIT_NOTE
            else UploadStandard.UBL
        )
        return await self.upload(xml, cif=cif, standard=standard, **upload_kwargs)

    async def get_status(self, upload_id: str) -> MessageStatus:
        """Poll the processing state for an ``upload_id`` (``index_incarcare``)."""
        response = await self._request(
            "GET", "stareMesaj", params={"id_incarcare": upload_id}
        )
        return self._parse_status(response.content)

    @staticmethod
    def _parse_status(body: bytes) -> MessageStatus:
        root = _parse_xml_header(body, "stareMesaj")
        errors = _header_errors(root)
        raw_state = root.get("stare")
        if raw_state is None:
            # `Errors` without `stare` is a *query* failure (unknown/invalid index,
            # missing SPV rights, daily limit — per the stareMesaj swagger), not a
            # document outcome; upload-time rejection arrives as
            # `stare="XML cu erori nepreluat de sistem"`.
            detail = "; ".join(errors) or f"missing `stare`: {as_text(body)[:200]}"
            raise AnafResponseError(
                f"stareMesaj error: {detail}",
                status_code=200,
                body=as_text(body),
            )
        try:
            state = MessageState.from_raw(raw_state)
        except ValueError as exc:
            # A state string we don't know: be explicit, in the AnafError hierarchy.
            raise AnafResponseError(
                str(exc), status_code=200, body=as_text(body)
            ) from exc
        download_id = root.get("id_descarcare")
        return MessageStatus(
            state=state, download_id=download_id, errors=errors, raw=body
        )

    async def download(self, message_id: str) -> DownloadedMessage:
        """Download the ZIP (signed invoice/errors + MF signature) for a message id.

        Raises:
            AnafResponseError: ANAF answered 200 with a non-ZIP body (it reports
                e.g. an unknown id as an error payload, not an HTTP error).
        """
        response = await self._request("GET", "descarcare", params={"id": message_id})
        try:
            return DownloadedMessage.from_zip(response.content)
        except zipfile.BadZipFile as exc:
            raise AnafResponseError(
                f"descarcare returned a non-ZIP body for id {message_id!r}: "
                f"{as_text(response.content)[:200]}",
                status_code=response.status_code,
                body=as_text(response.content),
            ) from exc

    def list_messages(
        self,
        *,
        cif: str,
        days: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        filter: Filter | None = None,
    ) -> AsyncIterator[MessageListItem]:
        """Iterate every e-Factura message in a window, paging under the hood.

        Specify the window with **either** ``days`` (1-60) **or** both ``start`` and
        ``end`` (datetimes; a naive one is interpreted in the machine's local
        timezone — pass timezone-aware values to be explicit). Either way the
        window must lie within the last 60 days — ANAF retains e-Factura
        messages for 60 days and rejects older ``start`` values — and ``end``
        may be neither before ``start`` nor in the future; violations raise
        :class:`AnafConfigError` locally, before any request. Yields each
        :class:`MessageListItem` across all pages of
        ``listaMesajePaginatieFactura``; an empty window yields nothing.

        Consume with ``async for``; materialise via
        ``[m async for m in client.list_messages(...)]``.

        Raises:
            AnafConfigError: the window arguments are invalid (raised eagerly).
            AnafResponseError: ANAF reported a genuine list error (bad CIF/interval, …);
                a benign "no messages" note yields an empty iterator instead.
            AnafRateLimitError / AnafTransportError: as for any request.
        """
        start_ms, end_ms = _resolve_window(days, start, end)  # eager validation
        return self._iter_messages(start_ms, end_ms, cif, filter)

    async def _iter_messages(
        self, start_ms: int, end_ms: int, cif: str, filter: Filter | None
    ) -> AsyncIterator[MessageListItem]:
        page = 1
        while page <= _MAX_LIST_PAGES:
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
            messages, total_pages = self._parse_message_page(response.content)
            if not messages:
                break  # empty/no-results page terminates the walk
            for item in messages:
                yield item
            if total_pages is not None and page >= total_pages:
                break
            page += 1
        else:
            # The cap was exhausted without a terminal page: be explicit rather
            # than silently yielding a truncated list.
            raise AnafResponseError(
                f"listaMesajePaginatieFactura returned no terminal page within "
                f"{_MAX_LIST_PAGES} pages — aborting rather than truncating",
                status_code=200,
            )

    @staticmethod
    def _parse_message_page(body: bytes) -> tuple[list[MessageListItem], int | None]:
        """Parse one page → ``(messages, total_pages|None)``.

        Raises :class:`AnafResponseError` when ANAF's ``eroare`` is a real error; a
        benign "no messages" note returns an empty page so iteration stops cleanly.
        """
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except ValueError as exc:
            raise AnafResponseError(
                f"unrecognised list response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            ) from exc
        error = data.get("eroare")
        if error is not None:
            if is_empty_result_message(str(error)):
                return [], None
            raise AnafResponseError(
                f"ANAF e-Factura list error: {error}",
                status_code=200,
                body=as_text(body),
            )
        messages = [
            MessageListItem.model_validate(m) for m in (data.get("mesaje") or [])
        ]
        total_pages: int | None = None
        if _PAGE_COUNT_KEY in data:
            try:
                total_pages = int(data[_PAGE_COUNT_KEY])
            except (TypeError, ValueError):
                total_pages = None
        return messages, total_pages

    async def validate_signature(
        self,
        file: str | bytes,
        signature: str | bytes,
    ) -> SignatureValidationResult:
        """Validate the MF detached signature over an invoice XML.

        Both files come from the ``descarcare`` ZIP
        (:attr:`DownloadedMessage.content_xml` / ``signature_xml``). The endpoint
        lives at the **host root** (``/api/validate/signature``) — outside the
        ``FCTEL/rest`` prefix and with no test/prod segment — so it ignores this
        client's ``environment``. A failed validation is returned as
        ``valid=False``, not raised.
        """
        files = {
            "file": ("file.xml", file.encode() if isinstance(file, str) else file),
            "signature": (
                "signature.xml",
                signature.encode() if isinstance(signature, str) else signature,
            ),
        }
        # Absolute deliberately: this endpoint lives outside the client's
        # base_url prefix (no FCTEL/rest, no env segment); httpx passes
        # absolute URLs through unmerged.
        url = f"{OAUTH_HOST}/api/validate/signature"
        response = await self._request_http("POST", url, files=files)
        raise_for_status(response)
        return self._parse_signature_validation(response.content)

    @staticmethod
    def _parse_signature_validation(body: bytes) -> SignatureValidationResult:
        try:
            data = json.loads(body)
            message = str(data["msg"])
        except (ValueError, TypeError, KeyError) as exc:
            raise AnafResponseError(
                f"unrecognised signature validation response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            ) from exc
        # Valid and invalid are both HTTP 200 `{msg}` payloads, distinguished only by
        # wording (per the validaresemnatura swagger): "… NU au putut fi validate …"
        # vs "… au fost validate cu succes …".
        normalized = " ".join(message.casefold().split())
        if "nu au putut fi validate" in normalized:
            valid = False
        elif "au fost validate cu succes" in normalized:
            valid = True
        else:
            raise AnafResponseError(
                f"unrecognised signature validation message: {message[:200]}",
                status_code=200,
                body=as_text(body),
            )
        return SignatureValidationResult(valid=valid, message=message, raw=body)

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
