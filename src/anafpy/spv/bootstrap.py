"""SPV session bootstrap — the one step that needs the qualified certificate.

M0 established (see ``docs/anaf-reference/spv/api.md`` §1.1) that SPV's mTLS is
an F5 APM **login choreography**, not a per-request transport: one redirect
chain through ``/my.policy`` performs the client-certificate TLS renegotiation
(firing the token PIN / cloud-HSM 2FA), and everything afterwards rides the
resulting cookies. So the platform-specific seam is a
:class:`SessionBootstrapper` that produces an :class:`~.session.SpvSession` —
not a request transport.

:class:`CurlBootstrapper` drives the **OS-shipped curl** in a subprocess:

* macOS — ``/usr/bin/curl`` with the SecureTransport backend, which takes the
  identity **by Keychain name** and, unlike Apple's own NSURLSession (which
  hangs, verified 2026-07-12), survives the mid-connection renegotiation.
* Windows — ``System32\\curl.exe`` (Schannel build) with the
  ``CurrentUser\\MY\\<thumbprint>`` cert-store syntax.

Python-level alternatives were evaluated and rejected: CPython's ``ssl`` only
loads private keys from files, so no httpx/requests-based stack can sign with a
non-exportable platform-store key.

The bootstrap is **interactive** (the 2FA prompt fires every time — the
middleware caches authorizations only for minutes) and intermittently flaky, so
it is bounded by a timeout and surfaces actionable errors instead of hanging.

The platform machinery (curl resolution, cert selectors, TLS-backend pin,
subprocess runner, failure taxonomy) lives in :mod:`anafpy._transport.curl`,
shared with the declaration portal bootstrap
(:class:`anafpy.declaratii.upload.PortalCurlBootstrapper`) — only the SPV
choreography (the one-probe redirect chain) and its success judgment (the SPV
JSON) live here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from .._transport.curl import CurlBootstrapperBase, parse_netscape_cookies
from ..exceptions import AnafAuthError
from .session import SpvSession

__all__ = [
    "SPV_BASE_URL",
    "CurlBootstrapper",
    "SessionBootstrapper",
    "parse_netscape_cookies",
]

#: Base URL of the SPV web services (no test/prod split — production only).
SPV_BASE_URL = "https://webserviced.anaf.ro/SPVWS2/rest"


@runtime_checkable
class SessionBootstrapper(Protocol):
    """Performs the certificate handshake and returns the APM cookie session."""

    async def bootstrap(self) -> SpvSession: ...


class CurlBootstrapper(CurlBootstrapperBase):
    """Establishes an SPV session via the platform curl and its native key store.

    The choreography is a single probe: one ``--location`` chain through
    ``/my.policy`` (the renegotiation fires the 2FA) that must land on the SPV
    ``listaMesaje`` JSON. Constructor arguments are the shared base's
    (:class:`~anafpy._transport.curl.CurlBootstrapperBase`): *identity* — the
    Keychain identity **name** on macOS (see
    :func:`~anafpy.spv.certs.list_keychain_identities`), the SHA-1
    **thumbprint** in ``CurrentUser\\MY`` on Windows — plus *timeout*,
    *curl_path*, and *platform*.
    """

    context = "SPV bootstrap"

    def command(self, jar_path: str) -> list[str]:
        """The curl argv for the bootstrap redirect chain."""
        return [
            *self.curl_base(jar_path),
            "--location",  # follow the /my.policy -> /my.policy_nonce chain
            "--cert",
            self.cert_selector,
            f"{SPV_BASE_URL}/listaMesaje?zile=1",
        ]

    def commands(self, jar_path: str) -> list[list[str]]:
        return [self.command(jar_path)]

    async def bootstrap(self) -> SpvSession:
        """Run the handshake and return the authenticated session.

        Success is judged by the **payload**, not curl's exit code: ANAF's F5
        closes the final connection without a TLS ``close_notify``, so a fully
        successful bootstrap still exits 56 (``SSLRead() error -9806``,
        live-observed 2026-07-12). If the body is the SPV JSON and the jar
        holds the APM session cookie, the handshake worked.

        Raises:
            AnafAuthError: the handshake timed out (usually an unanswered or
                stalled 2FA), curl failed, or ANAF answered with something other
                than the SPV JSON (certificate without SPV rights, APM hangup).
        """
        returncode, stdout, stderr, cookies = await self.run_chain()

        body = stdout.decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        answered = isinstance(payload, dict) and "titlu" in payload
        session = SpvSession(cookies=cookies, established_at=datetime.now(tz=UTC))
        if answered and session.is_authenticated_shape:
            return session

        self.raise_curl_failure(returncode, stderr)
        if not answered:
            snippet = " ".join(body.split())[:200]
            raise AnafAuthError(
                "SPV handshake did not reach the service — expected JSON, got: "
                f"{snippet!r} (an APM hangup page usually means the certificate "
                "was refused or has no SPV enrolment)"
            )
        raise AnafAuthError(
            "SPV handshake answered but no APM session cookie was set — "
            "cannot continue without MRHSession"
        )
