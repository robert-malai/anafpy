"""e-Transport nomenclatures (code lists) surfaced to the model.

The composing ``etransport_prepare_*`` tools accept enum members by name or ANAF
code; this module lets the model discover those names/codes without guessing. The
entries come straight from the generated XSD enums (regeneration keeps them in
sync); the human labels of the small nomenclatures (operation types, scopes,
document and confirmation types) are hand-carried here verbatim from the XSD's
``xs:documentation``, because the codegen keeps that text as source comments, not
runtime data. The one non-enum list is ``unit_codes`` — the UN/ECE Rec 20/21
codes ANAF's Schematron enforces for goods lines (the XSD only pattern-checks
them), carried in :mod:`.unitcodes`; its entries are code-only.
"""

from __future__ import annotations

from enum import Enum

from ...etransport.schema.schema_etr_v2_20230126 import (
    CodBirouVamalType,
    CodJudetType,
    CodPtfType,
    CodScopOperatiuneType,
    CodTaraType,
    CodTipOperatiuneType,
    TipConfirmareType,
    TipDocumentType,
)
from ...exceptions import AnafConfigError
from .unitcodes import UNIT_CODES

__all__ = ["nomenclature_entries"]

_KINDS: dict[str, type[Enum]] = {
    "operation_types": CodTipOperatiuneType,
    "operation_scopes": CodScopOperatiuneType,
    "counties": CodJudetType,
    "border_points": CodPtfType,
    "customs_offices": CodBirouVamalType,
    "countries": CodTaraType,
    "document_types": TipDocumentType,
    "confirmation_types": TipConfirmareType,
}

# Full labels from the XSD's xs:documentation for the operation-type siglas.
_OPERATION_TYPE_LABELS = {
    "AIC": "Achiziţie intracomunitară",
    "LHI": "Operațiuni în sistem lohn (UE) - intrare",
    "SCI": "Stocuri la dispoziția clientului (Call-off stock) - intrare",
    "LIC": "Livrare intracomunitară",
    "LHE": "Operațiuni în sistem lohn (UE) - ieșire",
    "SCE": "Stocuri la dispoziția clientului (Call-off stock) - ieșire",
    "TTN": "Transport pe teritoriul naţional",
    "IMP": "Import",
    "EXP": "Export",
    "DIN": "Tranzacţie intracomunitară - Intrare pentru depozitare/formare "
    "nou transport",
    "DIE": "Tranzacţie intracomunitară - Ieşire după depozitare/formare nou transport",
}

_OPERATION_SCOPE_LABELS = {
    "COMERCIALIZARE": "Comercializare",
    "PRODUCTIE": "Producție",
    "GRATUITATI": "Gratuități",
    "ECHIPAMENT_COMERCIAL": "Echipament comercial",
    "MIJLOACE_FIXE": "Mijloace fixe",
    "CONSUM_PROPRIU": "Consum propriu",
    "OPERATIUNI_DE_LIVRARE_CU_INSTALARE": "Operațiuni de livrare cu instalare",
    "TRANSFER_INTRE_GESTIUNI": "Transfer între gestiuni",
    "BUNURI_PUSE_LA_DISPOZITIA_CLIENTULUI": "Bunuri puse la dispoziția clientului",
    "LEASING_FINANCIAR_OPERATIONAL": "Leasing financiar/operațional",
    "BUNURI_IN_GARANTIE": "Bunuri în garanție",
    "OPERATIUNI_SCUTITE": "Operațiuni scutite",
    "INVESTITIE_IN_CURS": "Investiție in curs",
    "DONATII_AJUTOARE": "Donații, ajutoare",
    "ALTELE": "Altele",
    "ACELASI_CU_OPERATIUNEA": "Același cu operațiunea",
}

_DOCUMENT_TYPE_LABELS = {
    "CMR": "CMR",
    "FACTURA": "Factura",
    "AVIZ_DE_INSOTIRE_A_MARFII": "Aviz de însoțire a mărfii",
    "ALTELE": "Altele",
}

_CONFIRMATION_TYPE_LABELS = {
    "CONFIRMAT": "Confirmat",
    "CONFIRMAT_PARTIAL": "Confirmat parţial",
    "INFIRMAT": "Infirmat",
}

_LABELS: dict[type[Enum], dict[str, str]] = {
    CodTipOperatiuneType: _OPERATION_TYPE_LABELS,
    CodScopOperatiuneType: _OPERATION_SCOPE_LABELS,
    TipDocumentType: _DOCUMENT_TYPE_LABELS,
    TipConfirmareType: _CONFIRMATION_TYPE_LABELS,
}


def nomenclature_entries(kind: str) -> list[dict[str, object]]:
    """The ``{name, code[, label]}`` entries of one nomenclature.

    ``unit_codes`` entries are ``{code}`` only. Raises :class:`AnafConfigError`
    for an unknown ``kind`` (naming the valid ones).
    """
    if kind == "unit_codes":
        return [{"code": code} for code in UNIT_CODES]
    enum_cls = _KINDS.get(kind)
    if enum_cls is None:
        valid = sorted([*_KINDS, "unit_codes"])
        raise AnafConfigError(
            f"unknown nomenclature {kind!r}; one of: {', '.join(valid)}"
        )
    labels = _LABELS.get(enum_cls, {})
    return [
        {"name": member.name, "code": member.value}
        | ({"label": label} if (label := labels.get(member.name)) else {})
        for member in enum_cls
    ]
