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
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

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
    respx.get(f"{EFACTURA}/listaMesajeFactura").mock(
        return_value=httpx.Response(200, json={"mesaje": [{"id": "1", "tip": "T"}]})
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_list_messages", days=7)
    assert out["messages"][0]["id"] == "1"


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


def _flat_invoice_arg() -> dict[str, Any]:
    party = {
        "name": "Seller",
        "vat_id": "RO1",
        "county": "RO-B",
        "city": "Bucuresti",
        "address": "Str A 1",
    }
    return {
        "kind": "flat",
        "invoice_number": "INV-1",
        "issue_date": "2026-06-28",
        "currency": "RON",
        "seller": party,
        "buyer": {**party, "name": "Buyer", "vat_id": "RO2"},
        "lines": [
            {
                "description": "Widget",
                "quantity": "2",
                "unit_price": "10.50",
                "vat_category": "S",
                "vat_rate": "19",
            }
        ],
    }


async def test_prepare_invoice_returns_token_and_preview(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_prepare_invoice", document=_flat_invoice_arg())
    assert out["valid"] is True
    assert out["validation_available"] is False
    assert out["confirmation_token"]
    assert out["invoice_preview"]["total_with_vat"] == "24.99"


async def test_submit_invoice_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_flat_invoice_arg(),
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
        document=_flat_invoice_arg(),
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
    prepared = await _call(
        server, "efactura_prepare_invoice", document=_flat_invoice_arg()
    )
    token = prepared["confirmation_token"]
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=_flat_invoice_arg(),
        confirmation_token=token,
        confirm=True,
    )
    assert out["accepted"] is True
    assert out["upload_id"] == "777"
    assert route.called


@respx.mock
async def test_submit_rejects_token_for_different_document(tmp_path: Path) -> None:
    respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="1"/>')
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(
        server, "efactura_prepare_invoice", document=_flat_invoice_arg()
    )
    token = prepared["confirmation_token"]
    tampered = _flat_invoice_arg()
    tampered["lines"][0]["unit_price"] = "999.00"  # changed after prepare
    out = await _call(
        server,
        "efactura_submit_invoice",
        document=tampered,
        confirmation_token=token,
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"]


# --- gated submit: e-Transport ------------------------------------------------------


def _flat_transport_arg() -> dict[str, Any]:
    return {
        "kind": "flat",
        "operation_type": "30",
        "partner": {"name": "Foreign GmbH", "country": "DE", "code": "DE9"},
        "vehicle": {
            "plate": "B100XYZ",
            "carrier_name": "Carrier SRL",
            "carrier_country": "RO",
            "carrier_code": "123",
            "transport_date": "2026-06-28",
        },
        "start_location": {
            "county_code": "40",
            "locality": "Bucuresti",
            "street": "Str A",
            "number": "1",
        },
        "end_location": {
            "county_code": "12",
            "locality": "Cluj",
            "street": "Str B",
        },
        "goods": [
            {
                "operation_scope": "301",
                "name": "Marfa",
                "quantity": "100",
                "unit_code": "KGM",
                "gross_weight": "120",
            }
        ],
    }


@respx.mock
async def test_prepare_then_submit_files_transport(tmp_path: Path) -> None:
    route = respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200, text='<header index_incarcare="9" uit="3RO123"/>'
        )
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_flat_transport_arg())
    assert prepared["transport_preview"]["total_gross_weight"] == "120"
    out = await _call(
        server,
        "etransport_submit",
        document=_flat_transport_arg(),
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
