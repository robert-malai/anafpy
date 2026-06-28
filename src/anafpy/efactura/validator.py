"""e-Factura local Schematron validator (``anafpy[validation]`` extra).

Ships the CIUS-RO 1.0.9 pre-compiled XSLT (EN 16931 + BR-RO rules for UBL
invoices and credit notes).  Run ``scripts/compile_schematron.py`` to regenerate
the compiled XSLT after updating the source ``.sch`` files.
"""

from __future__ import annotations

from pathlib import Path

from ..validation import SchematronValidator

__all__ = ["create_validator"]

_SCHEMATRON_DIR = Path(__file__).parent / "schematron"
_DEFAULT_VERSION = "1.0.9"


def create_validator(version: str = _DEFAULT_VERSION) -> SchematronValidator:
    """Return a :class:`~anafpy.validation.SchematronValidator` for CIUS-RO *version*.

    Requires the ``anafpy[validation]`` extra.  The Saxon processor is
    initialised lazily on the first
    :meth:`~anafpy.validation.SchematronValidator.validate` call.
    """
    xsl = _SCHEMATRON_DIR / version / "compiled" / "validation.xsl"
    if not xsl.exists():
        available = _available()
        raise ValueError(
            f"No compiled CIUS-RO schematron for version {version!r}. "
            f"Available: {available}. "
            "Run: uv run python scripts/compile_schematron.py"
        )
    return SchematronValidator(xsl)


def _available() -> list[str]:
    if not _SCHEMATRON_DIR.exists():
        return []
    return sorted(
        d.name
        for d in _SCHEMATRON_DIR.iterdir()
        if d.is_dir() and (d / "compiled" / "validation.xsl").exists()
    )
