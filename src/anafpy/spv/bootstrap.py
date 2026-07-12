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
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..exceptions import AnafAuthError, AnafConfigError
from .session import SpvSession

__all__ = [
    "SPV_BASE_URL",
    "CurlBootstrapper",
    "SessionBootstrapper",
    "parse_netscape_cookies",
]

#: Base URL of the SPV web services (no test/prod split — production only).
SPV_BASE_URL = "https://webserviced.anaf.ro/SPVWS2/rest"

# curl's exit code for `--max-time` expiry — almost always an unanswered 2FA.
_CURL_EXIT_TIMEOUT = 28


@runtime_checkable
class SessionBootstrapper(Protocol):
    """Performs the certificate handshake and returns the APM cookie session."""

    async def bootstrap(self) -> SpvSession: ...


def parse_netscape_cookies(text: str) -> dict[str, str]:
    """Cookie ``name -> value`` from a curl-written Netscape cookie jar.

    Hand-rolled because stdlib ``MozillaCookieJar`` silently skips the
    ``#HttpOnly_`` lines curl emits for HttpOnly cookies.
    """
    cookies: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("#HttpOnly_"):
            line = line.removeprefix("#HttpOnly_")
        elif line.startswith("#") or not line.strip():
            continue
        # domain, include-subdomains, path, secure, expires, name, value
        fields = line.split("\t")
        if len(fields) == 7:
            cookies[fields[5]] = fields[6]
    return cookies


def _default_curl_path(platform: str) -> str:
    """The OS-shipped curl — deliberately not whatever is first on ``PATH``.

    A Homebrew curl (macOS) lacks the SecureTransport backend and a
    Git-for-Windows curl lacks Schannel; both would reject the platform
    cert-store ``--cert`` syntax.
    """
    if platform == "win32":
        system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
        return str(Path(system_root) / "System32" / "curl.exe")
    return "/usr/bin/curl"


class CurlBootstrapper:
    """Establishes an SPV session via the platform curl and its native key store.

    Args:
        identity: which certificate to present — the Keychain identity **name**
            on macOS (see :func:`~anafpy.spv.certs.list_keychain_identities`),
            the SHA-1 **thumbprint** in ``CurrentUser\\MY`` on Windows.
        timeout: seconds to wait for the whole handshake, 2FA included. The
            authorization prompt fires on every bootstrap, so keep this
            generous.
        curl_path: override the curl binary (tests, exotic installs).
        platform: override ``sys.platform`` (tests).
    """

    def __init__(
        self,
        identity: str,
        *,
        timeout: float = 240.0,
        curl_path: str | None = None,
        platform: str | None = None,
    ) -> None:
        if not identity:
            raise AnafConfigError("CurlBootstrapper: `identity` must be non-empty")
        self.identity = identity
        self.timeout = timeout
        self.platform = platform if platform is not None else sys.platform
        if self.platform not in ("darwin", "win32"):
            raise AnafConfigError(
                f"no SPV bootstrap backend for platform {self.platform!r} — "
                "supported: macOS (Keychain) and Windows (CertStore)"
            )
        self.curl_path = (
            curl_path if curl_path is not None else _default_curl_path(self.platform)
        )

    # -- command construction (separated for testability) -----------------------------

    def command(self, jar_path: str) -> list[str]:
        """The curl argv for the bootstrap redirect chain."""
        cert = (
            rf"CurrentUser\MY\{self.identity}"
            if self.platform == "win32"
            else self.identity
        )
        return [
            self.curl_path,
            "--silent",
            "--show-error",
            "--location",  # follow the /my.policy -> /my.policy_nonce chain
            "--max-time",
            str(int(self.timeout)),
            "--cert",
            cert,
            "--cookie-jar",
            jar_path,
            "--cookie",
            jar_path,
            f"{SPV_BASE_URL}/listaMesaje?zile=1",
        ]

    def environment(self) -> dict[str, str]:
        """Process environment for curl (selects SecureTransport on macOS)."""
        env = dict(os.environ)
        if self.platform == "darwin":
            env["CURL_SSL_BACKEND"] = "secure-transport"
        return env

    # -- execution ---------------------------------------------------------------------

    async def _run_curl(self, jar_path: str) -> tuple[int, bytes, bytes]:
        """Run curl; returns ``(returncode, stdout, stderr)``. Overridable in tests."""
        process = await asyncio.create_subprocess_exec(
            *self.command(jar_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.environment(),
        )
        try:
            # curl enforces --max-time itself; the outer margin covers process spawn.
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout + 30
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise AnafAuthError(
                f"SPV bootstrap did not finish within {self.timeout:.0f}s — "
                "the certificate middleware may be stuck; retry (the 2FA prompt "
                "fires again)"
            ) from None
        return process.returncode or 0, stdout, stderr

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
        with tempfile.TemporaryDirectory(prefix="anafpy-spv-") as tmp_dir:
            jar_path = str(Path(tmp_dir) / "cookies.txt")
            returncode, stdout, stderr = await self._run_curl(jar_path)
            jar_text = ""
            jar = Path(jar_path)
            if jar.exists():
                jar_text = jar.read_text(encoding="utf-8")

        body = stdout.decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        answered = isinstance(payload, dict) and "titlu" in payload
        cookies = parse_netscape_cookies(jar_text)
        session = SpvSession(cookies=cookies, established_at=datetime.now(tz=UTC))
        if answered and session.is_authenticated_shape:
            return session

        if returncode == _CURL_EXIT_TIMEOUT:
            raise AnafAuthError(
                f"SPV handshake timed out after {self.timeout:.0f}s — the token "
                "PIN / 2FA authorization was not completed in time, or the "
                "middleware stalled (observed intermittently). Retry; the "
                "prompt fires again on every attempt."
            )
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise AnafAuthError(
                f"SPV handshake failed (curl exit {returncode}): "
                f"{detail or 'no error output'} — check that the identity "
                f"{self.identity!r} exists and its middleware is running"
            )
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
