"""Behavioural tests for the SPV client (respx-mocked, no real network)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
import respx

from anafpy.exceptions import (
    AnafAuthError,
    AnafConfigError,
    AnafRateLimitError,
    AnafResponseError,
)
from anafpy.spv import (
    MemorySessionStore,
    ReportRequest,
    ReportType,
    SpvClient,
    SpvSession,
    SpvSessionProvider,
)

BASE = "https://webserviced.anaf.ro/SPVWS2/rest"
HOST = "https://webserviced.anaf.ro"

LISTING_BODY = {
    "titlu": "Lista Mesaje disponibile din ultimele 5 zile",
    "mesaje": [
        {
            "id": "100000000",
            "detalii": "recipisa pentru CIF 8000000000, tip D112",
            "cif": "8000000000",
            "data_creare": "20.12.2025 12:00:00",
            "id_solicitare": None,
            "tip": "RECIPISA",
        }
    ],
    "cnp": "1111111111118",
    "cui": "8000000000,8000000001",
    "serial": "20A0506B2450015C39C",
}

NO_MESSAGES_BODY = {
    "titlu": "Lista Mesaje",
    "eroare": "Nu exista mesaje in ultimele 5 zile",
}


def _session() -> SpvSession:
    return SpvSession(
        cookies={"MRHSession": "authenticated", "F5_ST": "1z1z"},
        established_at=datetime.now(tz=UTC),
    )


def _client(session: SpvSession | None = None) -> SpvClient:
    store = MemorySessionStore(session if session is not None else _session())
    return SpvClient(SpvSessionProvider(store=store))


# --- session handling -----------------------------------------------------------------


async def test_no_session_anywhere_raises_auth_error() -> None:
    async with SpvClient(SpvSessionProvider(store=MemorySessionStore())) as client:
        with pytest.raises(AnafAuthError, match="login"):
            await client.list_messages(5)


@respx.mock
async def test_session_loads_from_the_store_per_request() -> None:
    # The store is the source of truth: a login by another process (the CLI)
    # is picked up without rebuilding the client.
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    store = MemorySessionStore()
    async with SpvClient(SpvSessionProvider(store=store)) as client:
        with pytest.raises(AnafAuthError):
            await client.list_messages(5)
        store.save(_session())
        listing = await client.list_messages(5)
    assert listing.note == "Nu exista mesaje in ultimele 5 zile"


async def test_injected_client_without_base_url_raises_config_error() -> None:
    # An injected client is never mutated: an empty base_url is a
    # misconfiguration, named loudly at construction.
    provider = SpvSessionProvider(store=MemorySessionStore(_session()))
    async with httpx.AsyncClient() as http:
        with pytest.raises(AnafConfigError, match=f"{BASE}/"):
            SpvClient(provider, http=http)


@respx.mock
async def test_injected_client_with_base_url_is_used_and_not_closed() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    http = httpx.AsyncClient(base_url=f"{BASE}/")
    provider = SpvSessionProvider(store=MemorySessionStore(_session()))
    client = SpvClient(provider, http=http)
    listing = await client.list_messages(5)
    await client.aclose()
    assert listing.note == "Nu exista mesaje in ultimele 5 zile"
    assert not http.is_closed
    await http.aclose()


@respx.mock
async def test_cookies_ride_every_request() -> None:
    route = respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    async with _client() as client:
        await client.list_messages(5)
    sent = route.calls.last.request
    assert "MRHSession=authenticated" in sent.headers.get("Cookie", "")


@respx.mock
async def test_rotated_cookies_are_persisted_to_the_store() -> None:
    store = MemorySessionStore(_session())
    respx.get(f"{BASE}/listaMesaje").respond(
        json=NO_MESSAGES_BODY,
        headers={"Set-Cookie": "MRHSession=rotated;path=/;secure"},
    )
    async with SpvClient(SpvSessionProvider(store=store)) as client:
        await client.list_messages(5)
    saved = store.load()
    assert saved is not None
    assert saved.cookies["MRHSession"] == "rotated"


@respx.mock
async def test_revalidation_hop_is_followed_transparently() -> None:
    # APM mid-session revalidation: 302 -> /my.policy_nonce -> 302 back -> 200.
    api = respx.get(f"{BASE}/listaMesaje")
    api.side_effect = [
        httpx.Response(
            302,
            headers={
                "Location": f"{HOST}/my.policy_nonce?nonce=abc",
                "Set-Cookie": "MRHSession=revalidated;path=/;secure",
            },
        ),
        httpx.Response(200, json=LISTING_BODY),
    ]
    respx.get(f"{HOST}/my.policy_nonce").respond(
        302, headers={"Location": "/SPVWS2/rest/listaMesaje?zile=5"}
    )
    async with _client() as client:
        listing = await client.list_messages(5)
    assert len(listing.messages) == 1
    assert api.call_count == 2


@respx.mock
async def test_bounce_to_the_login_wall_raises_session_expired() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(
        302, headers={"Location": f"{HOST}/my.policy"}
    )
    async with _client() as client:
        with pytest.raises(AnafAuthError, match="expired"):
            await client.list_messages(5)


@respx.mock
async def test_login_bootstraps_and_saves_the_session() -> None:
    class FakeBootstrapper:
        async def bootstrap(self) -> SpvSession:
            return SpvSession(
                cookies={"MRHSession": "fresh"}, established_at=datetime.now(tz=UTC)
            )

    store = MemorySessionStore()
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    provider = SpvSessionProvider(store=store, bootstrapper=FakeBootstrapper())
    async with SpvClient(provider) as client:
        await client.login()
        await client.list_messages(5)
    saved = store.load()
    assert saved is not None
    assert saved.cookies == {"MRHSession": "fresh"}


async def test_login_without_a_bootstrapper_is_a_config_error() -> None:
    async with _client() as client:
        with pytest.raises(AnafConfigError, match="bootstrapper"):
            await client.login()


# --- listaMesaje ----------------------------------------------------------------------


@respx.mock
async def test_list_messages_parses_the_full_shape() -> None:
    route = respx.get(f"{BASE}/listaMesaje").respond(json=LISTING_BODY)
    async with _client() as client:
        listing = await client.list_messages(5, cif="8000000000")
    assert route.calls.last.request.url.params["zile"] == "5"
    assert route.calls.last.request.url.params["cif"] == "8000000000"
    assert listing.authorized_cuis == ["8000000000", "8000000001"]
    assert listing.messages[0].kind == "RECIPISA"
    assert listing.note is None


@respx.mock
async def test_list_messages_no_results_note_is_not_an_error() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    async with _client() as client:
        listing = await client.list_messages(5)
    assert listing.messages == []
    assert listing.note == "Nu exista mesaje in ultimele 5 zile"


@respx.mock
async def test_list_messages_genuine_error_raises_with_hint() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(
        json={
            "titlu": "Lista Mesaje",
            "eroare": "Nu veti drept sa solictati informatii despre CIF=1",
        }
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="no SPV rights") as info:
            await client.list_messages(5)
    assert "Nu veti drept" in str(info.value)  # verbatim Romanian kept


async def test_list_messages_rejects_non_positive_days_locally() -> None:
    async with _client() as client:
        with pytest.raises(AnafConfigError, match="days"):
            await client.list_messages(0)


# --- descarcare -----------------------------------------------------------------------


@respx.mock
async def test_download_returns_pdf_bytes() -> None:
    respx.get(f"{BASE}/descarcare").respond(content=b"%PDF-1.7 fake")
    async with _client() as client:
        document = await client.download_document("100000000")
    assert document.is_pdf
    assert document.message_id == "100000000"
    assert document.media_type == "application/pdf"


@respx.mock
async def test_download_error_payload_raises_with_hint() -> None:
    respx.get(f"{BASE}/descarcare").respond(
        json={
            "titlu": "Descarcare mesaj 1",
            "eroare": "Nu aveti dreptul sa descarcati acest mesaj",
        }
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="no SPV rights"):
            await client.download_document("1")


@respx.mock
async def test_download_unrecognised_body_is_explicit() -> None:
    respx.get(f"{BASE}/descarcare").respond(content=b"<html>gateway</html>")
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised descarcare"):
            await client.download_document("1")


# --- cerere ---------------------------------------------------------------------------

CERERE_BODY = {
    "id_solicitare": 260149,
    "parametri": "an=2017, cui=8000000000",
    "serial": "20A0506B2450015C39C",
    "cnp": "1111111111118",
    "titlu": "Transmitere cerere tip D101",
}


@respx.mock
async def test_request_report_files_and_parses() -> None:
    route = respx.get(f"{BASE}/cerere").respond(json=CERERE_BODY)
    async with _client() as client:
        result = await client.request_report(
            ReportRequest(type_=ReportType.D101, cui="8000000000", year=2017)
        )
    params = route.calls.last.request.url.params
    assert params["tip"] == "D101"
    assert params["an"] == "2017"
    assert result.request_id == "260149"


@respx.mock
async def test_request_report_error_raises_verbatim() -> None:
    respx.get(f"{BASE}/cerere").respond(
        json={"eroare": "Tip raport= CAF inca nu poate fi solicitat prin WS"}
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="CAF"):
            await client.request_report(
                ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="8000000000")
            )


# --- wait_for_report ------------------------------------------------------------------


@respx.mock
async def test_wait_for_report_polls_then_downloads() -> None:
    delivered = {
        "titlu": "Lista Mesaje",
        "mesaje": [
            {
                "id": "999",
                "detalii": "Obligatii de plata pentru CNP 1111111111118",
                "cif": "1111111111118",
                "data_creare": "20.12.2025 12:00:00",
                "id_solicitare": "260149",
                "tip": "RASPUNS SOLICITARE",
            }
        ],
        "cnp": "1111111111118",
        "cui": "1111111111118",
        "serial": "s",
    }
    listing = respx.get(f"{BASE}/listaMesaje")
    listing.side_effect = [
        httpx.Response(200, json=NO_MESSAGES_BODY),
        httpx.Response(200, json=delivered),
    ]
    respx.get(f"{BASE}/descarcare").respond(content=b"%PDF-1.7 report")
    async with _client() as client:
        document = await client.wait_for_report(
            "260149", timeout=5.0, initial_wait=0.01, max_wait=0.02
        )
    assert document.is_pdf
    assert document.message_id == "999"
    assert listing.call_count == 2


@respx.mock
async def test_wait_for_report_timeout_is_actionable() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(json=NO_MESSAGES_BODY)
    async with _client() as client:
        with pytest.raises(TimeoutError, match="same request_id"):
            await client.wait_for_report(
                "260149", timeout=0.05, initial_wait=0.01, max_wait=0.02
            )


# --- transport edges ------------------------------------------------------------------


@respx.mock
async def test_transient_network_failures_are_retried_on_reads() -> None:
    route = respx.get(f"{BASE}/listaMesaje")
    route.side_effect = [
        httpx.ConnectError("boom"),
        httpx.Response(200, json=NO_MESSAGES_BODY),
    ]
    async with _client() as client:
        listing = await client.list_messages(5)
    assert listing.messages == []
    assert route.call_count == 2


@respx.mock
async def test_off_host_redirect_is_refused() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(
        302, headers={"Location": "https://evil.example/x"}
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="off-host"):
            await client.list_messages(5)


@respx.mock
async def test_non_json_list_body_is_explicit() -> None:
    respx.get(f"{BASE}/listaMesaje").respond(content=b"<html>APM says hi</html>")
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised listaMesaje"):
            await client.list_messages(5)


@respx.mock
async def test_http_error_status_raises() -> None:
    route = respx.get(f"{BASE}/listaMesaje").respond(500, content=b"oops")
    async with _client() as client:
        with pytest.raises(AnafResponseError) as info:
            await client.list_messages(5)
    assert info.value.status_code == 500
    # A received answer is deterministic — the read retry must not repeat it.
    assert route.call_count == 1


@respx.mock
async def test_rate_limit_surfaces_immediately_without_retry() -> None:
    # The no-auto-backoff stance holds on the SPV reads too: only plain network
    # failures are retried, never a received 429.
    route = respx.get(f"{BASE}/listaMesaje").respond(429, headers={"Retry-After": "60"})
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as info:
            await client.list_messages(5)
    assert info.value.retry_after == 60.0
    assert route.call_count == 1


@respx.mock
async def test_unparseable_lista_shape_raises_response_error() -> None:
    # A 200 whose JSON does not fit the model must surface as AnafResponseError,
    # not leak a raw pydantic ValidationError (parity with the other clients).
    respx.get(f"{BASE}/listaMesaje").respond(
        json={"titlu": "Lista Mesaje", "mesaje": [{"id": "1"}]}
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError, match="unrecognised listaMesaje"):
            await client.list_messages(5)


def test_listing_bodies_are_valid_json() -> None:
    # Guard the fixtures themselves.
    json.dumps(LISTING_BODY)
    json.dumps(NO_MESSAGES_BODY)
    json.dumps(CERERE_BODY)
