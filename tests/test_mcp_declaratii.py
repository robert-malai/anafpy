"""Declaration MCP tool behaviour (DUK-free, credential-free).

The Java subprocess is faked by monkeypatching ``DukIntegrator._run``; signing
never runs (its confirm gate and its failure paths are what the tools promise).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, cast

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from anafpy.declaratii.duk import DukIntegrator
from anafpy.declaratii.upload import PORTAL_BASE_URL
from anafpy.exceptions import AnafAuthError
from anafpy.mcp import create_server
from anafpy.mcp.config import ServerConfig
from anafpy.spv import StoreIdentity, save_selected_identity


def _config(
    tmp_path: Path,
    *,
    with_duk: bool = True,
    default_cif: str | None = "8000000000",
    upload: bool = True,
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
        declaratii_upload=upload,
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


# --- portal filing (login / status / prepare / submit) -----------------------------

_UPLOAD_TOOLS = {
    "declaratie_portal_login",
    "declaratie_portal_status",
    "declaratie_prepare",
    "declaratie_submit",
}

_IDENTITY = StoreIdentity(
    name="MIHAI-ROBERT MALAI",
    sha1_thumbprint="C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D",
    platform="darwin",
)

# Minimal pages carrying the live-captured markers the client judges by.
_UPLOAD_FORM = (
    '<html><form method="POST" action="/WAS6DUS/displayFile.do"'
    ' enctype="multipart/form-data"><input type="file" name="linkdoc"></form></html>'
)
_LOGON_PAGE = "<html><form>Prezentare certificat</form></html>"
_SUCCESS_PAGE = (
    '<html>Fișierul "d300.pdf" a fost depus cu succes. '
    "Indexul este <b>1100000005</b>.</html>"
)
_REJECTION_PAGE = (
    "<html>Ne cerem scuze, dar cererea dumneavoastra nu a putut fi indeplinita!"
    '<br>Motivul: <span style="color: red">Semnatura nu este valida</span></html>'
)

_SIGNED_PDF = (
    b"%PDF-1.7\n1 0 obj\n<</Type/Sig/SubFilter/adbe.pkcs7.detached"
    b"/ByteRange [0 100 200 300]>>\n%%EOF"
)


class FakePortalBootstrapper:
    """Stands in for PortalCurlBootstrapper inside declaratie_portal_login."""

    fail_with: ClassVar[str | None] = None
    instances: ClassVar[list[FakePortalBootstrapper]] = []

    def __init__(self, identity: str, *, timeout: float = 180.0) -> None:
        self.identity = identity
        self.timeout = timeout
        FakePortalBootstrapper.instances.append(self)

    async def bootstrap(self) -> dict[str, str]:
        if FakePortalBootstrapper.fail_with is not None:
            raise AnafAuthError(FakePortalBootstrapper.fail_with)
        return {"MRHSession": "abc123", "JSESSIONID": "def456"}


@pytest.fixture(autouse=True)
def _reset_fake_portal_bootstrapper() -> None:
    FakePortalBootstrapper.fail_with = None
    FakePortalBootstrapper.instances = []


def _select_identity(tmp_path: Path) -> None:
    save_selected_identity(_IDENTITY, tmp_path / "spv-identity.json")


def _patch_bootstrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "anafpy.mcp.declaratii.tools.PortalCurlBootstrapper", FakePortalBootstrapper
    )


async def _login(server: Any) -> None:
    result = await _call(server, "declaratie_portal_login", confirm=True)
    assert result["logged_in"] is True


def _signed_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "d300.pdf"
    pdf.write_bytes(_SIGNED_PDF)
    return pdf


async def test_upload_tools_registered_by_default(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    names = {tool.name for tool in await server.list_tools()}
    assert names >= _UPLOAD_TOOLS


async def test_upload_opt_out_unregisters_tools_and_redirects_guidance(
    tmp_path: Path,
) -> None:
    server = create_server(_config(tmp_path, upload=False))
    tools = await server.list_tools()
    assert _UPLOAD_TOOLS.isdisjoint({tool.name for tool in tools})
    # declaratie_sign then guides toward manual portal filing.
    sign = next(tool for tool in tools if tool.name == "declaratie_sign")
    assert sign.description is not None
    assert "manually" in sign.description
    assert "ANAFPY_DECLARATII_UPLOAD" in sign.description


async def test_sign_guidance_points_at_portal_tools_when_enabled(
    tmp_path: Path,
) -> None:
    server = create_server(_config(tmp_path))
    sign = next(
        tool for tool in await server.list_tools() if tool.name == "declaratie_sign"
    )
    assert sign.description is not None
    assert "declaratie_submit" in sign.description


async def test_portal_login_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_portal_login")
    assert result["logged_in"] is False
    assert "confirm=true" in result["guidance"]


async def test_portal_login_without_certificate_selection(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_portal_login", confirm=True)
    assert result["logged_in"] is False
    assert "spv_select_certificate" in result["guidance"]


@respx.mock
async def test_portal_login_establishes_probeable_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    server = create_server(_config(tmp_path))

    # Before login: inactive, no network probe possible (no cookies).
    status = await _call(server, "declaratie_portal_status")
    assert status["session_active"] is False
    assert "declaratie_portal_login" in status["next_step"]

    result = await _call(server, "declaratie_portal_login", confirm=True)
    assert result["logged_in"] is True
    assert result["identity"] == "MIHAI-ROBERT MALAI"
    # macOS selection: the bootstrapper gets the Keychain NAME.
    assert FakePortalBootstrapper.instances[0].identity == "MIHAI-ROBERT MALAI"

    status = await _call(server, "declaratie_portal_status")
    assert status["session_active"] is True


async def test_portal_login_failure_returns_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    FakePortalBootstrapper.fail_with = "curl timed out awaiting the 2FA approval"
    server = create_server(_config(tmp_path))
    result = await _call(server, "declaratie_portal_login", confirm=True)
    assert result["logged_in"] is False
    assert "2FA" in result["guidance"]


async def test_prepare_missing_file_is_invalid(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    result = await _call(
        server, "declaratie_prepare", pdf_path=str(tmp_path / "absent.pdf")
    )
    assert result["valid"] is False
    assert result["confirmation_token"] is None
    assert "cannot read" in result["message"]


async def test_prepare_issues_token_and_detects_signature(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = _signed_pdf(tmp_path)
    result = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    assert result["valid"] is True
    assert result["confirmation_token"]
    assert result["filename"] == "d300.pdf"
    assert result["size_bytes"] == len(_SIGNED_PDF)
    assert result["looks_signed"] is True


async def test_prepare_warns_on_unsigned_pdf_but_issues_token(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = tmp_path / "d300.pdf"
    pdf.write_bytes(b"%PDF-1.7\nno signature here\n%%EOF")
    result = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    assert result["valid"] is True
    assert result["looks_signed"] is False
    assert "declaratie_sign" in result["message"]
    assert result["confirmation_token"]


async def test_submit_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = _signed_pdf(tmp_path)
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token="anything",
    )
    assert result["accepted"] is False
    assert "confirm=true" in result["message"]


async def test_submit_rejects_bad_token(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = _signed_pdf(tmp_path)
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token="not-a-token",
        confirm=True,
    )
    assert result["accepted"] is False
    assert "does not verify" in result["message"]


async def test_submit_rejects_changed_bytes(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    pdf = _signed_pdf(tmp_path)
    prepared = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    pdf.write_bytes(_SIGNED_PDF + b"\ntampered")
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert result["accepted"] is False
    assert "does not match" in result["message"]


@respx.mock
async def test_submit_dead_session_does_not_consume_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    probe = respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    upload = respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text=_SUCCESS_PAGE)
    )
    server = create_server(_config(tmp_path))
    pdf = _signed_pdf(tmp_path)
    prepared = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    token = prepared["confirmation_token"]

    # No login yet: the pre-flight refuses without spending the token.
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=token,
        confirm=True,
    )
    assert result["accepted"] is False
    assert "NOT consumed" in result["message"]
    assert probe.call_count == 0 and upload.call_count == 0

    # After the login the SAME token files successfully — proof it survived.
    await _login(server)
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=token,
        confirm=True,
    )
    assert result["accepted"] is True
    assert result["upload_index"] == "1100000005"
    assert "declaratie_status" in result["message"]

    # And it is single-use: a replay is refused.
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=token,
        confirm=True,
    )
    assert result["accepted"] is False
    assert "already used" in result["message"]
    assert upload.call_count == 1


@respx.mock
async def test_submit_rejection_page_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text=_REJECTION_PAGE)
    )
    server = create_server(_config(tmp_path))
    await _login(server)
    pdf = _signed_pdf(tmp_path)
    prepared = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert result["accepted"] is False
    assert "Semnatura nu este valida" in result["reason"]
    assert "declaratie_prepare" in result["message"]


@respx.mock
async def test_submit_unrecognised_page_is_unknown_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(200, text="<html>ceva nou</html>")
    )
    server = create_server(_config(tmp_path))
    await _login(server)
    pdf = _signed_pdf(tmp_path)
    prepared = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert result["accepted"] is None
    assert "declaratie_status" in result["message"]


@respx.mock
async def test_submit_session_expiry_mid_upload_reports_nothing_filed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _select_identity(tmp_path)
    _patch_bootstrapper(monkeypatch)
    respx.get(f"{PORTAL_BASE_URL}/WAS6DUS/").mock(
        return_value=httpx.Response(200, text=_UPLOAD_FORM)
    )
    respx.post(f"{PORTAL_BASE_URL}/WAS6DUS/displayFile.do").mock(
        return_value=httpx.Response(
            302, headers={"Location": f"{PORTAL_BASE_URL}/my.policy"}
        )
    )
    server = create_server(_config(tmp_path))
    await _login(server)
    pdf = _signed_pdf(tmp_path)
    prepared = await _call(server, "declaratie_prepare", pdf_path=str(pdf))
    result = await _call(
        server,
        "declaratie_submit",
        pdf_path=str(pdf),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert result["accepted"] is False
    assert "NOTHING was filed" in result["message"]
    assert "declaratie_prepare" in result["message"]
