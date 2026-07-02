"""Behavioural tests for the public-services client (respx-mocked, no real network).

Fixture bodies follow the live-confirmed shapes recorded in
docs/anaf-reference/public/api.md (2026-07-02).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import respx

from anafpy.exceptions import (
    AnafConfigError,
    AnafRateLimitError,
    AnafResponseError,
)
from anafpy.public import PublicClient

BASE = "https://webservicesp.anaf.ro"


def _client(interval: float = 0.0) -> PublicClient:
    return PublicClient(min_request_interval=interval)


# --- taxpayer / VAT registry (v9) ----------------------------------------


# Live-confirmed: no cod/message envelope; body starts at found/notFound.
_TVA_FOUND = {
    "found": [
        {
            "date_generale": {
                "cui": 1590082,
                "data": "2026-07-01",
                "denumire": "OMV PETROM S.A.",
                "adresa": "MUN. BUCUREŞTI, SECT. 1, STR. CORALILOR, NR.22",
                "nrRegCom": "J40/8302/1997",
                "telefon": "0372868930",
                "codPostal": "013329",
                "act": "",
                "stare_inregistrare": "INREGISTRAT din data 02.01.1998",
                "data_inregistrare": "1998-01-02",
                "cod_CAEN": "610",
                "iban": "",
                "statusRO_e_Factura": True,
                "data_inreg_Reg_RO_e_Factura": "2022-03-01",
                "organFiscalCompetent": "Administraţie pentru Contribuabili Mari",
                "forma_de_proprietate": "PROPR.MIXTA...",
                "forma_organizare": "PERSOANA JURIDICA",
                "forma_juridica": "SOCIETATE COMERCIALA PE ACTIUNI",
            },
            "inregistrare_scop_Tva": {
                "scpTVA": True,
                "perioade_TVA": [
                    {
                        "data_inceput_ScpTVA": "1993-07-01",
                        "data_sfarsit_ScpTVA": "",
                        "data_anul_imp_ScpTVA": "",
                        "mesaj_ScpTVA": "",
                    }
                ],
            },
            "inregistrare_RTVAI": {
                "dataInceputTvaInc": "",
                "dataSfarsitTvaInc": "",
                "dataActualizareTvaInc": "",
                "dataPublicareTvaInc": "",
                "tipActTvaInc": "",
                "statusTvaIncasare": False,
            },
            "stare_inactiv": {
                "dataInactivare": "",
                "dataReactivare": "",
                "dataPublicare": "",
                "dataRadiere": "",
                "statusInactivi": False,
            },
            "inregistrare_SplitTVA": {
                "dataInceputSplitTVA": "",
                "dataAnulareSplitTVA": "",
                "statusSplitTVA": False,
            },
            "adresa_sediu_social": {
                "sdenumire_Strada": "Str. Coralilor",
                "snumar_Strada": "22",
                "sdenumire_Localitate": "Mun. Bucureşti, Sect. 1",
                "scod_Localitate": "179132",
                "sdenumire_Judet": "MUNICIPIUL BUCUREŞTI",
                "scod_Judet": "40",
                "scod_JudetAuto": "B",
                "stara": "",
                "sdetalii_Adresa": "",
                "scod_Postal": "013329",
            },
            "adresa_domiciliu_fiscal": {
                "ddenumire_Strada": "Str. Coralilor",
                "dnumar_Strada": "22",
                "ddenumire_Localitate": "Mun. Bucureşti, Sect. 1",
                "dcod_Localitate": "179132",
                "ddenumire_Judet": "MUNICIPIUL BUCUREŞTI",
                "dcod_Judet": "40",
                "dcod_JudetAuto": "B",
                "dtara": "",
                "ddetalii_Adresa": "",
                "dcod_Postal": "013329",
            },
        }
    ],
    "notFound": [99999999],
}


@respx.mock
async def test_taxpayer_lookup_parses_found_and_not_found() -> None:
    route = respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(200, json=_TVA_FOUND)
    )
    async with _client() as client:
        result = await client.lookup_taxpayers([1590082, 99999999], date="2026-07-01")

    record = result.found[0]
    assert record.cui == 1590082
    assert record.name == "OMV PETROM S.A."
    assert record.vat_registered is True
    assert record.vat.periods[0].start == "1993-07-01"
    assert record.vat.periods[0].end is None  # "" -> None
    assert record.vat_on_collection.registered is False
    assert record.is_inactive is False
    assert record.split_vat.registered is False
    assert record.efactura_registered is True
    assert record.general.efactura_register_date == "2022-03-01"
    assert record.registered_office is not None
    assert record.registered_office.county_auto_code == "B"
    assert record.fiscal_address is not None
    assert record.fiscal_address.street == "Str. Coralilor"
    assert result.not_found == [99999999]
    assert result.raw  # raw body retained

    request = route.calls.last.request
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == [
        {"cui": 1590082, "data": "2026-07-01"},
        {"cui": 99999999, "data": "2026-07-01"},
    ]


@respx.mock
async def test_taxpayer_lookup_accepts_documented_envelope() -> None:
    # doc_WS_V9.txt documents a cod/message wrapper the live service does not send;
    # accept both shapes.
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(
            200,
            json={"cod": 200, "message": "SUCCESS", "found": [], "notFound": [123]},
        )
    )
    async with _client() as client:
        result = await client.lookup_taxpayers([123])
    assert result.found == []
    assert result.not_found == [123]


@respx.mock
async def test_taxpayer_lookup_accepts_string_cod_200() -> None:
    # ANAF's numeric/string typing is inconsistent across services; a stringly
    # `"200"` must not read as an error.
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(
            200,
            json={"cod": "200", "message": "SUCCESS", "found": [], "notFound": [123]},
        )
    )
    async with _client() as client:
        result = await client.lookup_taxpayers([123])
    assert result.not_found == [123]


@respx.mock
async def test_taxpayer_lookup_error_cod_raises() -> None:
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(
            200, json={"cod": 400, "message": "limita zilnica depasita"}
        )
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as excinfo:
            await client.lookup_taxpayers([123])
    assert excinfo.value.status_code == 200
    assert "limita zilnica" in str(excinfo.value)


@respx.mock
async def test_taxpayer_lookup_unrecognised_body_raises() -> None:
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(200, text="<html>maintenance</html>")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError):
            await client.lookup_taxpayers([123])


@respx.mock
async def test_taxpayer_lookup_normalizes_ro_prefixed_cui() -> None:
    route = respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(200, json={"found": [], "notFound": []})
    )
    async with _client() as client:
        await client.lookup_taxpayers(["RO 1590082"], date="2026-07-01")
    assert json.loads(route.calls.last.request.content) == [
        {"cui": 1590082, "data": "2026-07-01"}
    ]


async def test_taxpayer_lookup_rejects_bad_input_eagerly() -> None:
    async with _client() as client:
        with pytest.raises(AnafConfigError):
            await client.lookup_taxpayers(["not-a-cui"])
        with pytest.raises(AnafConfigError):
            await client.lookup_taxpayers([])
        with pytest.raises(AnafConfigError):
            await client.lookup_taxpayers(list(range(1, 102)))  # > 100
        with pytest.raises(AnafConfigError):
            await client.lookup_taxpayers([123], date="01.07.2026")


@respx.mock
async def test_rate_limit_surfaces_retry_after() -> None:
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "5"})
    )
    async with _client() as client:
        with pytest.raises(AnafRateLimitError) as excinfo:
            await client.lookup_taxpayers([123])
    assert excinfo.value.retry_after == 5.0


@respx.mock
async def test_http_error_raises_response_error() -> None:
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(500, text="boom")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as excinfo:
            await client.lookup_taxpayers([123])
    assert excinfo.value.status_code == 500


@respx.mock
async def test_requests_are_paced_by_min_interval() -> None:
    respx.post(f"{BASE}/api/PlatitorTvaRest/v9/tva").mock(
        return_value=httpx.Response(200, json={"found": [], "notFound": []})
    )
    async with PublicClient(min_request_interval=0.05) as client:
        loop = asyncio.get_running_loop()
        start = loop.time()
        await client.lookup_taxpayers([1])
        await client.lookup_taxpayers([2])
        elapsed = loop.time() - start
    assert elapsed >= 0.05


# --- RO e-Factura register ----------------------------------------


@respx.mock
async def test_efactura_register_found() -> None:
    respx.post(f"{BASE}/api/registruroefactura/v1/interogare").mock(
        return_value=httpx.Response(
            200,
            json={
                "found": [
                    {
                        "cui": 123,
                        "denumire": "FIRMA SRL",
                        "adresa": "BUCURESTI",
                        "registru": "RO e-Factura",
                        "categorie": "PJ",
                        "dataInscriere": "2022-01-15",
                        "dataRenuntare": "",
                        "dataRadiere": "",
                        "dataOptiuneB2G": "",
                        "stare": "1",
                    }
                ],
                "notFound": [],
            },
        )
    )
    async with _client() as client:
        result = await client.lookup_efactura_register([123])
    entry = result.found[0]
    assert entry.cui == 123
    assert entry.register_ == "RO e-Factura"
    assert entry.enrolment_date == "2022-01-15"
    assert entry.opt_out_date is None


@respx.mock
async def test_efactura_register_404_is_business_not_found() -> None:
    # Live-confirmed: 404 with a found/notFound body when no queried CUI has data.
    respx.post(f"{BASE}/api/registruroefactura/v1/interogare").mock(
        return_value=httpx.Response(404, json={"found": [], "notFound": [123, 456]})
    )
    async with _client() as client:
        result = await client.lookup_efactura_register([123, 456])
    assert result.found == []
    assert result.not_found == [123, 456]


@respx.mock
async def test_efactura_register_genuine_404_raises() -> None:
    respx.post(f"{BASE}/api/registruroefactura/v1/interogare").mock(
        return_value=httpx.Response(404, text="<html>Not Found</html>")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as excinfo:
            await client.lookup_efactura_register([123])
    assert excinfo.value.status_code == 404


@respx.mock
async def test_efactura_register_400_raises() -> None:
    respx.post(f"{BASE}/api/registruroefactura/v1/interogare").mock(
        return_value=httpx.Response(400, text="too many CUIs")
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as excinfo:
            await client.lookup_efactura_register([123])
    assert excinfo.value.status_code == 400


# --- farmers / cult registers ----------------------------------------


@respx.mock
async def test_farmers_membership_read_from_status_boolean() -> None:
    # Live note: a CUI not in the register still arrives under `found`, with empty
    # fields and statusRegAgric False — membership is the boolean.
    respx.post(f"{BASE}/RegAgric/api/v2/ws/agric").mock(
        return_value=httpx.Response(
            200,
            json={
                "cod": 200,
                "message": "SUCCESS",
                "found": [
                    {
                        "cui": 123,
                        "data": "2026-07-01",
                        "denumire": "",
                        "adresa": "",
                        "nrRegCom": "",
                        "telefon": "",
                        "fax": "",
                        "codPostal": "",
                        "act": "",
                        "stare_inregistrare": "",
                        "dataInceputRegAgric": "",
                        "dataAnulareRegAgric": "",
                        "statusRegAgric": False,
                    }
                ],
                "notFound": [],
            },
        )
    )
    async with _client() as client:
        result = await client.lookup_farmers([123])
    record = result.found[0]
    assert record.cui == 123
    assert record.registered is False
    assert record.name is None  # "" -> None


@respx.mock
async def test_cult_entities_parse_and_batch_cap() -> None:
    respx.post(f"{BASE}/RegCult/api/v2/ws/cult").mock(
        return_value=httpx.Response(
            200,
            json={
                "cod": 200,
                "message": "SUCCESS",
                "found": [
                    {
                        "cui": 456,
                        "denumire": "PAROHIA X",
                        "dataInceputRegCult": "2019-04-01",
                        "dataAnulareRegCult": "",
                        "statusRegCult": True,
                    }
                ],
                "notFound": [],
            },
        )
    )
    async with _client() as client:
        result = await client.lookup_cult_entities([456])
        assert result.found[0].registered is True
        assert result.found[0].start == "2019-04-01"

        with pytest.raises(AnafConfigError):
            await client.lookup_cult_entities(list(range(1, 502)))  # > 500


@respx.mock
async def test_farmers_error_envelope_raises() -> None:
    respx.post(f"{BASE}/RegAgric/api/v2/ws/agric").mock(
        return_value=httpx.Response(200, json={"cod": 500, "message": "EROARE INTERNA"})
    )
    async with _client() as client:
        with pytest.raises(AnafResponseError) as excinfo:
            await client.lookup_farmers([123])
    assert "EROARE INTERNA" in str(excinfo.value)


# --- financial statements ----------------------------------------


@respx.mock
async def test_financial_statement_parses_indicators() -> None:
    route = respx.get(f"{BASE}/bilant").mock(
        return_value=httpx.Response(
            200,
            json={
                "an": 2023,
                "cui": 1590082,
                "deni": "OMV PETROM S.A.",
                "caen": 610,
                "den_caen": "Extracţia petrolului brut",
                "i": [
                    {
                        "indicator": "I13",
                        "val_indicator": 38180875856,
                        "val_den_indicator": "Cifra de afaceri neta",
                    },
                    {
                        "indicator": "I20",
                        "val_indicator": 3291,
                        "val_den_indicator": "Numar mediu de salariati",
                    },
                ],
            },
        )
    )
    async with _client() as client:
        statement = await client.get_financial_statement("RO1590082", 2023)

    assert statement.year == 2023
    assert statement.cui == 1590082
    assert statement.name == "OMV PETROM S.A."
    assert statement.caen_code == "610"
    assert [i.code for i in statement.indicators] == ["I13", "I20"]
    assert statement.indicators[0].value == 38180875856
    params = dict(route.calls.last.request.url.params)
    assert params == {"an": "2023", "cui": "1590082"}


@respx.mock
async def test_financial_statement_null_indicators_tolerated() -> None:
    respx.get(f"{BASE}/bilant").mock(
        return_value=httpx.Response(
            200, json={"an": 2023, "cui": 123, "deni": None, "i": None}
        )
    )
    async with _client() as client:
        statement = await client.get_financial_statement(123, 2023)
    assert statement.indicators == []
    assert statement.name is None
