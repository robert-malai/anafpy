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

import httpx
from parsel import Selector

from .._transport.base import as_text, normalize_cui, raise_for_status
from .._transport.http import HttpClientBase
from ..exceptions import AnafConfigError, AnafResponseError
from ._html import strip_accents, whole_text
from .models import DeclarationDocument, DeclarationState, DeclarationStatusList

__all__ = ["DeclarationStatusClient"]

_STARE_HOST = "https://www.anaf.ro"
_STATUS_PATH = "StareD112/vizualizareStare.do"
_RECEIPT_PATH = "StareD112/ObtineRecipisa"

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
        state=DeclarationState.classify(cells[2]),
        state_text=cells[2],
        registration=cells[3],
        upload_date=_parse_date(cells[5]),
        receipt_available=receipt_link,
    )


def _parse_status_page(html: str, *, queried_cui: str) -> DeclarationStatusList:
    page = Selector(text=html)
    text = whole_text(page)
    normalized = strip_accents(text)

    if match := _FOUND_RE.search(normalized):
        # The page is JSP-era HTML with nested layout tables; rather than model
        # that, every <tr> is considered and only rows that look like result
        # rows (six direct cells, numeric index) survive. Direct-child ./td
        # keeps an outer layout row's cell (which stringifies its whole nested
        # table) from being mistaken for data — the filter drops it.
        documents = [
            document
            for row in page.css("tr")
            if (
                document := _document_from_row(
                    [whole_text(cell) for cell in row.xpath("./td")],
                    bool(row.xpath(".//a[contains(@href, 'ObtineRecipisa')]")),
                )
            )
            is not None
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


def _digits(value: int | str, *, name: str) -> str:
    """Coerce an internet upload index to the bare digit string expected."""
    text = str(value).strip()
    if not text.isdigit():
        raise AnafConfigError(f"invalid {name}: {value!r} (digits expected)")
    return text


def _counter_registration(value: int | str) -> str:
    """Preserve an ANAF-counter registration number, requiring only non-empty."""
    text = str(value).strip()
    if not text:
        raise AnafConfigError("invalid index: a registration number is required")
    return text


class DeclarationStatusClient(HttpClientBase):
    """Checks filed declarations on ANAF's public StareD112 service.

    No credentials are needed (the service is public and unauthenticated); the
    client owns an ``httpx.AsyncClient`` unless one is injected. An injected
    client with an empty ``base_url`` adopts the StareD112 host; a non-empty
    one is preserved. Use it as an async context manager so owned clients close
    cleanly. Like the other discrete client methods, it does **no transport
    retry** — one call, one result-or-raise.
    """

    def __init__(
        self,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(http=http, base_url=_STARE_HOST, timeout=timeout)

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
            AnafConfigError: *cui* or an internet *index* is not numeric, or a
                counter registration number is empty.
            AnafTransportError: network failure.
            AnafResponseError: non-success HTTP, or a page shape this client
                does not recognise.
        """
        data = {
            "ghiseu": "Y" if filed_at_counter else "N",
            "id": (
                _counter_registration(index)
                if filed_at_counter
                else _digits(index, name="index")
            ),
            "cui": normalize_cui(cui),
        }
        response = await self._request_http("POST", _STATUS_PATH, data=data)
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
        response = await self._request_http("GET", _RECEIPT_PATH, params=params)
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
