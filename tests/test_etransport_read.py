"""e-Transport XSD → FlatTransport read view (the MCP prepare-preview projection)."""

from __future__ import annotations

from decimal import Decimal

from _wire import build_transport, transport_xml
from anafpy.etransport import parse_etransport_document, read_flat_transport


def test_reads_declaration_header_and_route() -> None:
    view = read_flat_transport(build_transport())
    assert view.operation_type == "30"
    assert view.declarant_code == "123"
    assert view.partner.name == "Foreign GmbH"
    assert view.partner.country == "DE"
    assert view.vehicle.plate == "B100XYZ"
    assert view.vehicle.carrier_name == "Carrier SRL"
    assert view.vehicle.transport_date == "2026-06-28"
    assert view.start_location.county_code == "40"
    assert view.start_location.locality == "Bucuresti"
    assert view.end_location.county_code == "12"
    assert view.complete is True


def test_reads_goods_and_totals() -> None:
    view = read_flat_transport(build_transport())
    assert view.goods_count == 1
    assert view.total_gross_weight == Decimal("120")
    good = view.goods[0]
    assert good.operation_scope == "301"
    assert good.name == "Marfa"
    assert good.gross_weight == Decimal("120")
    assert good.net_weight == Decimal("100")
    assert len(view.documents) == 1
    assert view.documents[0].doc_type == "20"


def test_parse_etransport_document_handles_good_and_bad_input() -> None:
    parsed = parse_etransport_document(transport_xml().encode("utf-8"))
    assert parsed is not None
    assert read_flat_transport(parsed).operation_type == "30"
    assert parse_etransport_document(b"<nope/>") is None
