"""SPV nomenclatures (code lists) surfaced to the model.

``spv_cerere`` takes a report type and per-type parameters; this module lets the
model discover both without guessing. The entries come from the client-layer
:class:`~anafpy.spv.ReportType` nomenclature (each member carries ANAF's exact
wire value plus a one-line English description, so the model can map "my VAT
return for March" onto ``D300``); the per-type parameter lists are the
``ReportRequest`` validation rules, translated to the wire names the tool takes.
The fixed ``motiv`` list for 'Adeverinte Venit'
(:data:`~anafpy.spv.INCOME_CERTIFICATE_REASONS`) is served by the tool directly —
it is already a plain list of wire-exact strings.
"""

from __future__ import annotations

from ...exceptions import AnafConfigError
from ...spv import (
    REPORT_PARAMETER_WIRE_NAMES,
    ReportType,
    optional_parameters,
    required_parameters,
)

__all__ = ["REPORT_TYPES_NOTE", "report_type_entries", "resolve_report_type"]

REPORT_TYPES_NOTE = (
    "CAF (certificat de atestare fiscala) cannot be requested through this "
    "service yet — for one, point the user to the SPV web portal"
)


def resolve_report_type(tip: str) -> ReportType:
    """Resolve ``tip`` — exact wire value first, then enum member name."""
    try:
        # Value lookup, not construction — mypy misreads enum calls when the
        # enum defines __new__ (the (value, description) member pattern).
        return ReportType(tip)  # type: ignore[call-arg]
    except ValueError:
        pass
    try:
        return ReportType[tip.strip().upper().replace(" ", "_").replace("-", "_")]
    except KeyError:
        valid = ", ".join(t.value for t in ReportType)
        raise AnafConfigError(
            f"unknown report type {tip!r}; valid `tip` values: {valid}"
        ) from None


def report_type_entries() -> list[dict[str, object]]:
    """Every ``tip`` spv_cerere accepts: description + per-type wire parameters."""
    return [
        {
            "tip": type_.value,
            "description": type_.description,
            "required": [
                REPORT_PARAMETER_WIRE_NAMES[f] for f in required_parameters(type_)
            ],
            "optional": [
                REPORT_PARAMETER_WIRE_NAMES[f] for f in optional_parameters(type_)
            ],
        }
        for type_ in ReportType
    ]
