"""Declaration MCP tool behaviour (DUK-free, credential-free).

The Java subprocess is faked by monkeypatching ``DukIntegrator._run``; signing
never runs (its confirm gate and its failure paths are what the tools promise).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from anafpy.declaratii.duk import DukIntegrator
from anafpy.mcp import create_server
from anafpy.mcp.config import ServerConfig


def _config(tmp_path: Path, *, with_duk: bool = True) -> ServerConfig:
    duk_dir: Path | None = None
    if with_duk:
        duk_dir = tmp_path / "dist"
        (duk_dir / "lib").mkdir(parents=True)
        (duk_dir / "DUKIntegrator.jar").write_text("")
        (duk_dir / "lib" / "D300Validator.jar").write_text("")
    return ServerConfig(
        client_id=None,
        client_secret=None,
        store_backend="file",
        store_path=tmp_path / "tokens.json",
        default_cif="8000000000",
        spv_identity_path=tmp_path / "spv-identity.json",
        duk_dir=duk_dir,
        duk_java="java",
    )


async def _call(server: Any, name: str, **arguments: Any) -> dict[str, Any]:
    _content, structured = await server.call_tool(name, arguments)
    return cast("dict[str, Any]", structured)


def _fake_run(err: str = "ok", *, write_pdf: bool = True) -> Any:
    async def run(self: DukIntegrator, args: list[str]) -> tuple[int, bytes, bytes]:
        Path(args[3]).write_text(err, encoding="utf-8")
        if write_pdf and "-p" in args and err.strip() == "ok":
            Path(args[-1]).write_bytes(b"%PDF-1.7\ncontent")
        return 0, b"", b""

    return run


# --- registration -----------------------------------------------------------------


async def test_tools_registered(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    names = {tool.name for tool in await server.list_tools()}
    assert {
        "declaratie_validate",
        "declaratie_render",
        "declaratie_sign",
        "declaratie_nr_evid",
        "declaratie_duk_status",
    } <= names


# --- nr_evid ----------------------------------------------------------------------


async def test_nr_evid_tool(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_nr_evid", tip_decont="L", luna=6, an=2026)
    assert result["nr_evid"] == "10301010626250726000042"


async def test_nr_evid_bad_tip_raises(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="tip_decont"):
        await _call(server, "declaratie_nr_evid", tip_decont="X", luna=6, an=2026)


# --- validate ---------------------------------------------------------------------


async def test_validate_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("ok"))
    server = create_server(_config(tmp_path))
    result = await _call(
        server, "declaratie_validate", document={"xml": "<x/>"}, form="D300"
    )
    assert result["ok"] is True
    assert result["findings"] == []


async def test_validate_reports_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        DukIntegrator, "_run", _fake_run("E: eroare regula: R25: campul lipseste")
    )
    server = create_server(_config(tmp_path))
    result = await _call(
        server, "declaratie_validate", document={"xml": "<x/>"}, form="D300"
    )
    assert result["ok"] is False
    assert "R25" in result["findings"][0]["message"]


async def test_validate_without_duk_configured(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_duk=False))
    result = await _call(
        server, "declaratie_validate", document={"xml": "<x/>"}, form="D300"
    )
    assert result["ok"] is False
    assert "ANAFPY_DUK_DIR" in result["message"]


# --- render -----------------------------------------------------------------------


async def test_render_writes_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("ok"))
    server = create_server(_config(tmp_path))
    out = tmp_path / "d300.pdf"
    result = await _call(
        server,
        "declaratie_render",
        document={"xml": "<x/>"},
        form="D300",
        save_pdf_as=str(out),
    )
    assert result["ok"] is True
    assert result["pdf_path"] == str(out)
    assert out.read_bytes().startswith(b"%PDF")


async def test_render_validation_failure_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("E: eroare: ceva"))
    server = create_server(_config(tmp_path))
    out = tmp_path / "d300.pdf"
    result = await _call(
        server,
        "declaratie_render",
        document={"xml": "<x/>"},
        form="D300",
        save_pdf_as=str(out),
    )
    assert result["ok"] is False
    assert result["findings"]
    assert not out.exists()


async def test_render_refuses_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("ok"))
    server = create_server(_config(tmp_path))
    out = tmp_path / "exists.pdf"
    out.write_bytes(b"old")
    result = await _call(
        server,
        "declaratie_render",
        document={"xml": "<x/>"},
        form="D300",
        save_pdf_as=str(out),
    )
    assert result["ok"] is False
    assert "overwrite" in result["message"]
    assert out.read_bytes() == b"old"


# --- sign -------------------------------------------------------------------------


async def test_sign_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = tmp_path / "d300.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    result = await _call(server, "declaratie_sign", pdf_path=str(pdf))
    assert result["signed"] is False
    assert "confirm=true" in result["guidance"]


async def test_sign_without_certificate_returns_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No ANAFPY_SIGN_IDENTITY and no persisted selection -> label resolution
    # fails cleanly, before any Keychain / platform call.
    monkeypatch.delenv("ANAFPY_SIGN_IDENTITY", raising=False)
    server = create_server(_config(tmp_path))
    pdf = tmp_path / "d300.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    result = await _call(server, "declaratie_sign", pdf_path=str(pdf), confirm=True)
    assert result["signed"] is False
    assert "certificate" in result["guidance"]


# --- duk_status -------------------------------------------------------------------


async def test_duk_status_unconfigured_raises(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_duk=False))
    with pytest.raises(ToolError, match="ANAFPY_DUK_DIR"):
        await _call(server, "declaratie_duk_status")


@respx.mock
async def test_duk_status_reports_staleness(tmp_path: Path) -> None:
    feed = '<versiuni><element nume="D300Validator.jar" versiune="J13.0.0"/></versiuni>'
    respx.get("http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(200, text=feed)
    )
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_duk_status")
    assert "installed_forms" in result
    forms = {entry["form"]: entry for entry in result["forms"]}
    # Installed version is "unknown" (no history file), feed says J13.0.0 -> stale.
    assert forms["D300"]["current"] == "J13.0.0"
    assert forms["D300"]["stale"] is True
