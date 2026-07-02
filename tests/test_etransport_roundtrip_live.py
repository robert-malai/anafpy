"""Live e-Transport **roundtrip** against the authenticated TEST endpoint (opt-in).

Unlike the read-only shape checks in ``test_oauth_live.py``, this file **files a real
declaration** — it is the one deliberate exception to the "live tests never upload"
rule, and it targets the **TEST** environment only (never prod). Its job is to keep the
upload → ``stareMesaj`` → ``lista`` → ``info`` wire shapes honest end to end (they are
otherwise only respx-mocked).

Needs real credentials + a token store from ``anafpy auth login`` (a repo-root ``.env``
is loaded by conftest); run explicitly:

    ANAFPY_LIVE=1 uv run pytest -q -m live tests/test_etransport_roundtrip_live.py

Each run creates a fresh test UIT in the TEST SPV; that is expected and harmless.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlSerializer

from anafpy._transport.base import Environment
from anafpy.auth import FileTokenStore, TokenProvider
from anafpy.etransport import ETransport, ETransportClient
from anafpy.etransport.models import MessageState
from anafpy.etransport.schema.schema_etr_v2_20230126 import (
    BunuriTransportateType,
    CodJudetType,
    CodScopOperatiuneType,
    CodTaraType,
    CodTipOperatiuneType,
    DateTransportType,
    DocumenteTransportType,
    LocatieType,
    LocTraseuRutierType,
    NotificareType,
    PartenerComercialType,
    TipDocumentType,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]


def _store_path() -> Path:
    return Path(
        os.environ.get("ANAFPY_TOKEN_STORE", "~/.anafpy/tokens.json")
    ).expanduser()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set (see .env)")
    return value


@pytest.fixture
async def provider() -> AsyncIterator[TokenProvider]:
    client_id = _require("ANAFPY_CLIENT_ID")
    client_secret = _require("ANAFPY_CLIENT_SECRET")
    store = FileTokenStore(_store_path())
    if store.load() is None:
        pytest.skip("no token store — run `anafpy auth login` first")
    prov = TokenProvider(client_id=client_id, client_secret=client_secret, store=store)
    yield prov
    await prov.aclose()


@pytest.fixture
def cif() -> str:
    return _require("ANAFPY_CIF")


def _domestic_declaration(cif: str, transport_date: dt.date) -> ETransport:
    """A minimal, ANAF-valid domestic (``tip_op`` 30 = TTN) transport declaration."""
    day = XmlDate(transport_date.year, transport_date.month, transport_date.day)
    return ETransport(
        cod_declarant=cif,
        ref_declarant="anafpy-live-roundtrip",
        notificare=NotificareType(
            cod_tip_operatiune=CodTipOperatiuneType.VALUE_30,
            bunuri_transportate=[
                BunuriTransportateType(
                    cod_scop_operatiune=CodScopOperatiuneType.VALUE_101,
                    denumire_marfa="Materiale constructii",
                    cantitate="100.00",
                    cod_unitate_masura="KGM",
                    greutate_neta="100.00",
                    greutate_bruta="110.00",
                    valoare_lei_fara_tva="500.00",
                    cod_tarifar="6810",
                )
            ],
            partener_comercial=PartenerComercialType(
                cod_tara=CodTaraType.RO, cod=cif, denumire="Partener SRL"
            ),
            date_transport=DateTransportType(
                nr_vehicul="CJ01ABC",
                cod_tara_org_transport=CodTaraType.RO,
                cod_org_transport=cif,
                denumire_org_transport="Transport SRL",
                data_transport=day,
            ),
            loc_start_traseu_rutier=LocTraseuRutierType(
                locatie=LocatieType(
                    cod_judet=CodJudetType.VALUE_12,  # Cluj
                    denumire_localitate="Cluj-Napoca",
                    denumire_strada="Str. Memorandumului",
                    numar="28",
                )
            ),
            loc_final_traseu_rutier=LocTraseuRutierType(
                locatie=LocatieType(
                    cod_judet=CodJudetType.VALUE_40,  # Bucuresti
                    denumire_localitate="Bucuresti",
                    denumire_strada="Calea Victoriei",
                    numar="1",
                )
            ),
            documente_transport=[
                DocumenteTransportType(
                    tip_document=TipDocumentType.VALUE_10,
                    numar_document="FAC-001",
                    data_document=day,
                )
            ],
        ),
    )


async def test_etransport_test_roundtrip(provider: TokenProvider, cif: str) -> None:
    """File a domestic declaration to TEST and drive it to a terminal ``ok``.

    Confirms the upload (``index_incarcare`` + ``UIT`` + ``atentie``), ``stareMesaj``
    (``in prelucrare`` → ``ok``), ``lista``-with-results, and ``info`` no-results
    envelope shapes end to end — the ones the respx suite can only assert against
    fixtures.
    """
    transport_date = dt.date.today() + dt.timedelta(days=1)
    xml = XmlSerializer().render(_domestic_declaration(cif, transport_date))

    async with ETransportClient(provider, environment=Environment.TEST) as client:
        upload = await client.upload(xml, cif=cif, version=2)
        assert upload.accepted, upload.errors
        assert upload.upload_id
        assert upload.uit  # UIT issued immediately at upload time

        # Poll stareMesaj to a terminal state (in prelucrare -> ok).
        deadline = asyncio.get_event_loop().time() + 120.0
        status = await client.get_status(upload.upload_id)
        while status.is_processing and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(3.0)
            status = await client.get_status(upload.upload_id)
        assert status.is_terminal, "still processing after 120s"
        assert status.state is MessageState.OK, status.errors

        # The accepted UIT must now surface in the notification list.
        uits = {n.uit async for n in client.list_notifications(days=1, cif=cif)}
        assert upload.uit in uits

        # `info` is scoped to a transport organizer looking up *others'* UITs, so a
        # self-declared notification yields its no-results envelope — the top-level
        # singular `error` string that diverges from every other endpoint's `Errors[]`
        # (the one doc gap the 2026-07-02 roundtrip surfaced; api.md §4). Pin it.
        info = await client.info(cui_op=cif, uit=upload.uit)
        assert not info.items
        assert info.error is not None
        assert "nu exista informatii" in info.error.lower()
