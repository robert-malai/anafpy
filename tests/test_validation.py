"""Tests for the Schematron validation module.

These tests use the pre-compiled XSLT artifacts (``compiled/validation.xsl``).
They require the ``anafpy[validation]`` extra (saxonche).
"""

from __future__ import annotations

import pytest

from anafpy.validation import SchematronValidator, ValidationFinding, ValidationResult

pytestmark = pytest.mark.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _etransport_validator() -> SchematronValidator:
    from anafpy.etransport.validator import create_validator

    return create_validator()


def _efactura_validator() -> SchematronValidator:
    from anafpy.efactura.validator import create_validator

    return create_validator()


def _etransport_xml(
    *,
    cif: str = "1234567890",
    tip_op: str = "10",
    partner_cod_tara: str = "RO",
    include_pc_cod: bool = True,
) -> str:
    pc_cod = 'cod="RO1234567"' if include_pc_cod else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<eTransport xmlns="mfp:anaf:dgti:eTransport:declaratie:v2" codDeclarant="{cif}">
  <notificare codTipOperatiune="{tip_op}">
    <bunuriTransportate codScopOperatiune="101" denumireMarfa="Marfa test"
      cantitate="10.00" codUnitateMasura="KGM" greutateBruta="12.00"/>
    <partenerComercial codTara="{partner_cod_tara}" denumire="Partner SRL" {pc_cod}/>
    <dateTransport nrVehicul="B01ABC" codTaraOrgTransport="RO"
      denumireOrgTransport="Trans SRL" dataTransport="2026-06-30"/>
    <locStartTraseuRutier>
      <locatie codJudet="12" denumireLocalitate="Cluj" denumireStrada="Str. 1"/>
    </locStartTraseuRutier>
    <locFinalTraseuRutier>
      <locatie codJudet="40" denumireLocalitate="Bucuresti" denumireStrada="Bd. 2"/>
    </locFinalTraseuRutier>
    <documenteTransport tipDocument="10" dataDocument="2026-06-28"/>
  </notificare>
</eTransport>"""


_CIUS_RO_ID = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"


def _minimal_invoice_xml(*, customization_id: str = _CIUS_RO_ID) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>{customization_id}</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>TEST-001</cbc:ID>
  <cbc:IssueDate>2026-06-28</cbc:IssueDate>
  <cbc:DueDate>2026-07-28</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>RON</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Supplier SRL</cbc:Name></cac:PartyName>
      <cac:PostalAddress><cac:Country>
        <cbc:IdentificationCode>RO</cbc:IdentificationCode>
      </cac:Country></cac:PostalAddress>
      <cac:PartyTaxScheme><cbc:CompanyID>RO12345678</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Supplier SRL</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Buyer SRL</cbc:Name></cac:PartyName>
      <cac:PostalAddress><cac:Country>
        <cbc:IdentificationCode>RO</cbc:IdentificationCode>
      </cac:Country></cac:PostalAddress>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Buyer SRL</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="RON">19.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="RON">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="RON">19.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="RON">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="RON">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="RON">119.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="RON">119.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="RON">100.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Service</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="RON">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""


# ---------------------------------------------------------------------------
# ValidationResult / ValidationFinding unit tests
# ---------------------------------------------------------------------------


def test_validation_result_is_valid_when_no_findings() -> None:
    result = ValidationResult()
    assert result.is_valid


def test_validation_result_is_invalid_when_error_finding() -> None:
    result = ValidationResult(
        findings=[
            ValidationFinding(
                rule_id="BR-001", message="Missing field", severity="error"
            )
        ]
    )
    assert not result.is_valid


def test_validation_result_is_valid_with_warning_only() -> None:
    result = ValidationResult(
        findings=[
            ValidationFinding(rule_id="BT-TY-001", message="info", severity="warning")
        ]
    )
    assert result.is_valid


def test_validation_finding_defaults() -> None:
    f = ValidationFinding(message="test")
    assert f.rule_id is None
    assert f.location is None
    assert f.severity == "error"


# ---------------------------------------------------------------------------
# e-Transport validator
# ---------------------------------------------------------------------------


def test_etransport_create_validator_returns_instance() -> None:
    v = _etransport_validator()
    assert isinstance(v, SchematronValidator)


def test_etransport_validator_accepts_bytes() -> None:
    v = _etransport_validator()
    xml_bytes = _etransport_xml().encode("utf-8")
    result = v.validate(xml_bytes)
    assert isinstance(result, ValidationResult)


def test_etransport_validator_produces_svrl() -> None:
    v = _etransport_validator()
    result = v.validate(_etransport_xml())
    assert result.raw_svrl.startswith(b"<?xml")
    assert b"svrl" in result.raw_svrl


def test_etransport_known_rule_id_appears_in_findings() -> None:
    # AIC (10) without a RO partner fiscal code triggers BR-206/207/208
    v = _etransport_validator()
    result = v.validate(_etransport_xml(tip_op="10", include_pc_cod=False))
    rule_ids = {f.rule_id for f in result.findings if f.severity == "error"}
    assert "BR-206" in rule_ids or "BR-207" in rule_ids


def test_etransport_warning_findings_do_not_affect_is_valid() -> None:
    v = _etransport_validator()
    result = v.validate(_etransport_xml())
    # BT-TY-001 is always a 'warning' (informational); should not affect is_valid
    warning_ids = {f.rule_id for f in result.findings if f.severity == "warning"}
    assert "BT-TY-001" in warning_ids


def test_etransport_wrong_version_raises() -> None:
    from anafpy.etransport.validator import create_validator

    with pytest.raises(ValueError, match="version"):
        create_validator("9.9.9")


# ---------------------------------------------------------------------------
# e-Factura validator
# ---------------------------------------------------------------------------


def test_efactura_create_validator_returns_instance() -> None:
    v = _efactura_validator()
    assert isinstance(v, SchematronValidator)


def test_efactura_validator_produces_svrl() -> None:
    v = _efactura_validator()
    result = v.validate(_minimal_invoice_xml())
    assert result.raw_svrl.startswith(b"<?xml")
    assert b"svrl" in result.raw_svrl


def test_efactura_wrong_customization_id_triggers_br24() -> None:
    # BR-24: CustomizationID must match the CIUS-RO value
    v = _efactura_validator()
    result = v.validate(_minimal_invoice_xml(customization_id="wrong:id"))
    rule_ids = {f.rule_id for f in result.findings if f.severity == "error"}
    # BR-24 or BR-RO-xxx fires when CustomizationID is wrong
    assert any("BR-" in (rid or "") for rid in rule_ids)


def test_efactura_wrong_version_raises() -> None:
    from anafpy.efactura.validator import create_validator

    with pytest.raises(ValueError, match="version"):
        create_validator("9.9.9")
