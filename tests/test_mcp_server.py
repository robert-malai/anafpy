"""MCP server tool behaviour (respx-mocked, credential-free).

Local Schematron validation is forced *unavailable* here so the prepare → submit gate
is exercised deterministically regardless of BR-RO findings; the validator itself is
covered by ``test_validation.py``.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

from _wire import credit_note_xml, invoice_xml, transport_xml
from anafpy._transport.base import Environment
from anafpy.auth import FileTokenStore, TokenSet
from anafpy.mcp.config import ServerConfig
from anafpy.mcp.server import create_server

EFACTURA = "https://api.anaf.ro/test/FCTEL/rest"
ETRANSPORT = "https://api.anaf.ro/test/ETRANSPORT/ws/v1"


@pytest.fixture(autouse=True)
def _no_local_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make both Schematron validators report as unavailable."""

    def unavailable(*_args: object, **_kwargs: object) -> object:
        raise ImportError("validation extra not installed (test)")

    monkeypatch.setattr("anafpy.efactura.validator.create_validator", unavailable)
    monkeypatch.setattr("anafpy.etransport.validator.create_validator", unavailable)


def _jwt(exp: float) -> str:
    def seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{seg({'alg': 'RS512'})}.{seg({'exp': int(exp)})}.sig"


def _config(tmp_path: Path, *, authenticated: bool = True) -> ServerConfig:
    store = tmp_path / "tokens.json"
    if authenticated:
        token = TokenSet.from_token_response(
            {"access_token": _jwt(time.time() + 3600), "refresh_token": "r1"}
        )
        FileTokenStore(store).save(token)
    return ServerConfig(
        client_id="CID",
        client_secret="S",
        store_path=store,
        environment=Environment.TEST,
        default_cif="123",
    )


async def _call(server: Any, name: str, **arguments: Any) -> dict[str, Any]:
    _content, structured = await server.call_tool(name, arguments)
    return cast("dict[str, Any]", structured)


# --- auth ---------------------------------------------------------------------------


async def test_auth_status_reports_login_needed(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path, authenticated=False))
    out = await _call(server, "auth_status")
    assert out["authenticated"] is False
    assert out["needs_login"] is True


async def test_auth_status_authenticated(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(server, "auth_status")
    assert out["authenticated"] is True
    assert out["access_token_valid"] is True


# --- read-only e-Factura ------------------------------------------------------------


@respx.mock
async def test_efactura_list_messages(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/listaMesajePaginatieFactura").mock(
        side_effect=[
            httpx.Response(200, json={"mesaje": [{"id": "1", "tip": "T"}]}),
            httpx.Response(200, json={"mesaje": []}),
        ]
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_list_messages", days=7)
    assert out["messages"][0]["id"] == "1"
    assert out["count"] == 1


@respx.mock
async def test_efactura_list_messages_date_range(tmp_path: Path) -> None:
    route = respx.get(f"{EFACTURA}/listaMesajePaginatieFactura").mock(
        side_effect=[
            httpx.Response(200, json={"mesaje": [{"id": "9", "tip": "T"}]}),
            httpx.Response(200, json={"mesaje": []}),
        ]
    )
    server = create_server(_config(tmp_path))
    out = await _call(
        server, "efactura_list_messages", start="2026-06-01", end="2026-06-29"
    )
    assert out["count"] == 1
    params = dict(route.calls[0].request.url.params)
    assert params["startTime"] == str(int(datetime(2026, 6, 1).timestamp() * 1000))


@respx.mock
async def test_efactura_get_status(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="ok" id_descarcare="55"/>')
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_get_status", upload_id="42")
    assert out["state"] == "ok"
    assert out["download_id"] == "55"


# --- gated submit: e-Factura --------------------------------------------------------


def _invoice_doc(*, number: str = "INV-1") -> dict[str, Any]:
    return {"xml": invoice_xml(number=number)}


async def test_prepare_invoice_returns_token_and_preview(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_prepare_invoice", document=_invoice_doc())
    assert out["valid"] is True
    assert out["validation_available"] is False
    assert out["confirmation_token"]
    # Preview is the read view parsed back out of the supplied XML.
    assert out["invoice_preview"]["number"] == "INV-1"
    assert out["invoice_preview"]["total_with_vat"] == "24.99"
    assert out["invoice_preview"]["complete"] is True


async def test_submit_invoice_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_invoice_doc(),
        confirmation_token="whatever",
        confirm=False,
    )
    assert out["accepted"] is False
    assert "confirm=True" in out["message"]


async def test_submit_invoice_rejects_bad_token(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_invoice_doc(),
        confirmation_token="v1.efactura.invoice.9999999999.deadbeef",
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"] or "malformed" in out["message"]


@respx.mock
async def test_prepare_then_submit_files_invoice(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="777"/>')
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare_invoice", document=_invoice_doc())
    token = prepared["confirmation_token"]
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_invoice_doc(),
        confirmation_token=token,
        confirm=True,
    )
    assert out["accepted"] is True
    assert out["upload_id"] == "777"
    assert route.called
    assert route.calls.last.request.url.params["standard"] == "UBL"


@respx.mock
async def test_submit_credit_note_files_with_standard_cn(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="778"/>')
    )
    server = create_server(_config(tmp_path))
    doc = {"xml": credit_note_xml()}
    prepared = await _call(server, "efactura_prepare_invoice", document=doc)
    assert prepared["invoice_preview"]["document_type"] == "credit_note"
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=doc,
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is True
    assert route.calls.last.request.url.params["standard"] == "CN"


@respx.mock
async def test_submit_rejects_token_for_different_document(tmp_path: Path) -> None:
    respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="1"/>')
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare_invoice", document=_invoice_doc())
    token = prepared["confirmation_token"]
    # A different document (different XML bytes) must not match the token.
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_invoice_doc(number="INV-2"),
        confirmation_token=token,
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"]


# --- gated submit: e-Transport ------------------------------------------------------


def _transport_doc() -> dict[str, Any]:
    return {"xml": transport_xml()}


@respx.mock
async def test_prepare_then_submit_files_transport(tmp_path: Path) -> None:
    route = respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200, text='<header index_incarcare="9" uit="3RO123"/>'
        )
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    assert prepared["transport_preview"]["total_gross_weight"] == "120"
    assert prepared["transport_preview"]["operation_type"] == "30"
    out = await _call(
        server,
        "etransport_submit",
        document=_transport_doc(),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is True
    assert out["uit"] == "3RO123"
    assert route.called


# --- resources ----------------------------------------------------------------------


@pytest.fixture
def _docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    docs = tmp_path / "ref"
    (docs / "efactura").mkdir(parents=True)
    (docs / "efactura" / "api.md").write_text("# e-Factura API", encoding="utf-8")
    (docs / "README.md").write_text("index", encoding="utf-8")
    monkeypatch.setenv("ANAFPY_DOCS_DIR", str(docs))
    yield docs


async def test_reference_docs_exposed_as_resources(tmp_path: Path, _docs: Path) -> None:
    server = create_server(_config(tmp_path))
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "anafref://efactura/api" in uris
    # README is excluded.
    assert all("README" not in u for u in uris)
