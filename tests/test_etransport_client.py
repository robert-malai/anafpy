"""Behavioural tests for the e-Transport client (respx-mocked, no real network)."""

from __future__ import annotations

import base64
import json
import time

import httpx
import pytest
import respx

from anafpy._transport.base import Environment
from anafpy.auth import MemoryTokenStore, TokenProvider, TokenSet
from anafpy.auth.oauth import TOKEN_URL
from anafpy.etransport import (
    ETransportClient,
    MessageState,
)
from anafpy.exceptions import (
    AnafConfigError,
    AnafRateLimitError,
    AnafResponseError,
)

BASE = "https://api.anaf.ro/test/ETRANSPORT/ws/v1"


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


def _client() -> ETransportClient:
    return ETransportClient(_provider(), environment=Environment.TEST)


# --- upload ---------------------------------------------------------------------------


# Upload responses are JSON per the vendored upload swagger: index_incarcare + UIT on
# acceptance, Errors[{errorMessage}] on rejection. The *request* body stays XML.
_UPLOAD_OK = {
    "dateResponse": "202212231130",
    "ExecutionStatus": 0,
    "index_incarcare": 5001,
    "UIT": "UITABC123",
    "trace_id": "ba47ad72-f4c1-4457-b3f2-389602e49f69",
    "ref_declarant": "",
}


@respx.mock
async def test_upload_accepted_returns_upload_id_and_uit() -> None:
    route = respx.post(f"{BASE}/upload/ETRANSP/123456789/2").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    async with _client() as client:
        result = await client.upload(b"<decl/>", cif="123456789")

    assert result.accepted
    assert result.upload_id == "5001"
    assert result.uit == "UITABC123"
    assert result.errors == []
    req = route.calls.last.request
    assert req.headers["content-type"] == "application/xml"


@respx.mock
async def test_upload_sends_application_xml_not_text_plain() -> None:
    route = respx.post(f"{BASE}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    async with _client() as client:
        await client.upload(b"<x/>", cif="123")
    assert route.calls.last.request.headers["content-type"] == "application/xml"


@respx.mock
async def test_upload_version_defaults_to_2() -> None:
    route = respx.post(f"{BASE}/upload/ETRANSP/999/2").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    async with _client() as client:
        await client.upload(b"<x/>", cif="999")
    assert route.called


@respx.mock
async def test_upload_custom_version_in_path() -> None:
    route = respx.post(f"{BASE}/upload/ETRANSP/999/1").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    async with _client() as client:
        await client.upload(b"<x/>", cif="999", version=1)
    assert route.called


@respx.mock
async def test_upload_rejected_returns_errors_not_exception() -> None:
    respx.post(f"{BASE}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200,
            json={
                "ExecutionStatus": 1,
                "Errors": [{"errorMessage": "Schema invalid"}],
            },
        )
    )
    async with _client() as client:
        result = await client.upload(b"<bad/>", cif="123")

    assert not result.accepted
    assert result.upload_id is None
    assert result.uit is None
    assert result.errors == ["Schema invalid"]


@respx.mock
async def test_upload_non_json_response_raises() -> None:
    respx.post(f"{BASE}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(200, text="<header index_incarcare='1'/>")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.upload(b"<x/>", cif="123")
    assert ei.value.status_code == 200
    assert "unrecognised upload response" in str(ei.value)


@respx.mock
async def test_upload_string_xml_encoded_to_utf8() -> None:
    route = respx.post(f"{BASE}/upload/ETRANSP/1/2").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    async with _client() as client:
        result = await client.upload("<?xml version='1.0'?><decl/>", cif="1")
    assert result.accepted
    assert route.calls.last.request.content == b"<?xml version='1.0'?><decl/>"


# --- status ---------------------------------------------------------------------------


# stareMesaj responses are JSON per the vendored stare swagger: `stare` ok|nok (with
# Errors[] alongside a nok), and Errors[] *without* `stare` for query failures.
_STATUS_OK = {
    "stare": "ok",
    "dateResponse": "202208021047",
    "ExecutionStatus": 0,
    "trace_id": "366efb31-57a0-42c2-9404-72bfcbba4693",
}


@respx.mock
async def test_get_status_ok_is_terminal() -> None:
    respx.get(f"{BASE}/stareMesaj/5001").mock(
        return_value=httpx.Response(200, json=_STATUS_OK)
    )
    async with _client() as client:
        status = await client.get_status("5001")
    assert status.state is MessageState.OK
    assert status.is_terminal
    assert not status.is_processing


@respx.mock
async def test_get_status_nok_is_terminal_and_carries_errors() -> None:
    respx.get(f"{BASE}/stareMesaj/5002").mock(
        return_value=httpx.Response(
            200,
            json={
                "stare": "nok",
                "Errors": [{"errorMessage": "UIT-ul nu poate fi identificat."}],
            },
        )
    )
    async with _client() as client:
        status = await client.get_status("5002")
    assert status.state is MessageState.NOK
    assert status.is_terminal
    assert status.errors == ["UIT-ul nu poate fi identificat."]


@respx.mock
async def test_get_status_processing_is_non_terminal() -> None:
    respx.get(f"{BASE}/stareMesaj/5003").mock(
        return_value=httpx.Response(200, json={"stare": "in prelucrare"})
    )
    async with _client() as client:
        status = await client.get_status("5003")
    assert status.state is MessageState.PROCESSING
    assert status.is_processing
    assert not status.is_terminal


@respx.mock
async def test_get_status_rejected_is_terminal() -> None:
    # Upload-time rejection arrives as this `stare`; nothing further will happen
    # to the declaration, so polling must stop.
    respx.get(f"{BASE}/stareMesaj/5004").mock(
        return_value=httpx.Response(
            200, json={"stare": "XML cu erori nepreluat de sistem"}
        )
    )
    async with _client() as client:
        status = await client.get_status("5004")
    assert status.state is MessageState.REJECTED
    assert status.is_terminal
    assert not status.is_processing


@respx.mock
async def test_get_status_query_error_raises_not_rejected() -> None:
    # Errors without `stare` = query failure (bad index, no rights, daily limit),
    # not a document outcome.
    respx.get(f"{BASE}/stareMesaj/9999").mock(
        return_value=httpx.Response(
            200,
            json={"Errors": [{"errorMessage": "Nu aveti dreptul de interogare"}]},
        )
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.get_status("9999")
    assert ei.value.status_code == 200
    assert "Nu aveti dreptul de interogare" in str(ei.value)


@respx.mock
async def test_get_status_uses_path_param_not_query() -> None:
    route = respx.get(f"{BASE}/stareMesaj/9999").mock(
        return_value=httpx.Response(200, json=_STATUS_OK)
    )
    async with _client() as client:
        await client.get_status("9999")
    assert route.called
    # Confirm no query params on the URL.
    assert route.calls.last.request.url.query == b""


# --- list_notifications ---------------------------------------------------------------


@respx.mock
async def test_list_notifications_parses_mesaje_envelope() -> None:
    # Per the lista swagger: notifications under `mesaje`, plus serial/cui/titlu.
    payload = {
        "mesaje": [
            {
                "tip": "NOT",
                "stare": "OK",
                "uit": "UITABC",
                "tip_op": "10",
                "nr_veh": "B01ABC",
                "mesaje": [],
            }
        ],
        "serial": "1234AA456",
        "cui": "123456789",
        "titlu": "Lista Mesaje disponibile din ultimele 30 zile",
    }
    route = respx.get(f"{BASE}/lista/30/123456789").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        items = [n async for n in client.list_notifications(days=30, cif="123456789")]

    assert route.called
    assert len(items) == 1
    n = items[0]
    assert n.tip == "NOT"
    assert n.stare == "OK"
    assert n.uit == "UITABC"
    assert n.tip_op == "10"
    assert n.nr_veh == "B01ABC"


@respx.mock
async def test_list_notifications_empty_window_yields_nothing() -> None:
    # The no-results note rides the same Errors[] array as genuine errors.
    route = respx.get(f"{BASE}/lista/5/123").mock(
        return_value=httpx.Response(
            200,
            json={"Errors": [{"errorMessage": "Nu exista mesaje in ultimele 5 zile"}]},
        )
    )
    async with _client() as client:
        items = [n async for n in client.list_notifications(days=5, cif="123")]
    assert items == []
    assert route.called


@respx.mock
async def test_list_notifications_real_error_raises() -> None:
    respx.get(f"{BASE}/lista/5/123").mock(
        return_value=httpx.Response(
            200,
            json={
                "Errors": [
                    {"errorMessage": "Numarul de zile introdus= 60a nu este un numar"}
                ]
            },
        )
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            [n async for n in client.list_notifications(days=5, cif="123")]
    assert ei.value.status_code == 200
    assert "nu este un numar" in str(ei.value)


async def test_list_notifications_validates_days() -> None:
    client = _client()
    with pytest.raises(AnafConfigError):
        client.list_notifications(days=0, cif="1")


@respx.mock
async def test_list_notifications_uses_path_params() -> None:
    route = respx.get(f"{BASE}/lista/60/777").mock(
        return_value=httpx.Response(200, json={"mesaje": []})
    )
    async with _client() as client:
        items = [n async for n in client.list_notifications(days=60, cif="777")]
    assert items == []
    assert route.called
    # Confirm no query params.
    assert route.calls.last.request.url.query == b""


@respx.mock
async def test_list_notification_with_error_messages() -> None:
    payload = {
        "mesaje": [
            {
                "tip": "NOT",
                "stare": "ERR",
                "uit": None,
                "mesaje": [
                    {"tip": "ERR", "mesaj": "Vehicul neidentificat"},
                    {"tip": "WARN", "mesaj": "Greutate lipsa"},
                ],
            }
        ]
    }
    respx.get(f"{BASE}/lista/1/42").mock(return_value=httpx.Response(200, json=payload))
    async with _client() as client:
        items = [n async for n in client.list_notifications(days=1, cif="42")]
    n = items[0]
    assert n.stare == "ERR"
    assert len(n.mesaje) == 2
    assert n.mesaje[0].tip == "ERR"
    assert n.mesaje[0].mesaj == "Vehicul neidentificat"
    assert n.mesaje[1].tip == "WARN"


# --- info -----------------------------------------------------------------------------


@respx.mock
async def test_info_required_param_only() -> None:
    route = respx.get(f"{BASE}/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "uit": "UITXYZ",
                    "cod_decl": "2",
                    "den_decl": "Declarant SRL",
                    "ref_decl": "R2",
                    "data_transp": "20260701",
                    "data_exp_uit": "20260703",
                    "tr_tara": "RO",
                    "tr_cod": "TR999",
                    "tr_den": "Transp SRL",
                    "nr_veh": "CJ11XYZ",
                    "nr_rem1": None,
                    "nr_rem2": None,
                    "loc_start": {
                        "tip_loc": "ADR",
                        "judet": "Cluj",
                        "localitate": "Cluj-Napoca",
                        "strada": "Str. Principala",
                        "numar": "1",
                    },
                    "loc_final": {
                        "tip_loc": "PTF",
                        "judet": None,
                        "localitate": None,
                        "strada": None,
                        "numar": None,
                    },
                }
            ],
        )
    )
    async with _client() as client:
        result = await client.info(cui_op="123456789")

    assert route.called
    params = dict(route.calls.last.request.url.params)
    assert params == {"cui_op": "123456789"}
    assert len(result.items) == 1
    item = result.items[0]
    assert item.uit == "UITXYZ"
    assert item.data_exp_uit == "20260703"
    assert item.loc_start is not None
    assert item.loc_start.tip_loc == "ADR"
    assert item.loc_start.judet == "Cluj"
    assert item.loc_final is not None
    assert item.loc_final.tip_loc == "PTF"


@respx.mock
async def test_info_optional_params_forwarded() -> None:
    route = respx.get(f"{BASE}/info").mock(return_value=httpx.Response(200, json=[]))
    async with _client() as client:
        await client.info(
            cui_op="111",
            cui_decl="222",
            uit="UITAAA",
            ref_decl="REF99",
        )
    params = dict(route.calls.last.request.url.params)
    assert params == {
        "cui_op": "111",
        "cui_decl": "222",
        "uit": "UITAAA",
        "ref_decl": "REF99",
    }


@respx.mock
async def test_info_error_from_anaf() -> None:
    respx.get(f"{BASE}/info").mock(
        return_value=httpx.Response(
            200, json={"Errors": [{"errorMessage": "CUI necunoscut"}]}
        )
    )
    async with _client() as client:
        result = await client.info(cui_op="0")
    assert result.items == []
    assert result.error == "CUI necunoscut"


@respx.mock
async def test_info_unrecognised_body_raises() -> None:
    respx.get(f"{BASE}/info").mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.info(cui_op="0")
    assert "unrecognised info response" in str(ei.value)


# --- error handling -------------------------------------------------------------------


@respx.mock
async def test_rate_limit_raises_with_retry_after() -> None:
    respx.get(f"{BASE}/stareMesaj/1").mock(
        return_value=httpx.Response(
            429, headers={"Retry-After": "15"}, text="slow down"
        )
    )
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as ei:
            await client.get_status("1")
    assert ei.value.retry_after == 15.0


@respx.mock
async def test_server_error_raises_response_error() -> None:
    respx.get(f"{BASE}/stareMesaj/1").mock(
        return_value=httpx.Response(500, text="boom")
    )
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
    status_route = respx.get(f"{BASE}/stareMesaj/5001").mock(
        side_effect=[
            httpx.Response(401, text="expired"),
            httpx.Response(200, json=_STATUS_OK),
        ]
    )
    async with _client() as client:
        status = await client.get_status("5001")
    assert status.state is MessageState.OK
    assert status_route.call_count == 2


# --- upload_and_wait ------------------------------------------------------------------


@respx.mock
async def test_upload_and_wait_polls_until_terminal() -> None:
    respx.post(f"{BASE}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(200, json=_UPLOAD_OK)
    )
    respx.get(f"{BASE}/stareMesaj/5001").mock(
        side_effect=[
            httpx.Response(200, json={"stare": "in prelucrare"}),
            httpx.Response(200, json=_STATUS_OK),
        ]
    )
    async with _client() as client:
        status = await client.upload_and_wait(
            b"<decl/>", cif="123", initial_wait=0.01, max_wait=0.02
        )
    assert status.state is MessageState.OK


@respx.mock
async def test_upload_and_wait_returns_rejection_without_polling() -> None:
    upload = respx.post(f"{BASE}/upload/ETRANSP/123/2").mock(
        return_value=httpx.Response(
            200,
            json={
                "ExecutionStatus": 1,
                "Errors": [{"errorMessage": "bad xml"}],
            },
        )
    )
    status = respx.get(f"{BASE}/stareMesaj/5001")
    async with _client() as client:
        result = await client.upload_and_wait(b"<x/>", cif="123")
    assert result.state is MessageState.REJECTED
    assert result.errors == ["bad xml"]
    assert upload.called and not status.called
