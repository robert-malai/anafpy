"""e-Transport nomenclatures (code lists) surfaced to the model.

The composing ``etransport_prepare_*`` tools accept enum members by name or ANAF
code; this module lets the model discover those names/codes without guessing. The
entries come straight from the generated XSD enums (regeneration keeps them in
sync); only the operation-type labels are hand-carried here, because the codegen
keeps the XSD's ``xs:documentation`` text as source comments, not runtime data.
"""

from __future__ import annotations

from enum import Enum

from ..etransport.schema.schema_etr_v2_20230126 import (
    CodBirouVamalType,
    CodJudetType,
    CodPtfType,
    CodScopOperatiuneType,
    CodTaraType,
    CodTipOperatiuneType,
    TipConfirmareType,
    TipDocumentType,
)
from ..exceptions import AnafConfigError

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


def nomenclature_entries(kind: str) -> list[dict[str, object]]:
    """The ``{name, code[, label]}`` entries of one nomenclature.

    Raises :class:`AnafConfigError` for an unknown ``kind`` (naming the valid ones).
    """
    enum_cls = _KINDS.get(kind)
    if enum_cls is None:
        raise AnafConfigError(
            f"unknown nomenclature {kind!r}; one of: {', '.join(sorted(_KINDS))}"
        )
    labels = _OPERATION_TYPE_LABELS if enum_cls is CodTipOperatiuneType else {}
    return [
        {"name": member.name, "code": member.value}
        | ({"label": label} if (label := labels.get(member.name)) else {})
        for member in enum_cls
    ]
