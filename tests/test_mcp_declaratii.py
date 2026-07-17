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


def _config(
    tmp_path: Path,
    *,
    with_duk: bool = True,
    default_cif: str | None = "8000000000",
) -> ServerConfig:
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
        default_cif=default_cif,
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
        "declaratie_status",
        "declaratie_recipisa",
    } <= names


# --- nr_evid ----------------------------------------------------------------------


async def test_nr_evid_tool(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(
        server, "declaratie_nr_evid", tip_decont="L", month=6, year=2026
    )
    assert result["nr_evid"] == "10301010626250726000042"
    assert result["month"] == 6
    assert result["year"] == 2026


async def test_nr_evid_bad_tip_raises(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="tip_decont"):
        await _call(server, "declaratie_nr_evid", tip_decont="X", month=6, year=2026)


async def test_nr_evid_d100_obligation(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(
        server,
        "declaratie_nr_evid",
        form="D100",
        cod_oblig="604",
        scadenta="25.07.2026",
        month=6,
        year=2026,
    )
    assert result["nr_evid"] == "10604010626250726000048"
    assert result["form"] == "D100"
    assert result["cod_oblig"] == "604"


async def test_nr_evid_d301_new_transport(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(
        server,
        "declaratie_nr_evid",
        form="D301",
        mijl_trans=True,
        month=6,
        year=2026,
    )
    assert result["nr_evid"] == "10301010626250726100043"
    assert result["nr_evid"][17] == "1"


async def test_nr_evid_d100_missing_scadenta_raises(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="scadenta"):
        await _call(
            server,
            "declaratie_nr_evid",
            form="D100",
            cod_oblig="604",
            month=6,
            year=2026,
        )


async def test_nr_evid_unknown_form_raises(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="unknown form"):
        await _call(server, "declaratie_nr_evid", form="D999", month=6, year=2026)


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


async def test_validate_unparseable_err_explains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A broken/mis-versioned dist leaves err output the parser cannot read; the
    # fail-closed ok=false must carry a diagnostic, not empty findings + empty
    # message (which would steer the model into rewriting possibly-valid XML).
    monkeypatch.setattr(
        DukIntegrator, "_run", _fake_run("java.lang.NoClassDefFoundError: D300")
    )
    server = create_server(_config(tmp_path))
    result = await _call(
        server, "declaratie_validate", document={"xml": "<x/>"}, form="D300"
    )
    assert result["ok"] is False
    assert result["findings"] == []
    assert "declaratie_duk_status" in result["message"]
    assert "NoClassDefFoundError" in result["message"]


async def test_validate_without_duk_configured(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_duk=False))
    with pytest.raises(ToolError, match="ANAFPY_DUK_DIR"):
        await _call(
            server, "declaratie_validate", document={"xml": "<x/>"}, form="D300"
        )


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


async def test_render_unparseable_err_explains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("unrecognized gibberish"))
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
    assert result["findings"] == []
    assert "declaratie_duk_status" in result["message"]
    assert "no PDF was written" in result["message"]
    assert not out.exists()


async def test_render_refuses_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DukIntegrator, "_run", _fake_run("ok"))
    server = create_server(_config(tmp_path))
    out = tmp_path / "exists.pdf"
    out.write_bytes(b"old")
    with pytest.raises(ToolError, match="overwrite"):
        await _call(
            server,
            "declaratie_render",
            document={"xml": "<x/>"},
            form="D300",
            save_pdf_as=str(out),
        )
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


async def test_sign_refuses_collision_before_constructing_signer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructed = False

    class UnexpectedSigner:
        def __init__(self, _label: str) -> None:
            nonlocal constructed
            constructed = True

    monkeypatch.setattr(
        "anafpy.mcp.declaratii.tools.KeychainRawSigner", UnexpectedSigner
    )
    server = create_server(_config(tmp_path))
    source = tmp_path / "d300.pdf"
    source.write_bytes(b"%PDF-1.7\n")
    target = tmp_path / "d300-semnat.pdf"
    target.write_bytes(b"old")

    result = await _call(server, "declaratie_sign", pdf_path=str(source), confirm=True)

    assert result["signed"] is False
    assert "overwrite" in result["guidance"]
    assert constructed is False
    assert target.read_bytes() == b"old"


async def test_sign_missing_source_reports_read_failure(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    missing = tmp_path / "absent.pdf"
    result = await _call(server, "declaratie_sign", pdf_path=str(missing), confirm=True)
    assert result["signed"] is False
    assert result["guidance"].startswith(f"cannot read {missing}")


async def test_sign_write_failure_names_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A write-side OSError (after the 2FA signature was already produced) must
    # name the target and the write, never "cannot read <source>".
    class FakeSigned:
        pdf = b"%PDF-1.7 signed"
        warning: str | None = None
        chain_complete = True

    class FakePdfSign:
        async def sign_pdf(self, data: bytes, signer: object) -> FakeSigned:
            return FakeSigned()

    def denied_write(*args: object, **kwargs: object) -> str:
        raise PermissionError("Permission denied")

    monkeypatch.setattr(
        "anafpy.mcp.declaratii.tools.load_pdfsign", lambda: FakePdfSign()
    )
    monkeypatch.setattr(
        "anafpy.mcp.declaratii.tools.resolve_signing_label",
        lambda *args, **kwargs: "Test Identity",
    )
    monkeypatch.setattr(
        "anafpy.mcp.declaratii.tools.KeychainRawSigner", lambda label: object()
    )
    monkeypatch.setattr("anafpy.mcp.declaratii.tools.write_artifact", denied_write)
    server = create_server(_config(tmp_path))
    source = tmp_path / "d300.pdf"
    source.write_bytes(b"%PDF-1.7\n")
    target = tmp_path / "d300-semnat.pdf"

    result = await _call(server, "declaratie_sign", pdf_path=str(source), confirm=True)

    assert result["signed"] is False
    assert result["guidance"].startswith(f"cannot write {target}")
    assert str(source) not in result["guidance"]


# --- annotations ------------------------------------------------------------------


async def test_nr_evid_annotations_are_local(tmp_path: Path) -> None:
    # declaratie_nr_evid is pure local computation — no ANAF interaction, so it
    # must not carry the network-backed reads' openWorldHint.
    server = create_server(_config(tmp_path))
    tool = next(t for t in await server.list_tools() if t.name == "declaratie_nr_evid")
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.openWorldHint is False


# --- status / recipisa (StareD112 — needs no DUK) ----------------------------------

_STARED112_FIXTURES = Path(__file__).parent / "fixtures" / "stared112"


@respx.mock
async def test_status_tool_parses_found(tmp_path: Path) -> None:
    route = respx.post("https://www.anaf.ro/StareD112/vizualizareStare.do").mock(
        return_value=httpx.Response(
            200,
            text=(_STARED112_FIXTURES / "result-found.html").read_text(
                encoding="iso-8859-1"
            ),
        )
    )
    server = create_server(_config(tmp_path, with_duk=False))
    result = await _call(
        server, "declaratie_status", index="1100000001", cui="99999909"
    )
    assert result["found"] is True
    # The state serializes as ANAF's verbatim wording (the enum value).
    assert result["documents"][0]["state"] == "Documentul este valid"
    assert b"cui=99999909" in route.calls.last.request.content


@respx.mock
async def test_status_tool_uses_default_cif(tmp_path: Path) -> None:
    route = respx.post("https://www.anaf.ro/StareD112/vizualizareStare.do").mock(
        return_value=httpx.Response(
            200,
            text=(_STARED112_FIXTURES / "result-notfound.html").read_text(
                encoding="iso-8859-1"
            ),
        )
    )
    server = create_server(_config(tmp_path, with_duk=False))
    result = await _call(server, "declaratie_status", index="1100000001")
    assert result["found"] is False
    # The configured ANAFPY_CIF default fills the omitted `cui`.
    assert b"cui=8000000000" in route.calls.last.request.content


async def test_status_tool_returns_typed_failure_without_cif(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_duk=False, default_cif=None))
    result = await _call(server, "declaratie_status", index="1100000001")
    assert result["found"] is False
    assert result["cui"] == ""
    assert "ANAFPY_CIF" in result["message"]


async def test_status_tool_returns_typed_failure_for_bad_index(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_duk=False))
    result = await _call(
        server, "declaratie_status", index="not-an-index", cui="99999909"
    )
    assert result["found"] is False
    assert result["cui"] == "99999909"
    assert "digits expected" in result["message"]


@respx.mock
async def test_recipisa_tool_writes_pdf(tmp_path: Path) -> None:
    respx.get("https://www.anaf.ro/StareD112/ObtineRecipisa").mock(
        return_value=httpx.Response(
            200, content=b"%PDF-1.4 x", headers={"Content-Type": "application/pdf"}
        )
    )
    server = create_server(_config(tmp_path, with_duk=False))
    out = tmp_path / "recipisa.pdf"
    result = await _call(
        server, "declaratie_recipisa", index="1100000001", save_pdf_as=str(out)
    )
    assert result["ok"] is True
    assert result["pdf_path"] == str(out)
    assert out.read_bytes() == b"%PDF-1.4 x"


@respx.mock
async def test_recipisa_tool_not_available(tmp_path: Path) -> None:
    respx.get("https://www.anaf.ro/StareD112/ObtineRecipisa").mock(
        return_value=httpx.Response(
            200, content=b"", headers={"Content-Type": "application/pdf"}
        )
    )
    server = create_server(_config(tmp_path, with_duk=False))
    out = tmp_path / "recipisa.pdf"
    result = await _call(
        server, "declaratie_recipisa", index="9999999999", save_pdf_as=str(out)
    )
    assert result["ok"] is False
    assert "60-day" in result["message"]
    assert not out.exists()


@respx.mock
async def test_recipisa_tool_refuses_collision(tmp_path: Path) -> None:
    respx.get("https://www.anaf.ro/StareD112/ObtineRecipisa").mock(
        return_value=httpx.Response(
            200, content=b"%PDF-1.4 new", headers={"Content-Type": "application/pdf"}
        )
    )
    server = create_server(_config(tmp_path, with_duk=False))
    out = tmp_path / "exists.pdf"
    out.write_bytes(b"old")
    result = await _call(
        server, "declaratie_recipisa", index="1100000001", save_pdf_as=str(out)
    )
    assert result["ok"] is False
    assert "overwrite" in result["message"]
    assert out.read_bytes() == b"old"


# --- duk_status -------------------------------------------------------------------


@respx.mock
async def test_duk_status_unconfigured_still_reports_feed(tmp_path: Path) -> None:
    feed = (
        "<versiuni><D300><versiuneJ>J13.0.0</versiuneJ>"
        "<JURL>http://static.anaf.ro/static/10/Anaf/update5/D300/"
        "D300Validator.jar</JURL></D300></versiuni>"
    )
    respx.get("https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(200, text=feed)
    )
    server = create_server(_config(tmp_path, with_duk=False))
    result = await _call(server, "declaratie_duk_status")
    assert "ANAFPY_DUK_DIR" in result["install_error"]
    assert result["forms"][0]["form"] == "D300"
    assert result["forms"][0]["installed"] == "not installed"


@respx.mock
async def test_duk_status_reports_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_java_version(self: DukIntegrator) -> str:
        return 'openjdk version "21.0.1"'

    monkeypatch.setattr(DukIntegrator, "java_version", fake_java_version)
    feed = (
        "<versiuni><D300><versiuneJ>J13.0.0</versiuneJ>"
        "<JURL>http://static.anaf.ro/static/10/Anaf/update5/D300/"
        "D300Validator.jar</JURL></D300></versiuni>"
    )
    respx.get("https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(200, text=feed)
    )
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_duk_status")
    assert "installed_forms" in result
    assert result["java"] == 'openjdk version "21.0.1"'
    forms = {entry["form"]: entry for entry in result["forms"]}
    # Installed version is "unknown" (no history file), feed says J13.0.0 -> stale.
    assert forms["D300"]["current"] == "J13.0.0"
    assert forms["D300"]["stale"] is True
