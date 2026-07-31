"""e-Transport nomenclatures (code lists) surfaced to the model.

The composing ``etransport_prepare_*`` tools accept enum members by name or ANAF
code; this module lets the model discover those names/codes without guessing. The
entries come straight from the generated XSD enums (regeneration keeps them in
sync); the human labels live one layer down, in
:mod:`anafpy.etransport.labels`, which the card renderer shares. The one
non-enum list is ``unit_codes`` — the UN/ECE Rec 20/21 codes ANAF's Schematron
enforces for goods lines (the XSD only pattern-checks them), carried in
:mod:`.unitcodes`; its entries are code-only.
"""

from __future__ import annotations

from enum import Enum

from ...etransport.labels import LABELS_BY_ENUM
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
    labels = LABELS_BY_ENUM.get(enum_cls, {})
    return [
        {"name": member.name, "code": member.value}
        | ({"label": label} if (label := labels.get(member.name)) else {})
        for member in enum_cls
    ]
