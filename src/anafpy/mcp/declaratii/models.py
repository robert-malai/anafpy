"""Typed inputs and results for the declaration MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...declaratii.models import DukFinding
from ..gate import XmlInput

__all__ = [
    "DeclarationXmlInput",
    "NrEvidResult",
    "ReceiptResult",
    "RenderResult",
    "SignResult",
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
    """The composed 23-character D300 payment-evidence number."""

    nr_evid: str
    tip_decont: str
    month: int
    year: int


class ReceiptResult(BaseModel):
    """Outcome of ``declaratie_recipisa``. ``pdf_path`` is set only when ``ok``."""

    ok: bool
    index: str
    pdf_path: str | None = None
    message: str = ""
