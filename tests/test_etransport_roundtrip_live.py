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
from decimal import Decimal

import pytest

from anafpy._transport.base import Environment
from anafpy.auth import TokenProvider, TokenStore
from anafpy.etransport import (
    ETransportClient,
    FlatTransport,
    FlatTransportAddress,
    FlatTransportDocument,
    FlatTransportGood,
    FlatTransportLocation,
    FlatTransportPartner,
    FlatTransportVehicle,
)
from anafpy.etransport.models import MessageState
from anafpy.etransport.schema.schema_etr_v2_20230126 import (
    CodJudetType,
    CodScopOperatiuneType,
    CodTaraType,
    CodTipOperatiuneType,
    TipDocumentType,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set (see .env)")
    return value


@pytest.fixture
async def provider(live_token_store: TokenStore) -> AsyncIterator[TokenProvider]:
    client_id = _require("ANAFPY_CLIENT_ID")
    client_secret = _require("ANAFPY_CLIENT_SECRET")
    prov = TokenProvider(
        client_id=client_id, client_secret=client_secret, store=live_token_store
    )
    yield prov
    await prov.aclose()


@pytest.fixture
def cif() -> str:
    return _require("ANAFPY_CIF")


def _domestic_declaration(cif: str, transport_date: dt.date) -> FlatTransport:
    """A minimal, ANAF-valid domestic (TTN) declaration — via the flat authoring
    models, so the roundtrip also keeps anafpy's *composed* XML honest."""
    return FlatTransport(
        operation_type=CodTipOperatiuneType.TTN,
        declarant_ref="anafpy-live-roundtrip",
        partner=FlatTransportPartner(
            name="Partener SRL", country=CodTaraType.ROMANIA, code=cif
        ),
        vehicle=FlatTransportVehicle(
            plate="CJ01ABC",
            carrier_name="Transport SRL",
            carrier_country=CodTaraType.ROMANIA,
            carrier_code=cif,
            transport_date=transport_date,
        ),
        start_location=FlatTransportLocation(
            address=FlatTransportAddress(
                county=CodJudetType.CLUJ,
                locality="Cluj-Napoca",
                street="Str. Memorandumului",
                number="28",
            )
        ),
        end_location=FlatTransportLocation(
            address=FlatTransportAddress(
                county=CodJudetType.MUNICIPIUL_BUCURESTI,
                locality="Bucuresti",
                street="Calea Victoriei",
                number="1",
            )
        ),
        goods=[
            FlatTransportGood(
                operation_scope=CodScopOperatiuneType.COMERCIALIZARE,
                name="Materiale constructii",
                quantity=Decimal("100.00"),
                unit_code="KGM",
                gross_weight=Decimal("110.00"),
                net_weight=Decimal("100.00"),
                value_ron=Decimal("500.00"),
                tariff_code="6810",
            )
        ],
        documents=[
            FlatTransportDocument(
                doc_type=TipDocumentType.CMR, date=transport_date, number="FAC-001"
            )
        ],
    )


async def test_etransport_test_roundtrip(provider: TokenProvider, cif: str) -> None:
    """File a composed domestic declaration to TEST and drive it to a terminal ``ok``.

    Confirms the upload (``index_incarcare`` + ``UIT`` + ``atentie``), ``stareMesaj``
    (``in prelucrare`` → ``ok``), ``lista``-with-results, and ``info`` no-results
    envelope shapes end to end — the ones the respx suite can only assert against
    fixtures — and, since the declaration is composed by ``upload_document`` from the
    flat models, that ANAF accepts anafpy's own rendered XML.
    """
    transport_date = dt.date.today() + dt.timedelta(days=1)
    declaration = _domestic_declaration(cif, transport_date)

    async with ETransportClient(provider, environment=Environment.TEST) as client:
        upload = await client.upload_document(declaration, cif=cif)
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
        info = await client.info(organizer_cui=cif, uit=upload.uit)
        assert not info.items
        assert info.error is not None
        assert "nu exista informatii" in info.error.lower()
