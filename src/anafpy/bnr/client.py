"""Async client for BNR's published foreign-exchange reference rates.

The one non-ANAF source in anafpy (DESIGN.md §17). Romanian tax filings are
denominated in lei, so a foreign-currency invoice has to be converted before it
can be declared — e-Transport's ``value_ron``, e-Factura's BT-111, D301's
``curs_valutar``. BNR is who publishes the reference rate that conversion uses,
and this client is a **rate source, not a ruling**: it returns what BNR
published on a date. Which date a given filing must use is the caller's
question, not this module's answer.

BNR publishes static XML documents on ``curs.bnr.ro``, no auth and no key
(schema at ``https://curs.bnr.ro/xsd/nbrfxrates.xsd``):

- ``nbrfxrates.xml`` — the current rates (one day);
- ``nbrfxrates10days.xml`` — the last ten banking days;
- ``files/xml/years/nbrfxrates<YYYY>.xml`` — one year, back to 2005,
  regenerated daily so the current year reaches yesterday's close.

Two things shape the code. **Rates exist per banking day**, published just after
13:00, so a request for a weekend, a holiday, or this morning has no rate of its
own: :meth:`BnrClient.get_rates` resolves to the latest day *on or before* the
one asked for and reports that day in :attr:`~anafpy.bnr.models.FxRateSet.date`
— it never labels Friday's rate as Sunday's. And **BNR asks callers to cache**
rather than re-fetch, and to read these files instead of scraping the site
pages; hence the in-process cache and the smallest-sufficient document per
query (1.8 KB for today, 14 KB for the last fortnight, the 230 KB year archive
only for older dates).
"""

from __future__ import annotations

import asyncio
import datetime
import re
import time
from decimal import Decimal, InvalidOperation

import httpx2
from pydantic import ValidationError
from xsdata.exceptions import ParserError
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata_pydantic.bindings import XmlParser

from .._transport.base import ROMANIA_TZ, as_text
from .._transport.http import HttpClientBase
from ..exceptions import AnafConfigError, AnafResponseError
from .models import BASE_CURRENCY, Conversion, FxRate, FxRateSet
from .schema.nbrfxrates import DataSet

__all__ = ["BNR_FX_HOST", "BnrClient"]

#: Host of BNR's exchange-rate XML files. Separate from the site itself
#: (``www.bnr.ro``), which moved these files here and which BNR asks not to be
#: scraped for them.
BNR_FX_HOST = "https://curs.bnr.ro"

_CURRENT_PATH = "nbrfxrates.xml"
_TEN_DAYS_PATH = "nbrfxrates10days.xml"
_YEAR_PATH = "files/xml/years/nbrfxrates{year}.xml"

#: First year BNR publishes an archive for.
_FIRST_ARCHIVED_YEAR = 2005

#: How far back the ten-day file is worth trying: ten *banking* days is at most
#: two weeks of calendar plus holidays, and a miss only costs the year archive.
_TEN_DAYS_REACH = datetime.timedelta(days=18)

#: Parser guard. The largest real document is the year archive at ~230 KB;
#: anything past this is not a rate file and is refused rather than parsed.
_MAX_BODY = 16 * 1024 * 1024

#: BNR's target namespace as the generated models bind it, and the older spelling
#: the archives through 2025 are still served with. Same schema, two scheme
#: spellings; :func:`_canonical_namespace` folds the second into the first.
_NS_CANONICAL = "https://www.bnr.ro/xsd"
_NS_LEGACY = "http://www.bnr.ro/xsd"
_NS_DECLARATION = re.compile(rb"([\"'])http://www\.bnr\.ro/xsd\1")

#: Additions are tolerated, structure is not. An element or attribute BNR adds
#: must not take the client down (the rates around it are still correct), but a
#: document that no longer carries a Header/Body/Cube fails validation — and
#: :func:`_rate_sets` re-checks that rates actually arrived, so a namespace the
#: models do not know cannot degrade into a silently empty parse.
_PARSER = XmlParser(
    config=ParserConfig(
        fail_on_unknown_properties=False,
        fail_on_unknown_attributes=False,
    )
)


def _canonical_namespace(body: bytes) -> bytes:
    """Fold BNR's legacy ``http`` namespace onto the one the models bind.

    BNR serves two spellings of the same namespace — the year archives through
    2025 declare ``http://www.bnr.ro/xsd``, 2026 onwards ``https://…`` — and
    the generated models can only bind one. Only a namespace *declaration* is
    rewritten (a quoted, exact match); ``xsi:schemaLocation``, which points at
    ``curs.bnr.ro``, is a different string and is left alone.
    """
    return _NS_DECLARATION.sub(f'"{_NS_CANONICAL}"'.encode(), body)


def _rate_sets(dataset: DataSet, source_url: str) -> list[FxRateSet]:
    """Map the parsed wire document onto the domain models.

    The wire tier types rate values as ``str`` — BNR's XSD restricts a decimal
    with a pattern, which xsdata renders as text — so the ``Decimal`` conversion
    happens here, where a non-numeric value can be reported as the response
    error it is.
    """
    base = dataset.body.orig_currency or BASE_CURRENCY
    sets: list[FxRateSet] = []
    for cube in dataset.body.cube:
        rates: dict[str, FxRate] = {}
        for wire in cube.rate:
            currency = wire.currency.strip().upper()
            try:
                quoted = Decimal(wire.value.strip())
            except InvalidOperation as exc:
                raise AnafResponseError(
                    f"BNR rate for {currency or '?'} on {cube.date} is not a "
                    f"number: {wire.value!r}",
                    status_code=200,
                ) from exc
            if currency:
                rates[currency] = FxRate(
                    currency=currency,
                    quoted=quoted,
                    multiplier=wire.multiplier if wire.multiplier is not None else 1,
                )
        sets.append(
            FxRateSet(
                date=cube.date.to_date(),
                base_currency=base,
                rates=rates,
                source_url=source_url,
            )
        )
    if not any(entry.rates for entry in sets):
        raise AnafResponseError(
            f"BNR document at {source_url} parsed to no rates at all — the "
            "shape or the namespace has changed; re-vendor the XSD "
            "(scripts/generate_bnr.py)",
            status_code=200,
        )
    sets.sort(key=lambda entry: entry.date)
    return sets


def _as_date(value: datetime.date | str) -> datetime.date:
    """Coerce an ISO string to a date; a ``date`` passes through."""
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise AnafConfigError(f"invalid date: {value!r} (expected YYYY-MM-DD)") from exc


def _today() -> datetime.date:
    """Today in Romania — BNR's publication calendar, not the machine's."""
    return datetime.datetime.now(ROMANIA_TZ).date()


def _parse_document(body: bytes, source_url: str) -> list[FxRateSet]:
    """Read every ``<Cube>`` in a BNR rate document, oldest first.

    Parsing goes through the generated wire model
    (:mod:`anafpy.bnr.schema.nbrfxrates`, from the vendored XSD), after the
    namespace is canonicalised — see :func:`_canonical_namespace`.
    """
    if len(body) > _MAX_BODY:
        raise AnafResponseError(
            f"BNR document at {source_url} is {len(body)} bytes — refusing to "
            "parse; the largest real rate file is under 1 MB",
            status_code=200,
        )
    try:
        dataset = _PARSER.from_bytes(_canonical_namespace(body), DataSet)
    except (ParserError, ValidationError, SyntaxError) as exc:
        raise AnafResponseError(
            f"unrecognised BNR response from {source_url}: {as_text(body)[:200]}",
            status_code=200,
            body=as_text(body),
        ) from exc
    return _rate_sets(dataset, source_url)


def _latest_on_or_before(sets: list[FxRateSet], day: datetime.date) -> FxRateSet | None:
    """The most recent published set not after *day*, or ``None``."""
    candidates = [entry for entry in sets if entry.date <= day]
    return max(candidates, key=lambda entry: entry.date) if candidates else None


class BnrClient(HttpClientBase):
    """Reads BNR's published exchange-rate XML (``curs.bnr.ro``).

    No credentials, no test/prod split — like
    :class:`~anafpy.public.client.PublicClient`, but a different publisher.
    Use it as an async context manager so an owned client closes cleanly; an
    injected client must carry a non-empty ``base_url``.

    Fetched documents are cached in-process for ``cache_ttl`` seconds (BNR asks
    callers to store what they take rather than re-fetch it); pass ``0`` to
    disable. Concurrent misses share one request instead of racing.
    """

    _peer = "BNR"

    def __init__(
        self,
        *,
        http: httpx2.AsyncClient | None = None,
        timeout: float = 30.0,
        cache_ttl: float = 900.0,
    ) -> None:
        super().__init__(http=http, base_url=BNR_FX_HOST, timeout=timeout)
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, list[FxRateSet]]] = {}
        self._lock = asyncio.Lock()

    async def _document(self, path: str) -> list[FxRateSet]:
        """Fetch and parse one rate document, honouring the cache."""
        async with self._lock:
            now = time.monotonic()
            if (entry := self._cache.get(path)) is not None and now < entry[0]:
                return entry[1]
            response = await self._request_checked("GET", path)
            sets = _parse_document(response.content, f"{BNR_FX_HOST}/{path}")
            if self._cache_ttl > 0:
                self._cache[path] = (now + self._cache_ttl, sets)
            return sets

    def _sources_for(self, day: datetime.date) -> list[str]:
        """The documents to try for *day*, smallest first."""
        today = _today()
        paths: list[str] = []
        if day >= today:
            paths.append(_CURRENT_PATH)
        if day >= today - _TEN_DAYS_REACH:
            paths.append(_TEN_DAYS_PATH)
        paths.append(_YEAR_PATH.format(year=day.year))
        # A day in the first banking days of January predates its own archive.
        if day.year > _FIRST_ARCHIVED_YEAR:
            paths.append(_YEAR_PATH.format(year=day.year - 1))
        return paths

    async def get_rates(self, date: datetime.date | str | None = None) -> FxRateSet:
        """The reference rates in force for *date* (default: today in Romania).

        Rates are published per banking day just after 13:00, so the result is
        the latest set BNR published **on or before** *date* — read
        :attr:`~anafpy.bnr.models.FxRateSet.date` to see which day that was
        rather than assuming it is the one requested.

        Raises:
            AnafConfigError: *date* is unparseable or predates BNR's archive.
            AnafResponseError: BNR served something that is not a rate
                document, or published nothing on or before *date*.
        """
        day = _as_date(date) if date is not None else _today()
        if day.year < _FIRST_ARCHIVED_YEAR:
            raise AnafConfigError(
                f"BNR publishes exchange rates from {_FIRST_ARCHIVED_YEAR} "
                f"onwards; {day} is before that"
            )
        for path in self._sources_for(day):
            if found := _latest_on_or_before(await self._document(path), day):
                return found
        raise AnafResponseError(
            f"BNR published no reference rate on or before {day}",
            status_code=200,
        )

    async def convert(
        self,
        amount: Decimal | int | str,
        currency: str,
        *,
        date: datetime.date | str | None = None,
    ) -> Conversion:
        """Convert one amount to RON at *date*'s published rate.

        Convenience over :meth:`get_rates` plus
        :meth:`~anafpy.bnr.models.FxRateSet.convert`. To convert several
        amounts at one rate — an invoice's lines — fetch the set once and call
        its ``convert`` per amount, so every line demonstrably shares a rate.
        """
        rates = await self.get_rates(date)
        return rates.convert(amount, currency)
