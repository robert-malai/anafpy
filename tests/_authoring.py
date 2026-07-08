"""Shared factories for the invoice-authoring test suites.

``make_invoice`` builds a minimal valid CIUS-RO invoice (one 19% line, RON,
Romanian seller and buyer); keyword overrides replace whole fields. The
maximal-surface document used by the round-trip suite lives there, not here.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from anafpy.efactura.authoring import (
    InvoiceDocument,
    InvoiceLine,
    Party,
    PostalAddress,
    Seller,
)

ISSUE_DATE = dt.date(2026, 7, 8)
DUE_DATE = dt.date(2026, 8, 7)


def make_address(**overrides: Any) -> PostalAddress:
    fields: dict[str, Any] = {
        "street": "Str. Exemplu 1",
        "city": "Cluj-Napoca",
        "county": "RO-CJ",
        "country": "RO",
    }
    fields.update(overrides)
    return PostalAddress(**fields)


def make_seller(**overrides: Any) -> Seller:
    fields: dict[str, Any] = {
        "name": "Furnizor Test SRL",
        "vat_id": "RO12345678",
        "address": make_address(),
    }
    fields.update(overrides)
    return Seller(**fields)


def make_buyer(**overrides: Any) -> Party:
    fields: dict[str, Any] = {
        "name": "Client Test SRL",
        "vat_id": "RO87654321",
        "address": make_address(),
    }
    fields.update(overrides)
    return Party(**fields)


def make_line(**overrides: Any) -> InvoiceLine:
    fields: dict[str, Any] = {
        "name": "Servicii de consultanta",
        "quantity": Decimal("10"),
        "unit": "H87",
        "unit_price": Decimal("10.00"),
        "vat_category": "S",
        "vat_rate": Decimal("19"),
    }
    fields.update(overrides)
    return InvoiceLine(**fields)


def make_invoice(**overrides: Any) -> InvoiceDocument:
    fields: dict[str, Any] = {
        "number": "INV-2026-0042",
        "issue_date": ISSUE_DATE,
        "due_date": DUE_DATE,
        "currency": "RON",
        "seller": make_seller(),
        "buyer": make_buyer(),
        "lines": [make_line()],
    }
    fields.update(overrides)
    return InvoiceDocument(**fields)
