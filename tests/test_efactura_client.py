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

from _authoring import make_invoice
from anafpy._transport.base import Environment
from anafpy.auth import MemoryTokenStore, TokenProvider, TokenSet
from anafpy.auth.oauth import TOKEN_URL
from anafpy.efactura import (
    EFacturaClient,
    Filter,
    Invoice,
    MessageListItem,
    MessageState,
    UploadStandard,
)
from anafpy.efactura.authoring import InvoiceValidationError, PrecedingInvoice
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


@respx.mock
async def test_upload_invoice_composes_and_picks_the_standard() -> None:
    # The authored path: a flat InvoiceDocument is rendered to CIUS-RO UBL and
    # uploaded with the standard matching its kind (UBL / CN).
    route = respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(200, text='<header index_incarcare="42"/>')
    )
    async with _client() as client:
        result = await client.upload_invoice(make_invoice(), cif="123")
        assert result.accepted
        assert result.upload_id == "42"
        req = route.calls.last.request
        assert dict(req.url.params) == {"standard": "UBL", "cif": "123"}
        assert req.content.startswith(b"<?xml")

        credit_note = make_invoice(
            kind="credit_note",
            number="CN-1",
            preceding_invoices=[PrecedingInvoice(number="INV-2026-0042")],
        )
        await client.upload_invoice(credit_note, cif="123")
        assert route.calls.last.request.url.params["standard"] == "CN"


async def test_upload_invoice_validates_unless_skipped() -> None:
    # No due date / payment terms -> fatal BR-CO-25; the render gate raises before
    # any request unless the caller opts out and lets ANAF judge.
    faulty = make_invoice(due_date=None)
    async with _client() as client:
        with pytest.raises(InvoiceValidationError, match="BR-CO-25"):
            await client.upload_invoice(faulty, cif="123")

    with respx.mock:
        route = respx.post(f"{BASE}/upload").mock(
            return_value=httpx.Response(200, text='<header index_incarcare="1"/>')
        )
        async with _client() as client:
            result = await client.upload_invoice(
                faulty, cif="123", skip_validation=True
            )
        assert result.accepted
        assert route.call_count == 1


@respx.mock
async def test_upload_non_xml_body_raises_anaf_error() -> None:
    # A 200 that is not XML at all (HTML error page, gateway response) must land in
    # the AnafError hierarchy, not leak an ET.ParseError.
    respx.post(f"{BASE}/upload").mock(
        return_value=httpx.Response(200, text="<html>Service Unavailable</html> oops&")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised upload response"):
            await client.upload(b"<Invoice/>", cif="123")


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


async def test_injected_client_without_base_url_raises_config_error() -> None:
    # An injected client is never mutated: an empty base_url is a
    # misconfiguration, named loudly at construction.
    async with httpx.AsyncClient() as http:
        with pytest.raises(AnafConfigError, match=f"{BASE}/"):
            EFacturaClient(_provider(), environment=Environment.TEST, http=http)


@respx.mock
async def test_injected_client_with_base_url_is_used_and_not_closed() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="ok"/>')
    )
    http = httpx.AsyncClient(base_url=f"{BASE}/")
    client = EFacturaClient(_provider(), environment=Environment.TEST, http=http)
    status = await client.get_status("3828")
    await client.aclose()
    assert status.state is MessageState.OK
    assert not http.is_closed
    await http.aclose()


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


@respx.mock
async def test_get_status_rejected_is_terminal() -> None:
    # Upload-time rejection arrives as this `stare`; nothing further will happen
    # to the document, so polling must stop.
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(
            200, text='<header stare="XML cu erori nepreluat de sistem"/>'
        )
    )
    async with _client() as client:
        status = await client.get_status("3828")
    assert status.state is MessageState.REJECTED
    assert status.is_terminal
    assert not status.is_processing


@respx.mock
async def test_get_status_unknown_state_raises_anaf_error() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text='<header stare="suspendat"/>')
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.get_status("3828")
    assert ei.value.status_code == 200
    assert "suspendat" in str(ei.value)


@respx.mock
async def test_get_status_query_error_raises_not_rejected() -> None:
    # Errors without `stare` = query failure (bad/unknown index, no SPV rights, daily
    # limit — per the stareMesaj swagger), not a document rejection.
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(
            200,
            text="<header><Errors errorMessage="
            '"Nu exista factura cu id_incarcare= 15000"/></header>',
        )
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.get_status("15000")
    assert ei.value.status_code == 200
    assert "Nu exista factura" in str(ei.value)


@respx.mock
async def test_get_status_non_xml_body_raises_anaf_error() -> None:
    respx.get(f"{BASE}/stareMesaj").mock(
        return_value=httpx.Response(200, text="not xml at all")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised stareMesaj"):
            await client.get_status("3828")


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


@respx.mock
async def test_download_non_zip_body_raises_response_error_with_body() -> None:
    # ANAF reports e.g. an unknown id as a 200 error payload, not an HTTP error.
    respx.get(f"{BASE}/descarcare").mock(
        return_value=httpx.Response(200, json={"eroare": "id invalid"})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.download("bogus")
    assert ei.value.status_code == 200
    assert "id invalid" in (ei.value.body or "")


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
    # Relative to now so the range always sits inside ANAF's 60-day retention.
    end = datetime.now(tz=UTC) - timedelta(days=1)
    start = end - timedelta(days=28)
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
async def test_list_messages_page_cap_raises_not_truncates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A server that never returns a terminal page must raise, not silently
    # truncate the list at the defensive cap.
    import anafpy.efactura.client as efactura_client

    monkeypatch.setattr(efactura_client, "_MAX_LIST_PAGES", 3)
    respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(200, json={"mesaje": [_msg("1")]})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="no terminal page"):
            [m async for m in client.list_messages(days=10, cif="123")]


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


@respx.mock
async def test_list_messages_non_json_body_raises_anaf_error() -> None:
    # Garbage 200 bodies (HTML, or JSON that is not an object) must land in the
    # AnafError hierarchy, not leak a JSONDecodeError / AttributeError.
    respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(200, text="<html>502</html>")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised list response"):
            [m async for m in client.list_messages(days=5, cif="123")]


@respx.mock
async def test_list_messages_json_array_body_raises_anaf_error() -> None:
    respx.get(f"{BASE}/listaMesajePaginatieFactura").mock(
        return_value=httpx.Response(200, json=[1, 2, 3])
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised list response"):
            [m async for m in client.list_messages(days=5, cif="123")]


def test_list_messages_window_args_are_validated() -> None:
    # All raised eagerly, before any request — no respx mock is installed, so a
    # request slipping through would fail loudly.
    now = datetime.now(tz=UTC)
    client = _client()
    with pytest.raises(AnafConfigError):  # both windows
        client.list_messages(
            cif="1",
            days=5,
            start=now - timedelta(days=2),
            end=now - timedelta(days=1),
        )
    with pytest.raises(AnafConfigError):  # no window
        client.list_messages(cif="1")
    with pytest.raises(AnafConfigError):  # out-of-range days
        client.list_messages(cif="1", days=61)
    with pytest.raises(AnafConfigError, match="before `start`"):
        client.list_messages(
            cif="1", start=now - timedelta(days=1), end=now - timedelta(days=2)
        )
    with pytest.raises(AnafConfigError, match="in the future"):
        client.list_messages(
            cif="1", start=now - timedelta(days=1), end=now + timedelta(days=1)
        )
    with pytest.raises(AnafConfigError, match="older than 60 days"):
        client.list_messages(
            cif="1", start=now - timedelta(days=61), end=now - timedelta(days=1)
        )


# --- MessageListItem: CIF fallback from `detalii` -------------------------------------

# The wire never carries cif_emitent/cif_beneficiar (live-confirmed in production
# 2026-07-06, despite the API PDF listing them) — the model extracts them from the
# `detalii` prose. Wordings below are verbatim production/swagger samples.


def test_message_list_item_extracts_cifs_from_details() -> None:
    item = MessageListItem.model_validate(
        {
            "id": "7424075633",
            "id_solicitare": "6330291057",
            "tip": "FACTURA PRIMITA",
            "detalii": (
                "Factura cu id_incarcare=6330291057 emisa de "
                "cif_emitent=5990324 pentru cif_beneficiar=7323483"
            ),
        }
    )
    assert item.sender_cif == "5990324"
    assert item.receiver_cif == "7323483"


def test_message_list_item_self_billed_wording_swaps_parties() -> None:
    # The "in numele" party is the supplier — sender_cif keeps its seller meaning.
    # ANAF emits a double space before "ca autofactura"; kept verbatim.
    item = MessageListItem.model_validate(
        {
            "tip": "FACTURA TRIMISA",
            "detalii": (
                "Factura cu id_incarcare=6471405871 transmisa de cif=18680651 "
                " ca autofactura in numele cif=7323483"
            ),
        }
    )
    assert item.sender_cif == "7323483"
    assert item.receiver_cif == "18680651"


def test_message_list_item_error_wording_leaves_cifs_none() -> None:
    item = MessageListItem.model_validate(
        {
            "tip": "ERORI FACTURA",
            "detalii": (
                "Erori de validare identificate la factura primita cu "
                "id_incarcare=5001130147"
            ),
        }
    )
    assert item.sender_cif is None
    assert item.receiver_cif is None


def test_message_list_item_wire_cifs_win_over_details() -> None:
    # If ANAF ever starts sending the documented keys, they take precedence.
    item = MessageListItem.model_validate(
        {
            "cif_emitent": "111",
            "cif_beneficiar": "222",
            "detalii": (
                "Factura cu id_incarcare=1 emisa de cif_emitent=999 "
                "pentru cif_beneficiar=888"
            ),
        }
    )
    assert item.sender_cif == "111"
    assert item.receiver_cif == "222"


# --- validate_signature ---------------------------------------------------------------

# Host-root endpoint: no test/prod segment, outside FCTEL/rest (per the swagger).
SIGNATURE_URL = "https://api.anaf.ro/api/validate/signature"

# The two documented outcomes are both 200 `{msg}` payloads (validaresemnatura
# swagger), distinguished only by wording.
_SIG_VALID_MSG = (
    "Fișierele încărcate au fost validate cu succes, din perspectiva autenticității "
    "semnăturii aplicate."
)
_SIG_INVALID_MSG = (
    "Fișierele încărcate NU au putut fi validate cu succes, din perspectiva "
    "autenticității semnăturii aplicate."
)


@respx.mock
async def test_validate_signature_valid() -> None:
    route = respx.post(SIGNATURE_URL).mock(
        return_value=httpx.Response(200, json={"msg": _SIG_VALID_MSG})
    )
    async with _client() as client:
        result = await client.validate_signature(b"<Invoice/>", b"<Signature/>")
    assert result.valid
    assert "validate cu succes" in result.message
    body = route.calls.last.request.content
    assert b'name="file"' in body and b'name="signature"' in body


@respx.mock
async def test_validate_signature_invalid_is_value_not_exception() -> None:
    respx.post(SIGNATURE_URL).mock(
        return_value=httpx.Response(200, json={"msg": _SIG_INVALID_MSG})
    )
    async with _client() as client:
        result = await client.validate_signature("<Invoice/>", "<Signature/>")
    assert not result.valid


@respx.mock
async def test_validate_signature_unknown_message_raises() -> None:
    respx.post(SIGNATURE_URL).mock(
        return_value=httpx.Response(200, json={"msg": "Mentenanță programată"})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised signature"):
            await client.validate_signature(b"<x/>", b"<s/>")


@respx.mock
async def test_validate_signature_technical_error_raises() -> None:
    respx.post(SIGNATURE_URL).mock(
        return_value=httpx.Response(400, json={"msg": "Eroare tehnică"})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as ei:
            await client.validate_signature(b"<x/>", b"<s/>")
    assert ei.value.status_code == 400


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
