"""Local Schematron pre-validation (``anafpy[validation]`` extra).

Applies a pre-compiled XSLT (produced from a Schematron source by
``scripts/compile_schematron.py``) to an XML document and parses the
Schematron Validation Report Language (SVRL) output into typed
:class:`ValidationFinding` objects.

This is a **local pre-filter only** — ANAF's server is the authoritative
validator.  The compiled XSLTs are vendored; ``saxonche`` (Saxon-C HE) is the
only runtime dependency (guarded by the ``anafpy[validation]`` extra).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

__all__ = ["SchematronValidator", "ValidationFinding", "ValidationResult"]

_SVRL_NS = "http://purl.oclc.org/dsdl/svrl"
_SVRL_ASSERT = f"{{{_SVRL_NS}}}failed-assert"
_SVRL_REPORT = f"{{{_SVRL_NS}}}successful-report"
_SVRL_TEXT = f"{{{_SVRL_NS}}}text"


class ValidationFinding(BaseModel):
    """One Schematron assertion failure or diagnostic firing."""

    rule_id: str | None = None
    message: str
    location: str | None = None
    severity: Literal["error", "warning", "info"] = "error"


class ValidationResult(BaseModel):
    """Aggregated result of a Schematron validation run."""

    findings: list[ValidationFinding] = []
    raw_svrl: bytes = b""

    @property
    def is_valid(self) -> bool:
        """True when there are no error-severity findings."""
        return not any(f.severity == "error" for f in self.findings)


class SchematronValidator:
    """Validates XML documents against a pre-compiled Schematron XSLT.

    Construct from a ``.xsl`` path produced by ``scripts/compile_schematron.py``.
    The Saxon processor and compiled stylesheet are initialised on the first
    :meth:`validate` call and reused for subsequent calls.

    Requires the ``anafpy[validation]`` extra (``saxonche``).
    """

    def __init__(self, compiled_xsl: Path | str) -> None:
        self._xsl_path = Path(compiled_xsl)
        self._proc: object = None  # saxonche.PySaxonProcessor, alive for lifetime
        self._executable: object = None  # saxonche.PyXsltExecutable

    def _ensure_ready(self) -> None:
        if self._executable is not None:
            return
        try:
            import saxonche
        except ImportError as exc:
            raise ImportError(
                "Schematron validation requires the anafpy[validation] extra; "
                "install with: pip install 'anafpy[validation]'"
            ) from exc
        if not self._xsl_path.exists():
            raise FileNotFoundError(
                f"Compiled Schematron XSLT not found: {self._xsl_path}\n"
                "Run: uv run python scripts/compile_schematron.py"
            )
        proc = saxonche.PySaxonProcessor(license=False)
        self._proc = proc
        xslt = proc.new_xslt30_processor()
        self._executable = xslt.compile_stylesheet(stylesheet_file=str(self._xsl_path))

    def validate(self, xml: str | bytes) -> ValidationResult:
        """Validate an XML document supplied as a string or bytes.

        Returns a :class:`ValidationResult`; never raises for *business* rule
        failures — those are findings.  Saxon errors (malformed XML, missing
        files) propagate as exceptions.
        """
        self._ensure_ready()
        xml_text = (
            xml if isinstance(xml, str) else xml.decode("utf-8", errors="replace")
        )
        # parse_xml avoids writing a temp file; the node is owned by proc.
        import saxonche

        proc: saxonche.PySaxonProcessor = self._proc
        node = proc.parse_xml(xml_text=xml_text)
        svrl_str: str | None = self._executable.transform_to_string(  # type: ignore[attr-defined]
            xdm_node=node
        )
        if not svrl_str:
            return ValidationResult()
        svrl_bytes = svrl_str.encode("utf-8")
        return ValidationResult(findings=_parse_svrl(svrl_bytes), raw_svrl=svrl_bytes)

    def validate_file(self, path: Path | str) -> ValidationResult:
        """Validate an XML file at *path*."""
        self._ensure_ready()
        svrl_str: str | None = self._executable.transform_to_string(  # type: ignore[attr-defined]
            source_file=str(path)
        )
        if not svrl_str:
            return ValidationResult()
        svrl_bytes = svrl_str.encode("utf-8")
        return ValidationResult(findings=_parse_svrl(svrl_bytes), raw_svrl=svrl_bytes)


def _severity(elem: ET.Element, tag: str) -> Literal["error", "warning", "info"]:
    role = (elem.get("role") or "").lower()
    if "warn" in role:
        return "warning"
    if "info" in role or "info" in (elem.get("flag") or "").lower():
        return "info"
    # successful-report = diagnostic / warning by default; failed-assert = error
    if tag == _SVRL_REPORT:
        return "warning"
    return "error"


def _parse_svrl(svrl: bytes) -> list[ValidationFinding]:
    root = ET.fromstring(svrl)
    findings: list[ValidationFinding] = []
    for child in root.iter():
        tag = child.tag
        if tag not in (_SVRL_ASSERT, _SVRL_REPORT):
            continue
        text_el = child.find(_SVRL_TEXT)
        message = (text_el.text or "").strip() if text_el is not None else ""
        findings.append(
            ValidationFinding(
                rule_id=child.get("id"),
                message=message,
                location=child.get("location"),
                severity=_severity(child, tag),
            )
        )
    return findings
