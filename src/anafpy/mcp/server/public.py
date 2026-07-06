"""Read-only MCP lookups over ANAF's unauthenticated public services.

No CIF/auth involved; the client paces requests at ANAF's 1 req/s rule. ``raw``
body bytes are kept client-side and excluded from the tool payloads.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ...public.models import RegistryLookup
from ..context import AppContext
from ._shared import READ_ONLY

__all__ = ["register"]


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool(
        title="ANAF Info: Taxpayer lookup",
        annotations=READ_ONLY,
        description="Look up CUIs (max 100) in ANAF's public taxpayer/VAT registry — "
        "no auth needed. One call answers, per CUI as of `date` (ISO, default "
        "today): VAT registration, VAT-on-collection, inactive status, split-VAT, "
        "RO e-Factura register membership, and general company data. CUIs with no "
        "data come back in `not_found`. The 'RO' VAT prefix is tolerated.",
    )
    async def anaf_lookup_taxpayers(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_taxpayers(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        title="ANAF Info: RO e-Factura register",
        annotations=READ_ONLY,
        description="Query the Registrul RO e-Factura (opt-in register) for CUIs "
        "(max 100) — no auth needed. Mostly relevant for B2G option dates; for a "
        "plain 'is this CUI e-Factura-registered' check prefer anaf_lookup_taxpayers "
        "(its `efactura_registered` answers it alongside everything else).",
    )
    async def anaf_lookup_efactura_register(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_efactura_register(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        title="ANAF Info: Farmers register",
        annotations=READ_ONLY,
        description="Query ANAF's farmers' special-regime register (art. 315¹) for "
        "CUIs (max 500) — no auth needed. Membership is the record's `registered` "
        "boolean: unknown CUIs still come back under `found` with empty fields.",
    )
    async def anaf_lookup_farmers(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_farmers(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        title="ANAF Info: Religious entities register",
        annotations=READ_ONLY,
        description="Query ANAF's register of cult entities (tax-credit eligible "
        "religious entities) for CUIs (max 500) — no auth needed. Membership is the "
        "record's `registered` boolean.",
    )
    async def anaf_lookup_cult_entities(
        cuis: list[str | int], date: str | None = None
    ) -> dict[str, object]:
        result = await ctx.public().lookup_cult_entities(cuis, date=date)
        return _lookup_payload(result)

    @mcp.tool(
        title="ANAF Info: Financial statement",
        annotations=READ_ONLY,
        description="Fetch the public indicators of one CUI's annual financial "
        "statement (bilanț) for a given year — no auth needed. The indicator set "
        "varies by statement type (commercial / banking / insurance).",
    )
    async def anaf_financial_statement(cui: str | int, year: int) -> dict[str, object]:
        statement = await ctx.public().get_financial_statement(cui, year)
        return statement.model_dump(mode="json", exclude={"raw"})


def _lookup_payload(result: RegistryLookup[Any]) -> dict[str, object]:
    payload: dict[str, object] = result.model_dump(mode="json", exclude={"raw"})
    payload["count"] = len(result.found)
    return payload
