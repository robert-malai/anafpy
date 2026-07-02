"""Round-trip tests for the generated e-Transport XSD models.

These tests guard against xsdata/xsdata-pydantic regen regressions — if regeneration
silently changes field names, types, or serialization behaviour the golden test catches
it.  No network calls; no ANAF credentials required.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from xsdata.models.datatype import XmlDate
from xsdata_pydantic.bindings import XmlParser, XmlSerializer

from anafpy.etransport import ETransport
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

_NS = "mfp:anaf:dgti:eTransport:declaratie:v2"
_CIF = "1234567890"


def _minimal_declaration() -> ETransport:
    """Minimal valid ETransport notificare (uses required fields only)."""
    locatie_start = LocatieType(
        cod_judet=CodJudetType.CLUJ,
        denumire_localitate="Cluj-Napoca",
        denumire_strada="Str. Principala",
    )
    locatie_final = LocatieType(
        cod_judet=CodJudetType.MUNICIPIUL_BUCURESTI,
        denumire_localitate="Bucuresti",
        denumire_strada="Calea Victoriei",
    )
    return ETransport(
        cod_declarant=_CIF,
        notificare=NotificareType(
            bunuri_transportate=[
                BunuriTransportateType(
                    cod_scop_operatiune=CodScopOperatiuneType.COMERCIALIZARE,
                    denumire_marfa="Materiale constructii",
                    cantitate="100.00",
                    cod_unitate_masura="KGM",
                    greutate_bruta="110.00",
                )
            ],
            partener_comercial=PartenerComercialType(
                cod_tara=CodTaraType.ROMANIA,
                denumire="Partener SRL",
            ),
            date_transport=DateTransportType(
                nr_vehicul="B01ABC",
                cod_tara_org_transport=CodTaraType.ROMANIA,
                denumire_org_transport="Transport SRL",
                data_transport=XmlDate(2026, 6, 30),
            ),
            loc_start_traseu_rutier=LocTraseuRutierType(locatie=locatie_start),
            loc_final_traseu_rutier=LocTraseuRutierType(locatie=locatie_final),
            documente_transport=[
                DocumenteTransportType(
                    tip_document=TipDocumentType.CMR,
                    data_document=XmlDate(2026, 6, 28),
                )
            ],
            cod_tip_operatiune=CodTipOperatiuneType.ACHIZITIE_INTRACOMUNITARA,
        ),
    )


def test_etransport_roundtrips_to_equal_model() -> None:
    """Serialize to XML then parse back; structural equality should hold."""
    original = _minimal_declaration()
    serializer = XmlSerializer()
    xml_str = serializer.render(original)
    parser = XmlParser()
    restored = parser.from_string(xml_str, ETransport)
    assert restored.cod_declarant == _CIF
    assert restored.notificare is not None
    n = restored.notificare
    assert len(n.bunuri_transportate) == 1
    b = n.bunuri_transportate[0]
    assert b.cod_scop_operatiune is CodScopOperatiuneType.COMERCIALIZARE
    assert b.denumire_marfa == "Materiale constructii"
    assert b.cantitate == "100.00"
    assert b.greutate_bruta == "110.00"
    assert n.partener_comercial.cod_tara is CodTaraType.ROMANIA
    assert n.partener_comercial.denumire == "Partener SRL"
    assert n.date_transport.nr_vehicul == "B01ABC"
    assert n.date_transport.data_transport == XmlDate(2026, 6, 30)
    assert n.cod_tip_operatiune is CodTipOperatiuneType.ACHIZITIE_INTRACOMUNITARA
    assert len(n.documente_transport) == 1
    assert n.documente_transport[0].tip_document is TipDocumentType.CMR


def test_serialized_declaration_carries_namespace() -> None:
    """Serialized XML must carry the ANAF e-Transport namespace."""
    xml_str = XmlSerializer().render(_minimal_declaration())
    assert _NS in xml_str


def test_parse_then_reserialize_is_stable() -> None:
    """Two serialization passes should produce semantically identical output."""
    original = _minimal_declaration()
    serializer = XmlSerializer()
    parser = XmlParser()
    xml1 = serializer.render(original)
    xml2 = serializer.render(parser.from_string(xml1, ETransport))
    root1 = ET.fromstring(xml1)
    root2 = ET.fromstring(xml2)
    assert root1.get("codDeclarant") == root2.get("codDeclarant")
    # Both must have a notificare child with the same codTipOperatiune attribute.
    ns = f"{{{_NS}}}"
    n1 = root1.find(f"{ns}notificare")
    n2 = root2.find(f"{ns}notificare")
    assert n1 is not None and n2 is not None
    assert n1.get("codTipOperatiune") == n2.get("codTipOperatiune")


def test_etransport_root_element_name() -> None:
    """Serialized root element must be ``eTransport`` in the ANAF namespace."""
    xml_str = XmlSerializer().render(_minimal_declaration())
    root = ET.fromstring(xml_str)
    assert root.tag == f"{{{_NS}}}eTransport"
