"""ANAF public (no-auth) web services: registries, financial statements, and the
stateless e-Factura document services (``validare`` / ``transformare``).

The zero-credential surface on ``webservicesp.anaf.ro`` — a separate family
from the OAuth-protected e-Factura / e-Transport clients. See
``docs/anaf-reference/public/api.md`` for the compiled API reference.
"""

from __future__ import annotations

from .client import PublicClient
from .models import (
    Address,
    CultLookup,
    CultRecord,
    EfacturaRegisterEntry,
    EfacturaRegisterLookup,
    FarmerLookup,
    FarmerRecord,
    FinancialIndicator,
    FinancialStatement,
    GeneralData,
    InactiveState,
    RegistryLookup,
    RemoteValidationResult,
    SplitVat,
    TaxpayerLookup,
    TaxpayerRecord,
    TransformStandard,
    VatOnCollection,
    VatPeriod,
    VatRegistration,
)

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
    "PublicClient",
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
