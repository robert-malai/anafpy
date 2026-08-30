"""Value types for BNR's published foreign-exchange reference rates.

BNR quotes **lei per unit of foreign currency**, with a ``multiplier`` attribute
on the small-denomination currencies: ``<Rate currency="HUF" multiplier="100">
1.4430</Rate>`` means 100 HUF = 1.4430 RON, not 1 HUF. Keeping ``quoted`` and
``multiplier`` exactly as published — and dividing only inside
:meth:`FxRateSet.convert` — is what stops that factor-of-100 from being lost in
a rounded intermediate.

:attr:`FxRateSet.date` is the date BNR **published**, which is not always the
date that was asked for: rates exist per banking day, so a Sunday, a holiday, or
a moment before the 13:00 publication resolves to the last published day. The
set carries the real date so a caller can say which day it actually got.
"""

from __future__ import annotations

import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..exceptions import AnafConfigError

__all__ = ["Conversion", "FxRate", "FxRateSet"]

_CENT = Decimal("0.01")

#: BNR's own quotation base — every rate is *this many lei* per unit.
BASE_CURRENCY = "RON"


class FxRate(BaseModel):
    """One currency's reference quotation, as BNR published it."""

    model_config = ConfigDict(frozen=True)

    currency: str = Field(description="ISO 4217 code, e.g. 'EUR'.")
    quoted: Decimal = Field(
        description="The published figure — lei per `multiplier` units."
    )
    multiplier: int = Field(
        default=1,
        gt=0,
        description="Units the quotation covers (100 for HUF, IDR, ISK, JPY, KRW).",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def lei_per_unit(self) -> Decimal:
        """Lei for **one** unit — ``quoted`` with the multiplier applied.

        Exact: the multiplier is always a power of ten, so the division adds
        digits rather than losing them.
        """
        return self.quoted / self.multiplier


class FxRateSet(BaseModel):
    """Every reference rate BNR published on one banking day."""

    date: datetime.date = Field(
        description="The banking day BNR published these rates for."
    )
    base_currency: str = Field(
        default=BASE_CURRENCY, description="The currency the rates are quoted in."
    )
    rates: dict[str, FxRate] = Field(description="Rates by ISO 4217 code.")
    source_url: str = Field(description="The BNR XML document this was read from.")

    @property
    def currencies(self) -> list[str]:
        """The quoted currency codes, sorted."""
        return sorted(self.rates)

    def rate(self, currency: str) -> FxRate | None:
        """The rate for *currency*, or ``None`` if BNR does not quote it."""
        return self.rates.get(currency.strip().upper())

    def convert(self, amount: Decimal | int | str, currency: str) -> Conversion:
        """Convert *amount* of *currency* into RON at this day's rate.

        The multiplier is applied and the result rounded to two decimals half
        away from zero — once, on the final figure. The base currency converts
        one-for-one (BNR quotes no rate for it).

        Raises:
            AnafConfigError: BNR does not quote *currency* on this day. The
                message lists what it does quote, so a wrong code self-heals.
        """
        code = currency.strip().upper()
        value = Decimal(str(amount))
        if code == self.base_currency:
            rate = FxRate(currency=code, quoted=Decimal(1))
        elif (found := self.rate(code)) is not None:
            rate = found
        else:
            raise AnafConfigError(
                f"BNR quotes no rate for {code!r} on {self.date} — it quotes "
                f"{', '.join([self.base_currency, *self.currencies])}"
            )
        converted = (value * rate.quoted / rate.multiplier).quantize(
            _CENT, rounding=ROUND_HALF_UP
        )
        return Conversion(amount=value, currency=code, amount_ron=converted, rate=rate)


class Conversion(BaseModel):
    """One amount converted to RON at a published BNR reference rate."""

    amount: Decimal = Field(description="The original amount.")
    currency: str = Field(description="The original currency (ISO 4217).")
    amount_ron: Decimal = Field(description="The amount in RON, at two decimals.")
    rate: FxRate = Field(description="The rate applied.")
