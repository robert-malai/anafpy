"""Async client for ANAF's unauthenticated public web services.

These are the no-auth services on ``webservicesp.anaf.ro`` (see
``docs/anaf-reference/public/api.md``): the taxpayer/VAT registry, the RO e-Factura
register, the farmers' and cult-entities registers, public annual financial
statements — plus the **stateless e-Factura document services** ``validare``
(:meth:`PublicClient.validate_invoice`) and ``transformare``
(:meth:`PublicClient.render_invoice_pdf`), which are public, no-auth, and
**prod-only** (their ``test`` paths answer HTTP 404, live-confirmed 2026-07-02) —
they validate/render a document without filing anything. Key differences from the
OAuth clients:

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
from typing import Any

import httpx
from pydantic import ValidationError

from .._transport.base import (
    PUBLIC_HOST,
    ROMANIA_TZ,
    Service,
    as_text,
    normalize_cui,
    raise_for_status,
)
from .._transport.http import HttpClientBase
from ..exceptions import (
    AnafConfigError,
    AnafResponseError,
)
from .models import (
    CultLookup,
    EfacturaRegisterLookup,
    FarmerLookup,
    FinancialStatement,
    RegistryLookup,
    RemoteValidationResult,
    TaxpayerLookup,
    TransformStandard,
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

#: `validare`/`transformare` exist only under the `prod` segment (no test variant).
_EFACTURA_DOC_PREFIX = f"prod/{Service.EFACTURA.value}"

# ANAF wants the XML payload as a raw text/plain body (per the API PDF), despite it
# being XML.
_XML_BODY_HEADERS = {"Content-Type": "text/plain"}


def _normalize_cui(value: int | str) -> int:
    """Return the positive integer the public APIs expect.

    The shared normalizer preserves leading zeroes for services that need a
    string; this wrapper deliberately converts to the public API's integer form.
    """
    normalized = int(normalize_cui(value))
    if normalized <= 0:
        raise AnafConfigError(f"invalid CUI: {value!r}")
    return normalized


def _query_date(date: datetime.date | str | None) -> str:
    """Resolve the as-of date of a registry query (default: today on the
    register's own clock — Romania time — not the machine's)."""
    if date is None:
        return datetime.datetime.now(ROMANIA_TZ).date().isoformat()
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
    cod = data.get("cod") if isinstance(data, dict) else None
    # `cod` compared as text: ANAF's numeric/string typing is inconsistent across
    # services, so a stringly `"200"` must not read as an error.
    if cod is not None and str(cod) != "200":
        message = data.get("message") or text[:200]
        raise AnafResponseError(
            f"{operation} error: cod={cod} {message}",
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


class PublicClient(HttpClientBase):
    """Talks to ANAF's unauthenticated public services (``webservicesp.anaf.ro``).

    No credentials are needed; the client owns an ``httpx.AsyncClient`` unless
    one is injected. An injected client with an empty ``base_url`` adopts
    :data:`PUBLIC_HOST`; a non-empty one is preserved. Use it as an async
    context manager so owned clients close cleanly. Requests are paced at
    ``min_request_interval`` seconds (default 1.0, ANAF's stated limit); pass
    ``0`` to disable pacing and bring your own.
    """

    def __init__(
        self,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
        min_request_interval: float = 1.0,
    ) -> None:
        # No keep-alive: ANAF's public host resets pooled idle connections between
        # paced requests (RegAgric RSTs on reuse, live-observed 2026-07-02), and at
        # ≤1 req/s a fresh connection per request costs nothing.
        super().__init__(
            http=http,
            base_url=PUBLIC_HOST,
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=0),
        )
        self._pacer = _RequestPacer(min_request_interval)

    # -- transport -------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: list[dict[str, int | str]] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
        tolerate: tuple[int, ...] = (),
    ) -> httpx.Response:
        await self._pacer.wait()
        response = await self._request_http(
            method,
            path,
            params=params,
            json=json_body,
            content=content,
            headers=headers,
        )
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

    # -- stateless e-Factura document services (validare / transformare) --------------

    async def validate_invoice(
        self,
        xml: str | bytes,
        *,
        standard: TransformStandard = TransformStandard.INVOICE,
    ) -> RemoteValidationResult:
        """Validate e-Factura XML server-side (``validare/{std}``) without filing it.

        ANAF's own validator — authoritative, unlike any local pre-check. Pass
        ``standard=TransformStandard.CREDIT_NOTE`` for a credit note. An invalid
        document is returned as a :class:`RemoteValidationResult` with
        ``valid=False`` and the findings in ``messages``, not raised. Nothing is
        filed anywhere.
        """
        response = await self._post_document(f"validare/{standard.value}", xml)
        return _parse_validate(response.content)

    async def render_invoice_pdf(
        self,
        xml: str | bytes,
        *,
        standard: TransformStandard = TransformStandard.INVOICE,
        validate: bool = True,
    ) -> bytes:
        """Render e-Factura XML to a PDF (``transformare/{std}``).

        ``validate=False`` skips ANAF's validation (it then does not guarantee the
        PDF — use it for documents that already passed validation at filing). A
        body that cannot be rendered still answers HTTP 200, with a JSON error
        payload instead of PDF bytes; callers decide how strictly to check.
        """
        path = f"transformare/{standard.value}"
        if not validate:
            path += "/DA"
        response = await self._post_document(path, xml)
        return response.content

    async def _post_document(self, path: str, xml: str | bytes) -> httpx.Response:
        body = xml.encode("utf-8") if isinstance(xml, str) else xml
        return await self._request(
            "POST",
            f"{_EFACTURA_DOC_PREFIX}/{path}",
            content=body,
            headers=_XML_BODY_HEADERS,
        )


def _json_or_none(body: bytes) -> Any:
    try:
        return json.loads(body)
    except ValueError:
        return None


def _parse_validate(body: bytes) -> RemoteValidationResult:
    try:
        data = json.loads(body)
        state = data["stare"]
    except (ValueError, TypeError, KeyError) as exc:
        # Be explicit rather than inventing an outcome for an unknown shape.
        raise AnafResponseError(
            f"unrecognised validare response: {as_text(body)[:200]}",
            status_code=200,
            body=as_text(body),
        ) from exc
    messages = [
        str(m.get("message", m)) if isinstance(m, dict) else str(m)
        for m in data.get("Messages") or []
    ]
    trace_id = data.get("trace_id")
    return RemoteValidationResult(
        valid=str(state).strip().lower() == "ok",
        messages=messages,
        trace_id=str(trace_id) if trace_id is not None else None,
        raw=body,
    )
