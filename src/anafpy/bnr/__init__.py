"""BNR (Banca Națională a României) foreign-exchange reference rates.

The one non-ANAF publisher anafpy reads (DESIGN.md §17), because ANAF filings
are denominated in lei and BNR is who publishes the rate a foreign-currency
amount is converted at. Read-only, no credentials, production only. See
``docs/library/bnr.md``.
"""

from __future__ import annotations

from .client import BNR_FX_HOST, BnrClient
from .models import Conversion, FxRate, FxRateSet

__all__ = [
    "BNR_FX_HOST",
    "BnrClient",
    "Conversion",
    "FxRate",
    "FxRateSet",
]
