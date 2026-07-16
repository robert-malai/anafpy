"""Value types for declaration filing-status tracking (StareD112).

The wire reference is ``docs/anaf-reference/declaratii/stared112.md``; the
client and page parsing live in :mod:`.status`. Like the SPV nomenclature,
:class:`DeclarationState` keeps **ANAF's verbatim Romanian wording as the enum
value** (the page documents exactly four states) and carries a one-line English
:attr:`~DeclarationState.description` — the enum-with-attributes pattern shared
with :class:`anafpy.spv.models.ReportType`, where a member declared without a
description fails at import time.
"""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel

from .._transport.base import strip_accents

__all__ = [
    "DeclarationDocument",
    "DeclarationState",
    "DeclarationStatusList",
]


class DeclarationState(StrEnum):
    """Processing state of a filed declaration, in ANAF's own words.

    Values are the four state wordings the StareD112 results page documents,
    **verbatim Romanian** (diacritics included, trailing period dropped);
    :attr:`description` is the English rendering of the page's explanation.
    Classification is :meth:`classify` — accent-insensitive substring matching,
    so wire text with or without diacritics (ANAF emits both) and with trailing
    detail resolves to the same member. Anything unrecognised maps to
    :attr:`UNKNOWN` — the one synthetic member (its value is not ANAF wording) —
    with the verbatim text preserved in
    :attr:`~DeclarationDocument.state_text`.
    """

    #: One-line English rendering of ANAF's explanation of the state.
    description: str

    def __new__(cls, value: str, description: str) -> Self:
        member = str.__new__(cls, value)
        member._value_ = value
        member.description = description
        return member

    PROCESSING = (
        # ANAF's page writes this one without the diacritic (unlike "Fişierul").
        "In prelucrare",
        "Still processing on ANAF's central servers — check again later",
    )
    NOT_VALID = (
        "Fişierul depus nu este un document valid",
        "Failed pre-validation (unknown form / unsigned / the signature has no "
        "filing right for the CIF / no reporting period / no XML attached) — "
        "NOT registered; fix the document and refile",
    )
    VALIDATION_ERRORS = (
        "Documentul are erori de validare",
        "Validation errors, detailed in the recipisa — fix them and refile",
    )
    VALID = (
        "Documentul este valid",
        "Accepted; the data is forwarded to the beneficiary institutions",
    )
    UNKNOWN = (
        "unknown",
        "anafpy's fallback for wording it does not recognise — read the "
        "document's state_text",
    )

    @classmethod
    def classify(cls, text: str) -> DeclarationState:
        """The member whose wording appears in *text* (accent-insensitively).

        The full sentences are mutually non-overlapping (``NOT_VALID`` does not
        contain ``VALID``'s "documentul este valid"), so declaration order does
        not matter; no match yields :attr:`UNKNOWN`.
        """
        normalized = strip_accents(text)
        for member in cls:
            if member is not cls.UNKNOWN and strip_accents(member.value) in normalized:
                return member
        return cls.UNKNOWN


class DeclarationDocument(BaseModel):
    """One row of the StareD112 results table — one filed document."""

    index: str
    """Upload index (also the recipisa number)."""
    form: str
    """ANAF's document type as shown (e.g. ``D300``, ``F4109``)."""
    state: DeclarationState
    state_text: str
    """ANAF's state wording, verbatim as served (casing/diacritics/detail)."""
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
