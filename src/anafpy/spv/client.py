"""Async client for the SPV web services (``webserviced.anaf.ro/SPVWS2/rest``).

Read-only by design: list inbox messages (``listaMesaje``), download documents
(``descarcare``), request official reports (``cerere``) and wait for their
asynchronous delivery. Declaration submission is out of scope.

Transport model (see ``docs/anaf-reference/spv/api.md`` §1.1): the certificate
is involved **only** in the interactive session bootstrap
(:class:`~anafpy.spv.bootstrap.CurlBootstrapper` — drive it via
:meth:`SpvClient.login`); every request here is plain httpx riding the APM
cookies. Mid-session the APM occasionally bounces through
``/my.policy_nonce`` — followed transparently — while a redirect to bare
``/my.policy`` means the session is gone and raises
:class:`~anafpy.exceptions.AnafAuthError` (the client never re-runs the
bootstrap on its own: that fires the owner's 2FA, which must stay a deliberate
act).

Unlike the OAuth clients' no-retry stance, the SPV reads (``listaMesaje``,
``descarcare``) retry transient network failures with exponential backoff and
jitter — every SPV operation is an idempotent GET, ANAF documents no rate
limits, and the polling flows would otherwise surface every blip. ``cerere``
stays single-shot (it creates server-side work); dedupe of repeated requests is
deliberately a caller concern — the MCP layer guards agent loops.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from urllib.parse import urljoin, urlparse

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

from .._transport.base import as_text, is_empty_result_message, raise_for_status
from ..exceptions import (
    AnafAuthError,
    AnafConfigError,
    AnafResponseError,
    AnafTransportError,
)
from .bootstrap import SPV_BASE_URL, SessionBootstrapper
from .models import (
    MessageList,
    ReportRequest,
    ReportRequestResult,
    SpvDocument,
    SpvMessage,
    english_error_hint,
)
from .session import SessionStore, SpvSession

__all__ = ["SpvClient"]

_SPV_HOST = urlparse(SPV_BASE_URL).netloc

# The APM login-wall paths (docs/anaf-reference/spv/api.md §1.1): a bounce to the
# nonce revalidation is routine and followed; the bare policy page or the hangup
# path means the cookie session is gone.
_REVALIDATION_PATH = "/my.policy_nonce"
_LOGIN_WALL_PATHS = ("/my.policy", "/vdesk/")

# Defensive bound on followed redirects; the observed chains are 2-3 hops.
_MAX_REDIRECT_HOPS = 8

_SESSION_EXPIRED = (
    "SPV session missing or expired — establish one with SpvClient.login() "
    "(fires the certificate 2FA)"
)


def _business_error(operation: str, eroare: str, body: bytes) -> AnafResponseError:
    """An ``{titlu, eroare}`` payload as an exception, with the English hint."""
    hint = english_error_hint(eroare)
    message = f"ANAF SPV {operation} error: {eroare}"
    if hint:
        message += f" ({hint})"
    return AnafResponseError(message, status_code=200, body=as_text(body))


class SpvClient:
    """Talks to a taxpayer's SPV over an established APM cookie session.

    Construct with a :class:`~anafpy.spv.session.SessionStore` holding a session
    from an earlier :meth:`login` (or pass ``session`` directly). The client
    owns an ``httpx.AsyncClient`` (unless one is injected) and should be used
    as an async context manager. Cookie rotations are saved back to the store
    transparently.
    """

    def __init__(
        self,
        *,
        session: SpvSession | None = None,
        session_store: SessionStore | None = None,
        bootstrapper: SessionBootstrapper | None = None,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._store = session_store
        self._bootstrapper = bootstrapper
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(timeout=timeout)
        self._session_loaded = False
        self._established_at: datetime | None = None
        self._saved_cookies: dict[str, str] = {}
        if session is not None:
            self._adopt_session(session)

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

    # -- session -----------------------------------------------------------------------

    def _adopt_session(self, session: SpvSession) -> None:
        for name, value in session.cookies.items():
            self._http.cookies.set(name, value, domain=_SPV_HOST, path="/")
        self._established_at = session.established_at
        self._saved_cookies = dict(session.cookies)
        self._session_loaded = True

    def _ensure_session(self) -> None:
        if self._session_loaded:
            return
        if self._store is not None and (session := self._store.load()) is not None:
            self._adopt_session(session)
            return
        raise AnafAuthError(_SESSION_EXPIRED)

    def _cookie_snapshot(self) -> dict[str, str]:
        return {
            cookie.name: cookie.value
            for cookie in self._http.cookies.jar
            if cookie.value is not None
            and _SPV_HOST.endswith(cookie.domain.lstrip("."))
        }

    def _persist_cookies(self) -> None:
        """Save the session back when the APM rotated a cookie mid-flight."""
        current = self._cookie_snapshot()
        if current != self._saved_cookies:
            self._saved_cookies = current
            if self._store is not None:
                self._store.save(
                    SpvSession(
                        cookies=current,
                        established_at=self._established_at or datetime.now(tz=UTC),
                    )
                )

    async def login(self) -> SpvSession:
        """Establish a fresh APM session via the configured bootstrapper.

        Interactive: the certificate middleware's PIN/2FA prompt fires. The new
        session replaces the client's cookies and is saved to the store.

        Raises:
            AnafConfigError: the client was built without a ``bootstrapper``.
            AnafAuthError: the handshake failed or timed out (retryable — the
                bootstrap is intermittently flaky; the prompt fires again).
        """
        if self._bootstrapper is None:
            raise AnafConfigError(
                "SpvClient.login() needs a bootstrapper (e.g. CurlBootstrapper "
                "with your certificate identity)"
            )
        session = await self._bootstrapper.bootstrap()
        self._http.cookies.clear()
        self._adopt_session(session)
        if self._store is not None:
            self._store.save(session)
        return session

    # -- transport ---------------------------------------------------------------------

    async def _send(self, url: str, params: dict[str, str] | None) -> httpx.Response:
        try:
            return await self._http.get(url, params=params, follow_redirects=False)
        except httpx.HTTPError as exc:  # connect/read/timeout/etc.
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc

    async def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """One GET, following the APM's revalidation redirects with cookies."""
        self._ensure_session()
        url = f"{SPV_BASE_URL}/{path}"
        for _hop in range(_MAX_REDIRECT_HOPS):
            response = await self._send(url, params)
            if response.is_redirect:
                location = urljoin(url, response.headers.get("Location", ""))
                parsed = urlparse(location)
                if parsed.netloc != _SPV_HOST:
                    raise AnafResponseError(
                        f"SPV redirected off-host to {location!r}",
                        status_code=response.status_code,
                    )
                if any(parsed.path.startswith(p) for p in _LOGIN_WALL_PATHS) and not (
                    parsed.path.startswith(_REVALIDATION_PATH)
                ):
                    raise AnafAuthError(_SESSION_EXPIRED)
                url, params = location, None
                continue
            raise_for_status(response)
            self._persist_cookies()
            return response
        raise AnafResponseError(
            f"SPV redirect chain exceeded {_MAX_REDIRECT_HOPS} hops",
            status_code=302,
        )

    async def _get_retrying(
        self, path: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """A :meth:`_get` with backoff on transient network failures (reads only)."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(AnafTransportError),
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
        return MessageList.model_validate(data)

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
        return ReportRequestResult.model_validate(data)

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
