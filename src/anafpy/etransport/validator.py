"""e-Transport local Schematron validator (``anafpy[validation]`` extra).

Ships the e-Transport v2.0.2 (2024-08-12) pre-compiled XSLT.  Run
``scripts/compile_schematron.py`` to regenerate after updating the source.
"""

from __future__ import annotations

from pathlib import Path

from ..validation import SchematronValidator

__all__ = ["create_validator"]

_SCHEMATRON_DIR = Path(__file__).parent / "schematron"
_DEFAULT_VERSION = "2.0.2"


def create_validator(version: str = _DEFAULT_VERSION) -> SchematronValidator:
    """Return a :class:`~anafpy.validation.SchematronValidator` for the given
    e-Transport Schematron *version*.

    Requires the ``anafpy[validation]`` extra.  The Saxon processor is
    initialised lazily on the first
    :meth:`~anafpy.validation.SchematronValidator.validate` call.
    """
    xsl = _SCHEMATRON_DIR / version / "compiled" / "validation.xsl"
    if not xsl.exists():
        available = _available()
        raise ValueError(
            f"No compiled e-Transport schematron for version {version!r}. "
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
