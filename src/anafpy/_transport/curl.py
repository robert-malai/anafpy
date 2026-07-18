"""Shared platform-curl machinery for ANAF's F5 APM certificate logins.

Two ANAF surfaces sit behind the same F5 BigIP APM model — SPV
(``webserviced.anaf.ro``, see :mod:`anafpy.spv.bootstrap`) and the declaration
upload portal (``decl.anaf.mfinante.gov.ro``, see
:mod:`anafpy.declaratii.upload`): one interactive certificate handshake (which
fires the token PIN / 2FA) mints a cookie session that every later request
rides. CPython's ``ssl`` cannot present a non-exportable platform-store key,
so that handshake is driven through the **OS-shipped curl** against the
platform key store — macOS SecureTransport takes the identity by Keychain
name, Windows Schannel by ``CurrentUser\\MY`` thumbprint.

This module is the single home for everything the two bootstrappers share:
curl resolution (including the ``ANAFPY_CURL`` override, covering **both**
bootstraps), the certificate selector syntax, the
TLS-backend pin, the subprocess runner with its 2FA-aware timeout, the
cookie-jar plumbing, and the common curl-level failure taxonomy. What stays in
each subclass is exactly what differs per service: the request choreography
(:meth:`CurlBootstrapperBase.commands`) and how success is judged from the
final payload (their ``bootstrap()``).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import ClassVar

from ..exceptions import AnafAuthError, AnafConfigError
from .subprocess import run_subprocess

__all__ = ["CurlBootstrapperBase", "default_curl_path", "parse_netscape_cookies"]

# curl's exit code for `--max-time` expiry — almost always an unanswered 2FA.
_CURL_EXIT_TIMEOUT = 28


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


def default_curl_path(platform: str) -> str:
    """``ANAFPY_CURL`` if set, else the OS-shipped curl.

    Deliberately not whatever is first on ``PATH``: a Homebrew curl (macOS)
    or a curl.se Windows build lacks the platform TLS backend
    (SecureTransport / Schannel) and would reject the platform cert-store
    ``--cert`` syntax. One known case *needs* the override: on **Windows on
    ARM** with x64-only vendor middleware (e.g. certSIGN Paperless vToken,
    observed 2026-07-13) the ARM64 System32 curl cannot load the key-storage
    provider — point ``ANAFPY_CURL`` (or ``curl_path``) at an **x64**
    Schannel curl (Git for Windows' ``mingw64\\bin\\curl.exe`` is one; it is
    multi-backend, which is why :meth:`CurlBootstrapperBase.environment` pins
    ``CURL_SSL_BACKEND`` on Windows too). See the SPV reference §1.1.
    """
    if override := os.environ.get("ANAFPY_CURL"):
        return override
    if platform == "win32":
        system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
        return str(Path(system_root) / "System32" / "curl.exe")
    return "/usr/bin/curl"


class CurlBootstrapperBase:
    """Common base of the APM certificate bootstrappers.

    Subclasses define :meth:`commands` (the choreography — one or more curl
    invocations sharing a cookie jar) and a ``bootstrap()`` that calls
    :meth:`run_chain`, judges the final **payload** (ANAF's F5 closes the last
    connection without a TLS ``close_notify``, so a fully successful login can
    still exit 56 — never judge by the exit code), and falls back to
    :meth:`raise_curl_failure` for the shared curl-level failure taxonomy.

    Args:
        identity: which certificate to present — the Keychain identity **name**
            on macOS, the SHA-1 **thumbprint** in ``CurrentUser\\MY`` on
            Windows.
        timeout: seconds to wait per curl step, 2FA included. The
            authorization prompt fires on every bootstrap, so keep this
            generous.
        curl_path: override the curl binary (tests, exotic installs); the
            ``ANAFPY_CURL`` environment variable does the same for the
            CLI and the MCP server (see :func:`default_curl_path`).
        platform: override ``sys.platform`` (tests).
    """

    #: Human label used in error messages ("SPV bootstrap", "portal login").
    context: ClassVar[str] = "certificate login"

    def __init__(
        self,
        identity: str,
        *,
        timeout: float = 240.0,
        curl_path: str | None = None,
        platform: str | None = None,
    ) -> None:
        if not identity:
            raise AnafConfigError(
                f"{type(self).__name__}: `identity` must be non-empty"
            )
        self.identity = identity
        self.timeout = timeout
        self.platform = platform if platform is not None else sys.platform
        if self.platform not in ("darwin", "win32"):
            raise AnafConfigError(
                f"no {self.context} backend for platform {self.platform!r} — "
                "supported: macOS (Keychain) and Windows (CertStore)"
            )
        self.curl_path = (
            curl_path if curl_path is not None else default_curl_path(self.platform)
        )

    # -- command construction (separated for testability) -----------------------------

    @property
    def cert_selector(self) -> str:
        """The ``--cert`` value for the platform key store."""
        return (
            rf"CurrentUser\MY\{self.identity}"
            if self.platform == "win32"
            else self.identity
        )

    def curl_base(self, jar_path: str) -> list[str]:
        """The shared flag prefix every choreography step starts from."""
        return [
            self.curl_path,
            "--silent",
            "--show-error",
            "--max-time",
            str(int(self.timeout)),
            "--cookie-jar",
            jar_path,
            "--cookie",
            jar_path,
        ]

    def commands(self, jar_path: str) -> list[list[str]]:
        """The curl invocations of the login choreography, in order."""
        raise NotImplementedError

    def environment(self) -> dict[str, str]:
        """Process environment for curl — pins the platform TLS backend.

        Single-backend builds ignore ``CURL_SSL_BACKEND``; setting it matters
        for multi-backend ones (a Git-for-Windows curl defaults to OpenSSL,
        which rejects the CertStore ``--cert`` syntax).
        """
        env = dict(os.environ)
        env["CURL_SSL_BACKEND"] = (
            "secure-transport" if self.platform == "darwin" else "schannel"
        )
        return env

    # -- execution ---------------------------------------------------------------------

    async def _run_curl(self, argv: list[str]) -> tuple[int, bytes, bytes]:
        """Run one curl step; returns ``(returncode, stdout, stderr)``."""
        try:
            # curl enforces --max-time itself; the outer margin covers process spawn.
            return await run_subprocess(
                argv,
                timeout=self.timeout + 30,
                env=self.environment(),
            )
        except TimeoutError:
            raise AnafAuthError(
                f"{self.context} did not finish within {self.timeout:.0f}s — "
                "the certificate middleware may be stuck; retry (the 2FA prompt "
                "fires again)"
            ) from None

    async def run_chain(self) -> tuple[int, bytes, bytes, dict[str, str]]:
        """Run :meth:`commands` sequentially over one temporary cookie jar.

        Returns the **last** step's ``(returncode, stdout, stderr)`` plus the
        jar's final cookie set.
        """
        with tempfile.TemporaryDirectory(prefix="anafpy-curl-") as tmp_dir:
            jar_path = str(Path(tmp_dir) / "cookies.txt")
            returncode, stdout, stderr = 0, b"", b""
            commands = self.commands(jar_path)
            for step, argv in enumerate(commands, start=1):
                returncode, stdout, stderr = await self._run_curl(argv)
                if returncode != 0 and step < len(commands):
                    # Only the final payload can redeem ANAF's observed curl-56
                    # close-notify quirk. An earlier failed step dooms the
                    # choreography, so stop before a later certificate step can
                    # fire the user's 2FA.
                    self.raise_curl_failure(returncode, stderr, step=step)
            jar_text = ""
            jar = Path(jar_path)
            if jar.exists():
                jar_text = jar.read_text(encoding="utf-8")
        return returncode, stdout, stderr, parse_netscape_cookies(jar_text)

    def raise_curl_failure(
        self, returncode: int, stderr: bytes, *, step: int | None = None
    ) -> None:
        """Raise for the curl-level failures; return when the body must judge.

        Call **after** the payload said "not success": exit 28 is the
        unanswered 2FA, any other non-zero exit is a hard curl failure. A zero
        exit returns — the caller then raises its service-specific
        wrong-payload error.
        """
        step_text = f" step {step}" if step is not None else ""
        if returncode == _CURL_EXIT_TIMEOUT:
            raise AnafAuthError(
                f"{self.context}{step_text} timed out after {self.timeout:.0f}s — the "
                "token PIN / 2FA authorization was not completed in time, or "
                "the middleware stalled (observed intermittently). Retry; the "
                "prompt fires again on every attempt."
            )
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise AnafAuthError(
                f"{self.context}{step_text} failed (curl exit {returncode}): "
                f"{detail or 'no error output'} — check that the identity "
                f"{self.identity!r} exists and its middleware is running"
            )
