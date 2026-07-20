"""Typed inputs and results for the declaration MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...declaratii.models import DukFinding
from ..gate import XmlInput

__all__ = [
    "DeclarationXmlInput",
    "NrEvidResult",
    "PortalLoginResult",
    "PortalStatusResult",
    "PreparedUpload",
    "ReceiptResult",
    "RenderResult",
    "SignResult",
    "UploadSubmitResult",
    "ValidationResult",
]


class DeclarationXmlInput(XmlInput):
    """A tax declaration as XML — exactly one of ``xml`` / ``path``.

    Author the XML from the form's XSD (attributes on a single root element for
    the D300 family); compute ``nr_evid`` with ``declaratie_nr_evid``, never by
    hand.
    """

    xml: str | None = Field(
        default=None, description="The declaration as XML text (a single root element)."
    )
    path: str | None = Field(
        default=None, description="Path to a declaration XML file."
    )


class ValidationResult(BaseModel):
    """Outcome of ``declaratie_validate`` — DUKIntegrator's verdict, verbatim.

    ``ok=false`` carries the blocking errors in ``findings``. ``ok=true`` means
    valid, but ``warnings`` may still hold DUK's informational notices (e.g.
    D700's "will be processed at the tax office" atentionare) — relay them, do
    not treat them as failure.
    """

    ok: bool
    form: str
    findings: list[DukFinding] = []
    warnings: list[DukFinding] = []
    message: str = ""


class RenderResult(BaseModel):
    """Outcome of ``declaratie_render``. ``pdf_path`` is set only when ``ok``.

    On success ``warnings`` may still hold DUK's informational notices (the
    document is validated before rendering).
    """

    ok: bool
    form: str
    findings: list[DukFinding] = []
    warnings: list[DukFinding] = []
    pdf_path: str | None = None
    message: str = ""


class SignResult(BaseModel):
    """Outcome of ``declaratie_sign``.

    ``signed`` is ``False`` (with ``guidance``) on any non-exceptional failure —
    a dismissed/timed-out approval, a missing certificate, a name collision — so
    the model can relay the reason and retry.
    """

    signed: bool
    pdf_path: str | None = None
    chain_complete: bool = False
    guidance: str | None = None


class NrEvidResult(BaseModel):
    """The composed 23-character ``nr_evid`` payment-evidence number.

    ``form`` echoes the declaration it was composed for; the per-form inputs
    that were used (``tip_decont`` for D300, ``cod_oblig``/``scadenta`` for
    D100/D710/D101) are echoed back for traceability, ``None`` when they do
    not apply.
    """

    nr_evid: str
    form: str
    month: int
    year: int
    tip_decont: str | None = None
    cod_oblig: str | None = None
    scadenta: str | None = None


class ReceiptResult(BaseModel):
    """Outcome of ``declaratie_recipisa``. ``pdf_path`` is set only when ``ok``."""

    ok: bool
    index: str
    pdf_path: str | None = None
    message: str = ""


class PortalLoginResult(BaseModel):
    """Outcome of ``declaratie_portal_login``.

    ``logged_in`` is ``False`` (with ``guidance``) on any non-exceptional
    failure — a missing ``confirm``, no certificate selected, a dismissed or
    timed-out 2FA approval, ANAF-side flakiness — mirroring ``spv_login``'s
    contract so the model can relay the reason and retry with the user's
    go-ahead.
    """

    logged_in: bool
    identity: str | None = None
    guidance: str | None = None


class PortalStatusResult(BaseModel):
    """Outcome of ``declaratie_portal_status`` — the no-2FA session probe."""

    session_active: bool
    detail: str = ""
    next_step: str | None = None


class PreparedUpload(BaseModel):
    """STEP-1 result of ``declaratie_prepare``: the filing gate's token.

    ``valid`` is ``False`` (and ``confirmation_token`` ``None``) only when the
    signed PDF could not be read. ``looks_signed`` is a cheap local sanity
    check (an embedded PKCS#7 signature was detected) — informational, never
    withholding the token; the portal's own verdict is authoritative. Pass the
    token (with the *same* file and ``filename``) to ``declaratie_submit``.
    """

    valid: bool
    confirmation_token: str | None = None
    pdf_path: str | None = None
    filename: str | None = None
    size_bytes: int | None = None
    looks_signed: bool | None = None
    message: str = ""


class UploadSubmitResult(BaseModel):
    """STEP-2 result of ``declaratie_submit``.

    ``accepted`` mirrors the portal's answer: ``True`` with ``upload_index``
    on the success page, ``False`` with ``reason`` on the known rejection
    page, and ``None`` when the page was not recognised (check
    ``declaratie_status`` before assuming either way).
    """

    accepted: bool | None = False
    upload_index: str | None = None
    reason: str | None = None
    message: str = ""
