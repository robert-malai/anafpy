"""The read-only BNR exchange-rate lookup.

One tool, deliberately: it answers "what did BNR publish for this currency on
this day", and converts amounts at that rate so a declared lei figure is
arithmetic rather than model mental-maths. It does **not** rule on which day's
rate a given filing must use — that is the workflow's call, and the payload
reports the day it actually served so a wrong one is visible.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from inspect import cleandoc

from mcp.server import MCPServer

from ...exceptions import AnafConfigError
from ..artifacts import READ_ONLY
from ..context import AppContext

__all__ = ["register"]


def register(mcp: MCPServer, ctx: AppContext) -> None:
    @mcp.tool(
        title="BNR: Exchange rate",
        annotations=READ_ONLY,
        description=cleandoc("""
            The official BNR (Romania's central bank) reference rate for one
            currency, optionally converting amounts to RON at it. No auth
            needed — this is a public feed, not an ANAF service.

            Use it whenever a Romanian filing needs a lei figure for a
            foreign-currency amount (e-Transport `value_ron`, an invoice's
            BT-111, D301's `curs_valutar`) instead of computing a conversion
            yourself.

            BNR publishes once per banking day, just after 13:00. A weekend, a
            holiday, or a call before publication therefore has no rate of its
            own, and the answer carries the last published one. Always read:
            - `rate_date` — the day the returned rate was published for
            - `requested_date` — the day you asked about
            - `fallback_to_last_published` — true when they differ

            Report `rate_date` to the user as the rate's date; never present
            the requested date as though BNR published on it.

            Parameters:
            - `currency` — ISO 4217 code ('EUR', 'HUF'); case-insensitive
            - `date` — ISO YYYY-MM-DD to price at, default today in Romania
            - `amounts` — numbers or decimal strings in `currency`

            `amounts` come back in `conversions`, each rounded to two decimals,
            all at the one rate — so an invoice's lines demonstrably share it.
            An unquoted currency errors with the list of quoted ones.
        """),
    )
    async def bnr_fx_rate(
        currency: str,
        date: str | None = None,
        amounts: list[float | str] | None = None,
    ) -> dict[str, object]:
        rates = await ctx.bnr.get_rates(date)
        # Resolve the rate through convert() even with no amounts to convert:
        # it is the one place that knows the base currency and that raises the
        # self-healing error for an unquoted code.
        rate = rates.convert(0, currency).rate
        conversions = [
            rates.convert(_amount(value), currency).model_dump(
                mode="json", include={"amount", "amount_ron"}
            )
            for value in amounts or []
        ]
        # Asked of the client, not recomputed: it owns what "today" means
        # here (Romania's, not the host's), and a second clock would drift
        # from the one get_rates actually resolved against.
        requested = ctx.bnr.resolve_date(date).isoformat()
        return {
            "currency": rate.currency,
            "requested_date": requested,
            "rate_date": rates.date.isoformat(),
            "fallback_to_last_published": rates.date.isoformat() != requested,
            "lei_per_unit": str(rate.lei_per_unit),
            "quoted": str(rate.quoted),
            "multiplier": rate.multiplier,
            "base_currency": rates.base_currency,
            "source": rates.source_url,
            "conversions": conversions,
        }


def _amount(value: float | str) -> Decimal:
    """Read one requested amount, exactly as written where it is written out."""
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise AnafConfigError(f"not a number: {value!r}") from exc
