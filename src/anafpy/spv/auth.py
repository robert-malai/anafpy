"""SPV session lifecycle: hand out the APM cookie set, persisting rotations.

The SPV analog of :mod:`anafpy.auth.provider`. The per-request credential is
not the certificate (that participates only in the interactive login bootstrap
— see :mod:`anafpy.spv.bootstrap`) but the F5 APM **cookie session** it mints:
a bearer credential, exactly like an OAuth access token. So the same two-piece
shape applies:

* :class:`SpvSessionProvider` mirrors ``TokenProvider`` — the
  :class:`~anafpy.spv.session.SessionStore` is the single source of truth, and
  the provider also owns the deliberate :meth:`~SpvSessionProvider.login`.
* :class:`SpvAuth` mirrors ``AnafAuth`` — an ``httpx.Auth`` flow that attaches
  the cookies, follows the APM's mid-session ``/my.policy_nonce`` revalidation
  hops (re-yielding requests, the same mechanism ``AnafAuth`` uses for its 401
  retry), and persists rotated cookies back through the provider.

The one deliberate asymmetry: ``AnafAuth`` refreshes on a 401, but
:class:`SpvAuth` has **no recovery leg**. Re-establishing an SPV session means
re-running the certificate bootstrap, which fires the owner's PIN/2FA — that
must stay a deliberate act, so a bounce to the APM login wall raises
:class:`~anafpy.exceptions.AnafAuthError`, full stop. Do not "complete" the
symmetry by calling :meth:`SpvSessionProvider.login` from the auth flow.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from urllib.parse import urljoin, urlparse

import httpx

from ..exceptions import AnafAuthError, AnafConfigError, AnafResponseError
from .bootstrap import SPV_BASE_URL, SessionBootstrapper
from .session import SessionStore, SpvSession

__all__ = ["SpvAuth", "SpvSessionProvider"]

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


class SpvSessionProvider:
    """Provides the current APM cookie set, persisting rotations and owning login.

    The ``SessionStore`` is the single source of truth: the provider keeps no
    session state of its own. Every operation reads the freshest persisted set
    under the lock, so a login performed by another process sharing the store
    (the CLI, a second server) is picked up on the next call.
    """

    def __init__(
        self,
        *,
        store: SessionStore,
        bootstrapper: SessionBootstrapper | None = None,
    ) -> None:
        self._store = store
        self._bootstrapper = bootstrapper
        self._lock = asyncio.Lock()

    async def cookies(self) -> dict[str, str]:
        """The stored session's cookie set.

        Raises:
            AnafAuthError: no session is stored — log in first.
        """
        # Store I/O is synchronous — accepted for a local single-user process,
        # same trade-off as TokenProvider.
        async with self._lock:
            if (session := self._store.load()) is None:
                raise AnafAuthError(_SESSION_EXPIRED)
            return dict(session.cookies)

    async def rotated(self, cookies: dict[str, str], *, seen: dict[str, str]) -> None:
        """Persist a cookie set the APM rotated mid-flight (save-if-changed).

        ``seen`` is the set the request started from. The save happens only
        while the store still holds it: if another process replaced the
        session mid-flight (a fresh login), this rotation belongs to the dead
        session and must not clobber the new one (last-writer-wins would).
        """
        async with self._lock:
            current = self._store.load()
            if current is None or current.cookies != seen:
                return  # replaced (or logged out) underneath — keep the store
            if current.cookies == cookies:
                return
            self._store.save(
                SpvSession(cookies=cookies, established_at=current.established_at)
            )

    async def login(self) -> SpvSession:
        """Establish a fresh APM session via the configured bootstrapper.

        Interactive: the certificate middleware's PIN/2FA prompt fires. The new
        session replaces whatever the store held.

        Raises:
            AnafConfigError: the provider was built without a ``bootstrapper``.
            AnafAuthError: the handshake failed or timed out (retryable — the
                bootstrap is intermittently flaky; the prompt fires again).
        """
        if self._bootstrapper is None:
            raise AnafConfigError(
                "SPV login needs a bootstrapper (e.g. CurlBootstrapper with "
                "your certificate identity)"
            )
        session = await self._bootstrapper.bootstrap()
        async with self._lock:
            self._store.save(session)
        return session

    @property
    def session(self) -> SpvSession | None:
        """The persisted session, if any (read-only snapshot)."""
        return self._store.load()


class SpvAuth(httpx.Auth):
    """httpx auth flow: attach the APM cookies, follow revalidation hops.

    Every request gets the stored cookie set; a redirect to
    ``/my.policy_nonce`` is followed transparently (folding in rotated
    cookies), a bounce to the bare login wall raises
    :class:`~anafpy.exceptions.AnafAuthError`, and an off-host redirect is
    refused. Rotated cookies are saved back through the provider.

    The client must send with ``follow_redirects=False`` so this flow sees the
    raw 302s instead of httpx silently following them onto the login wall.
    """

    def __init__(self, provider: SpvSessionProvider) -> None:
        self._provider = provider

    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response]:
        raise AnafConfigError("anafpy SPV is async-only; use an httpx.AsyncClient")
        yield request  # unreachable; makes this a generator to satisfy httpx.Auth

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        initial = await self._provider.cookies()
        jar = httpx.Cookies()
        for name, value in initial.items():
            jar.set(name, value, domain=_SPV_HOST, path="/")
        # The store is authoritative: drop whatever Cookie header the owning
        # client's jar stamped on at build time. set_cookie_header (via
        # http.cookiejar) only adds a Cookie header when none is present, so a
        # jar left over from earlier responses would otherwise shadow a fresh
        # session another process saved to the shared store (a re-login).
        request.headers.pop("Cookie", None)
        jar.set_cookie_header(request)
        response = yield request
        for _hop in range(_MAX_REDIRECT_HOPS):
            if not response.is_redirect:
                break
            jar.extract_cookies(response)
            location = urljoin(
                str(response.request.url), response.headers.get("Location", "")
            )
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
            # Same-host by the check above, so carrying the original headers is
            # safe. The Cookie header must go first: set_cookie_header (via
            # http.cookiejar) only adds one when none is present, and the hop
            # must carry the freshly rotated set, not the original.
            hop_headers = httpx.Headers(
                [(k, v) for k, v in request.headers.items() if k.lower() != "cookie"]
            )
            next_request = httpx.Request("GET", location, headers=hop_headers)
            jar.set_cookie_header(next_request)
            response = yield next_request
        else:
            raise AnafResponseError(
                f"SPV redirect chain exceeded {_MAX_REDIRECT_HOPS} hops",
                status_code=302,
            )
        jar.extract_cookies(response)
        if (snapshot := _snapshot(jar)) != initial:
            await self._provider.rotated(snapshot, seen=initial)


def _snapshot(jar: httpx.Cookies) -> dict[str, str]:
    """The SPV-host cookies as a persistable ``name -> value`` map."""
    return {
        cookie.name: cookie.value
        for cookie in jar.jar
        if cookie.value is not None and _SPV_HOST.endswith(cookie.domain.lstrip("."))
    }
