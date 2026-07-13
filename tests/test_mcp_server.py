"""MCP server tool behaviour (respx-mocked, credential-free)."""

from __future__ import annotations

import base64
import io
import json
import time
import zipfile
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import jsonschema
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import GetPromptResult, TextContent

from _authoring import make_invoice
from _wire import build_flat_transport, credit_note_xml, invoice_xml, transport_xml
from anafpy._transport.base import Environment
from anafpy.auth import FileTokenStore, KeyringTokenStore, TokenSet
from anafpy.exceptions import AnafConfigError
from anafpy.mcp import create_server
from anafpy.mcp.config import ServerConfig
from anafpy.mcp.context import AppContext
from conftest import FakeKeyring

EFACTURA = "https://api.anaf.ro/test/FCTEL/rest"
ETRANSPORT = "https://api.anaf.ro/test/ETRANSPORT/ws/v1"
# `validare` is public, no-auth, and prod-only — routed there whatever ANAFPY_ENV is.
EFACTURA_PUBLIC = "https://webservicesp.anaf.ro/prod/FCTEL/rest"


def _jwt(exp: float) -> str:
    def seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{seg({'alg': 'RS512'})}.{seg({'exp': int(exp)})}.sig"


def _config(
    tmp_path: Path, *, authenticated: bool = True, credentials: bool = True
) -> ServerConfig:
    store = tmp_path / "tokens.json"
    if authenticated:
        token = TokenSet.from_token_response(
            {"access_token": _jwt(time.time() + 3600), "refresh_token": "r1"}
        )
        FileTokenStore(store).save(token)
    return ServerConfig(
        client_id="CID" if credentials else None,
        client_secret="S" if credentials else None,
        # Explicit file backend: these tests seed tokens via FileTokenStore
        # (the shipped default is keyring).
        store_backend="file",
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
    assert out["credentials_configured"] is True


# --- credential-free server (public lookups only) -------------------------------------


def _credential_free(tmp_path: Path) -> ServerConfig:
    return _config(tmp_path, authenticated=False, credentials=False)


async def test_auth_status_reports_missing_credentials(tmp_path: Path) -> None:
    server = create_server(_credential_free(tmp_path))
    out = await _call(server, "auth_status")
    assert out["credentials_configured"] is False
    assert out["authenticated"] is False
    assert out["needs_login"] is True
    assert "ANAFPY_CLIENT_ID" in out["message"]


async def test_authenticated_tool_without_credentials_says_how_to_enable(
    tmp_path: Path,
) -> None:
    server = create_server(_credential_free(tmp_path))
    with pytest.raises(ToolError, match="ANAFPY_CLIENT_ID"):
        await _call(server, "etransport_get_status", upload_id="1")


@respx.mock
async def test_public_lookup_works_without_credentials(tmp_path: Path) -> None:
    respx.post("https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(
            200,
            json={
                "found": [{"date_generale": {"cui": 1590082, "denumire": "OMV"}}],
                "notFound": [],
            },
        )
    )
    server = create_server(_credential_free(tmp_path))
    out = await _call(server, "anaf_lookup_taxpayers", cuis=[1590082])
    assert out["count"] == 1


async def test_prepare_works_but_submit_needs_credentials(tmp_path: Path) -> None:
    # Composing + previewing a declaration touches no ANAF endpoint, so the
    # two-step flow is usable up to the human gate; only the actual filing needs
    # the OAuth credentials.
    server = create_server(_credential_free(tmp_path))
    declaration = build_flat_transport().model_dump(mode="json")
    prepared = await _call(
        server, "etransport_prepare_declaration", declaration=declaration
    )
    assert prepared["valid"] is True
    with pytest.raises(ToolError, match="ANAFPY_CLIENT_ID"):
        await _call(
            server,
            "etransport_submit",
            document={"xml": prepared["xml"]},
            confirmation_token=prepared["confirmation_token"],
            confirm=True,
        )


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
    # Relative to now so the range always sits inside ANAF's 60-day retention.
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=28)
    out = await _call(
        server, "efactura_list_messages", start=start.isoformat(), end=end.isoformat()
    )
    assert out["count"] == 1
    params = dict(route.calls[0].request.url.params)
    assert params["startTime"] == str(int(start.timestamp() * 1000))


def _download_zip() -> bytes:
    # Built once: ZIP entries embed a 2-second-resolution timestamp, so two builds
    # straddling a boundary differ byte-wise and must not be compared to each other.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("3828.xml", invoice_xml())
        zf.writestr("semnatura_3828.xml", b"<Signature/>")
    return buf.getvalue()


_DOWNLOAD_ZIP = _download_zip()


@respx.mock
async def test_efactura_download_saves_zip_and_pdf(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/descarcare").mock(
        return_value=httpx.Response(200, content=_DOWNLOAD_ZIP)
    )
    # `transformare` is public/prod-only like `validare`; /DA skips re-validation
    # (the message already passed ANAF's validation when it was filed).
    pdf_route = respx.post(f"{EFACTURA_PUBLIC}/transformare/FACT1/DA").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.7 fake")
    )
    server = create_server(_config(tmp_path))
    pdf_target = tmp_path / "out" / "2026-06-28 - ACME SRL.pdf"
    zip_target = tmp_path / "out" / "archive.zip"
    out = await _call(
        server,
        "efactura_download",
        message_id="55",
        save_pdf_as=str(pdf_target),
        save_zip_as=str(zip_target),
    )
    assert out["invoice"]["number"] == "INV-1"
    assert out["pdf_error"] is None
    assert out["pdf_path"] == str(pdf_target)
    assert out["zip_path"] == str(zip_target)
    assert pdf_target.read_bytes() == b"%PDF-1.7 fake"
    assert zip_target.read_bytes() == _DOWNLOAD_ZIP
    assert pdf_route.called


@respx.mock
async def test_efactura_download_pdf_failure_is_best_effort(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/descarcare").mock(
        return_value=httpx.Response(200, content=_DOWNLOAD_ZIP)
    )
    # transformare answers 200 with a JSON error body when it cannot render.
    respx.post(f"{EFACTURA_PUBLIC}/transformare/FACT1/DA").mock(
        return_value=httpx.Response(200, json={"stare": "nok"})
    )
    server = create_server(_config(tmp_path))
    pdf_target = tmp_path / "invoice.pdf"
    out = await _call(
        server, "efactura_download", message_id="55", save_pdf_as=str(pdf_target)
    )
    # The download itself still succeeds; the PDF failure is reported, not raised.
    assert out["invoice"]["number"] == "INV-1"
    assert out["pdf_path"] is None
    assert "no PDF" in out["pdf_error"]
    assert not pdf_target.exists()


@respx.mock
async def test_efactura_download_refuses_to_overwrite_by_default(
    tmp_path: Path,
) -> None:
    # A batch flow naming files from invoice metadata must not lose an invoice to
    # a name collision: an existing file is refused (reported per artifact), and
    # only overwrite=True replaces it.
    respx.get(f"{EFACTURA}/descarcare").mock(
        return_value=httpx.Response(200, content=_DOWNLOAD_ZIP)
    )
    respx.post(f"{EFACTURA_PUBLIC}/transformare/FACT1/DA").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.7 fake")
    )
    server = create_server(_config(tmp_path))
    pdf_target = tmp_path / "2026-06-28 - ACME SRL.pdf"
    zip_target = tmp_path / "archive.zip"
    pdf_target.write_bytes(b"an earlier invoice")
    zip_target.write_bytes(b"an earlier archive")

    out = await _call(
        server,
        "efactura_download",
        message_id="55",
        save_pdf_as=str(pdf_target),
        save_zip_as=str(zip_target),
    )
    assert out["pdf_path"] is None
    assert "overwrite" in out["pdf_error"]
    assert out["zip_path"] is None
    assert "overwrite" in out["zip_error"]
    assert pdf_target.read_bytes() == b"an earlier invoice"
    assert zip_target.read_bytes() == b"an earlier archive"

    out = await _call(
        server,
        "efactura_download",
        message_id="55",
        save_pdf_as=str(pdf_target),
        save_zip_as=str(zip_target),
        overwrite=True,
    )
    assert out["pdf_error"] is None
    assert out["zip_error"] is None
    assert pdf_target.read_bytes() == b"%PDF-1.7 fake"
    assert zip_target.read_bytes() == _DOWNLOAD_ZIP


@respx.mock
async def test_efactura_message_pdf_resource(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/descarcare").mock(
        return_value=httpx.Response(200, content=_DOWNLOAD_ZIP)
    )
    respx.post(f"{EFACTURA_PUBLIC}/transformare/FACT1/DA").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.7 fake")
    )
    server = create_server(_config(tmp_path))
    templates = await server.list_resource_templates()
    assert "anafmsg://{message_id}/pdf" in {t.uriTemplate for t in templates}
    contents = list(await server.read_resource("anafmsg://55/pdf"))
    assert contents[0].content == b"%PDF-1.7 fake"
    assert contents[0].mime_type == "application/pdf"


@respx.mock
async def test_efactura_validate_calls_anaf_validator(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA_PUBLIC}/validare/FACT1").mock(
        return_value=httpx.Response(
            200,
            json={
                "stare": "nok",
                "Messages": [{"message": "BR-RO-020 error"}],
                "trace_id": "t1",
            },
        )
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_validate", document={"xml": invoice_xml()})
    assert out["valid"] is False
    assert out["messages"] == ["BR-RO-020 error"]
    assert route.called


@respx.mock
async def test_efactura_validate_routes_credit_notes_to_fcn(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA_PUBLIC}/validare/FCN").mock(
        return_value=httpx.Response(200, json={"stare": "ok"})
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_validate", document={"xml": credit_note_xml()})
    assert out["valid"] is True
    assert route.called


@respx.mock
async def test_efactura_validate_works_without_credentials(tmp_path: Path) -> None:
    # `validare` is a public no-auth service (served via PublicClient), so the
    # tool must work on a credential-free server, like the anaf_* lookups.
    route = respx.post(f"{EFACTURA_PUBLIC}/validare/FACT1").mock(
        return_value=httpx.Response(200, json={"stare": "ok"})
    )
    server = create_server(_credential_free(tmp_path))
    out = await _call(server, "efactura_validate", document={"xml": invoice_xml()})
    assert out["valid"] is True
    assert route.called


# --- gated filing: e-Factura ----------------------------------------------------------
#
# Reinstated 2026-07-08 with the authoring package: efactura_prepare_invoice composes
# the CIUS-RO XML from the flat InvoiceDocument; efactura_prepare takes ready-made
# XML (the recommended path when invoicing software exists); both feed the same
# two-step gate as e-Transport.


def _flat_invoice(**overrides: Any) -> dict[str, Any]:
    return make_invoice(**overrides).model_dump(mode="json")


async def test_efactura_filing_tools_are_registered(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    names = {t.name for t in await server.list_tools()}
    assert {
        "efactura_prepare_invoice",
        "efactura_prepare",
        "efactura_submit",
        "efactura_get_status",
    } <= names


@respx.mock
async def test_efactura_prepare_invoice_composes_and_submit_files(
    tmp_path: Path,
) -> None:
    route = respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(
            200,
            text='<header xmlns="mfp:anaf:dgti:spv:respUploadFisier:v1"'
            ' ExecutionStatus="0" index_incarcare="3828"/>',
        )
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare_invoice", invoice=_flat_invoice())
    assert prepared["valid"] is True
    assert prepared["cif"] == "123"
    assert prepared["local_findings"] == []
    assert prepared["invoice_preview"]["number"] == "INV-2026-0042"
    assert prepared["xml"].startswith("<?xml")
    # PreparedInvoice carries no e-Transport fields (per-service result models).
    assert "transport_preview" not in prepared

    out = await _call(
        server,
        "efactura_submit",
        document={"xml": prepared["xml"]},
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is True
    assert out["upload_id"] == "3828"
    assert route.calls.last.request.url.params["standard"] == "UBL"
    assert route.calls.last.request.url.params["cif"] == "123"


async def test_efactura_prepare_invoice_findings_never_withhold_the_token(
    tmp_path: Path,
) -> None:
    # No due date and no payment terms -> BR-CO-25 is a fatal local finding, yet
    # the token is still issued: findings inform the human, ANAF is the judge.
    server = create_server(_config(tmp_path))
    prepared = await _call(
        server, "efactura_prepare_invoice", invoice=_flat_invoice(due_date=None)
    )
    assert prepared["valid"] is True
    assert prepared["confirmation_token"]
    rules = {finding["rule"] for finding in prepared["local_findings"]}
    assert "BR-CO-25" in rules
    assert "do not block filing" in prepared["message"]


@respx.mock
async def test_efactura_submit_credit_note_uses_cn_standard(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="9"/>')
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(
        server,
        "efactura_prepare_invoice",
        invoice=_flat_invoice(
            kind="credit_note",
            number="CN-1",
            preceding_invoices=[{"number": "INV-2026-0042"}],
        ),
    )
    out = await _call(
        server,
        "efactura_submit",
        document={"xml": prepared["xml"]},
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is True
    assert route.calls.last.request.url.params["standard"] == "CN"


async def test_efactura_prepare_xml_previews_the_document(tmp_path: Path) -> None:
    from anafpy.efactura.authoring import render_invoice

    server = create_server(_config(tmp_path))
    xml = render_invoice(make_invoice()).decode()
    prepared = await _call(server, "efactura_prepare", document={"xml": xml})
    assert prepared["valid"] is True
    assert prepared["invoice_preview"]["number"] == "INV-2026-0042"
    assert prepared["confirmation_token"]


async def test_efactura_prepare_unparseable_xml_still_issues_a_token(
    tmp_path: Path,
) -> None:
    # Pass-through means the bytes go to ANAF verbatim even when the strict flat
    # view cannot represent them; the message says there is no preview.
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare", document={"xml": "<NotUbl/>"})
    assert prepared["valid"] is True
    assert prepared["invoice_preview"] is None
    assert "no preview" in prepared["message"]


async def test_efactura_submit_requires_confirm_and_matching_token(
    tmp_path: Path,
) -> None:
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare_invoice", invoice=_flat_invoice())
    out = await _call(
        server,
        "efactura_submit",
        document={"xml": prepared["xml"]},
        confirmation_token=prepared["confirmation_token"],
        confirm=False,
    )
    assert out["accepted"] is False
    assert "confirm=True" in out["message"]
    tampered = prepared["xml"].replace("INV-2026-0042", "INV-9999")
    out = await _call(
        server,
        "efactura_submit",
        document={"xml": tampered},
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"]


@respx.mock
async def test_efactura_submit_token_is_single_use(tmp_path: Path) -> None:
    route = respx.post(f"{EFACTURA}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="7"/>')
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "efactura_prepare_invoice", invoice=_flat_invoice())
    args = {
        "document": {"xml": prepared["xml"]},
        "confirmation_token": prepared["confirmation_token"],
        "confirm": True,
    }
    first = await _call(server, "efactura_submit", **args)
    second = await _call(server, "efactura_submit", **args)
    assert first["accepted"] is True
    assert second["accepted"] is False
    assert "already used" in second["message"]
    assert route.call_count == 1


@respx.mock
async def test_efactura_get_status_returns_download_id(tmp_path: Path) -> None:
    respx.get(f"{EFACTURA}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="ok" id_descarcare="55"/>')
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "efactura_get_status", upload_id="3828")
    assert out["state"] == "ok"
    assert out["is_terminal"] is True
    assert out["download_id"] == "55"


# --- gated submit: e-Transport ------------------------------------------------------


def _transport_doc() -> dict[str, Any]:
    return {"xml": transport_xml()}


async def test_submit_requires_confirm(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(
        server,
        "etransport_submit",
        document=_transport_doc(),
        confirmation_token="whatever",
        confirm=False,
    )
    assert out["accepted"] is False
    assert "confirm=True" in out["message"]


async def test_submit_rejects_bad_token(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    out = await _call(
        server,
        "etransport_submit",
        document=_transport_doc(),
        confirmation_token="v1.etransport.declaration.9999999999.deadbeef",
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"] or "malformed" in out["message"]


@respx.mock
async def test_submit_rejects_token_for_different_document(tmp_path: Path) -> None:
    respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(200, json={"ExecutionStatus": 0})
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    # PreparedTransport carries no e-Factura fields (per-service result models).
    assert "invoice_preview" not in prepared
    assert "local_findings" not in prepared
    # A different document (different XML bytes) must not match the token.
    out = await _call(
        server,
        "etransport_submit",
        document={"xml": transport_xml().replace("B100XYZ", "B200XYZ")},
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"]


@respx.mock
async def test_submit_rejects_token_for_different_cif(tmp_path: Path) -> None:
    respx.post(f"{ETRANSPORT}/upload/ETRANSP/999/2").mock(
        return_value=httpx.Response(200, json={"ExecutionStatus": 0})
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    assert prepared["cif"] == "123"  # the default the human approved
    out = await _call(
        server,
        "etransport_submit",
        document=_transport_doc(),
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
        cif="999",  # not what was prepared
    )
    assert out["accepted"] is False
    assert "does not match" in out["message"]


@respx.mock
async def test_submit_token_is_single_use(tmp_path: Path) -> None:
    route = respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200,
            json={"ExecutionStatus": 0, "index_incarcare": 9, "UIT": "3RO123"},
        )
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    args = {
        "document": _transport_doc(),
        "confirmation_token": prepared["confirmation_token"],
        "confirm": True,
    }
    first = await _call(server, "etransport_submit", **args)
    second = await _call(server, "etransport_submit", **args)
    assert first["accepted"] is True
    assert second["accepted"] is False
    assert "already used" in second["message"]
    assert route.call_count == 1  # the non-idempotent POST went out exactly once


@respx.mock
async def test_submit_upload_failure_reports_unknown_outcome(tmp_path: Path) -> None:
    # A transport failure after approval returns a structured result that says
    # the outcome is unknown and the token is spent — replaying must not be able
    # to double-file; the agent is told to check before preparing again.
    respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        side_effect=httpx.ConnectTimeout("connection timed out")
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    args = {
        "document": _transport_doc(),
        "confirmation_token": prepared["confirmation_token"],
        "confirm": True,
    }
    out = await _call(server, "etransport_submit", **args)
    assert out["accepted"] is False
    assert "UNKNOWN" in out["message"]
    assert out["errors"]  # the transport error is carried for diagnostics
    replay = await _call(server, "etransport_submit", **args)
    assert replay["accepted"] is False
    assert "already used" in replay["message"]


@respx.mock
async def test_prepare_then_submit_files_transport(tmp_path: Path) -> None:
    route = respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200,
            json={"ExecutionStatus": 0, "index_incarcare": 9, "UIT": "3RO123"},
        )
    )
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare", document=_transport_doc())
    assert prepared["transport_preview"]["total_gross_weight"] == "120"
    assert prepared["transport_preview"]["operation_type"] == "TTN"
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


async def test_prepare_unreadable_xml_file_is_reported_not_raised(
    tmp_path: Path,
) -> None:
    # A bad `path` must come back as an invalid PreparedSubmission (the documented
    # shape), not escape the tool as a raw FileNotFoundError.
    server = create_server(_config(tmp_path))
    out = await _call(
        server, "etransport_prepare", document={"path": str(tmp_path / "missing.xml")}
    )
    assert out["valid"] is False
    assert out["confirmation_token"] is None
    assert "cannot read XML file" in out["message"]


async def test_efactura_list_messages_rejects_unknown_filter(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    with pytest.raises(ToolError, match="unknown `filter`"):
        await _call(server, "efactura_list_messages", days=5, filter="X")


# --- composed e-Transport filings (structured fields, no caller XML) ------------------

_UIT = "0123456789ACDE94"


@respx.mock
async def test_prepare_declaration_composes_and_submit_files_it(tmp_path: Path) -> None:
    route = respx.post(f"{ETRANSPORT}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200,
            json={"ExecutionStatus": 0, "index_incarcare": 9, "UIT": "3RO123"},
        )
    )
    server = create_server(_config(tmp_path))
    declaration = build_flat_transport().model_dump(mode="json")
    prepared = await _call(
        server, "etransport_prepare_declaration", declaration=declaration
    )
    assert prepared["valid"] is True
    # The composed XML is echoed for the submit step; the preview is its read-back.
    assert prepared["xml"].startswith("<?xml")
    assert 'codDeclarant="123"' in prepared["xml"]
    assert prepared["transport_preview"]["operation_type"] == "TTN"
    out = await _call(
        server,
        "etransport_submit",
        document={"xml": prepared["xml"]},
        confirmation_token=prepared["confirmation_token"],
        confirm=True,
    )
    assert out["accepted"] is True
    assert out["uit"] == "3RO123"
    # What went on the wire is byte-for-byte the XML the human approved.
    assert route.calls.last.request.content == prepared["xml"].encode("utf-8")


async def test_prepare_declaration_rejects_invalid_fields(tmp_path: Path) -> None:
    # Structured input is validated at the tool boundary (FastMCP applies the
    # FlatTransport schema), so bad fields surface as a tool error — nothing is
    # composed and no confirmation token is issued.
    server = create_server(_config(tmp_path))
    declaration = build_flat_transport().model_dump(mode="json")
    declaration["goods"] = []
    with pytest.raises(ToolError, match="at least 1 item"):
        await _call(server, "etransport_prepare_declaration", declaration=declaration)


async def test_prepare_declaration_output_matches_declared_schema(
    tmp_path: Path,
) -> None:
    # Regression: the flat models serialize enum-coded fields as member names
    # ('TTN', 'GERMANIA', 'NADLAC_2_A1'), but pydantic's default enum schema lists
    # only the raw ANAF codes — MCP clients validate structured output against the
    # declared schema, so a code-only schema rejected every prepare result.
    server = create_server(_config(tmp_path))
    declaration = build_flat_transport().model_dump(mode="json")
    declaration["start_location"] = {"border_point": "NADLAC_2_A1"}
    prepared = await _call(
        server, "etransport_prepare_declaration", declaration=declaration
    )
    assert prepared["valid"] is True
    tool = next(
        t
        for t in await server.list_tools()
        if t.name == "etransport_prepare_declaration"
    )
    assert tool.outputSchema is not None
    jsonschema.validate(prepared, tool.outputSchema)


async def test_prepare_deletion_composes_stergere(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare_deletion", uit=_UIT)
    assert prepared["valid"] is True
    assert f'stergere uit="{_UIT}"' in prepared["xml"]
    assert prepared["transport_preview"]["uit"] == _UIT


async def test_prepare_deletion_rejects_malformed_uit(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    prepared = await _call(server, "etransport_prepare_deletion", uit="not-a-uit")
    assert prepared["valid"] is False
    assert prepared["confirmation_token"] is None


async def test_prepare_confirmation_accepts_name_or_code(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    by_name = await _call(
        server,
        "etransport_prepare_confirmation",
        uit=_UIT,
        confirmation_type="CONFIRMAT_PARTIAL",
    )
    by_code = await _call(
        server, "etransport_prepare_confirmation", uit=_UIT, confirmation_type="20"
    )
    assert by_name["valid"] is by_code["valid"] is True
    assert 'tipConfirmare="20"' in by_name["xml"]
    assert 'tipConfirmare="20"' in by_code["xml"]


async def test_prepare_vehicle_change_composes_modif_vehicul(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    prepared = await _call(
        server,
        "etransport_prepare_vehicle_change",
        uit=_UIT,
        plate="cj 99 aaa",
        trailer1="CJ98BBB",
    )
    assert prepared["valid"] is True
    assert 'nrVehicul="CJ99AAA"' in prepared["xml"]
    assert prepared["transport_preview"]["plate"] == "CJ99AAA"


async def test_scalar_prepare_tools_all_take_declarant_ref(tmp_path: Path) -> None:
    # The three scalar prepare tools expose the same root fields — an agent that
    # used declarant_ref on a deletion must not find it missing on the others.
    server = create_server(_config(tmp_path))
    for name, extra in (
        ("etransport_prepare_deletion", {}),
        ("etransport_prepare_confirmation", {"confirmation_type": "CONFIRMAT"}),
        ("etransport_prepare_vehicle_change", {"plate": "CJ99AAA"}),
    ):
        prepared = await _call(server, name, uit=_UIT, declarant_ref="REF-42", **extra)
        assert prepared["valid"] is True, name
        assert prepared["transport_preview"]["declarant_ref"] == "REF-42", name
        assert 'refDeclarant="REF-42"' in prepared["xml"], name


async def test_etransport_nomenclature_lists_names_and_codes(tmp_path: Path) -> None:
    server = create_server(_config(tmp_path))
    counties = await _call(server, "etransport_nomenclature", kind="counties")
    assert {"name": "CLUJ", "code": 12} in counties["entries"]
    ops = await _call(server, "etransport_nomenclature", kind="operation_types")
    ttn = next(e for e in ops["entries"] if e["name"] == "TTN")
    assert ttn["code"] == 30
    assert "teritoriul" in ttn["label"]
    docs = await _call(server, "etransport_nomenclature", kind="document_types")
    aviz = next(e for e in docs["entries"] if e["code"] == 30)
    assert aviz["label"] == "Aviz de însoțire a mărfii"
    scopes = await _call(server, "etransport_nomenclature", kind="operation_scopes")
    same_as_op = next(e for e in scopes["entries"] if e["code"] == 9999)
    assert same_as_op["label"] == "Același cu operațiunea"
    # unit_codes is code-only: the Schematron's closed UN/ECE list (BR-CL-003).
    units = await _call(server, "etransport_nomenclature", kind="unit_codes")
    codes = {entry["code"] for entry in units["entries"]}
    assert {"KGM", "LTR", "H87", "TNE"} <= codes
    assert "KG" not in codes  # kilogram is KGM; bare KG is not on ANAF's list


# --- public no-auth lookups -----------------------------------------------------------

PUBLIC = "https://webservicesp.anaf.ro"


@respx.mock
async def test_anaf_lookup_taxpayers_works_without_login(tmp_path: Path) -> None:
    respx.post(f"{PUBLIC}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(
            200,
            json={
                "found": [
                    {
                        "date_generale": {"cui": 1590082, "denumire": "OMV PETROM"},
                        "inregistrare_scop_Tva": {"scpTVA": True},
                    }
                ],
                "notFound": [456],
            },
        )
    )
    # The public lookups need no ANAF session at all.
    server = create_server(_config(tmp_path, authenticated=False))
    out = await _call(server, "anaf_lookup_taxpayers", cuis=["RO 1590082", 456])
    assert out["count"] == 1
    assert out["found"][0]["general"]["name"] == "OMV PETROM"
    assert out["found"][0]["vat"]["registered"] is True
    assert out["not_found"] == [456]
    assert "raw" not in out


@respx.mock
async def test_anaf_lookup_efactura_register_404_is_not_found(tmp_path: Path) -> None:
    respx.post(f"{PUBLIC}/api/registruroefactura/v1/interogare").mock(
        return_value=httpx.Response(404, json={"found": [], "notFound": [123]})
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "anaf_lookup_efactura_register", cuis=[123])
    assert out["count"] == 0
    assert out["not_found"] == [123]


@respx.mock
async def test_anaf_lookup_farmers_membership_boolean(tmp_path: Path) -> None:
    respx.post(f"{PUBLIC}/RegAgric/api/v2/ws/agric").mock(
        return_value=httpx.Response(
            200,
            json={
                "cod": 200,
                "message": "SUCCESS",
                "found": [{"cui": 123, "statusRegAgric": False}],
                "notFound": [],
            },
        )
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "anaf_lookup_farmers", cuis=[123])
    assert out["found"][0]["registered"] is False


@respx.mock
async def test_anaf_financial_statement(tmp_path: Path) -> None:
    route = respx.get(f"{PUBLIC}/bilant").mock(
        return_value=httpx.Response(
            200,
            json={
                "an": 2023,
                "cui": 1590082,
                "deni": "OMV PETROM S.A.",
                "i": [
                    {
                        "indicator": "I13",
                        "val_indicator": 100,
                        "val_den_indicator": "Cifra de afaceri neta",
                    }
                ],
            },
        )
    )
    server = create_server(_config(tmp_path))
    out = await _call(server, "anaf_financial_statement", cui="RO1590082", year=2023)
    assert out["year"] == 2023
    assert out["indicators"][0]["code"] == "I13"
    assert "raw" not in out
    assert dict(route.calls.last.request.url.params) == {
        "an": "2023",
        "cui": "1590082",
    }


# --- tool metadata ------------------------------------------------------------------


async def test_every_tool_has_a_service_prefixed_title(tmp_path: Path) -> None:
    # Human-facing display names follow "Service: operation"; clients that render
    # titles (per spec, over the snake_case name) group the tools by service.
    server = create_server(_config(tmp_path))
    prefixes = ("e-Factura: ", "e-Transport: ", "ANAF Info: ", "SPV: ", "ANAF: ")
    for tool in await server.list_tools():
        assert tool.title is not None, f"{tool.name} has no title"
        assert tool.title.startswith(prefixes), f"{tool.name}: {tool.title!r}"


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


# --- prompts (workflow skills) --------------------------------------------------------


@pytest.fixture
def _skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    skills = tmp_path / "skills"
    (skills / "demo-flow").mkdir(parents=True)
    (skills / "demo-flow" / "SKILL.md").write_text(
        "---\n"
        "name: demo-flow\n"
        "description: >\n"
        "  Do the demo thing\n"
        "  end to end.\n"
        "---\n"
        "\n"
        "# Demo\n"
        "\n"
        "Call `demo_tool` first.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ANAFPY_SKILLS_DIR", str(skills))
    yield skills


def _prompt_text(result: GetPromptResult) -> str:
    (message,) = result.messages
    assert isinstance(message.content, TextContent)
    return message.content.text


async def test_skills_exposed_as_prompts(tmp_path: Path, _skills: Path) -> None:
    server = create_server(_config(tmp_path))
    (prompt,) = await server.list_prompts()
    assert prompt.name == "demo-flow"
    # The `>` folded frontmatter scalar becomes a one-line description.
    assert prompt.description == "Do the demo thing end to end."
    assert prompt.arguments is not None
    (argument,) = prompt.arguments
    assert (argument.name, argument.required) == ("source", False)


async def test_prompt_renders_body_without_frontmatter(
    tmp_path: Path, _skills: Path
) -> None:
    server = create_server(_config(tmp_path))
    text = _prompt_text(await server.get_prompt("demo-flow"))
    assert text.startswith("# Demo")
    assert "demo_tool" in text


async def test_prompt_source_argument_is_appended(
    tmp_path: Path, _skills: Path
) -> None:
    server = create_server(_config(tmp_path))
    text = _prompt_text(
        await server.get_prompt("demo-flow", {"source": "invoice 42 from ACME"})
    )
    assert text.startswith("# Demo")
    assert text.rstrip().endswith("invoice 42 from ACME")


async def test_repo_skills_parse_and_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default resolution serves the repo's own skills/ — keeps the real SKILL.md
    # frontmatter parseable by the loader.
    monkeypatch.delenv("ANAFPY_SKILLS_DIR", raising=False)
    server = create_server(_config(tmp_path))
    names = {p.name for p in await server.list_prompts()}
    assert "etransport-declare" in names


async def test_missing_skills_dir_serves_no_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANAFPY_SKILLS_DIR", str(tmp_path / "nope"))
    server = create_server(_config(tmp_path))
    assert await server.list_prompts() == []


def test_malformed_skill_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = tmp_path / "skills"
    (skills / "bad").mkdir(parents=True)
    (skills / "bad" / "SKILL.md").write_text(
        "---\ndescription: no name here\n---\nbody\n", encoding="utf-8"
    )
    monkeypatch.setenv("ANAFPY_SKILLS_DIR", str(skills))
    with pytest.raises(AnafConfigError, match="name"):
        create_server(_config(tmp_path))


# --- config -------------------------------------------------------------------------


def test_signing_key_never_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # The confirmation-token key is a fresh per-process secret; a stray SIGNING_KEY
    # env var must not become the HMAC key (BaseSettings populates fields by name).
    monkeypatch.setenv("ANAFPY_CLIENT_ID", "CID")
    monkeypatch.setenv("ANAFPY_CLIENT_SECRET", "S")
    monkeypatch.setenv("SIGNING_KEY", "weakkey")
    monkeypatch.setenv("signing_key", "weakkey")
    cfg = ServerConfig.from_env()
    assert cfg.signing_key != b"weakkey"
    assert len(cfg.signing_key) == 32


def test_signing_key_unique_per_config() -> None:
    a = ServerConfig(client_id="CID", client_secret="S")
    b = ServerConfig(client_id="CID", client_secret="S")
    assert a.signing_key != b.signing_key


def test_store_backend_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "file")
    assert ServerConfig.from_env().store_backend == "file"
    # Unset/blank falls back to the default backend: the OS credential store.
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "")
    assert ServerConfig.from_env().store_backend == "keyring"


def test_invalid_store_backend_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "vault")
    with pytest.raises(AnafConfigError, match="ANAFPY_TOKEN_STORE_BACKEND"):
        ServerConfig.from_env()


def test_keyring_backend_builds_a_keyring_store(fake_keyring: FakeKeyring) -> None:
    config = ServerConfig(client_id="CID", client_secret="S", store_backend="keyring")
    context = AppContext(config)
    assert isinstance(context.provider._store, KeyringTokenStore)
