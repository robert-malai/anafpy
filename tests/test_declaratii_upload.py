"""Tests for the WAS6DUS portal upload client — choreography and page parsing.

Credential-free: the curl subprocess is faked by overriding ``_run_curl`` and
the upload POST is respx-mocked. The success-page parse follows the page
live-captured by the first D406T test filing; its tests pin the contract:
known rejection page -> returned business outcome,
unknown page -> ``accepted=None`` with the raw HTML carried.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from anafpy.declaratii import DeclarationUploadClient, PortalCurlBootstrapper
from anafpy.declaratii.upload import PORTAL_BASE_URL, _parse_upload_page
from anafpy.exceptions import AnafAuthError, AnafConfigError

_LOGON_PAGE = "<html><form>Prezentare certificat</form></html>"
_UPLOAD_FORM = (
    '<html><form name="uf" method="POST" action="/WAS6DUS/displayFile.do"'
    ' enctype="multipart/form-data"><input type="file" name="linkdoc"></form></html>'
)
_REJECTION_PAGE = (
    "<html><body>Ne cerem scuze, dar cererea dumneavoastra nu a putut fi "
    'indeplinita!<br>Motivul: <span style="color: red">Nu ati selectat fisierul '
    "ce urmeaza a fi transmis</span>"
    '<a href="/WAS6DUS/welcome.do">aici</a></body></html>'
)
# The real success page, live-captured 2026-07-17 (D406T filing; the full page
# is _sources/decl-portal/upload-response-d406t.html) — key markup verbatim.
_SUCCESS_PAGE = (
    "<table><tr><td><em><h2>Agentia Nationala de Administrare Fiscala</h2>"
    "<br><br>Succes depunere</em>"
    "<p>Fi&#351;ierul dumneavoastr&#259; cu numele "
    '<font color="blue">"d406t.pdf</font>" a fost depus cu succes. Indexul '
    'este <b style="color: #000000">1100000005</b>.</p>'
    "<p><b> Acest mesaj nu constituie confirmarea inregistr&#259;rii "
    "documentului. Confirmarea depunerii va fi afisat&#259; in recipis&#259;. "
    "</b></p></td></tr></table>"
)


class FakeBootstrapper(PortalCurlBootstrapper):
    """A bootstrapper whose curl steps are canned ``(code, stdout, stderr)``."""

    def __init__(
        self,
        *steps: tuple[int, bytes, bytes],
        cookies: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__("Test Identity", platform="darwin", **kwargs)  # type: ignore[arg-type]
        self.steps = list(steps)
        self.cookie_jar_text = cookies
        self.commands_run: list[list[str]] = []

    async def _run_curl(self, argv: list[str]) -> tuple[int, bytes, bytes]:
        self.commands_run.append(argv)
        # The jar path rides in the argv; write the canned jar alongside.
        jar = argv[argv.index("--cookie-jar") + 1]
        Path(jar).write_text(self.cookie_jar_text, encoding="utf-8")
        return self.steps.pop(0)


_JAR = (
    "# Netscape HTTP Cookie File\n"
    "#HttpOnly_decl.anaf.mfinante.gov.ro\tFALSE\t/\tTRUE\t0\tMRHSession\tabc123\n"
    "decl.anaf.mfinante.gov.ro\tFALSE\t/\tFALSE\t0\tJSESSIONID\tdef456\n"
)


def _ok_steps() -> list[tuple[int, bytes, bytes]]:
    return [
        (0, _LOGON_PAGE.encode(), b""),
        (0, b"", b""),
        # Success despite exit 56 — the F5 no-close_notify quirk.
        (56, _UPLOAD_FORM.encode(), b"SSLRead() error -9806"),
    ]


# -- bootstrapper ------------------------------------------------------------------


def test_bootstrap_command_choreography() -> None:
    boot = FakeBootstrapper((0, b"", b""), (0, b"", b""), (0, b"", b""))
    commands = boot.commands("/tmp/jar.txt")
    assert len(commands) == 3
    prime, logon_post, cert_get = commands
    assert prime[-1] == f"{PORTAL_BASE_URL}/WAS6DUS/"
    assert "--location" in prime and "--cert" not in prime
    # The logon POST must not follow its redirect and must not present the cert.
    assert logon_post[-1] == f"{PORTAL_BASE_URL}/my.policy"
    assert "--data" in logon_post
    assert "--location" not in logon_post and "--cert" not in logon_post
    # The certificate step presents the identity and follows the nonce chain.
    assert cert_get[-1] == f"{PORTAL_BASE_URL}/my.policy"
    assert "--cert" in cert_get and "--location" in cert_get
    assert cert_get[cert_get.index("--cert") + 1] == "Test Identity"


def test_bootstrap_windows_cert_syntax() -> None:
    boot = PortalCurlBootstrapper("AB12", platform="win32", curl_path="curl.exe")
    cert_get = boot.commands("jar")[-1]
    assert cert_get[cert_get.index("--cert") + 1] == r"CurrentUser\MY\AB12"


def test_bootstrap_unsupported_platform() -> None:
    with pytest.raises(AnafConfigError, match="no portal login backend"):
        PortalCurlBootstrapper("x", platform="linux")


def test_bootstrap_env_pins_tls_backend() -> None:
    boot = PortalCurlBootstrapper("x", platform="darwin", curl_path="curl")
    assert boot.environment()["CURL_SSL_BACKEND"] == "secure-transport"
    boot = PortalCurlBootstrapper("x", platform="win32", curl_path="curl")
    assert boot.environment()["CURL_SSL_BACKEND"] == "schannel"


async def test_bootstrap_success_despite_exit_56() -> None:
    boot = FakeBootstrapper(*_ok_steps(), cookies=_JAR)
    cookies = await boot.bootstrap()
    assert cookies["MRHSession"] == "abc123"
    assert cookies["JSESSIONID"] == "def456"
    assert len(boot.commands_run) == 3


async def test_bootstrap_timeout_exit_raises_2fa_hint() -> None:
    boot = FakeBootstrapper((0, b"", b""), (0, b"", b""), (28, b"", b""), cookies=_JAR)
    with pytest.raises(AnafAuthError, match="2FA"):
        await boot.bootstrap()


async def test_bootstrap_stops_at_first_failing_step() -> None:
    boot = FakeBootstrapper(
        (0, b"", b""),
        (56, b"", b"connection reset by peer"),
        (0, _UPLOAD_FORM.encode(), b""),
        cookies=_JAR,
    )
    with pytest.raises(AnafAuthError, match=r"step 2.*connection reset"):
        await boot.bootstrap()
    assert len(boot.commands_run) == 2


async def test_bootstrap_hangup_page_raises() -> None:
    boot = FakeBootstrapper(
        (0, b"", b""), (0, b"", b""), (0, b"<html>hangup</html>", b""), cookies=_JAR
    )
    with pytest.raises(AnafAuthError, match="did not reach the upload app"):
        await boot.bootstrap()


async def test_bootstrap_no_session_cookie_raises() -> None:
    boot = FakeBootstrapper(*_ok_steps(), cookies="")
    with pytest.raises(AnafAuthError):
        await boot.bootstrap()


# -- upload client -----------------------------------------------------------------


def _client(**kwargs: object) -> DeclarationUploadClient:
    http = httpx.AsyncClient(base_url=PORTAL_BASE_URL, follow_redirects=True)
    http.cookies.set("MRHSession", "abc123")
    http.cookies.set("JSESSIONID", "def456")
    return DeclarationUploadClient(http=http, **kwargs)  # type: ignore[arg-type]


@respx.mock
async def test_upload_rejection_is_returned() -> None:
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text=_REJECTION_PAGE)
    )
    async with _client() as client:
        result = await client.upload(b"%PDF-1.7", filename="d406t.pdf")
    assert result.accepted is False
    assert result.reason is not None
    assert "Nu ati selectat fisierul" in result.reason


@respx.mock
async def test_upload_success_page_yields_index() -> None:
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text=_SUCCESS_PAGE)
    )
    async with _client() as client:
        result = await client.upload(b"%PDF-1.7", filename="d406t.pdf")
    assert result.accepted is True
    assert result.upload_index == "1100000005"


async def test_injected_client_without_base_url_raises_config_error() -> None:
    # An injected client is never mutated: an empty base_url is a
    # misconfiguration, named loudly at construction.
    async with httpx.AsyncClient() as http:
        http.cookies.set("MRHSession", "abc123")
        with pytest.raises(AnafConfigError, match=PORTAL_BASE_URL):
            DeclarationUploadClient(http=http)


@respx.mock
async def test_upload_unknown_page_carries_html() -> None:
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text="<html>ceva nou</html>")
    )
    async with _client() as client:
        result = await client.upload(b"%PDF-1.7", filename="d406t.pdf")
    assert result.accepted is None
    assert "ceva nou" in result.html


@respx.mock
async def test_upload_login_wall_bounce_raises() -> None:
    # The 302 must NOT be followed (httpx would re-issue a body-less GET):
    # the redirect itself raises, and no request ever hits /my.policy.
    route = respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(
            302, headers={"Location": f"{PORTAL_BASE_URL}/my.policy"}
        )
    )
    async with _client() as client:
        with pytest.raises(AnafAuthError, match="session expired"):
            await client.upload(b"%PDF-1.7", filename="d406t.pdf")
    assert route.call_count == 1


@respx.mock
async def test_upload_revalidation_hop_raises_not_misreports() -> None:
    # An APM /my.policy_nonce revalidation 302 on the POST is a session event
    # (raised), never followed into a body-less GET whose "no file selected"
    # error page would misread as a business rejection.
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(
            302,
            headers={"Location": f"{PORTAL_BASE_URL}/my.policy_nonce?nonce=x"},
        )
    )
    async with _client() as client:
        with pytest.raises(AnafAuthError, match=r"my\.policy_nonce"):
            await client.upload(b"%PDF-1.7", filename="d406t.pdf")


@respx.mock
async def test_upload_sends_linkdoc_multipart() -> None:
    route = respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text=_REJECTION_PAGE)
    )
    async with _client() as client:
        await client.upload(b"%PDF-1.7 payload", filename="d406t_test.pdf")
    request = route.calls.last.request
    body = request.content
    assert b'name="linkdoc"' in body
    assert b'filename="d406t_test.pdf"' in body
    assert b"%PDF-1.7 payload" in body


async def test_upload_without_session_raises() -> None:
    async with DeclarationUploadClient() as client:
        with pytest.raises(AnafConfigError, match="login"):
            await client.upload(b"%PDF-1.7", filename="x.pdf")


async def test_login_without_bootstrapper_raises() -> None:
    async with DeclarationUploadClient() as client:
        with pytest.raises(AnafConfigError, match="no bootstrapper"):
            await client.login()


async def test_login_installs_cookies() -> None:
    boot = FakeBootstrapper(*_ok_steps(), cookies=_JAR)
    async with DeclarationUploadClient(bootstrapper=boot) as client:
        await client.login()
        assert client._http.cookies["MRHSession"] == "abc123"


async def test_login_scopes_cookies_to_portal_host() -> None:
    # The bearer cookies must be domain-scoped: httpx's default empty domain
    # would send MRHSession to ANY host an off-portal redirect lands on.
    boot = FakeBootstrapper(*_ok_steps(), cookies=_JAR)
    async with DeclarationUploadClient(bootstrapper=boot) as client:
        await client.login()
        domains = {cookie.domain for cookie in client._http.cookies.jar}
        assert domains == {"decl.anaf.mfinante.gov.ro"}


async def test_install_session_scopes_cookies_to_portal_host() -> None:
    # The seam callers with their own bootstrap use — same scoping as login().
    async with DeclarationUploadClient() as client:
        client.install_session({"MRHSession": "abc123"})
        domains = {cookie.domain for cookie in client._http.cookies.jar}
        assert domains == {"decl.anaf.mfinante.gov.ro"}


# -- session probe -----------------------------------------------------------------


@respx.mock
async def test_probe_active_session_sees_upload_form() -> None:
    route = respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    async with _client() as client:
        assert await client.probe() is True
    assert route.call_count == 1


@respx.mock
async def test_probe_logon_page_answer_is_false() -> None:
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_LOGON_PAGE)
    )
    async with _client() as client:
        assert await client.probe() is False


@respx.mock
async def test_probe_follows_bounce_to_logon_page() -> None:
    # Unlike the upload POST, the probe GET follows the APM bounce — landing
    # anywhere but the upload form is simply "not logged in".
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(
            302, headers={"Location": f"{PORTAL_BASE_URL}/my.policy"}
        )
    )
    respx.get(f"{PORTAL_BASE_URL}/my.policy").mock(
        return_value=httpx.Response(200, text=_LOGON_PAGE)
    )
    async with _client() as client:
        assert await client.probe() is False


@respx.mock
async def test_probe_without_cookies_is_false_with_no_network_call() -> None:
    # respx would raise on any unmatched request — none may happen.
    async with DeclarationUploadClient() as client:
        assert await client.probe() is False


# -- page parsing ------------------------------------------------------------------


def test_parse_rejection_reason_from_red_span() -> None:
    result = _parse_upload_page(_REJECTION_PAGE)
    assert result.accepted is False
    assert result.reason == "Nu ati selectat fisierul ce urmeaza a fi transmis"


def test_parse_rejection_reason_includes_inline_markup() -> None:
    html = (
        "<html>Ne cerem scuze. Motivul: "
        '<span style="color:red">Semnatura <b>nu este valida</b><br>pentru CUI</span>'
        "</html>"
    )
    result = _parse_upload_page(html)
    assert result.reason == "Semnatura nu este valida pentru CUI"


def test_parse_success_page_with_diacritics() -> None:
    # Diacritics survive: "depus cu succes" rides accent-stripped matching.
    html = "<html>Fișierul a fost depus cu succes. Indexul este 987654321</html>"
    result = _parse_upload_page(html)
    assert result.accepted is True
    assert result.upload_index == "987654321"


def test_parse_success_ignores_index_like_filename() -> None:
    html = (
        '<html>Fișierul "index_20260630.pdf" a fost depus cu succes. '
        "Indexul este <b>1100000005</b>.</html>"
    )
    result = _parse_upload_page(html)
    assert result.upload_index == "1100000005"


def test_parse_index_without_success_marker_is_unrecognised() -> None:
    # A stray number near "index" alone must not read as an accepted filing.
    html = "<html>Indexul dumneavoastra: 987654321</html>"
    result = _parse_upload_page(html)
    assert result.accepted is None
    assert result.upload_index is None
