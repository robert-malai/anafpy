"""Async client for ANAF's unauthenticated public web services.

These are the no-auth lookup services on ``webservicesp.anaf.ro`` (see
``docs/anaf-reference/public/api.md``): the taxpayer/VAT registry, the RO e-Factura
register, the farmers' and cult-entities registers, and public annual financial
statements. Key differences from the OAuth clients:

1. **No authentication** — no ``TokenProvider``, no certificate; and **no test/prod
   split**: there is only the production host.
2. **Client-side pacing.** ANAF states a 1 request/second limit as a usage *rule*
   (not via 429s), so — unlike the OAuth clients' no-auto-backoff stance — this
   client spaces its own requests (``min_request_interval``, set ``0`` to opt out).
3. **Registry queries are batched**: a list of CUIs evaluated at one date, capped at
   100 (taxpayer, e-Factura register) or 500 (RegAgric, RegCult) per request.
4. The RO e-Factura register answers **HTTP 404 when no queried CUI has data** —
   that is a business "not found" (returned), not a transport error (raised).

The synchronous services only. The async job variant of the taxpayer lookup
(``/AsynchWebService/…``) is deliberately not wrapped: its result is downloadable
exactly once and its not-ready response is undocumented, so wrapping it blind would
invent semantics — revisit if a real batching need appears.
"""

from __future__ import annotations

import asyncio
import datetime
import json
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import ValidationError

from .._transport.base import PUBLIC_HOST, as_text, raise_for_status
from ..exceptions import (
    AnafConfigError,
    AnafResponseError,
    AnafTransportError,
)
from .models import (
    CultLookup,
    EfacturaRegisterLookup,
    FarmerLookup,
    FinancialStatement,
    RegistryLookup,
    TaxpayerLookup,
)

__all__ = ["PublicClient"]

#: Documented per-request CUI caps.
_BATCH_CAP_TVA = 100
_BATCH_CAP_REGISTERS = 500

_TVA_PATH = "api/PlatitorTvaRest/v9/tva"
_EFACTURA_REGISTER_PATH = "api/registruroefactura/v1/interogare"
_BILANT_PATH = "bilant"
_AGRIC_PATH = "RegAgric/api/v2/ws/agric"
_CULT_PATH = "RegCult/api/v2/ws/cult"


def _normalize_cui(value: int | str) -> int:
    """Coerce a CUI to the bare number ANAF expects (an optional ``RO`` VAT prefix
    and whitespace are tolerated). Raises :class:`AnafConfigError` on anything else.
    """
    if isinstance(value, str):
        text = value.strip().upper().removeprefix("RO").strip()
        if not text.isdigit():
            raise AnafConfigError(f"invalid CUI: {value!r}")
        value = int(text)
    if value <= 0:
        raise AnafConfigError(f"invalid CUI: {value!r}")
    return value


def _query_date(date: datetime.date | str | None) -> str:
    """Resolve the as-of date of a registry query (default: today)."""
    if date is None:
        return datetime.date.today().isoformat()
    if isinstance(date, datetime.date):
        return date.isoformat()
    try:
        return datetime.date.fromisoformat(date).isoformat()
    except ValueError as exc:
        raise AnafConfigError(f"invalid query date: {date!r}") from exc


def _query_payload(
    cuis: Sequence[int | str],
    date: datetime.date | str | None,
    *,
    cap: int,
    operation: str,
) -> list[dict[str, int | str]]:
    if not cuis:
        raise AnafConfigError(f"{operation}: at least one CUI is required")
    if len(cuis) > cap:
        raise AnafConfigError(
            f"{operation}: at most {cap} CUIs per request (got {len(cuis)})"
        )
    as_of = _query_date(date)
    return [{"cui": _normalize_cui(cui), "data": as_of} for cui in cuis]


def _parse_lookup[LookupT: RegistryLookup[Any]](
    body: bytes, model: type[LookupT], operation: str
) -> LookupT:
    """Validate a registry response against its lookup model.

    RegAgric/RegCult (and, per the instruction files, nominally the TVA service too)
    wrap the payload in a ``{"cod", "message", ...}`` envelope; a non-200 ``cod``
    inside an HTTP 200 is a genuine query error and raises. A body that matches
    neither shape raises :class:`AnafResponseError` — explicit, rather than
    inventing an outcome.
    """
    text = as_text(body)
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise AnafResponseError(
            f"unrecognised {operation} response: {text[:200]}",
            status_code=200,
            body=text,
        ) from exc
    if isinstance(data, dict) and data.get("cod") not in (None, 200):
        message = data.get("message") or text[:200]
        raise AnafResponseError(
            f"{operation} error: cod={data.get('cod')} {message}",
            status_code=200,
            body=text,
        )
    try:
        result = model.model_validate(data)
    except ValidationError as exc:
        raise AnafResponseError(
            f"unrecognised {operation} response: {text[:200]}",
            status_code=200,
            body=text,
        ) from exc
    result.raw = body
    return result


class _RequestPacer:
    """Serialize requests so consecutive sends stay ``interval`` seconds apart —
    ANAF's stated 1 req/s usage rule for the public host, honoured client-side."""

    def __init__(self, interval: float) -> None:
        self._interval = interval
        self._lock = asyncio.Lock()
        self._earliest = 0.0

    async def wait(self) -> None:
        if self._interval <= 0:
            return
        async with self._lock:
            loop = asyncio.get_running_loop()
            delay = self._earliest - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            self._earliest = loop.time() + self._interval


class PublicClient:
    """Talks to ANAF's unauthenticated public services (``webservicesp.anaf.ro``).

    No credentials are needed; the client owns an ``httpx.AsyncClient`` (unless one
    is injected) and should be used as an async context manager so it is closed
    cleanly. Requests are paced at ``min_request_interval`` seconds (default 1.0,
    ANAF's stated limit); pass ``0`` to disable pacing and bring your own.
    """

    def __init__(
        self,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
        min_request_interval: float = 1.0,
    ) -> None:
        self._owns_http = http is None
        # No keep-alive: ANAF's public host resets pooled idle connections between
        # paced requests (RegAgric RSTs on reuse, live-observed 2026-07-02), and at
        # ≤1 req/s a fresh connection per request costs nothing.
        self._http = http or httpx.AsyncClient(
            timeout=timeout, limits=httpx.Limits(max_keepalive_connections=0)
        )
        self._pacer = _RequestPacer(min_request_interval)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    # -- transport -------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: list[dict[str, int | str]] | None = None,
        tolerate: tuple[int, ...] = (),
    ) -> httpx.Response:
        url = f"{PUBLIC_HOST}/{path}"
        await self._pacer.wait()
        try:
            response = await self._http.request(
                method, url, params=params, json=json_body
            )
        except httpx.HTTPError as exc:
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc
        if response.status_code not in tolerate:
            raise_for_status(response)
        return response

    # -- operations ------------------------------------------------------------------

    async def lookup_taxpayers(
        self,
        cuis: Sequence[int | str],
        *,
        date: datetime.date | str | None = None,
    ) -> TaxpayerLookup:
        """Query the taxpayer/VAT registry (v9) for up to 100 CUIs at one date.

        The workhorse lookup: each :class:`~anafpy.public.models.TaxpayerRecord`
        answers VAT registration (art. 316), VAT-on-collection, inactive status,
        split-VAT, and RO e-Factura register membership *as of* ``date`` (default
        today), plus general company data. CUIs ANAF has no data for come back in
        ``not_found``.
        """
        payload = _query_payload(
            cuis, date, cap=_BATCH_CAP_TVA, operation="lookup_taxpayers"
        )
        response = await self._request("POST", _TVA_PATH, json_body=payload)
        return _parse_lookup(response.content, TaxpayerLookup, "taxpayer lookup")

    async def lookup_efactura_register(
        self,
        cuis: Sequence[int | str],
        *,
        date: datetime.date | str | None = None,
    ) -> EfacturaRegisterLookup:
        """Query the Registrul RO e-Factura (opt-in register) for up to 100 CUIs.

        ANAF answers **HTTP 404 when no queried CUI has data**, with a regular
        ``found``/``notFound`` body — returned here as a normal (empty) lookup, not
        raised. For a plain "is this CUI e-Factura-registered" check, prefer
        ``lookup_taxpayers`` — its ``efactura_registered`` answers it alongside
        everything else.
        """
        payload = _query_payload(
            cuis, date, cap=_BATCH_CAP_TVA, operation="lookup_efactura_register"
        )
        response = await self._request(
            "POST", _EFACTURA_REGISTER_PATH, json_body=payload, tolerate=(404,)
        )
        if response.status_code == httpx.codes.NOT_FOUND:
            data = _json_or_none(response.content)
            if not (isinstance(data, dict) and ("found" in data or "notFound" in data)):
                # A genuine 404 (bad path, gateway), not the register's "no data".
                raise_for_status(response)
        return _parse_lookup(
            response.content, EfacturaRegisterLookup, "e-Factura register lookup"
        )

    async def lookup_farmers(
        self,
        cuis: Sequence[int | str],
        *,
        date: datetime.date | str | None = None,
    ) -> FarmerLookup:
        """Query the farmers' special-regime register (art. 315¹) for up to 500 CUIs.

        A CUI that is *not* in the register still comes back under ``found`` with
        ``registered is False`` — read membership from the boolean, not from
        presence in ``found``.
        """
        payload = _query_payload(
            cuis, date, cap=_BATCH_CAP_REGISTERS, operation="lookup_farmers"
        )
        response = await self._request("POST", _AGRIC_PATH, json_body=payload)
        return _parse_lookup(response.content, FarmerLookup, "RegAgric lookup")

    async def lookup_cult_entities(
        self,
        cuis: Sequence[int | str],
        *,
        date: datetime.date | str | None = None,
    ) -> CultLookup:
        """Query the cult-entities register for up to 500 CUIs at one date.

        Same conventions as ``lookup_farmers`` (membership is the ``registered``
        boolean); a future ``date`` is answered as of the current date by ANAF.
        """
        payload = _query_payload(
            cuis, date, cap=_BATCH_CAP_REGISTERS, operation="lookup_cult_entities"
        )
        response = await self._request("POST", _CULT_PATH, json_body=payload)
        return _parse_lookup(response.content, CultLookup, "RegCult lookup")

    async def get_financial_statement(
        self, cui: int | str, year: int
    ) -> FinancialStatement:
        """Fetch the public indicators of one CUI's annual financial statement.

        One CUI + one year per call (that is the API's shape). The indicator set
        varies by statement type; see :class:`~anafpy.public.models.FinancialStatement`.
        """
        params = {"an": str(year), "cui": str(_normalize_cui(cui))}
        response = await self._request("GET", _BILANT_PATH, params=params)
        body = response.content
        try:
            statement = FinancialStatement.model_validate(json.loads(body))
        except (ValueError, ValidationError) as exc:
            raise AnafResponseError(
                f"unrecognised bilant response: {as_text(body)[:200]}",
                status_code=200,
                body=as_text(body),
            ) from exc
        statement.raw = body
        return statement


def _json_or_none(body: bytes) -> Any:
    try:
        return json.loads(body)
    except ValueError:
        return None
