"""Filing status of uploaded declarations via ANAF's public StareD112 service.

``https://www.anaf.ro/StareD112/`` is ANAF's public "Vizualizare documente"
page: given the **upload index** (the number the portal returns on submission,
also the recipisa number) and the taxpayer's **CUI**, it answers with the
processing state of every document that CUI filed in the **last three months**
(capped at the **last 200** submissions). Despite the ``D112`` in the name it
covers all declaration forms. The service is **public and unauthenticated** —
no certificate, no OAuth, no session priming (cold POST live-confirmed
2026-07-16) — which is why status tracking lands here ahead of the automated
portal upload: the index from a manual portal filing is enough.

Wire facts (live-confirmed 2026-07-16, captures under
``docs/anaf-reference/_sources/stared112/``; reference:
``docs/anaf-reference/declaratii/stared112.md``):

* ``POST /StareD112/vizualizareStare.do`` (form-encoded ``ghiseu`` (``N`` =
  internet / ``Y`` = counter), ``id``, ``cui``) answers HTTP 200 HTML in all
  cases — a results table, a "no declaration identified" page, or a
  "Nu ati introdus un index valid" page for malformed input.
* A **valid (index, CUI) pair returns the whole recent list**, not just the
  queried document — the pair is knowledge-based access to the CUI's filings.
* ``GET /StareD112/ObtineRecipisa?numefisier=<index>.pdf`` serves the signed
  recipisa PDF; an unknown/expired index answers HTTP 200 with an **empty**
  ``application/pdf`` body. Receipts stay available **~60 days** from filing
  (rows older than that lose their download link but keep their status).

Per the error model, "no declaration identified" is a business outcome —
returned as :attr:`DeclarationStatusList.found` ``False``, never raised — while
an unrecognisable page raises :class:`~anafpy.exceptions.AnafResponseError`
(explicit over silently returning empty results).
"""

from __future__ import annotations

import datetime
import re
from enum import StrEnum
from html.parser import HTMLParser
from types import TracebackType
from typing import Self

import httpx
from pydantic import BaseModel

from .._transport.base import as_text, raise_for_status, strip_accents
from ..exceptions import AnafConfigError, AnafResponseError, AnafTransportError

__all__ = [
    "DeclarationDocument",
    "DeclarationState",
    "DeclarationStatusClient",
    "DeclarationStatusList",
]

_STARE_HOST = "https://www.anaf.ro"
_STATUS_PATH = "/StareD112/vizualizareStare.do"
_RECEIPT_PATH = "/StareD112/ObtineRecipisa"

#: Header of a results page: CUI + the three-month query window.
_FOUND_RE = re.compile(
    r"documente depuse pentru cui:\s*(\d+)\s*in perioada\s*"
    r"(\d{2}\.\d{2}\.\d{4})\s*/\s*(\d{2}\.\d{2}\.\d{4})"
)
#: Accent-stripped markers of the two non-result pages.
_NOT_FOUND_MARKER = "nu a fost identificata nicio declaratie"
_INVALID_INPUT_MARKER = "nu ati introdus un index valid"

_NOT_FOUND_MESSAGE = (
    "no declaration matches this index/CUI pair — the pair may be wrong, the "
    "declaration may be older than 3 months, or it may not be among the CUI's "
    "last 200 submissions"
)


class DeclarationState(StrEnum):
    """Processing state of a filed declaration, classified from ANAF's wording.

    The page documents exactly four states; anything unrecognised maps to
    :attr:`UNKNOWN` with the verbatim text preserved in
    :attr:`DeclarationDocument.state_text`.
    """

    PROCESSING = "processing"  # "In prelucrare" — check again later
    NOT_VALID = "not_valid"  # "nu este un document valid" — not registered at all
    VALIDATION_ERRORS = "validation_errors"  # errors in the recipisa; refile
    VALID = "valid"  # accepted; data forwarded to the beneficiary institutions
    UNKNOWN = "unknown"


#: Accent-stripped state markers, most specific first — ``NOT_VALID``'s wording
#: must win over ``VALID``'s.
_STATE_MARKERS = (
    ("in prelucrare", DeclarationState.PROCESSING),
    ("nu este un document valid", DeclarationState.NOT_VALID),
    ("erori de validare", DeclarationState.VALIDATION_ERRORS),
    ("documentul este valid", DeclarationState.VALID),
)


class DeclarationDocument(BaseModel):
    """One row of the StareD112 results table — one filed document."""

    index: str
    """Upload index (also the recipisa number)."""
    form: str
    """ANAF's document type as shown (e.g. ``D300``, ``F4109``)."""
    state: DeclarationState
    state_text: str
    """ANAF's state wording, verbatim."""
    registration: str
    """Registration line, verbatim (e.g. ``INTERNT-1100000001-2026 din 16.07.2026``)."""
    upload_date: datetime.date | None
    receipt_available: bool
    """Whether the page offered a recipisa download link (lapses ~60 days in)."""


class DeclarationStatusList(BaseModel):
    """Outcome of a status query.

    ``found`` mirrors the page shape: ``True`` carries the CUI's recent filings
    (all of them — the queried index is just the access key), ``False`` is the
    "no declaration identified" business outcome with ``message`` explaining
    the possible reasons.
    """

    found: bool
    cui: str
    period_start: datetime.date | None = None
    period_end: datetime.date | None = None
    documents: list[DeclarationDocument] = []
    message: str = ""

    def document(self, index: int | str) -> DeclarationDocument | None:
        """The row for *index*, if present."""
        wanted = str(index).strip()
        return next((d for d in self.documents if d.index == wanted), None)


class _PageScraper(HTMLParser):
    """Collect table rows (cell texts + recipisa-link flag) and the page text.

    The page is JSP-era HTML with nested layout tables; rather than model that,
    every ``<tr>``/``<td>`` run is collected and the caller keeps only rows that
    look like result rows (six cells, numeric index). An inner table's rows
    simply restart collection, so outer layout rows never survive the filter.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[list[str], bool]] = []
        self._text: list[str] = []
        self._cells: list[str] | None = None
        self._cell: list[str] | None = None
        self._receipt_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._flush_row()
            self._cells = []
        elif tag == "td":
            # The results table's header cells sit directly under <thead> with
            # no <tr> — tolerate a cell opening outside a row.
            if self._cells is None:
                self._cells = []
            self._flush_cell()
            self._cell = []
        elif tag == "a":
            href = next((value for name, value in attrs if name == "href"), None)
            if href and "ObtineRecipisa" in href:
                self._receipt_link = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self._flush_cell()
        elif tag in ("tr", "table", "thead"):
            self._flush_row()

    def handle_data(self, data: str) -> None:
        self._text.append(data)
        if self._cell is not None:
            self._cell.append(data)

    @property
    def text(self) -> str:
        """The page's whole text content, whitespace-normalized."""
        return " ".join(" ".join(self._text).split())

    def _flush_cell(self) -> None:
        if self._cell is not None and self._cells is not None:
            self._cells.append(" ".join(" ".join(self._cell).split()))
        self._cell = None

    def _flush_row(self) -> None:
        self._flush_cell()
        if self._cells:
            self.rows.append((self._cells, self._receipt_link))
        self._cells = None
        self._receipt_link = False


def _classify_state(text: str) -> DeclarationState:
    normalized = strip_accents(text)
    for marker, state in _STATE_MARKERS:
        if marker in normalized:
            return state
    return DeclarationState.UNKNOWN


def _parse_date(text: str) -> datetime.date | None:
    """Parse the page's two date shapes (``dd.mm.yyyy`` and ISO); lenient."""
    for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text.strip(), pattern).date()
        except ValueError:
            continue
    return None


def _document_from_row(
    cells: list[str], receipt_link: bool
) -> DeclarationDocument | None:
    """A result row is six cells with a numeric index; anything else is layout."""
    if len(cells) != 6 or not cells[0].isdigit():
        return None
    return DeclarationDocument(
        index=cells[0],
        form=cells[1],
        state=_classify_state(cells[2]),
        state_text=cells[2],
        registration=cells[3],
        upload_date=_parse_date(cells[5]),
        receipt_available=receipt_link,
    )


def _parse_status_page(html: str, *, queried_cui: str) -> DeclarationStatusList:
    scraper = _PageScraper()
    scraper.feed(html)
    scraper.close()
    text = scraper.text
    normalized = strip_accents(text)

    if match := _FOUND_RE.search(normalized):
        documents = [
            document
            for cells, receipt_link in scraper.rows
            if (document := _document_from_row(cells, receipt_link)) is not None
        ]
        return DeclarationStatusList(
            found=True,
            cui=match.group(1),
            period_start=_parse_date(match.group(2)),
            period_end=_parse_date(match.group(3)),
            documents=documents,
        )
    if _NOT_FOUND_MARKER in normalized:
        return DeclarationStatusList(
            found=False, cui=queried_cui, message=_NOT_FOUND_MESSAGE
        )
    if _INVALID_INPUT_MARKER in normalized:
        # Inputs are validated client-side, so reaching this page is unexpected.
        raise AnafResponseError(
            "StareD112 rejected the query input ('Nu ati introdus un index valid')",
            status_code=200,
            body=text[:500],
        )
    raise AnafResponseError(
        f"unrecognised StareD112 response: {text[:200]}",
        status_code=200,
        body=text[:500],
    )


def _digits(value: int | str, *, name: str, strip_ro: bool = False) -> str:
    """Coerce an index/CUI to the bare digit string the form expects."""
    text = str(value).strip()
    if strip_ro:
        text = text.upper().removeprefix("RO").strip()
    if not text.isdigit():
        raise AnafConfigError(f"invalid {name}: {value!r} (digits expected)")
    return text


class DeclarationStatusClient:
    """Checks filed declarations on ANAF's public StareD112 service.

    No credentials are needed (the service is public and unauthenticated); the
    client owns an ``httpx.AsyncClient`` (unless one is injected) and should be
    used as an async context manager so it is closed cleanly. Like the other
    discrete client methods, it does **no transport retry** — one call, one
    result-or-raise.
    """

    def __init__(
        self,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(timeout=timeout)

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

    async def check_status(
        self,
        index: int | str,
        cui: int | str,
        *,
        filed_at_counter: bool = False,
    ) -> DeclarationStatusList:
        """Query the processing status of a filed declaration.

        Args:
            index: the upload index for internet filings (the number the portal
                returned on submission — also the recipisa number), or the
                registration number for counter filings.
            cui: the taxpayer's fiscal code (an ``RO`` VAT prefix is tolerated).
            filed_at_counter: ``True`` when the document was filed at an ANAF
                counter (``ghiseu``) rather than online — *index* is then the
                registration number.

        Returns:
            A :class:`DeclarationStatusList`. When the pair matches, it carries
            **all** documents the CUI filed in the last three months (up to
            200), not just the queried one; ``found=False`` is the service's
            "no declaration identified" business outcome.

        Raises:
            AnafConfigError: *index*/*cui* is not a number.
            AnafTransportError: network failure.
            AnafResponseError: non-success HTTP, or a page shape this client
                does not recognise.
        """
        data = {
            "ghiseu": "Y" if filed_at_counter else "N",
            "id": _digits(index, name="index"),
            "cui": _digits(cui, name="cui", strip_ro=True),
        }
        try:
            response = await self._http.post(f"{_STARE_HOST}{_STATUS_PATH}", data=data)
        except httpx.HTTPError as exc:
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc
        raise_for_status(response)
        return _parse_status_page(response.text, queried_cui=data["cui"])

    async def download_receipt(self, index: int | str) -> bytes | None:
        """Download the signed recipisa PDF for an upload *index*.

        Returns:
            The PDF bytes, or ``None`` when no receipt is available — an
            unknown index, or one whose ~60-day availability window has lapsed
            (ANAF answers HTTP 200 with an empty PDF body for both).

        Raises:
            AnafConfigError: *index* is not a number.
            AnafTransportError: network failure.
            AnafResponseError: non-success HTTP, or a non-PDF body.
        """
        params = {"numefisier": f"{_digits(index, name='index')}.pdf"}
        try:
            response = await self._http.get(
                f"{_STARE_HOST}{_RECEIPT_PATH}", params=params
            )
        except httpx.HTTPError as exc:
            raise AnafTransportError(f"network error talking to ANAF: {exc}") from exc
        raise_for_status(response)
        if not response.content:
            return None
        if not response.content.startswith(b"%PDF"):
            raise AnafResponseError(
                "unrecognised ObtineRecipisa response (expected a PDF)",
                status_code=response.status_code,
                body=as_text(response.content)[:500],
            )
        return response.content
