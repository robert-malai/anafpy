"""Live e-Factura **roundtrip** against the authenticated TEST endpoint (opt-in).

Like ``test_etransport_roundtrip_live.py``, this file **files a real document** — the
two roundtrip files are the deliberate exceptions to the "live tests never upload"
rule, and both target the **TEST** environment only (never prod). Its job is to keep
the upload → ``stareMesaj`` → ``descarcare`` wire shapes honest end to end — and,
since the invoice is **composed via the authoring models and filed with
``upload_invoice``**, to keep anafpy's own rendered XML honest against ANAF's
upload-time validation, and the strict ``DownloadedMessage.view`` reader honest
against what ANAF hands back.

Needs real credentials + a token store from ``anafpy auth login`` (a repo-root ``.env``
is loaded by conftest); run explicitly:

    ANAFPY_LIVE=1 uv run pytest -q -m live tests/test_efactura_roundtrip_live.py

Each run files a fresh test invoice into the TEST SPV; that is expected and harmless.

This file also holds the ``validare``/``transformare`` checks. Those endpoints are
**public, no-auth, and prod-only** (the ``test`` paths 404, live-confirmed
2026-07-02) and live on :class:`PublicClient` — the checks are read-only, need no
credentials, and file nothing anywhere. ``test_validare_agrees_with_local_rules``
doubles as the **drift tripwire**: when ANAF revises the CIUS-RO rule set, the
local ``authoring.validate()`` verdict and ANAF's stop agreeing and this test
announces it.
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
from anafpy.efactura import EFacturaClient, Invoice
from anafpy.efactura.authoring import (
    InvoiceDocument,
    InvoiceLine,
    Party,
    PostalAddress,
    Seller,
    Totals,
    VatCategory,
    render_invoice,
    validate,
)
from anafpy.efactura.models import MessageState
from anafpy.public import PublicClient

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


def _minimal_invoice(cif: str, number: str, issue: dt.date) -> InvoiceDocument:
    """A minimal authored invoice: one 19%-VAT line, RON, seller == buyer.

    Composed via the authoring models — totals and the VAT breakdown are
    computed, exactly as a library/MCP caller with no invoicing software would
    file. Accepted by ANAF TEST with ``stare=ok`` (first authored filing
    2026-07-08; the generated-model predecessor passed 2026-07-02).
    """
    address = PostalAddress(
        street="Str. Exemplu 1", city="Cluj-Napoca", county="RO-CJ", country="RO"
    )
    return InvoiceDocument(
        number=number,
        issue_date=issue,
        due_date=issue + dt.timedelta(days=30),
        currency="RON",
        seller=Seller(name="Furnizor Test SRL", vat_id=f"RO{cif}", address=address),
        buyer=Party(name="Client Test SRL", vat_id=f"RO{cif}", address=address),
        lines=[
            InvoiceLine(
                name="Servicii de consultanta",
                quantity=Decimal("10"),
                unit="H87",
                unit_price=Decimal("10.00"),
                vat_category=VatCategory.STANDARD,
                vat_rate=Decimal("19"),
            )
        ],
    )


async def test_efactura_test_roundtrip(provider: TokenProvider, cif: str) -> None:
    """File an authored invoice to TEST and drive it to ``ok`` + a downloadable ZIP.

    Proves the flagship authoring path end to end: compose → ``upload_invoice``
    (render + standard selection inside) → ``stareMesaj`` (``in prelucrare`` →
    ``ok`` + ``id_descarcare``) → ``descarcare`` — where all three read tiers
    must parse, including the strict ``view`` reading ANAF's returned XML back
    into the very model that authored it. (List membership of the *fresh*
    upload is not asserted: lista indexing lags filing by up to ~15 minutes.)
    """
    now = dt.datetime.now(dt.UTC)
    number = f"ANAFPY-LIVE-{now:%Y%m%d%H%M%S}"  # fresh id per run
    invoice = _minimal_invoice(cif, number, now.date())
    report = validate(invoice)
    assert report.ok, [f.model_dump() for f in report.findings]

    async with EFacturaClient(provider, environment=Environment.TEST) as client:
        upload = await client.upload_invoice(invoice, cif=cif)
        assert upload.accepted, upload.errors
        assert upload.upload_id

        # Poll stareMesaj to a terminal state (in prelucrare -> ok).
        deadline = asyncio.get_event_loop().time() + 120.0
        status = await client.get_status(upload.upload_id)
        while status.is_processing and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(3.0)
            status = await client.get_status(upload.upload_id)
        assert status.is_terminal, "still processing after 120s"
        assert status.state is MessageState.OK, status.errors
        assert status.download_id

        # The ZIP carries the signed invoice + detached MF signature; all three
        # read tiers (raw bytes -> UBL model -> authoring view) must parse.
        message = await client.download(status.download_id)
        assert message.content_xml is not None
        assert message.signature_xml is not None
        document = message.document
        assert isinstance(document, Invoice)
        assert document.id is not None and document.id.value == number
        view = message.view
        assert view is not None, "strict reader balked at ANAF's returned XML"
        assert view.number == number
        assert view.totals is not None
        assert view.totals.payable == Decimal("119.00")
        assert validate(view).ok  # the read-back document passes the rule set too

        # Message-list indexing runs asynchronously and lags filing by anywhere
        # from seconds to ~15 minutes (observed on TEST 2026-07-02), so *this*
        # upload's presence cannot be asserted reliably; earlier roundtrip runs'
        # messages exercise the lista-with-results shape instead. Filing with
        # seller == buyer creates both a FACTURA TRIMISA and a FACTURA PRIMITA
        # entry once indexed.
        async for item in client.list_messages(cif=cif, days=1):
            assert item.id
            assert item.request_id
            assert item.message_type


async def test_validare_agrees_with_local_rules(cif: str) -> None:
    """The drift tripwire: local ``validate()`` verdicts track ANAF's ``validare``.

    Read-only (public, no-auth prod endpoint; nothing is filed). Two probes:

    - a locally-clean authored invoice must pass ANAF's validator with no
      messages;
    - an invoice whose explicit payable breaks BR-CO-16 must be flagged
      **by both sides with the same rule id**.

    When ANAF revises the CIUS-RO rule set, one of these stops holding — that
    is the signal to re-vendor the Schematron sources and re-align the
    translated rules (see CLAUDE.md "Generated code").
    """
    now = dt.datetime.now(dt.UTC)
    good = _minimal_invoice(cif, f"ANAFPY-VLD-{now:%Y%m%d%H%M%S}", now.date())
    assert validate(good).ok

    # BR-CO-16: payable must equal tax inclusive - prepaid + rounding.
    bad = good.model_copy(update={"totals": Totals(payable=Decimal("1.00"))})
    bad_report = validate(bad)
    assert not bad_report.ok
    assert "BR-CO-16" in {finding.rule for finding in bad_report.fatal}

    async with PublicClient() as client:
        good_remote = await client.validate_invoice(render_invoice(good))
        assert good_remote.valid, good_remote.messages
        assert good_remote.messages == []

        bad_remote = await client.validate_invoice(
            render_invoice(bad, skip_validation=True)
        )
        assert not bad_remote.valid
        assert any("BR-CO-16" in message for message in bad_remote.messages), (
            bad_remote.messages
        )
        assert bad_remote.trace_id


async def test_transformare_renders_authored_invoice_to_pdf(cif: str) -> None:
    """``transformare`` renders an authored invoice to PDF bytes (public prod,
    read-only)."""
    now = dt.datetime.now(dt.UTC)
    xml = render_invoice(
        _minimal_invoice(cif, f"ANAFPY-PDF-{now:%Y%m%d%H%M%S}", now.date())
    )
    async with PublicClient() as client:
        pdf = await client.render_invoice_pdf(xml)
    assert pdf.startswith(b"%PDF"), pdf[:200]
