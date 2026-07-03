"""Value types returned by :class:`anafpy.public.client.PublicClient`.

The public services answer JSON with Romanian wire names in wildly inconsistent
casing (``scpTVA``, ``statusRO_e_Factura``, ``nrRegCom``); the models here expose an
English snake_case surface and keep the wire names as pydantic aliases, so the
reference doc (``docs/anaf-reference/public/api.md``) stays the map between the two.

Conventions shared with the other clients: string fields tolerate ANAF returning
numbers, empty strings (ANAF's "absent") become ``None``, and every response
container keeps the raw body bytes for fidelity — the typed view is a convenience,
not the source of truth.

Membership caveat (per the live-confirmed reference): RegAgric/RegCult return CUIs
that are *not* in the register under ``found`` with empty fields and a ``False``
status — read membership from the ``registered`` booleans, never from presence in
``found``.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

__all__ = [
    "Address",
    "CultLookup",
    "CultRecord",
    "EfacturaRegisterEntry",
    "EfacturaRegisterLookup",
    "FarmerLookup",
    "FarmerRecord",
    "FinancialIndicator",
    "FinancialStatement",
    "GeneralData",
    "InactiveState",
    "RegistryLookup",
    "RemoteValidationResult",
    "SplitVat",
    "TaxpayerLookup",
    "TaxpayerRecord",
    "TransformStandard",
    "VatOnCollection",
    "VatPeriod",
    "VatRegistration",
]


def _blank_to_none(value: Any) -> str | None:
    """ANAF encodes "absent" as ``""``; numbers occasionally arrive for text fields."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_Str = Annotated[str | None, BeforeValidator(_blank_to_none)]


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


_Int = Annotated[int | None, BeforeValidator(_empty_to_none)]
_Dec = Annotated[Decimal | None, BeforeValidator(_empty_to_none)]

#: ANAF sometimes sends ``null`` where an array is documented; read it as empty.
_none_to_list = BeforeValidator(lambda v: [] if v is None else v)


class _WireModel(BaseModel):
    """Base for wire-facing models: alias-populated, constructible by field name."""

    model_config = ConfigDict(populate_by_name=True)


# --- stateless e-Factura document services (validare / transformare) -----------------


class TransformStandard(StrEnum):
    """``std`` path segment for ``/validare`` and ``/transformare``."""

    INVOICE = "FACT1"
    CREDIT_NOTE = "FCN"


class RemoteValidationResult(BaseModel):
    """Outcome of ANAF's server-side ``validare`` endpoint.

    An invalid document is a *business* outcome: ``valid`` is ``False`` and
    ``messages`` carries ANAF's findings — never an exception.
    """

    valid: bool
    messages: list[str] = []
    trace_id: str | None = None
    raw: bytes = b""


# --- taxpayer / VAT registry (§1 of the reference) -----------------------------------


class GeneralData(_WireModel):
    """``date_generale``: company identity, registration, and e-Factura membership."""

    cui: _Int = None
    query_date: _Str = Field(default=None, alias="data")
    name: _Str = Field(default=None, alias="denumire")
    address: _Str = Field(default=None, alias="adresa")
    trade_register_number: _Str = Field(default=None, alias="nrRegCom")
    phone: _Str = Field(default=None, alias="telefon")
    fax: _Str = None
    postal_code: _Str = Field(default=None, alias="codPostal")
    registration_act: _Str = Field(default=None, alias="act")
    registration_status: _Str = Field(default=None, alias="stare_inregistrare")
    registration_date: _Str = Field(default=None, alias="data_inregistrare")
    caen_code: _Str = Field(default=None, alias="cod_CAEN")
    iban: _Str = None
    efactura_registered: bool = Field(default=False, alias="statusRO_e_Factura")
    efactura_register_date: _Str = Field(
        default=None, alias="data_inreg_Reg_RO_e_Factura"
    )
    fiscal_authority: _Str = Field(default=None, alias="organFiscalCompetent")
    ownership_form: _Str = Field(default=None, alias="forma_de_proprietate")
    organization_form: _Str = Field(default=None, alias="forma_organizare")
    legal_form: _Str = Field(default=None, alias="forma_juridica")


class VatPeriod(_WireModel):
    """One ``perioade_TVA[]`` entry: an interval of art. 316 VAT registration."""

    start: _Str = Field(default=None, alias="data_inceput_ScpTVA")
    end: _Str = Field(default=None, alias="data_sfarsit_ScpTVA")
    year_date: _Str = Field(default=None, alias="data_anul_imp_ScpTVA")
    message: _Str = Field(default=None, alias="mesaj_ScpTVA")


class VatRegistration(_WireModel):
    """``inregistrare_scop_Tva``: art. 316 Cod Fiscal VAT registration."""

    registered: bool = Field(default=False, alias="scpTVA")
    periods: Annotated[list[VatPeriod], _none_to_list] = Field(
        default_factory=list, alias="perioade_TVA"
    )


class VatOnCollection(_WireModel):
    """``inregistrare_RTVAI``: TVA la încasare (VAT on collection)."""

    registered: bool = Field(default=False, alias="statusTvaIncasare")
    start: _Str = Field(default=None, alias="dataInceputTvaInc")
    end: _Str = Field(default=None, alias="dataSfarsitTvaInc")
    updated: _Str = Field(default=None, alias="dataActualizareTvaInc")
    published: _Str = Field(default=None, alias="dataPublicareTvaInc")
    act_type: _Str = Field(default=None, alias="tipActTvaInc")


class InactiveState(_WireModel):
    """``stare_inactiv``: inactive / reactivated taxpayer status."""

    inactive: bool = Field(default=False, alias="statusInactivi")
    inactivation_date: _Str = Field(default=None, alias="dataInactivare")
    reactivation_date: _Str = Field(default=None, alias="dataReactivare")
    publication_date: _Str = Field(default=None, alias="dataPublicare")
    delisting_date: _Str = Field(default=None, alias="dataRadiere")


class SplitVat(_WireModel):
    """``inregistrare_SplitTVA``: split-VAT registration."""

    registered: bool = Field(default=False, alias="statusSplitTVA")
    start: _Str = Field(default=None, alias="dataInceputSplitTVA")
    cancelled: _Str = Field(default=None, alias="dataAnulareSplitTVA")


def _strip_key_prefix(prefix: str) -> BeforeValidator:
    """ANAF prefixes every address key with ``s``/``d`` per address kind; strip it so
    one :class:`Address` model covers both ``adresa_sediu_social`` and
    ``adresa_domiciliu_fiscal``."""

    def strip(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            (key[len(prefix) :] if key.startswith(prefix) else key): item
            for key, item in value.items()
        }

    return BeforeValidator(strip)


class Address(_WireModel):
    """A structured address (registered office or fiscal domicile), wire prefix
    (``s``/``d``) already stripped by the parent model."""

    street: _Str = Field(default=None, alias="denumire_Strada")
    street_number: _Str = Field(default=None, alias="numar_Strada")
    locality: _Str = Field(default=None, alias="denumire_Localitate")
    locality_code: _Str = Field(default=None, alias="cod_Localitate")
    county: _Str = Field(default=None, alias="denumire_Judet")
    county_code: _Str = Field(default=None, alias="cod_Judet")
    county_auto_code: _Str = Field(default=None, alias="cod_JudetAuto")
    country: _Str = Field(default=None, alias="tara")
    details: _Str = Field(default=None, alias="detalii_Adresa")
    postal_code: _Str = Field(default=None, alias="cod_Postal")


class TaxpayerRecord(_WireModel):
    """One ``found[]`` entry of the v9 taxpayer/VAT registry lookup.

    The ``status`` booleans answer membership *as of the queried date*; absent
    registrations come back ``False`` with empty date fields. Note that
    ``efactura_registered is False`` only means the CUI never joined the pre-mandate
    opt-in register — post-2024 it does **not** mean it can't receive e-Factura.
    """

    general: GeneralData = Field(default_factory=GeneralData, alias="date_generale")
    vat: VatRegistration = Field(
        default_factory=VatRegistration, alias="inregistrare_scop_Tva"
    )
    vat_on_collection: VatOnCollection = Field(
        default_factory=VatOnCollection, alias="inregistrare_RTVAI"
    )
    inactive_state: InactiveState = Field(
        default_factory=InactiveState, alias="stare_inactiv"
    )
    split_vat: SplitVat = Field(default_factory=SplitVat, alias="inregistrare_SplitTVA")
    registered_office: Annotated[Address | None, _strip_key_prefix("s")] = Field(
        default=None, alias="adresa_sediu_social"
    )
    fiscal_address: Annotated[Address | None, _strip_key_prefix("d")] = Field(
        default=None, alias="adresa_domiciliu_fiscal"
    )

    @property
    def cui(self) -> int | None:
        return self.general.cui

    @property
    def name(self) -> str | None:
        return self.general.name

    @property
    def vat_registered(self) -> bool:
        return self.vat.registered

    @property
    def is_inactive(self) -> bool:
        return self.inactive_state.inactive

    @property
    def efactura_registered(self) -> bool:
        return self.general.efactura_registered


# --- RO e-Factura register (§2) ----------------------------------------


class EfacturaRegisterEntry(_WireModel):
    """One ``found[]`` entry of the Registrul RO e-Factura query.

    Shape per ``docV1.txt``; not yet live-confirmed (see the reference doc §2).
    """

    cui: _Int = None
    name: _Str = Field(default=None, alias="denumire")
    address: _Str = Field(default=None, alias="adresa")
    # `register` shadows a BaseModel attribute; repo convention: `_`-suffix on conflict.
    register_: _Str = Field(default=None, alias="registru")
    category: _Str = Field(default=None, alias="categorie")
    enrolment_date: _Str = Field(default=None, alias="dataInscriere")
    opt_out_date: _Str = Field(default=None, alias="dataRenuntare")
    removal_date: _Str = Field(default=None, alias="dataRadiere")
    b2g_option_date: _Str = Field(default=None, alias="dataOptiuneB2G")
    state: _Str = Field(default=None, alias="stare")


# --- farmers / cult registers (§4, §5) ----------------------------------------


class FarmerRecord(_WireModel):
    """One ``found[]`` entry of the farmers' special-regime register (art. 315¹)."""

    cui: _Int = None
    query_date: _Str = Field(default=None, alias="data")
    name: _Str = Field(default=None, alias="denumire")
    address: _Str = Field(default=None, alias="adresa")
    trade_register_number: _Str = Field(default=None, alias="nrRegCom")
    phone: _Str = Field(default=None, alias="telefon")
    fax: _Str = None
    postal_code: _Str = Field(default=None, alias="codPostal")
    registration_act: _Str = Field(default=None, alias="act")
    registration_status: _Str = Field(default=None, alias="stare_inregistrare")
    start: _Str = Field(default=None, alias="dataInceputRegAgric")
    cancelled: _Str = Field(default=None, alias="dataAnulareRegAgric")
    registered: bool = Field(default=False, alias="statusRegAgric")


class CultRecord(_WireModel):
    """One ``found[]`` entry of the cult-entities register (tax-credit eligible)."""

    cui: _Int = None
    query_date: _Str = Field(default=None, alias="data")
    name: _Str = Field(default=None, alias="denumire")
    address: _Str = Field(default=None, alias="adresa")
    trade_register_number: _Str = Field(default=None, alias="nrRegCom")
    phone: _Str = Field(default=None, alias="telefon")
    fax: _Str = None
    postal_code: _Str = Field(default=None, alias="codPostal")
    registration_act: _Str = Field(default=None, alias="act")
    registration_status: _Str = Field(default=None, alias="stare_inregistrare")
    start: _Str = Field(default=None, alias="dataInceputRegCult")
    cancelled: _Str = Field(default=None, alias="dataAnulareRegCult")
    registered: bool = Field(default=False, alias="statusRegCult")


# --- shared lookup container ----------------------------------------


class RegistryLookup[RecordT: BaseModel](_WireModel):
    """A registry query outcome: matched records plus the CUIs ANAF had no data for.

    Membership in a specific register must be read from the record's ``registered``
    / ``status`` booleans — RegAgric/RegCult put unknown CUIs in ``found`` too.
    """

    found: Annotated[list[RecordT], _none_to_list] = Field(default_factory=list)
    not_found: Annotated[list[int], _none_to_list] = Field(
        default_factory=list, alias="notFound"
    )
    raw: bytes = b""


TaxpayerLookup = RegistryLookup[TaxpayerRecord]
EfacturaRegisterLookup = RegistryLookup[EfacturaRegisterEntry]
FarmerLookup = RegistryLookup[FarmerRecord]
CultLookup = RegistryLookup[CultRecord]


# --- financial statements (§3) ----------------------------------------


class FinancialIndicator(_WireModel):
    """One ``i[]`` entry: a published balance-sheet indicator."""

    code: _Str = Field(default=None, alias="indicator")
    value: _Dec = Field(default=None, alias="val_indicator")
    label: _Str = Field(default=None, alias="val_den_indicator")


class FinancialStatement(_WireModel):
    """Public indicators from an annual financial statement (``GET /bilant``).

    The indicator set varies by statement type (commercial vs banking vs insurance),
    so indicators are a list, not fixed fields.
    """

    year: _Int = Field(default=None, alias="an")
    cui: _Int = None
    name: _Str = Field(default=None, alias="deni")
    caen_code: _Str = Field(default=None, alias="caen")
    caen_name: _Str = Field(default=None, alias="den_caen")
    indicators: Annotated[list[FinancialIndicator], _none_to_list] = Field(
        default_factory=list, alias="i"
    )
    raw: bytes = b""
