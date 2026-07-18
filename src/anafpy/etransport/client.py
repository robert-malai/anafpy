"""Async client for the RO e-Transport web services (``ETRANSPORT/ws/v1``).

Design mirrors ``anafpy.efactura.client`` with four key differences:
1. Upload path embeds ``standard``, ``cif``, and ``versiune`` as path segments
   (``POST /upload/ETRANSP/{cif}/{versiune}``), not query params; the body must be the
   declaration **XML** (``application/xml`` — there is no JSON request format).
2. **Responses are JSON**, not e-Factura's XML ``<header>`` (per the vendored swagger
   specs); errors ride an ``Errors[{errorMessage}]`` array, including ``lista``'s
   no-results note.
3. Status uses a **path param** (``GET stareMesaj/{id_incarcare}``), not a query param.
4. **No download step** — the UIT code is returned in the upload response; state is
   tracked via ``lista`` / ``stareMesaj``.
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import AsyncIterator

import httpx
from pydantic import ValidationError
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
from .models import (
    FlatSubmission,
    InfoItem,
    InfoList,
    MessageState,
    MessageStatus,
    Notification,
    UploadResult,
    _InfoEnvelope,
    _JsonEnvelope,
    _ListaEnvelope,
    _StatusEnvelope,
    _UploadEnvelope,
    render_etransport,
)

__all__ = ["ETransportClient"]

_STANDARD = "ETRANSP"
_XML_BODY_HEADERS = {"Content-Type": "application/xml"}


def _segment(value: str) -> str:
    """Encode a caller-supplied value as a single URL path segment.

    Unlike e-Factura's query params, this service embeds ``cif``/``upload_id`` in
    the path — a stray ``/`` must not silently reroute the request.
    """
    return urllib.parse.quote(value, safe="")


def _load_envelope[EnvelopeT: _JsonEnvelope](
    body: bytes, model: type[EnvelopeT], operation: str
) -> EnvelopeT:
    """Validate a JSON response body against its envelope model.

    A body that is not the documented JSON shape raises :class:`AnafResponseError` —
    explicit, rather than inventing an outcome.
    """
    try:
        return model.model_validate(json.loads(body))
    except (ValueError, ValidationError) as exc:
        raise AnafResponseError(
            f"unrecognised {operation} response: {as_text(body)[:200]}",
            status_code=200,
            body=as_text(body),
        ) from exc


class ETransportClient(HttpClientBase):
    """Talks to ANAF e-Transport over OAuth2.

    Construct with an authenticated :class:`~anafpy.auth.provider.TokenProvider`; the
    client owns an ``httpx.AsyncClient`` (unless one is injected — it must then
    carry :class:`~anafpy.auth.oauth.AnafAuth` and a non-empty ``base_url``;
    an empty one raises :class:`~anafpy.exceptions.AnafConfigError`, since
    injected clients are never mutated) and should
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
            base_url=service_base_url(Service.ETRANSPORT, environment),
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
        version: int = 2,
    ) -> UploadResult:
        """Submit a transport declaration XML for processing.

        Returns an :class:`UploadResult` whose ``upload_id`` feeds ``get_status`` and
        ``uit`` is the transport declaration code returned on acceptance.  A document
        rejected at submission comes back with ``accepted is False`` and ``errors``
        populated — not as an exception.
        """
        body = xml.encode("utf-8") if isinstance(xml, str) else xml
        path = f"upload/{_STANDARD}/{_segment(cif)}/{version}"
        response = await self._request(
            "POST", path, content=body, headers=_XML_BODY_HEADERS
        )
        return self._parse_upload(response.content)

    @staticmethod
    def _parse_upload(body: bytes) -> UploadResult:
        envelope = _load_envelope(body, _UploadEnvelope, "upload")
        errors = envelope.error_messages
        if envelope.upload_index is None and not errors:
            # Be explicit rather than silently returning an empty result.
            errors = [f"unrecognised upload response: {as_text(body)[:200]}"]
        return UploadResult(
            upload_id=envelope.upload_index,
            uit=envelope.uit,
            errors=errors,
            raw=body,
        )

    async def upload_document(
        self,
        document: FlatSubmission,
        *,
        cif: str,
        version: int = 2,
    ) -> UploadResult:
        """Compose a flat e-Transport document and file it — no XML handling needed.

        Accepts any of the four flat documents (a :class:`FlatTransport`
        declaration/correction, :class:`FlatDeletion`, :class:`FlatConfirmation`, or
        :class:`FlatVehicleChange` from :mod:`anafpy.etransport.models`), renders it
        to the ANAF declaration XML with ``cod_declarant`` taken from ``cif`` (unless
        the document sets ``declarant_code`` itself), and uploads it. One call, one
        result-or-raise, same as :meth:`upload`.
        """
        xml = render_etransport(document, declarant_code=cif)
        return await self.upload(xml, cif=cif, version=version)

    async def get_status(self, upload_id: str) -> MessageStatus:
        """Poll the processing state for an ``upload_id`` (``index_incarcare``)."""
        response = await self._request("GET", f"stareMesaj/{_segment(upload_id)}")
        return self._parse_status(response.content)

    @staticmethod
    def _parse_status(body: bytes) -> MessageStatus:
        envelope = _load_envelope(body, _StatusEnvelope, "stareMesaj")
        errors = envelope.error_messages
        if envelope.state is None:
            # `Errors` without `stare` is a *query* failure (unknown/invalid index,
            # missing SPV rights, daily limit — per the stare swagger), not a document
            # outcome — so it raises rather than masquerading as a rejection.
            detail = "; ".join(errors) or f"missing `stare`: {as_text(body)[:200]}"
            raise AnafResponseError(
                f"stareMesaj error: {detail}", status_code=200, body=as_text(body)
            )
        try:
            state = MessageState.from_raw(envelope.state)
        except ValueError as exc:
            # A state string we don't know: be explicit, in the AnafError hierarchy.
            raise AnafResponseError(
                str(exc), status_code=200, body=as_text(body)
            ) from exc
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
        response = await self._request("GET", f"lista/{days}/{_segment(cif)}")
        for notification in self._parse_notifications(response.content):
            yield notification

    @staticmethod
    def _parse_notifications(body: bytes) -> list[Notification]:
        """Parse a ``lista`` response (``mesaje[]`` envelope) to notifications.

        Raises :class:`AnafResponseError` when ANAF's ``Errors[]`` carry a real error
        (bad ``zile``, missing SPV rights, daily limit); the benign "no notifications"
        note — which rides the same ``Errors[]`` array — returns an empty list.
        """
        envelope = _load_envelope(body, _ListaEnvelope, "lista")
        errors = envelope.error_messages
        # A genuine error raises even when `mesaje` is also present (an undocumented
        # combination): explicit, rather than silently dropping the error note.
        if errors and not all(is_empty_result_message(message) for message in errors):
            raise AnafResponseError(
                f"ANAF e-Transport list error: {'; '.join(errors)}",
                status_code=200,
                body=as_text(body),
            )
        return envelope.messages

    async def info(
        self,
        *,
        organizer_cui: str,
        declarant_cui: str | None = None,
        uit: str | None = None,
        declarant_ref: str | None = None,
    ) -> InfoList:
        """Look up active notifications where ``organizer_cui`` (ANAF: ``cui_op``)
        is the transport organizer.

        A benign "no results" note comes back as an empty :class:`InfoList` with
        ``error`` carrying ANAF's wording; a genuine query error (missing SPV
        rights, daily limit, unknown CUI) raises :class:`AnafResponseError` —
        the same split the list endpoints apply.
        """
        params: dict[str, str] = {"cui_op": organizer_cui}
        if declarant_cui is not None:
            params["cui_decl"] = declarant_cui
        if uit is not None:
            params["uit"] = uit
        if declarant_ref is not None:
            params["ref_decl"] = declarant_ref
        response = await self._request("GET", "info", params=params)
        return self._parse_info(response.content)

    @staticmethod
    def _parse_info(body: bytes) -> InfoList:
        """Parse an ``info`` response: a bare JSON array of records (per the info
        swagger). A JSON object carries an error note instead — a top-level ``error``
        string (live-confirmed 2026-07-02: the no-results case is ``{"error": "Nu
        exista informatii pentru aceasta solicitare"}``) or an ``Errors[]`` array.
        Like the list endpoints, a benign no-results note is returned (via
        ``InfoList.error``) while a genuine query error (missing SPV rights, daily
        limit, bad CUI) raises :class:`AnafResponseError`."""
        try:
            data = json.loads(body)
            if isinstance(data, list):
                items = [InfoItem.model_validate(item) for item in data]
                return InfoList(items=items, raw=body)
            envelope = _InfoEnvelope.model_validate(data)
        except (ValueError, ValidationError) as exc:
            raise AnafResponseError(
                f"unrecognised info response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            ) from exc
        errors = envelope.all_error_messages
        if not errors:
            raise AnafResponseError(
                f"unrecognised info response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            )
        if all(is_empty_result_message(message) for message in errors):
            return InfoList(items=[], error="; ".join(errors), raw=body)
        raise AnafResponseError(
            f"ANAF e-Transport info error: {'; '.join(errors)}",
            status_code=200,
            body=as_text(body),
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
