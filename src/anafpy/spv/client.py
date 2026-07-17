"""Async client for the SPV web services (``webserviced.anaf.ro/SPVWS2/rest``).

Read-only by design: list inbox messages (``listaMesaje``), download documents
(``descarcare``), request official reports (``cerere``) and wait for their
asynchronous delivery. Declaration submission is out of scope.

Transport model (see ``docs/anaf-reference/spv/api.md`` §1.1): the certificate
is involved **only** in the interactive session bootstrap
(:class:`~anafpy.spv.bootstrap.CurlBootstrapper` — drive it via
:meth:`SpvClient.login`); every request here is plain httpx riding the APM
cookies. The cookie credential lives in :mod:`anafpy.spv.auth` — construct the
client with a :class:`~anafpy.spv.auth.SpvSessionProvider`, mirroring how the
OAuth clients take a ``TokenProvider``. The :class:`~anafpy.spv.auth.SpvAuth`
flow attaches the cookies, follows the APM's occasional ``/my.policy_nonce``
revalidation bounces transparently, and raises
:class:`~anafpy.exceptions.AnafAuthError` on a redirect to bare ``/my.policy``
(the client never re-runs the bootstrap on its own: that fires the owner's
2FA, which must stay a deliberate act).

Unlike the OAuth clients' no-retry stance, the SPV reads (``listaMesaje``,
``descarcare``) retry transient network failures with exponential backoff and
jitter — every SPV operation is an idempotent GET, ANAF documents no rate
limits, and the polling flows would otherwise surface every blip. ``cerere``
stays single-shot (it creates server-side work); dedupe of repeated requests is
deliberately a caller concern — the MCP layer guards agent loops.
"""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    retry_if_not_exception_type,
    retry_if_result,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

from .._transport.base import as_text, is_empty_result_message, raise_for_status
from .._transport.http import HttpClientBase
from ..exceptions import (
    AnafConfigError,
    AnafResponseError,
    AnafTransportError,
)
from .auth import SpvAuth, SpvSessionProvider
from .bootstrap import SPV_BASE_URL
from .models import (
    MessageList,
    ReportRequest,
    ReportRequestResult,
    SpvDocument,
    SpvMessage,
    english_error_hint,
)
from .session import SpvSession

__all__ = ["SpvClient"]


def _business_error(operation: str, eroare: str, body: bytes) -> AnafResponseError:
    """An ``{titlu, eroare}`` payload as an exception, with the English hint."""
    hint = english_error_hint(eroare)
    message = f"ANAF SPV {operation} error: {eroare}"
    if hint:
        message += f" ({hint})"
    return AnafResponseError(message, status_code=200, body=as_text(body))


class SpvClient(HttpClientBase):
    """Talks to a taxpayer's SPV over an established APM cookie session.

    Construct with a :class:`~anafpy.spv.auth.SpvSessionProvider` over the
    session store an earlier :meth:`login` filled. The client owns an
    ``httpx.AsyncClient`` (unless one is injected — it must then carry
    :class:`~anafpy.spv.auth.SpvAuth` itself; an empty injected ``base_url``
    adopts SPV's URL, while a non-empty one is preserved) and should be used as
    an async context manager. Cookie rotations are saved back to the store.
    """

    def __init__(
        self,
        provider: SpvSessionProvider,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._provider = provider
        super().__init__(
            http=http,
            base_url=SPV_BASE_URL,
            timeout=timeout,
            auth=SpvAuth(provider),
        )

    # -- session -----------------------------------------------------------------------

    async def login(self) -> SpvSession:
        """Establish a fresh APM session (delegates to the provider).

        Interactive: the certificate middleware's PIN/2FA prompt fires. The new
        session is saved to the provider's store, where the next request picks
        it up.

        Raises:
            AnafConfigError: the provider was built without a ``bootstrapper``.
            AnafAuthError: the handshake failed or timed out (retryable — the
                bootstrap is intermittently flaky; the prompt fires again).
        """
        return await self._provider.login()

    # -- transport ---------------------------------------------------------------------

    async def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """One GET; cookie attach and revalidation hops live in ``SpvAuth``.

        ``follow_redirects=False`` is essential: the auth flow must see the raw
        302s to tell a revalidation hop from the login wall.
        """
        response = await self._request_http(
            "GET", path, params=params, follow_redirects=False
        )
        raise_for_status(response)
        return response

    async def _get_retrying(
        self, path: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """A :meth:`_get` with backoff on transient network failures (reads only).

        Only the plain network layer is retried: :class:`AnafResponseError` and
        its subclass :class:`~anafpy.exceptions.AnafRateLimitError` (HTTP 429)
        extend :class:`AnafTransportError` but describe a *received* answer —
        deterministic failures that must surface immediately, per the repo's
        no-auto-backoff error model.
        """
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(AnafTransportError)
            & retry_if_not_exception_type(AnafResponseError),
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1.0, max=8.0),
            reraise=True,
        ):
            with attempt:
                return await self._get(path, params)
        raise AssertionError("unreachable")  # reraise=True guarantees an exit above

    # -- operations --------------------------------------------------------------------

    async def list_messages(self, days: int, *, cif: str | None = None) -> MessageList:
        """Inbox messages that arrived in the last ``days`` days (``listaMesaje``).

        ``cif`` narrows to one CUI/CNP; by default ANAF returns every message
        the certificate has rights for. Besides the messages, the result
        carries the certificate's **authorization inventory**
        (:attr:`~anafpy.spv.models.MessageList.authorized_cuis`).

        Raises:
            AnafConfigError: ``days`` is not positive (raised locally).
            AnafAuthError: no session, or it expired (log in again).
            AnafResponseError: ANAF reported a genuine error; a benign "no
                messages in the window" note yields empty ``messages`` with the
                wording in ``note`` instead.
        """
        if days < 1:
            raise AnafConfigError("list_messages: `days` must be >= 1")
        params = {"zile": str(days)}
        if cif is not None:
            params["cif"] = cif
        response = await self._get_retrying("listaMesaje", params)
        data = self._parse_json_object(response.content, "listaMesaje")
        if (eroare := data.get("eroare")) is not None:
            if is_empty_result_message(str(eroare)):
                title = data.get("titlu")
                return MessageList(
                    title=str(title) if title is not None else None,
                    note=str(eroare),
                )
            raise _business_error("listaMesaje", str(eroare), response.content)
        try:
            return MessageList.model_validate(data)
        except ValidationError as exc:
            raise AnafResponseError(
                f"unrecognised listaMesaje response: {as_text(response.content)[:200]}",
                status_code=200,
                body=as_text(response.content),
            ) from exc

    async def download_document(self, message_id: str) -> SpvDocument:
        """Download one inbox document (``descarcare``) — PDF bytes.

        Raises:
            AnafResponseError: ANAF answered with an ``eroare`` payload (e.g. no
                right to this message) or an unrecognised body.
        """
        response = await self._get_retrying("descarcare", {"id": message_id})
        body = response.content
        if body.startswith(b"%PDF"):
            return SpvDocument(message_id=message_id, content=body)
        try:
            data = json.loads(body)
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("eroare") is not None:
            raise _business_error("descarcare", str(data["eroare"]), body)
        raise AnafResponseError(
            f"unrecognised descarcare response for id {message_id!r}: "
            f"{as_text(body)[:200]}",
            status_code=200,
            body=as_text(body),
        )

    async def request_report(self, request: ReportRequest) -> ReportRequestResult:
        """File a report request (``cerere``); the report arrives asynchronously.

        The returned ``request_id`` will show up as an inbox message's
        ``request_id`` once the report is generated — poll with
        :meth:`wait_for_report` or match it in :meth:`list_messages` output.

        This method deliberately does no transport retry — one call, one
        result-or-raise — and no dedupe: every call files a request with ANAF
        (a repeated ``cerere`` is harmless but yields a second inbox message).
        Callers that might repeat themselves (agent loops) own their dedupe —
        the MCP layer is where that guard lives.

        Raises:
            AnafAuthError: no session, or it expired.
            AnafResponseError: ANAF refused the request (no rights, invalid
                CUI, ...) — verbatim Romanian plus an English hint.
        """
        params = request.wire_params()
        response = await self._get("cerere", params)
        data = self._parse_json_object(response.content, "cerere")
        if (eroare := data.get("eroare")) is not None:
            raise _business_error("cerere", str(eroare), response.content)
        if "id_solicitare" not in data:
            raise AnafResponseError(
                f"unrecognised cerere response: {as_text(response.content)[:200]}",
                status_code=200,
                body=as_text(response.content),
            )
        try:
            return ReportRequestResult.model_validate(data)
        except ValidationError as exc:
            raise AnafResponseError(
                f"unrecognised cerere response: {as_text(response.content)[:200]}",
                status_code=200,
                body=as_text(response.content),
            ) from exc

    async def wait_for_report(
        self,
        request_id: str,
        *,
        cif: str | None = None,
        days: int = 7,
        timeout: float = 600.0,
        initial_wait: float = 15.0,
        max_wait: float = 120.0,
    ) -> SpvDocument:
        """Poll the inbox until the report for ``request_id`` lands, then download.

        Polls :meth:`list_messages` (a ``days``-wide window, optionally narrowed
        by ``cif``) with growing intervals — generous by design, ANAF documents
        no SLA. Raises :class:`TimeoutError` when the budget runs out; the
        request itself stays valid, so retrying later with the same
        ``request_id`` is always safe.
        """
        wanted = str(request_id)

        async def _find() -> SpvMessage | None:
            listing = await self.list_messages(days, cif=cif)
            for message in listing.messages:
                if message.request_id == wanted:
                    return message
            return None

        found: SpvMessage | None = None
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_result(lambda m: m is None),
                wait=wait_exponential_jitter(initial=initial_wait, max=max_wait),
                stop=stop_after_delay(timeout),
                reraise=True,
            ):
                with attempt:
                    found = await _find()
                if not attempt.retry_state.outcome.failed:  # type: ignore[union-attr]
                    attempt.retry_state.set_result(found)
        except RetryError:
            raise TimeoutError(
                f"report for request {wanted} not delivered within {timeout:.0f}s "
                "— ANAF generates reports asynchronously with no SLA; call "
                "wait_for_report again later with the same request_id"
            ) from None
        assert found is not None
        return await self.download_document(found.id)

    # -- helpers -----------------------------------------------------------------------

    @staticmethod
    def _parse_json_object(body: bytes, operation: str) -> dict[str, object]:
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except ValueError as exc:
            raise AnafResponseError(
                f"unrecognised {operation} response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            ) from exc
        return data
