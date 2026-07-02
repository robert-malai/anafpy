"""ANAF public (no-auth) web services: registries and financial statements.

The zero-credential lookup surface on ``webservicesp.anaf.ro`` — a separate family
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
    SplitVat,
    TaxpayerLookup,
    TaxpayerRecord,
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
    "SplitVat",
    "TaxpayerLookup",
    "TaxpayerRecord",
    "VatOnCollection",
    "VatPeriod",
    "VatRegistration",
]
