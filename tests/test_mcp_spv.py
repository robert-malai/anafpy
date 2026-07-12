"""SPV MCP tool behaviour (respx-mocked, no real network, no certificate)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, cast

import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from anafpy.mcp.config import ServerConfig
from anafpy.mcp.server import create_server
from anafpy.spv import FileSessionStore, SpvSession, StoreIdentity

BASE = "https://webserviced.anaf.ro/SPVWS2/rest"

LISTING_BODY = {
    "titlu": "Lista Mesaje disponibile din ultimele 30 zile",
    "mesaje": [
        {
            "id": "100",
            "detalii": "recipisa pentru CIF 8000000000, tip D112",
            "cif": "8000000000",
            "data_creare": "20.12.2025 12:00:00",
            "id_solicitare": None,
            "tip": "RECIPISA",
        },
        {
            "id": "200",
            "detalii": "Obligatii de plata",
            "cif": "8000000000",
            "data_creare": "21.12.2025 09:00:00",
            "id_solicitare": "260149",
            "tip": "RASPUNS SOLICITARE",
        },
    ],
    "cnp": "1111111111118",
    "cui": "8000000000,8000000001",
    "serial": "20A0506B2450015C39C",
}

NO_MESSAGES_BODY = {
    "titlu": "Lista Mesaje",
    "eroare": "Nu exista mesaje in ultimele 1 zile",
}

CERERE_BODY = {
    "id_solicitare": 260149,
    "parametri": "cui=8000000000",
    "serial": "20A0506B2450015C39C",
    "cnp": "1111111111118",
    "titlu": "Transmitere cerere tip VECTOR FISCAL",
}


def _config(tmp_path: Path, *, with_session: bool = True) -> ServerConfig:
    session_path = tmp_path / "spv-session.json"
    if with_session:
        FileSessionStore(session_path).save(
            SpvSession(
                cookies={"MRHSession": "authenticated"},
                established_at=datetime.now(tz=UTC),
            )
        )
    return ServerConfig(
        client_id=None,
        client_secret=None,
        store_backend="file",
        store_path=tmp_path / "tokens.json",
        default_cif="8000000000",
        spv_session_path=session_path,
        spv_identity_path=tmp_path / "spv-identity.json",
    )


async def _call(server: Any, name: str, **arguments: Any) -> dict[str, Any]:
    _content, structured = await server.call_tool(name, arguments)
    return cast("dict[str, Any]", structured)


# --- spv_status -------------------------------------------------------------------


async def test_status_without_session_points_to_the_cli_login(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_session=False))
    result = await _call(server, "spv_status")
    assert result["reachable"] is False
    assert "anafpy spv login" in result["next_step"]


@respx.mock
async def test_status_reports_the_authorization_inventory(tmp_path: Path) -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=LISTING_BODY)
    server = create_server(_config(tmp_path))
    result = await _call(server, "spv_status")
    assert result["reachable"] is True
    assert result["authorized_cuis"] == ["8000000000", "8000000001"]
    assert result["cnp"] == "1111111111118"


@respx.mock
async def test_status_with_expired_session_points_to_login(tmp_path: Path) -> None:
    respx.get(f"{BASE}/listaMesaje").respond(
        302, headers={"Location": "https://webserviced.anaf.ro/my.policy"}
    )
    server = create_server(_config(tmp_path))
    result = await _call(server, "spv_status")
    assert result["reachable"] is False
    assert "anafpy spv login" in result["next_step"]


# --- spv_lista_mesaje ---------------------------------------------------------------


@respx.mock
async def test_lista_mesaje_filters_by_tip_and_pages(tmp_path: Path) -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=LISTING_BODY)
    server = create_server(_config(tmp_path))
    result = await _call(server, "spv_lista_mesaje", zile=30, tip="RECIPISA")
    assert result["total"] == 1
    assert result["messages"][0]["id"] == "100"

    result = await _call(server, "spv_lista_mesaje", zile=30, limit=1)
    assert result["total"] == 2
    assert result["returned"] == 1
    assert result["has_more"] is True
    result = await _call(server, "spv_lista_mesaje", zile=30, limit=1, offset=1)
    assert result["messages"][0]["id"] == "200"
    assert result["has_more"] is False


# --- spv_descarca -------------------------------------------------------------------


@respx.mock
async def test_descarca_saves_the_pdf_and_never_overwrites(tmp_path: Path) -> None:
    respx.get(f"{BASE}/descarcare").respond(content=b"%PDF-1.7 doc")
    server = create_server(_config(tmp_path))
    target = tmp_path / "out" / "receipt.pdf"

    result = await _call(server, "spv_descarca", mesaj_id="100", save_as=str(target))
    assert result["is_pdf"] is True
    assert Path(result["saved_as"]).read_bytes() == b"%PDF-1.7 doc"

    with pytest.raises(ToolError, match="refusing to overwrite"):
        await _call(server, "spv_descarca", mesaj_id="100", save_as=str(target))
    result = await _call(
        server, "spv_descarca", mesaj_id="100", save_as=str(target), overwrite=True
    )
    assert result["saved_as"] == str(target)


@respx.mock
async def test_descarca_dest_dir_generates_the_name(tmp_path: Path) -> None:
    respx.get(f"{BASE}/descarcare").respond(content=b"%PDF-1.7 doc")
    server = create_server(_config(tmp_path))
    result = await _call(server, "spv_descarca", mesaj_id="100", dest_dir=str(tmp_path))
    assert result["saved_as"].endswith("spv-100.pdf")


async def test_descarca_requires_a_destination(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="save_as"):
        await _call(server, "spv_descarca", mesaj_id="100")


# --- spv_cerere ---------------------------------------------------------------------


@respx.mock
async def test_cerere_files_and_dedupes_same_day_repeats(tmp_path: Path) -> None:
    route = respx.get(f"{BASE}/cerere").respond(json=CERERE_BODY)
    server = create_server(_config(tmp_path))

    first = await _call(server, "spv_cerere", tip="VECTOR FISCAL")
    assert first["id_solicitare"] == "260149"
    assert first["deduplicated"] is False

    second = await _call(server, "spv_cerere", tip="VECTOR FISCAL")
    assert second["deduplicated"] is True
    assert second["id_solicitare"] == "260149"
    assert route.call_count == 1

    forced = await _call(server, "spv_cerere", tip="VECTOR FISCAL", force=True)
    assert forced["deduplicated"] is False
    assert route.call_count == 2


@respx.mock
async def test_cerere_accepts_enum_member_names_too(tmp_path: Path) -> None:
    route = respx.get(f"{BASE}/cerere").respond(json=CERERE_BODY)
    server = create_server(_config(tmp_path))
    await _call(server, "spv_cerere", tip="vector fiscal")
    assert route.calls.last.request.url.params["tip"] == "VECTOR FISCAL"


async def test_cerere_validates_parameters_before_the_wire(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="requires cui, year"):
        await _call(server, "spv_cerere", tip="D101")
    with pytest.raises(ToolError, match="valid `tip` values"):
        await _call(server, "spv_cerere", tip="NO SUCH REPORT")


# --- spv_asteapta_raport --------------------------------------------------------------


@respx.mock
async def test_asteapta_raport_downloads_when_delivered(tmp_path: Path) -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=LISTING_BODY)
    respx.get(f"{BASE}/descarcare").respond(content=b"%PDF-1.7 report")
    server = create_server(_config(tmp_path))
    result = await _call(
        server,
        "spv_asteapta_raport",
        id_solicitare="260149",
        dest_dir=str(tmp_path),
        timeout_s=5,
        poll_interval_s=0.01,
    )
    assert result["status"] == "delivered"
    assert result["message_id"] == "200"
    assert Path(result["saved_as"]).read_bytes() == b"%PDF-1.7 report"


@respx.mock
async def test_asteapta_raport_timeout_is_a_pending_answer(tmp_path: Path) -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    server = create_server(_config(tmp_path))
    result = await _call(
        server,
        "spv_asteapta_raport",
        id_solicitare="999",
        dest_dir=str(tmp_path),
        timeout_s=0.05,
        poll_interval_s=0.01,
    )
    assert result["status"] == "pending"
    assert result["id_solicitare"] == "999"
    assert "again later" in result["detail"]


# --- certificates ---------------------------------------------------------------------

_IDENTITY = StoreIdentity(
    name="MIHAI-ROBERT MALAI",
    sha1_thumbprint="C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D",
    platform="darwin",
)


async def test_list_and_select_certificates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "anafpy.mcp.server.spv.discover_identities", lambda: [_IDENTITY]
    )
    monkeypatch.setattr("anafpy.spv.certs.discover_identities", lambda: [_IDENTITY])
    server = create_server(_config(tmp_path))

    listing = await _call(server, "spv_list_certificates")
    assert listing["selected_thumbprint"] is None
    assert listing["certificates"][0]["name"] == "MIHAI-ROBERT MALAI"

    result = await _call(
        server, "spv_select_certificate", thumbprint=_IDENTITY.sha1_thumbprint
    )
    assert "anafpy spv login" in result["next_step"]

    listing = await _call(server, "spv_list_certificates")
    assert listing["selected_thumbprint"] == _IDENTITY.sha1_thumbprint


async def test_select_unknown_thumbprint_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("anafpy.spv.certs.discover_identities", lambda: [_IDENTITY])
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="no usable identity"):
        await _call(server, "spv_select_certificate", thumbprint="AB" * 20)


# --- spv_login ------------------------------------------------------------------------


def _select_identity(tmp_path: Path) -> None:
    from anafpy.spv import save_selected_identity

    save_selected_identity(_IDENTITY, tmp_path / "spv-identity.json")


class FakeCurlBootstrapper:
    """Stands in for CurlBootstrapper inside the spv_login tool."""

    instances: ClassVar[list[FakeCurlBootstrapper]] = []
    fail_with: ClassVar[str | None] = None

    def __init__(self, identity: str, *, timeout: float = 240.0) -> None:
        self.identity = identity
        self.timeout = timeout
        FakeCurlBootstrapper.instances.append(self)

    async def bootstrap(self) -> SpvSession:
        from anafpy.exceptions import AnafAuthError

        if FakeCurlBootstrapper.fail_with is not None:
            raise AnafAuthError(FakeCurlBootstrapper.fail_with)
        return SpvSession(
            cookies={"MRHSession": "fresh-from-login"},
            established_at=datetime.now(tz=UTC),
        )


@pytest.fixture(autouse=True)
def _reset_fake_bootstrapper() -> None:
    FakeCurlBootstrapper.instances = []
    FakeCurlBootstrapper.fail_with = None


async def test_login_without_confirm_is_refused(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, with_session=False))
    with pytest.raises(ToolError, match="explicit approval"):
        await _call(server, "spv_login")


async def test_login_without_a_selected_certificate_is_actionable(
    tmp_path: Path,
) -> None:
    server = create_server(_config(tmp_path, with_session=False))
    with pytest.raises(ToolError, match="spv_select_certificate"):
        await _call(server, "spv_login", confirm=True)


@respx.mock
async def test_login_establishes_the_session_and_reports_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("anafpy.mcp.server.spv.CurlBootstrapper", FakeCurlBootstrapper)
    respx.get(f"{BASE}/listaMesaje").respond(json=LISTING_BODY)
    config = _config(tmp_path, with_session=False)
    _select_identity(tmp_path)
    server = create_server(config)

    result = await _call(server, "spv_login", confirm=True)
    assert result["logged_in"] is True
    assert result["identity"] == "MIHAI-ROBERT MALAI"
    assert result["authorized_cuis"] == ["8000000000", "8000000001"]
    # macOS selection: the bootstrapper gets the Keychain NAME.
    assert FakeCurlBootstrapper.instances[0].identity == "MIHAI-ROBERT MALAI"
    # The shared store now holds the fresh session (single source of truth).
    saved = FileSessionStore(tmp_path / "spv-session.json").load()
    assert saved is not None
    assert saved.cookies == {"MRHSession": "fresh-from-login"}


async def test_login_flaky_handshake_is_a_graceful_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("anafpy.mcp.server.spv.CurlBootstrapper", FakeCurlBootstrapper)
    FakeCurlBootstrapper.fail_with = "SPV handshake timed out after 180s"
    config = _config(tmp_path, with_session=False)
    _select_identity(tmp_path)
    server = create_server(config)

    result = await _call(server, "spv_login", confirm=True)
    assert result["logged_in"] is False
    assert "timed out" in result["detail"]
    assert "again" in result["next_step"]


async def test_login_timeout_is_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("anafpy.mcp.server.spv.CurlBootstrapper", FakeCurlBootstrapper)
    FakeCurlBootstrapper.fail_with = "flaky"  # short-circuit before any probe
    config = _config(tmp_path, with_session=False)
    _select_identity(tmp_path)
    server = create_server(config)
    await _call(server, "spv_login", confirm=True, timeout_s=9999)
    assert FakeCurlBootstrapper.instances[0].timeout == 300.0


@respx.mock
async def test_login_success_survives_a_failed_identity_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Observed live: the bootstrap succeeded (session saved) but the follow-up
    # probe raised — the tool must still report the login as successful.
    monkeypatch.setattr("anafpy.mcp.server.spv.CurlBootstrapper", FakeCurlBootstrapper)
    respx.get(f"{BASE}/listaMesaje").respond(500, content=b"hiccup")
    config = _config(tmp_path, with_session=False)
    _select_identity(tmp_path)
    server = create_server(config)

    result = await _call(server, "spv_login", confirm=True)
    assert result["logged_in"] is True
    assert "probe" in result["probe_error"]
    saved = FileSessionStore(tmp_path / "spv-session.json").load()
    assert saved is not None and saved.cookies == {"MRHSession": "fresh-from-login"}
