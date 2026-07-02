"""e-Transport flat models: create <-> view round-trips over the XSD wire shape.

Unlike e-Factura's read-only flat view, the e-Transport flat models are
bidirectional: the same model authors a document (``render_etransport``) and views
a parsed one (``read_flat_transport``). The round-trips here pin that symmetry for
all four operations.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from _wire import build_flat_transport, build_transport, transport_xml
from anafpy.etransport import (
    ETransport,
    FlatConfirmation,
    FlatDeletion,
    FlatSubmission,
    FlatTransport,
    FlatTransportLocation,
    FlatVehicleChange,
    build_etransport,
    parse_etransport_document,
    read_flat_transport,
    render_etransport,
)
from anafpy.etransport.schema.schema_etr_v2_20230126 import (
    CodBirouVamalType,
    CodJudetType,
    CodPtfType,
    CodTipOperatiuneType,
    TipConfirmareType,
)
from anafpy.exceptions import AnafConfigError

UIT = "0123456789ACDE42"


def _round_trip(document: FlatSubmission) -> FlatSubmission:
    xml = render_etransport(document, declarant_code="123")
    parsed = parse_etransport_document(xml)
    assert parsed is not None
    return read_flat_transport(parsed)


# --- declaration ----------------------------------------------------------------------


def test_declaration_round_trips() -> None:
    flat = build_flat_transport()
    back = _round_trip(flat)
    # The only difference is the declarant code filled in from the upload CIF.
    assert back == flat.model_copy(update={"declarant_code": "123"})


def test_declaration_reads_header_route_and_goods() -> None:
    back = _round_trip(build_flat_transport())
    assert isinstance(back, FlatTransport)
    assert back.operation_type is CodTipOperatiuneType.TTN
    assert back.partner.name == "Foreign GmbH"
    assert back.partner.country.value == "DE"
    assert back.vehicle.plate == "B100XYZ"
    assert back.vehicle.transport_date == dt.date(2026, 6, 28)
    address = back.start_location.address
    assert address is not None
    assert address.county is CodJudetType.MUNICIPIUL_BUCURESTI
    assert back.goods_count == 1
    assert back.total_gross_weight == Decimal("120")
    assert back.documents[0].date == dt.date(2026, 6, 27)


def test_flat_models_dump_enum_names_for_readability() -> None:
    dump = build_flat_transport().model_dump(mode="json")
    assert dump["operation_type"] == "TTN"
    assert dump["partner"]["country"] == "GERMANIA"
    assert dump["end_location"]["address"]["county"] == "CLUJ"
    assert dump["goods"][0]["operation_scope"] == "GRATUITATI"
    assert dump["documents"][0]["doc_type"] == "FACTURA"


def test_enum_fields_accept_names_codes_and_numeric_strings() -> None:
    base = build_flat_transport().model_dump()
    for value in (30, "30", "TTN", "ttn"):
        base["operation_type"] = value
        validated = FlatTransport.model_validate(base)
        assert validated.operation_type is CodTipOperatiuneType.TTN


def test_correction_and_post_incident_round_trip() -> None:
    flat = build_flat_transport().model_copy(
        update={"correction_of_uit": UIT, "post_incident": True}
    )
    xml = render_etransport(flat, declarant_code="123")
    assert b'declPostAvarie="D"' in xml
    assert f'corectie uit="{UIT}"'.encode() in xml
    back = _round_trip(flat)
    assert isinstance(back, FlatTransport)
    assert back.correction_of_uit == UIT
    assert back.post_incident is True


def test_route_point_requires_exactly_one_kind() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        FlatTransportLocation()
    with pytest.raises(ValidationError, match="exactly one"):
        FlatTransportLocation(
            border_point=CodPtfType.NADLAC,
            customs_office=CodBirouVamalType.BVI_ARAD,
        )
    # Names are accepted anywhere a JSON/dict input arrives (the MCP path).
    point = FlatTransportLocation.model_validate({"border_point": "NADLAC"})
    assert point.border_point is CodPtfType.NADLAC


def test_plate_and_uit_are_normalized() -> None:
    deletion = FlatDeletion(uit=f" {UIT.lower()} ")
    assert deletion.uit == UIT
    change = FlatVehicleChange(uit=UIT, plate="b-100 xyz")
    assert change.plate == "B100XYZ"


# --- deletion / confirmation / vehicle change -----------------------------------------


def test_deletion_round_trips() -> None:
    back = _round_trip(FlatDeletion(uit=UIT, declarant_ref="R1"))
    assert isinstance(back, FlatDeletion)
    assert back.uit == UIT
    assert back.declarant_ref == "R1"
    assert back.declarant_code == "123"


def test_confirmation_round_trips() -> None:
    flat = FlatConfirmation(
        uit=UIT,
        confirmation_type=TipConfirmareType.CONFIRMAT_PARTIAL,
        note="partial",
    )
    xml = render_etransport(flat, declarant_code="123")
    assert b'tipConfirmare="20"' in xml
    back = _round_trip(flat)
    assert back == flat.model_copy(update={"declarant_code": "123"})


def test_vehicle_change_round_trips() -> None:
    flat = FlatVehicleChange(
        uit=UIT,
        plate="CJ99AAA",
        trailer1="CJ98BBB",
        changed_at=dt.datetime(2026, 7, 2, 12, 30),
        note="tractor swap",
    )
    back = _round_trip(flat)
    assert back == flat.model_copy(update={"declarant_code": "123"})


def test_vehicle_change_defaults_changed_at_to_now() -> None:
    change = FlatVehicleChange(uit=UIT, plate="B1AAA")
    doc = build_etransport(change, declarant_code="1")
    assert doc.modif_vehicul is not None
    assert doc.modif_vehicul.data_modificare.year == dt.date.today().year


# --- declarant code -------------------------------------------------------------------


def test_build_requires_a_declarant_code() -> None:
    with pytest.raises(AnafConfigError, match="declarant_code is required"):
        build_etransport(FlatDeletion(uit=UIT))


def test_build_rejects_conflicting_declarant_codes() -> None:
    flat = FlatDeletion(uit=UIT, declarant_code="999")
    with pytest.raises(AnafConfigError, match="mismatch"):
        build_etransport(flat, declarant_code="123")
    # Matching values are fine.
    assert build_etransport(flat, declarant_code="999").cod_declarant == "999"


# --- reading external wire XML --------------------------------------------------------


def test_reads_externally_produced_declaration() -> None:
    view = read_flat_transport(build_transport())
    assert isinstance(view, FlatTransport)
    assert view.operation_type is CodTipOperatiuneType.TTN
    assert view.declarant_code == "123"
    assert view.partner.name == "Foreign GmbH"
    assert view.total_gross_weight == Decimal("120")


def test_read_rejects_document_without_an_operation() -> None:
    with pytest.raises(ValueError, match="none of"):
        read_flat_transport(ETransport(cod_declarant="123"))


def test_parse_etransport_document_handles_good_and_bad_input() -> None:
    parsed = parse_etransport_document(transport_xml().encode("utf-8"))
    assert parsed is not None
    assert isinstance(read_flat_transport(parsed), FlatTransport)
    assert parse_etransport_document(b"<nope/>") is None
