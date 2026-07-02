"""Live e-Factura **roundtrip** against the authenticated TEST endpoint (opt-in).

Like ``test_etransport_roundtrip_live.py``, this file **files a real document** — the
two roundtrip files are the deliberate exceptions to the "live tests never upload"
rule, and both target the **TEST** environment only (never prod). Its job is to keep
the upload → ``stareMesaj`` → ``descarcare`` wire shapes honest end to end (they are
otherwise only respx-mocked).

Needs real credentials + a token store from ``anafpy auth login`` (a repo-root ``.env``
is loaded by conftest); run explicitly:

    ANAFPY_LIVE=1 uv run pytest -q -m live tests/test_efactura_roundtrip_live.py

Each run files a fresh test invoice into the TEST SPV; that is expected and harmless.
The minimal invoice below was accepted by ANAF TEST with ``stare=ok`` on 2026-07-02 —
ANAF's own upload-time validation is the arbiter of its CIUS-RO validity.

This file also holds the ``validare``/``transformare`` shape checks. Those endpoints
are **public, no-auth, and prod-only** (the ``test`` paths 404, live-confirmed
2026-07-02), so the client routes them to ``webservicesp.anaf.ro/prod`` regardless of
its ``environment`` — the checks are read-only and file nothing anywhere.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

import pytest
from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlSerializer

from anafpy._transport.base import Environment
from anafpy.auth import FileTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient, Invoice
from anafpy.efactura.models import MessageState
from anafpy.efactura.ubl.common.ubl_common_aggregate_components_2_1 import (
    AccountingCustomerParty,
    AccountingSupplierParty,
    ClassifiedTaxCategory,
    Country,
    InvoiceLine,
    Item,
    LegalMonetaryTotal,
    Party,
    PartyLegalEntity,
    PartyTaxScheme,
    PostalAddress,
    Price,
    TaxCategory,
    TaxScheme,
    TaxSubtotal,
    TaxTotal,
)
from anafpy.efactura.ubl.common.ubl_common_basic_components_2_1 import (
    CityName,
    CompanyId,
    CountrySubentity,
    CustomizationId,
    DocumentCurrencyCode,
    DueDate,
    Id,
    IdentificationCode,
    InvoicedQuantity,
    InvoiceTypeCode,
    IssueDate,
    LineExtensionAmount,
    Name,
    PayableAmount,
    Percent,
    PriceAmount,
    RegistrationName,
    StreetName,
    TaxableAmount,
    TaxAmount,
    TaxExclusiveAmount,
    TaxInclusiveAmount,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]

CIUS_RO = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"


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


def _address() -> PostalAddress:
    return PostalAddress(
        street_name=StreetName(value="Str. Exemplu 1"),
        city_name=CityName(value="Cluj-Napoca"),
        country_subentity=CountrySubentity(value="RO-CJ"),
        country=Country(identification_code=IdentificationCode(value="RO")),
    )


def _party(cif: str, name: str) -> Party:
    return Party(
        postal_address=_address(),
        party_tax_scheme=[
            PartyTaxScheme(
                company_id=CompanyId(value=f"RO{cif}"),
                tax_scheme=TaxScheme(id=Id(value="VAT")),
            )
        ],
        party_legal_entity=[
            PartyLegalEntity(
                registration_name=RegistrationName(value=name),
                company_id=CompanyId(value=f"RO{cif}"),
            )
        ],
    )


def _minimal_invoice(cif: str, number: str, issue: dt.date) -> Invoice:
    """A minimal CIUS-RO-valid invoice: one 19%-VAT line, RON, seller == buyer."""
    day = XmlDate(issue.year, issue.month, issue.day)
    due = issue + dt.timedelta(days=30)
    return Invoice(
        customization_id=CustomizationId(value=CIUS_RO),
        id=Id(value=number),
        issue_date=IssueDate(value=day),
        due_date=DueDate(value=XmlDate(due.year, due.month, due.day)),
        invoice_type_code=InvoiceTypeCode(value="380"),
        document_currency_code=DocumentCurrencyCode(value="RON"),
        accounting_supplier_party=AccountingSupplierParty(
            party=_party(cif, "Furnizor Test SRL")
        ),
        accounting_customer_party=AccountingCustomerParty(
            party=_party(cif, "Client Test SRL")
        ),
        tax_total=[
            TaxTotal(
                tax_amount=TaxAmount(value=Decimal("19.00"), currency_id="RON"),
                tax_subtotal=[
                    TaxSubtotal(
                        taxable_amount=TaxableAmount(
                            value=Decimal("100.00"), currency_id="RON"
                        ),
                        tax_amount=TaxAmount(value=Decimal("19.00"), currency_id="RON"),
                        tax_category=TaxCategory(
                            id=Id(value="S"),
                            percent=Percent(value=Decimal("19")),
                            tax_scheme=TaxScheme(id=Id(value="VAT")),
                        ),
                    )
                ],
            )
        ],
        legal_monetary_total=LegalMonetaryTotal(
            line_extension_amount=LineExtensionAmount(
                value=Decimal("100.00"), currency_id="RON"
            ),
            tax_exclusive_amount=TaxExclusiveAmount(
                value=Decimal("100.00"), currency_id="RON"
            ),
            tax_inclusive_amount=TaxInclusiveAmount(
                value=Decimal("119.00"), currency_id="RON"
            ),
            payable_amount=PayableAmount(value=Decimal("119.00"), currency_id="RON"),
        ),
        invoice_line=[
            InvoiceLine(
                id=Id(value="1"),
                invoiced_quantity=InvoicedQuantity(
                    value=Decimal("10"), unit_code="H87"
                ),
                line_extension_amount=LineExtensionAmount(
                    value=Decimal("100.00"), currency_id="RON"
                ),
                item=Item(
                    name=Name(value="Servicii de consultanta"),
                    classified_tax_category=[
                        ClassifiedTaxCategory(
                            id=Id(value="S"),
                            percent=Percent(value=Decimal("19")),
                            tax_scheme=TaxScheme(id=Id(value="VAT")),
                        )
                    ],
                ),
                price=Price(
                    price_amount=PriceAmount(value=Decimal("10.00"), currency_id="RON")
                ),
            )
        ],
    )


async def test_efactura_test_roundtrip(provider: TokenProvider, cif: str) -> None:
    """File an invoice to TEST and drive it to ``ok`` + a downloadable ZIP.

    Confirms the upload (``index_incarcare``), ``stareMesaj`` (``in prelucrare`` →
    ``ok`` + ``id_descarcare``), ``descarcare`` (ZIP with signed invoice + MF
    signature), and lista-with-results shapes end to end — the ones the respx suite
    can only assert against fixtures. (List membership of the *fresh* upload is not
    asserted: lista indexing lags filing by up to ~15 minutes.)
    """
    now = dt.datetime.now(dt.UTC)
    number = f"ANAFPY-LIVE-{now:%Y%m%d%H%M%S}"  # fresh id per run
    xml = XmlSerializer().render(_minimal_invoice(cif, number, now.date()))

    async with EFacturaClient(provider, environment=Environment.TEST) as client:
        upload = await client.upload(xml, cif=cif)
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
        # read tiers (raw bytes -> UBL model -> flat view) must parse.
        message = await client.download(status.download_id)
        assert message.content_xml is not None
        assert message.signature_xml is not None
        document = message.document
        assert isinstance(document, Invoice)
        assert document.id is not None and document.id.value == number
        view = message.view
        assert view is not None
        assert view.number == number

        # Message-list indexing runs asynchronously and lags filing by anywhere
        # from seconds to ~15 minutes (observed on TEST 2026-07-02), so *this*
        # upload's presence cannot be asserted reliably; earlier roundtrip runs'
        # messages exercise the lista-with-results shape instead. Filing with
        # seller == buyer creates both a FACTURA TRIMISA and a FACTURA PRIMITA
        # entry once indexed.
        async for item in client.list_messages(cif=cif, days=1):
            assert item.id
            assert item.id_solicitare
            assert item.tip


async def test_efactura_validare_public_prod_shapes(
    provider: TokenProvider, cif: str
) -> None:
    """ANAF's public validator: ``ok`` for the minimal invoice, ``nok`` + findings
    for an incomplete one.

    Read-only — ``validare`` validates without filing, and the client calls the
    public no-auth prod variant whatever its ``environment`` (here TEST). Confirms
    the ``{stare, Messages[], trace_id}`` shape both ways.
    """
    now = dt.datetime.now(dt.UTC)
    serializer = XmlSerializer()
    valid_xml = serializer.render(
        _minimal_invoice(cif, f"ANAFPY-VLD-{now:%Y%m%d%H%M%S}", now.date())
    )
    # Schema-parseable but nowhere near CIUS-RO-complete: empty parties, no lines.
    invalid_xml = serializer.render(
        Invoice(
            customization_id=CustomizationId(value=CIUS_RO),
            id=Id(value="ANAFPY-VLD-INVALID"),
            issue_date=IssueDate(value=XmlDate(now.year, now.month, now.day)),
            document_currency_code=DocumentCurrencyCode(value="RON"),
            accounting_supplier_party=AccountingSupplierParty(),
            accounting_customer_party=AccountingCustomerParty(),
            legal_monetary_total=LegalMonetaryTotal(
                payable_amount=PayableAmount(value=Decimal("1.00"), currency_id="RON")
            ),
        )
    )

    async with EFacturaClient(provider, environment=Environment.TEST) as client:
        good = await client.validate_remote(valid_xml)
        assert good.valid, good.messages
        assert good.messages == []

        bad = await client.validate_remote(invalid_xml)
        assert not bad.valid
        assert bad.messages  # rule findings, e.g. BR-* / BR-RO-*
        assert bad.trace_id


async def test_efactura_transformare_public_prod_renders_pdf(
    provider: TokenProvider, cif: str
) -> None:
    """``transformare`` renders the minimal invoice to PDF bytes (public prod,
    read-only)."""
    now = dt.datetime.now(dt.UTC)
    xml = XmlSerializer().render(
        _minimal_invoice(cif, f"ANAFPY-PDF-{now:%Y%m%d%H%M%S}", now.date())
    )
    async with EFacturaClient(provider, environment=Environment.TEST) as client:
        pdf = await client.to_pdf(xml)
    assert pdf.startswith(b"%PDF"), pdf[:200]
