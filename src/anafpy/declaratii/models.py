"""Value types shared by declaration validation, signing, filing, and status.

This module remains importable without the optional ``declaratii`` extra:
these are plain Pydantic/domain values and never import pyHanko.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel

from .._transport.base import DescribedStrEnum, strip_accents

__all__ = [
    "DeclarationDocument",
    "DeclarationState",
    "DeclarationStatusList",
    "DukFeed",
    "DukFeedEntry",
    "DukFinding",
    "DukInstallReport",
    "DukResult",
    "PdfSignResult",
    "PortalUploadResult",
]


class DukFinding(BaseModel):
    """One DUK finding: an ``E:``/``F:`` error, or a ``W:``/``A:`` warning.

    ``severity`` is ``"error"`` (``E:``/``F:`` — blocking) or ``"warning"``
    (``W:`` warning / ``A:`` atentionare — informational).
    """

    severity: str
    message: str


class DukResult(BaseModel):
    """Outcome of a DUK validation/render run, judged by its err file.

    ``ok`` is ``True`` on a clean run and on a **warning-only** run (findings
    present but none of ``severity == "error"`` — e.g. D700, which always emits
    an ``A:`` atentionare). Warnings still ride ``findings`` so a caller can act
    on them; check :attr:`warnings` / :attr:`errors` to split them. ``raw`` is
    the err file verbatim; on a failure with **no parseable findings** (the
    empty err file a broken/mis-versioned dist leaves behind) it also carries a
    bounded tail of the process stdout/stderr — the only diagnostics DUK leaves
    in those modes.
    """

    ok: bool
    findings: list[DukFinding]
    raw: str

    @property
    def errors(self) -> list[DukFinding]:
        """The blocking findings (``severity == "error"``)."""
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[DukFinding]:
        """The informational findings (``severity == "warning"``)."""
        return [f for f in self.findings if f.severity == "warning"]


class DukFeedEntry(BaseModel):
    """One form's entry in ANAF's DUKIntegrator update feed.

    The feed names a container element after the form (``<D300>``) holding the
    validator/PDF jar versions and the URLs to fetch them from. Every one of
    the 173 entries carries the full set (live shape, 2026-07-23).
    """

    form: str
    validator_version: str
    pdf_version: str
    validator_url: str
    pdf_url: str
    history_url: str


class DukFeed(BaseModel):
    """ANAF's ``versiuni.xml`` — everything needed to assemble a dist.

    The feed carries not just the per-form jars but the **whole distribution**:
    the core jar (``zJars``), the shared libraries (``iJars`` + ``sJars``), and
    the ``config/`` files (``cFisiere``). Fields here are named for where a
    file lands rather than for the feed element it came from, since placement
    is what assembly needs. The GUI updater's own jar (``dJars``), the Windows
    help file, and the documentation set are deliberately not carried — a
    headless dist has no use for them.
    """

    core_version: str
    root_jars: list[str]
    lib_jars: list[str]
    config_files: list[str]
    forms: dict[str, DukFeedEntry]

    @property
    def versions(self) -> dict[str, str]:
        """Per-form validator versions — the staleness-comparison projection."""
        return {form: entry.validator_version for form, entry in self.forms.items()}


class DukInstallReport(BaseModel):
    """What one dist install/update actually changed.

    ``forms_updated`` maps a form to its ``"<old> -> <new>"`` transition;
    ``forms_unchanged`` lists the forms already at the feed's version (skipped
    unless forced). ``smoke_ok`` is the post-install liveness verdict — see
    :func:`~anafpy.declaratii.dukdist.smoke_test`; ``None`` means the check was
    not run.
    """

    duk_dir: str
    core_version: str
    core_files: int
    forms_installed: dict[str, str]
    forms_updated: dict[str, str]
    forms_unchanged: list[str]
    offline_mode: bool
    java_version: str | None = None
    smoke_ok: bool | None = None
    smoke_detail: str | None = None


class PortalUploadResult(BaseModel):
    """Outcome of one declaration-portal upload POST."""

    accepted: bool | None
    upload_index: str | None = None
    reason: str | None = None
    html: str


class PdfSignResult(BaseModel):
    """A signed PDF plus whether the leaf's direct issuer was embedded.

    ``chain_complete=True`` means exactly that the leaf's **direct** issuer
    certificate was resolved (via the AIA URL) and embedded in the CMS. Deeper
    intermediates are never chased, so on a hierarchy with more than one
    intermediate the embedded chain still stops at the direct issuer.
    """

    pdf: bytes
    chain_complete: bool
    warning: str | None = None


class DeclarationState(DescribedStrEnum):
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
