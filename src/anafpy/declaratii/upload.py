"""Declaration portal upload (``decl.anaf.mfinante.gov.ro/WAS6DUS``) — M2.

The portal behind anaf.ro → "Depunere declarații": where the signed declaration
PDF is actually filed. Access is the same F5 APM cookie-session model as SPV
(see :mod:`anafpy.spv.bootstrap`) with one extra step — a certificate-less
logon-form POST precedes the certificate renegotiation — and the steps must be
**discrete** (letting curl carry the POST across the redirect downgrades the
connection and the F5 resets it; live-proven 2026-07-16, reference:
``docs/anaf-reference/declaratii/portal-upload.md``). Sessions are disposable
(stated 10-minute inactivity timeout): login → upload → done, nothing is
persisted.

:class:`PortalCurlBootstrapper` drives the OS curl exactly like the SPV
bootstrap (platform key store, 2FA fires on the renegotiation step);
:class:`DeclarationUploadClient` then rides the cookies with plain httpx for
the one multipart POST.

The success page was captured live on 2026-07-17 (a D406T test filing; raw
capture ``_sources/decl-portal/upload-response-d406t.html``): the marker is
*"Succes depunere"* / *"a fost depus cu succes"* and the upload index rides in
the sentence *"Indexul este <b>…</b>"*. The page itself stresses that it is
**not** the registration confirmation — that is the recipisa, tracked via
StareD112 (:class:`~anafpy.declaratii.status.DeclarationStatusClient`, which
was live-confirmed to list a D406T filing as ``In prelucrare`` minutes after
upload). :class:`PortalUploadResult` still carries the **raw HTML**, and
``accepted`` is ``None`` for pages this module does not recognise (the known
rejection page is a returned business outcome, per the error model).
"""

from __future__ import annotations

import contextlib
import re
from typing import Protocol, runtime_checkable

import httpx
from parsel import Selector

from .._transport.base import raise_for_status
from .._transport.curl import CurlBootstrapperBase
from .._transport.http import HttpClientBase
from ..exceptions import AnafAuthError, AnafConfigError
from ._html import strip_accents, whole_text
from .models import PortalUploadResult

__all__ = [
    "PORTAL_BASE_URL",
    "DeclarationUploadClient",
    "PortalCurlBootstrapper",
    "PortalSessionBootstrapper",
]

#: Base URL of the declaration upload portal (production only — there is no
#: TEST environment for declaration filing; D406T is the no-effect test path).
PORTAL_BASE_URL = "https://decl.anaf.mfinante.gov.ro"

_UPLOAD_PATH = "WAS6DUS/displayFile.do"

#: Accent-stripped marker of the app's generic rejection page.
_REJECTION_MARKER = "ne cerem scuze"
#: Markers of the upload form — the authenticated landing page.
_FORM_MARKER = "displayfile.do"
#: Accent-stripped marker of the success page (captured 2026-07-17).
_SUCCESS_MARKER = "depus cu succes"
#: The upload index on the success page: "… Indexul este <b>1100000005</b>."
_INDEX_RE = re.compile(r"indexul\s+este[^\d]{0,60}(\d{6,})")


@runtime_checkable
class PortalSessionBootstrapper(Protocol):
    """Performs the certificate login and returns the APM cookie set."""

    async def bootstrap(self) -> dict[str, str]: ...


class PortalCurlBootstrapper(CurlBootstrapperBase):
    """Portal login via the platform curl — SPV's model, discrete steps.

    The choreography (live-proven, reference §1): a cookie-priming ``GET``
    (bounces to the APM logon page), the certificate-less logon-form ``POST``
    (``vhost=standard``; must **not** be carried across its redirect), then the
    certificate ``GET`` whose TLS renegotiation fires the token PIN / 2FA and
    lands back on ``/WAS6DUS/``. ``F5_ST`` is timestamped and short-lived, so
    the steps run promptly in one :meth:`bootstrap` call. Constructor
    arguments are the shared base's
    (:class:`~anafpy._transport.curl.CurlBootstrapperBase`): *identity*,
    *timeout*, *curl_path*, *platform* — the same selectors as the SPV
    bootstrap.
    """

    context = "portal login"

    def commands(self, jar_path: str) -> list[list[str]]:
        """The discrete curl invocations of the login choreography, in order."""
        base = self.curl_base(jar_path)
        return [
            # 1. Cookie priming: land on the APM logon page (GETs may follow).
            [*base, "--location", f"{PORTAL_BASE_URL}/WAS6DUS/"],
            # 2. Logon-form POST — deliberately NOT followed across its 302.
            [*base, "--data", "vhost=standard", f"{PORTAL_BASE_URL}/my.policy"],
            # 3. Certificate GET: renegotiation fires the 2FA, then the
            #    /my.policy_nonce -> /WAS6DUS/ chain is followed.
            [
                *base,
                "--location",
                "--cert",
                self.cert_selector,
                f"{PORTAL_BASE_URL}/my.policy",
            ],
        ]

    async def bootstrap(self) -> dict[str, str]:
        """Run the login choreography and return the session cookie set.

        Success is judged by the final **payload** (the upload form), not curl's
        exit code — ANAF's F5 closes the last connection without a TLS
        ``close_notify``, so a fully successful login can still exit 56 (same
        quirk as the SPV bootstrap).

        Raises:
            AnafAuthError: a step timed out (usually an unanswered 2FA), curl
                failed, or the chain did not land on the upload app (certificate
                refused / APM hangup).
        """
        returncode, stdout, stderr, cookies = await self.run_chain()

        body = stdout.decode("utf-8", errors="replace")
        if _FORM_MARKER in body.lower() and "MRHSession" in cookies:
            return cookies

        self.raise_curl_failure(returncode, stderr)
        snippet = " ".join(body.split())[:200]
        raise AnafAuthError(
            "portal login did not reach the upload app — expected the upload "
            f"form, got: {snippet!r} (a hangup page usually means the "
            "certificate was refused)"
        )


def _parse_upload_page(html: str) -> PortalUploadResult:
    """Parse the ``displayFile.do`` response (shapes live-captured, see §3-§4)."""
    page = Selector(text=html)
    text = whole_text(page)
    normalized = strip_accents(text).lower()

    if _REJECTION_MARKER in normalized:
        reason = whole_text(page.css("span[style*='red']"))
        if not reason.strip():
            # Fallback: the sentence after the "Motivul:" label.
            match = re.search(r"motivul:\s*(.+?)(?:\.|$)", normalized)
            reason = match.group(1).strip() if match else text[:200]
        return PortalUploadResult(accepted=False, reason=reason.strip(), html=html)

    if _SUCCESS_MARKER in normalized:
        match = _INDEX_RE.search(normalized)
        return PortalUploadResult(
            accepted=True,
            upload_index=match.group(1) if match else None,
            html=html,
        )

    return PortalUploadResult(accepted=None, html=html)


class DeclarationUploadClient(HttpClientBase):
    """Files a signed declaration PDF on the ``WAS6DUS`` upload portal.

    The client is deliberately session-per-use (the portal states a 10-minute
    inactivity timeout): :meth:`login` runs the certificate bootstrap — firing
    the token PIN / 2FA — and :meth:`upload` performs the one multipart POST.
    Like every discrete client method there is **no transport retry**, and the
    upload POST is non-idempotent — one call, one result-or-raise.

    Args:
        bootstrapper: the certificate login step (a
            :class:`PortalCurlBootstrapper` in production; fakes in tests).
            Optional when an *http* client with a live cookie set is injected.
        http: injected ``httpx.AsyncClient`` (tests). Must carry a non-empty
            ``base_url`` (an empty one raises
            :class:`~anafpy.exceptions.AnafConfigError`; injected clients are
            never mutated).
        timeout: HTTP timeout for the upload POST (the PDF is small, but the
            portal can be slow).
    """

    def __init__(
        self,
        *,
        bootstrapper: PortalSessionBootstrapper | None = None,
        http: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._bootstrapper = bootstrapper
        super().__init__(
            http=http,
            base_url=PORTAL_BASE_URL,
            timeout=timeout,
            follow_redirects=True,
        )

    async def login(self) -> None:
        """Run the certificate bootstrap and install its cookies.

        Fires the token PIN / 2FA prompt (once per call — the portal session
        model has no silent re-login).

        Raises:
            AnafConfigError: no bootstrapper was provided.
            AnafAuthError: the login choreography failed.
        """
        if self._bootstrapper is None:
            raise AnafConfigError(
                "no bootstrapper configured — construct the client with "
                "PortalCurlBootstrapper(identity) to log in"
            )
        cookies = await self._bootstrapper.bootstrap()
        # Scope the bearer-cookie set to the portal host: httpx's default
        # empty domain would attach MRHSession to a request to ANY host, so
        # an off-portal redirect must never carry the session with it.
        host = self._http.base_url.host
        self._http.cookies.clear()
        for name, value in cookies.items():
            self._http.cookies.set(name, value, domain=host)

    async def upload(self, pdf: bytes, *, filename: str) -> PortalUploadResult:
        """POST the signed declaration PDF to ``displayFile.do``.

        Args:
            pdf: the signed smart-PDF bytes (form PDF with the XML embedded).
            filename: the multipart filename (the portal shows it back in
                messages; use the conventional ``<form>_<cui>_<period>.pdf``
                shape when in doubt).

        Returns:
            A :class:`PortalUploadResult` — the known rejection page is a
            returned business outcome; the success page yields the upload
            index (then poll StareD112 for the recipisa — the page itself is
            not the registration confirmation); an unrecognised page returns
            ``accepted=None`` with the raw HTML.

        Raises:
            AnafAuthError: the portal answered the POST with a redirect —
                an APM login wall / ``/my.policy_nonce`` revalidation bounce
                (the session expired; sessions die after ~10 idle minutes;
                log in again).
            AnafTransportError: network failure.
            AnafResponseError: non-success HTTP status.
        """
        if not self._http.cookies:
            raise AnafConfigError("no portal session — call login() first")
        # Redirects are NOT followed on this POST: httpx would re-issue a 3xx
        # as a body-less GET (silently dropping the multipart file) and the
        # resulting error page would misread as a business rejection. A
        # redirect here is always an APM session event — the login wall or a
        # /my.policy_nonce revalidation hop — never part of the happy path
        # (the live D406T filing answered 200 directly).
        response = await self._request_http(
            "POST",
            _UPLOAD_PATH,
            files={"linkdoc": (filename, pdf, "application/pdf")},
            follow_redirects=False,
        )
        if response.is_redirect:
            target = response.headers.get("Location", "")
            raise AnafAuthError(
                "the portal answered the upload POST with a redirect to "
                f"{target!r} — an APM login-wall / session-revalidation "
                "bounce, so the session expired or went stale (10-minute "
                "inactivity timeout); call login() again and retry the upload"
            )
        raise_for_status(response)
        return _parse_upload_page(response.text)

    async def logout(self) -> None:
        """Tear the APM session down (``GET /exit``); best-effort."""
        with contextlib.suppress(httpx.HTTPError):
            await self._http.get("exit")
        self._http.cookies.clear()
