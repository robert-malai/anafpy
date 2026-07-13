"""Tests for the curl session bootstrapper and its cookie-jar parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anafpy.exceptions import AnafAuthError, AnafConfigError
from anafpy.spv import CurlBootstrapper
from anafpy.spv.bootstrap import parse_netscape_cookies

OK_BODY = json.dumps(
    {"titlu": "Lista Mesaje", "eroare": "Nu exista mesaje in ultimele 1 zile"}
).encode()

JAR_TEXT = (
    "# Netscape HTTP Cookie File\n"
    "# https://curl.se/docs/http-cookies.html\n"
    "\n"
    "webserviced.anaf.ro\tFALSE\t/\tTRUE\t0\tMRHSession\tf5ac3b0f17212f25\n"
    "#HttpOnly_webserviced.anaf.ro\tFALSE\t/\tTRUE\t0\tLastMRH_Session\tdb869b1f\n"
    "webserviced.anaf.ro\tFALSE\t/\tTRUE\t0\tF5_ST\t1z1z1z1783875207z-1\n"
)


class ScriptedBootstrapper(CurlBootstrapper):
    """A CurlBootstrapper whose curl run is scripted, not executed."""

    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: bytes = OK_BODY,
        jar_text: str | None = JAR_TEXT,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("identity", "MIHAI-ROBERT MALAI")
        kwargs.setdefault("platform", "darwin")
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._scripted = (returncode, stdout)
        self._jar_text = jar_text

    async def _run_curl(self, jar_path: str) -> tuple[int, bytes, bytes]:
        if self._jar_text is not None:
            Path(jar_path).write_text(self._jar_text, encoding="utf-8")
        returncode, stdout = self._scripted
        return returncode, stdout, b"curl said something"


# --- cookie jar parsing ---------------------------------------------------------------


def test_netscape_jar_parsing_includes_httponly_lines() -> None:
    cookies = parse_netscape_cookies(JAR_TEXT)
    assert cookies == {
        "MRHSession": "f5ac3b0f17212f25",
        "LastMRH_Session": "db869b1f",
        "F5_ST": "1z1z1z1783875207z-1",
    }


def test_netscape_jar_parsing_skips_comments_and_junk() -> None:
    assert parse_netscape_cookies("# only comments\n\nnot-a-cookie-line\n") == {}


# --- command construction -------------------------------------------------------------


def test_macos_command_uses_secure_transport_and_the_identity_name() -> None:
    bootstrapper = CurlBootstrapper("My Identity", platform="darwin")
    command = bootstrapper.command("/tmp/jar.txt")
    assert command[0] == "/usr/bin/curl"
    assert command[command.index("--cert") + 1] == "My Identity"
    assert "--location" in command
    assert bootstrapper.environment()["CURL_SSL_BACKEND"] == "secure-transport"
    assert command[-1].endswith("listaMesaje?zile=1")


def test_windows_command_uses_the_cert_store_syntax() -> None:
    bootstrapper = CurlBootstrapper("C5E18AB5", platform="win32")
    command = bootstrapper.command("jar.txt")
    assert command[0].endswith("curl.exe")
    assert "System32" in command[0]
    assert command[command.index("--cert") + 1] == r"CurrentUser\MY\C5E18AB5"
    assert "CURL_SSL_BACKEND" not in bootstrapper.environment() or (
        bootstrapper.environment().get("CURL_SSL_BACKEND") != "secure-transport"
    )


def test_unsupported_platform_is_a_config_error() -> None:
    with pytest.raises(AnafConfigError, match="platform"):
        CurlBootstrapper("x", platform="linux")


def test_empty_identity_is_a_config_error() -> None:
    with pytest.raises(AnafConfigError, match="identity"):
        CurlBootstrapper("")


# --- bootstrap outcomes ---------------------------------------------------------------


async def test_bootstrap_success_returns_the_cookie_session() -> None:
    session = await ScriptedBootstrapper().bootstrap()
    assert session.cookies["MRHSession"] == "f5ac3b0f17212f25"
    assert session.is_authenticated_shape


async def test_bootstrap_timeout_names_the_2fa() -> None:
    with pytest.raises(AnafAuthError, match="2FA"):
        await ScriptedBootstrapper(returncode=28, stdout=b"").bootstrap()


async def test_bootstrap_success_despite_curl_exit_56() -> None:
    # ANAF's F5 closes without a TLS close_notify: a fully successful handshake
    # still exits 56 (SSLRead -9806, live-observed) — the payload decides.
    session = await ScriptedBootstrapper(returncode=56).bootstrap()
    assert session.is_authenticated_shape


async def test_bootstrap_curl_failure_carries_stderr() -> None:
    with pytest.raises(AnafAuthError, match="curl said something"):
        await ScriptedBootstrapper(returncode=58, stdout=b"").bootstrap()


async def test_bootstrap_html_body_means_no_spv_access() -> None:
    with pytest.raises(AnafAuthError, match=r"hangup|did not reach"):
        await ScriptedBootstrapper(stdout=b"<html>APM wall</html>").bootstrap()


async def test_bootstrap_without_session_cookie_fails_loudly() -> None:
    with pytest.raises(AnafAuthError, match="MRHSession"):
        await ScriptedBootstrapper(jar_text="# empty jar\n").bootstrap()
