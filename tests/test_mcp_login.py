"""auth_login MCP tool behaviour (fake listener + fake browser, mocked exchange)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, cast

import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError

from anafpy.auth import FileTokenStore
from anafpy.exceptions import AnafAuthError, AnafConfigError
from anafpy.mcp import create_server
from anafpy.mcp.config import ServerConfig

TOKEN_URL = "https://logincert.anaf.ro/anaf-oauth2/v1/token"

TOKEN_BODY = {"access_token": "A", "refresh_token": "R", "expires_in": 3600}

#: Authorize URLs the fake browser was asked to open.
opened: list[str] = []


def _config(tmp_path: Path, **overrides: Any) -> ServerConfig:
    return ServerConfig(
        client_id="test-client-id",
        client_secret="test-client-secret",
        store_backend="file",
        store_path=tmp_path / "tokens.json",
        **overrides,
    )


async def _call(server: Any, name: str, **arguments: Any) -> dict[str, Any]:
    result = await server.call_tool(name, arguments)
    return cast("dict[str, Any]", result.structured_content)


class FakeListener:
    """Stands in for CallbackListener inside the auth_login tool."""

    instances: ClassVar[list[FakeListener]] = []
    code: ClassVar[str | None] = "anaf-code"
    error: ClassVar[str | None] = None
    bind_error: ClassVar[str | None] = None

    def __init__(
        self,
        redirect_uri: str,
        *,
        ssl_context: object = None,
        expected_state: str | None = None,
    ) -> None:
        if FakeListener.bind_error is not None:
            raise AnafConfigError(FakeListener.bind_error)
        self.redirect_uri = redirect_uri
        self.ssl_context = ssl_context
        self.expected_state = expected_state
        self.wait_timeout: float | None = None
        self.closed = False
        FakeListener.instances.append(self)

    def __enter__(self) -> FakeListener:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.closed = True

    def wait(self, timeout: float = 180.0) -> str | None:
        self.wait_timeout = timeout
        if FakeListener.error is not None:
            raise AnafAuthError(FakeListener.error)
        return FakeListener.code


@pytest.fixture(autouse=True)
def _fake_login_plumbing(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeListener.instances = []
    FakeListener.code = "anaf-code"
    FakeListener.error = None
    FakeListener.bind_error = None
    opened.clear()
    monkeypatch.setattr("anafpy.mcp.login.CallbackListener", FakeListener)

    def open_browser(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr(
        "anafpy.mcp.login.webbrowser", SimpleNamespace(open=open_browser)
    )


async def test_login_without_confirm_is_refused(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="explicit approval"):
        await _call(server, "auth_login")
    assert not opened  # no browser fired without the gate


async def test_login_without_credentials_is_actionable(tmp_path: Path) -> None:
    server = create_server(
        ServerConfig(
            client_id=None,
            client_secret=None,
            store_backend="file",
            store_path=tmp_path / "tokens.json",
        )
    )
    with pytest.raises(ToolError, match="ANAFPY_CLIENT_ID"):
        await _call(server, "auth_login", confirm=True)


@respx.mock
async def test_login_succeeds_and_persists_the_tokens(tmp_path: Path) -> None:
    route = respx.post(TOKEN_URL).respond(json=TOKEN_BODY)
    server = create_server(_config(tmp_path))

    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is True
    assert result["status"]["authenticated"] is True
    # The shared store holds the tokens (the provider re-reads it — no restart).
    saved = FileTokenStore(tmp_path / "tokens.json").load()
    assert saved is not None
    assert saved.access_token == "A"
    # The exchange carried the captured code and the configured redirect URI.
    body = urllib.parse.parse_qs(route.calls.last.request.content.decode())
    assert body["code"] == ["anaf-code"]
    assert body["redirect_uri"] == ["https://localhost:9002/callback"]
    # State binding: the opened authorize URL carries the state the listener
    # demands back, and the https redirect got an ephemeral TLS context.
    listener = FakeListener.instances[0]
    query = urllib.parse.parse_qs(urllib.parse.urlparse(opened[0]).query)
    assert listener.expected_state is not None
    assert query["state"] == [listener.expected_state]
    assert listener.ssl_context is not None
    assert listener.closed


async def test_login_timeout_reports_the_url_and_the_fallback(
    tmp_path: Path,
) -> None:
    FakeListener.code = None
    server = create_server(_config(tmp_path))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is False
    assert "logincert.anaf.ro" in result["authorize_url"]
    assert "anafpy auth login" in result["next_step"]


async def test_login_denied_certificate_is_a_graceful_answer(
    tmp_path: Path,
) -> None:
    FakeListener.error = "authorization failed: access_denied"
    server = create_server(_config(tmp_path))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is False
    assert "access_denied" in result["detail"]
    assert "go-ahead" in result["next_step"]


async def test_login_bind_failure_points_to_the_terminal(tmp_path: Path) -> None:
    FakeListener.bind_error = "cannot bind callback listener on localhost:9002"
    server = create_server(_config(tmp_path))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is False
    assert "cannot bind" in result["detail"]
    assert "anafpy auth login" in result["next_step"]


async def test_login_without_a_browser_points_to_the_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "anafpy.mcp.login.webbrowser", SimpleNamespace(open=lambda url: False)
    )
    server = create_server(_config(tmp_path))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is False
    assert "authorize_url" in result
    assert "anafpy auth login" in result["next_step"]
    assert FakeListener.instances[0].closed  # no dangling listener


@respx.mock
async def test_login_expired_code_suggests_a_fresh_attempt(tmp_path: Path) -> None:
    respx.post(TOKEN_URL).respond(400, json={"error": "invalid_grant"})
    server = create_server(_config(tmp_path))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is False
    assert "invalid_grant" in result["detail"]
    assert "again" in result["next_step"]
    assert FileTokenStore(tmp_path / "tokens.json").load() is None


async def test_login_timeout_is_clamped(tmp_path: Path) -> None:
    FakeListener.code = None  # short-circuit after the wait
    server = create_server(_config(tmp_path))
    await _call(server, "auth_login", confirm=True, timeout_s=9999)
    assert FakeListener.instances[0].wait_timeout == 300.0


@respx.mock
async def test_custom_http_redirect_skips_tls(tmp_path: Path) -> None:
    # An http:// redirect means an external TLS terminator fronts the listener.
    respx.post(TOKEN_URL).respond(json=TOKEN_BODY)
    server = create_server(_config(tmp_path, redirect_uri="http://localhost:7777/cb"))
    result = await _call(server, "auth_login", confirm=True)
    assert result["logged_in"] is True
    listener = FakeListener.instances[0]
    assert listener.redirect_uri == "http://localhost:7777/cb"
    assert listener.ssl_context is None


async def test_login_is_annotated_as_mutating(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    tool = next(t for t in await server.list_tools() if t.name == "auth_login")
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.idempotent_hint is False


def test_blank_redirect_uri_falls_back_to_the_default() -> None:
    config = ServerConfig(redirect_uri="")
    assert config.redirect_uri == "https://localhost:9002/callback"
