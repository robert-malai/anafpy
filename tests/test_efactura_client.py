"""Behavioural tests for the e-Factura client (respx-mocked, no real network)."""

from __future__ import annotations

import base64
import io
import json
import time
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest
import respx
from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlSerializer

from anafpy._transport.base import Environment
from anafpy.auth import MemoryTokenStore, TokenProvider, TokenSet
from anafpy.auth.oauth import TOKEN_URL
from anafpy.efactura import (
    EFacturaClient,
    Filter,
    Invoice,
    MessageState,
    UploadStandard,
)
from anafpy.efactura.ubl.common.ubl_common_aggregate_components_2_1 import (
    AccountingCustomerParty,
    AccountingSupplierParty,
    LegalMonetaryTotal,
)
from anafpy.efactura.ubl.common.ubl_common_basic_components_2_1 import (
    Id,
    IssueDate,
    PayableAmount,
)
from anafpy.exceptions import AnafConfigError, AnafRateLimitError, AnafResponseError

BASE = "https://api.anaf.ro/test/FCTEL/rest"


def _jwt(exp: float) -> str:
    def seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{seg({'alg': 'RS512'})}.{seg({'exp': int(exp)})}.sig"


def _provider() -> TokenProvider:
    token = TokenSet.from_token_response(
        {
            "access_token": _jwt(time.time() + 3600),
            "refresh_token": "r1",
            "token_type": "Bearer",
        }
    )
    return TokenProvider(
        client_id="CID", client_secret="S", store=MemoryTokenStore(token)
    )


def _client() -> EFacturaClient:
    return EFacturaClient(_provider(), environment=Environment.TEST)


def _invoice_xml() -> bytes:
    inv = Invoice(
        id=Id(value="INV-1"),
        issue_date=IssueDate(value=XmlDate(2026, 6, 28)),
        accounting_supplier_party=AccountingSupplierParty(),
        accounting_customer_party=AccountingCustomerParty(),
        legal_monetary_total=LegalMonetaryTotal(
            payable_amount=PayableAmount(value=Decimal("100.00"), currency_id="RON"),
        ),
    )
    return XmlSerializer().render(inv).encode()


# --- upload ---------------------------------------------------------------------------


@respx.mock
async def test_upload_accepted_parses_index_and_sends_text_plain() -> None:
    route = respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(
            200,
            text='<header xmlns="mfp:anaf:dgti:spv:respUploadFisier:v1"'
            ' ExecutionStatus="0" index_incarcare="3828"/>',
        )
    )
    async with _client() as client:
        result = await client.upload(
            b"<Invoice/>", cif="123", standard=UploadStandard.UBL
        )

    assert result.accepted
    assert result.upload_id == "3828"
    req = route.calls.last.request
    assert req.headers["content-type"] == "text/plain"
    assert dict(req.url.params) == {"standard": "UBL", "cif": "123"}


@respx.mock
async def test_upload_rejected_returns_errors_not_exception() -> None:
    respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(
            200,
            text='<header xmlns="mfp:anaf:dgti:spv:respUploadFisier:v1"'
            ' ExecutionStatus="1"><Errors errorMessage="Fisier invalid"/></header>',
        )
    )
    async with _client() as client:
        result = await client.upload(b"<Invoice/>", cif="123")

    assert not result.accepted
    assert result.upload_id is None
    assert result.errors == ["Fisier invalid"]


@respx.mock
async def test_upload_optional_flags_become_query_params() -> None:
    route = respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="1"/>')
    )
    async with _client() as client:
        await client.upload(b"<x/>", cif="9", extern=True, autofactura=True)
    params = dict(route.calls.last.request.url.params)
    assert params["extern"] == "DA"
    assert params["autofactura"] == "DA"
    assert "executare" not in params


# --- status ---------------------------------------------------------------------------


@respx.mock
async def test_get_status_ok_exposes_download_id() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="ok" id_descarcare="55"/>')
    )
    async with _client() as client:
        status = await client.get_status("3828")
    assert status.state is MessageState.OK
    assert status.is_terminal
    assert status.download_id == "55"


@respx.mock
async def test_get_status_nok_is_terminal_business_outcome() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="nok" id_descarcare="7"/>')
    )
    async with _client() as client:
        status = await client.get_status("3828")
    assert status.state is MessageState.NOK
    assert status.is_terminal
    assert not status.is_processing


@respx.mock
async def test_get_status_processing_is_non_terminal() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="in prelucrare"/>')
    )
    async with _client() as client:
        status = await client.get_status("3828")
    assert status.state is MessageState.PROCESSING
    assert status.is_processing
    assert not status.is_terminal


# --- download -------------------------------------------------------------------------


@respx.mock
async def test_download_preserves_raw_and_parses_invoice() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("3828.xml", _invoice_xml())
        zf.writestr("semnatura_3828.xml", b"<Signature/>")
    zip_bytes = buf.getvalue()

    respx.get(f"{BASE}/descarcare").mock(
        return_value=httpx.Response(200, content=zip_bytes)
    )
    async with _client() as client:
        msg = await client.download("18")

    assert msg.raw_zip == zip_bytes
    assert msg.signature_xml == b"<Signature/>"
    assert isinstance(msg.document, Invoice)
    assert msg.document.id is not None and msg.document.id.value == "INV-1"


# --- lists ----------------------------------------------------------------------------


def _msg(idx: str) -> dict[str, object]:
    return {"id": idx, "id_solicitare": "3828", "tip": "FACTURA TRIMISA"}


@respx.mock
async def test_list_messages_days_window_drives_paginated_endpoint() -> None:
    route = respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        side_effect=[
            httpx.Response(200, json={"mesaje": [_msg("18")]}),
            httpx.Response(200, json={"mesaje": []}),  # terminates the walk
        ]
    )
    async with _client() as client:
        items = [
            m
            async for m in client.list_messages(days=30, cif="123", filter=Filter.SENT)
        ]

    assert [m.id for m in items] == ["18"]
    first = dict(route.calls[0].request.url.params)
    assert first["cif"] == "123" and first["pagina"] == "1" and first["filtru"] == "T"
    # days=30 maps to a 30-day millisecond window.
    assert int(first["endTime"]) - int(first["startTime"]) == 30 * 86_400_000


@respx.mock
async def test_list_messages_explicit_range_passes_exact_ms() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 29, tzinfo=UTC)
    route = respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(200, json={"mesaje": []})
    )
    async with _client() as client:
        items = [m async for m in client.list_messages(start=start, end=end, cif="9")]

    assert items == []
    params = dict(route.calls[0].request.url.params)
    assert params["startTime"] == str(int(start.timestamp() * 1000))
    assert params["endTime"] == str(int(end.timestamp() * 1000))


@respx.mock
async def test_list_messages_paginates_until_empty_page() -> None:
    route = respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        side_effect=[
            httpx.Response(200, json={"mesaje": [_msg("1"), _msg("2")]}),
            httpx.Response(200, json={"mesaje": [_msg("3")]}),
            httpx.Response(200, json={"mesaje": []}),
        ]
    )
    async with _client() as client:
        items = [m async for m in client.list_messages(days=10, cif="123")]

    assert [m.id for m in items] == ["1", "2", "3"]
    assert [c.request.url.params["pagina"] for c in route.calls] == ["1", "2", "3"]


@respx.mock
async def test_list_messages_honours_total_pages_field() -> None:
    route = respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(
            200, json={"mesaje": [_msg("1")], "numar_total_pagini": 1}
        )
    )
    async with _client() as client:
        items = [m async for m in client.list_messages(days=10, cif="123")]

    assert len(items) == 1
    assert route.call_count == 1  # stopped on total_pages, no extra empty request


@respx.mock
async def test_list_messages_empty_window_yields_nothing() -> None:
    route = respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(
            200, json={"eroare": "Nu există mesaje în interval"}
        )
    )
    async with _client() as client:
        items = [m async for m in client.list_messages(days=5, cif="123")]
    assert items == []
    assert route.call_count == 1


@respx.mock
async def test_list_messages_real_error_raises() -> None:
    respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(200, json={"eroare": "CIF invalid"})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            [m async for m in client.list_messages(days=5, cif="bad")]
    assert ei.value.status_code == 200
    assert "CIF invalid" in str(ei.value)


def test_list_messages_window_args_are_validated() -> None:
    client = _client()
    with pytest.raises(AnafConfigError):  # both windows
        client.list_messages(
            cif="1",
            days=5,
            start=datetime(2026, 6, 1, tzinfo=UTC),
            end=datetime(2026, 6, 2, tzinfo=UTC),
        )
    with pytest.raises(AnafConfigError):  # no window
        client.list_messages(cif="1")
    with pytest.raises(AnafConfigError):  # out-of-range days
        client.list_messages(cif="1", days=61)


# --- errors & auth --------------------------------------------------------------------


@respx.mock
async def test_rate_limit_raises_with_retry_after() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(
            429, headers={"Retry-After": "12"}, text="slow down"
        )
    )
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as ei:
            await client.get_status("1")
    assert ei.value.retry_after == 12.0


@respx.mock
async def test_rate_limit_parses_http_date_retry_after() -> None:
    # RFC 9110 allows an HTTP-date; it must not mask the rate-limit error.
    when = datetime.now(UTC) + timedelta(seconds=90)
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(
            429, headers={"Retry-After": format_datetime(when, usegmt=True)}
        )
    )
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as ei:
            await client.get_status("1")
    assert ei.value.retry_after is not None
    assert 80 <= ei.value.retry_after <= 91


@respx.mock
async def test_rate_limit_tolerates_unparseable_retry_after() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "soon"})
    )
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as ei:
            await client.get_status("1")
    assert ei.value.retry_after is None


@respx.mock
async def test_server_error_raises_response_error() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(return_value=httpx.Response(500, text="boom"))
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.get_status("1")
    assert ei.value.status_code == 500


@respx.mock
async def test_401_triggers_refresh_then_retries() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": _jwt(time.time() + 3600),
                "refresh_token": "r2",
                "token_type": "Bearer",
            },
        )
    )
    status_route = respx.get(f"{BASE}/stareMesaj").mock(
        side_effect=[
            httpx.Response(401, text="expired"),
            httpx.Response(200, text='<header stare="ok"/>'),
        ]
    )
    async with _client() as client:
        status = await client.get_status("3828")
    assert status.state is MessageState.OK
    assert status_route.call_count == 2


# --- upload_and_wait ------------------------------------------------------------------


@respx.mock
async def test_upload_and_wait_polls_until_terminal() -> None:
    respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="3828"/>')
    )
    respx.get(f"{BASE}/stareMesaj").mock(
        side_effect=[
            httpx.Response(200, text='<header stare="in prelucrare"/>'),
            httpx.Response(200, text='<header stare="ok" id_descarcare="9"/>'),
        ]
    )
    async with _client() as client:
        status = await client.upload_and_wait(
            b"<Invoice/>", cif="123", initial_wait=0.01, max_wait=0.02
        )
    assert status.state is MessageState.OK
    assert status.download_id == "9"


@respx.mock
async def test_upload_and_wait_returns_rejection_without_polling() -> None:
    upload = respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(
            200,
            text='<header ExecutionStatus="1"><Errors errorMessage="bad"/></header>',
        )
    )
    status = respx.get(f"{BASE}/stareMesaj")
    async with _client() as client:
        result = await client.upload_and_wait(b"<x/>", cif="123")
    assert result.state is MessageState.REJECTED
    assert result.errors == ["bad"]
    assert upload.called and not status.called
