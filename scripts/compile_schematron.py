#!/usr/bin/env python
"""Pre-compile Schematron sources to standalone XSLT for use by SchematronValidator.

Requires ``saxonche`` (``uv sync --group validation`` or install manually).

The ISO Schematron pipeline XSLTs live in ``schemas/iso-schematron/`` (developer-only,
not shipped).  Compiled output goes into the package under
``src/anafpy/{efactura,etransport}/schematron/{version}/compiled/validation.xsl``.

Usage:
    uv run python scripts/compile_schematron.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISO_DIR = ROOT / "schemas" / "iso-schematron"

_INCLUDE_XSL = ISO_DIR / "iso_dsdl_include.xsl"
_ABSTRACT_XSL = ISO_DIR / "iso_abstract_expand.xsl"
_SVRL_XSL = ISO_DIR / "iso_svrl_for_xslt2.xsl"

_EFACTURA_SCH = (
    ROOT
    / "src"
    / "anafpy"
    / "efactura"
    / "schematron"
    / "1.0.9"
    / "EN16931-CIUS_RO-UBL-validation.sch"
)
_EFACTURA_OUT = (
    ROOT
    / "src"
    / "anafpy"
    / "efactura"
    / "schematron"
    / "1.0.9"
    / "compiled"
    / "validation.xsl"
)

_ETRANSPORT_SCH = (
    ROOT
    / "src"
    / "anafpy"
    / "etransport"
    / "schematron"
    / "2.0.2"
    / "eTransport-validation.sch"
)
_ETRANSPORT_OUT = (
    ROOT
    / "src"
    / "anafpy"
    / "etransport"
    / "schematron"
    / "2.0.2"
    / "compiled"
    / "validation.xsl"
)


def _check_iso_xsls() -> bool:
    missing = [p for p in (_INCLUDE_XSL, _ABSTRACT_XSL, _SVRL_XSL) if not p.exists()]
    if missing:
        print(f"Missing ISO Schematron XSLTs: {missing}", file=sys.stderr)
        print(
            "Download from https://github.com/Schematron/schematron to schemas/iso-schematron/",
            file=sys.stderr,
        )
        return False
    return True


def _xslt(proc: object, xsl_file: Path, src_file: Path | None = None, src_text: str | None = None) -> str:
    """Apply an XSLT stylesheet and return the result as a string."""
    import saxonche  # type: ignore[import-untyped]

    p: saxonche.PySaxonProcessor = proc  # type: ignore[assignment]
    xslt = p.new_xslt30_processor()
    exe = xslt.compile_stylesheet(stylesheet_file=str(xsl_file))
    if src_file is not None:
        result = exe.transform_to_string(source_file=str(src_file))
    else:
        assert src_text is not None
        with tempfile.NamedTemporaryFile(
            suffix=".xml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(src_text)
            tmp = f.name
        try:
            result = exe.transform_to_string(source_file=tmp)
        finally:
            import os
            os.unlink(tmp)
    if result is None:
        raise RuntimeError(f"XSLT produced no output: {xsl_file.name}")
    return result


def compile_etransport(proc: object) -> bool:
    """One-step compile: iso_svrl_for_xslt2.xsl applied directly (no includes)."""
    print("  Compiling e-Transport v2.0.2 (1 step)...")
    t0 = time.time()
    compiled = _xslt(proc, _SVRL_XSL, src_file=_ETRANSPORT_SCH)
    _ETRANSPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    _ETRANSPORT_OUT.write_text(compiled, encoding="utf-8")
    print(f"  OK: {_ETRANSPORT_OUT.relative_to(ROOT)} ({len(compiled)} chars, {time.time()-t0:.1f}s)")
    return True


def compile_efactura(proc: object) -> bool:
    """Three-step compile: include expansion → abstract expansion → code gen."""
    print("  Compiling e-Factura CIUS-RO 1.0.9 (3 steps, ~60s)...")
    t0 = time.time()
    step1 = _xslt(proc, _INCLUDE_XSL, src_file=_EFACTURA_SCH)
    step2 = _xslt(proc, _ABSTRACT_XSL, src_text=step1)
    compiled = _xslt(proc, _SVRL_XSL, src_text=step2)
    _EFACTURA_OUT.parent.mkdir(parents=True, exist_ok=True)
    _EFACTURA_OUT.write_text(compiled, encoding="utf-8")
    print(f"  OK: {_EFACTURA_OUT.relative_to(ROOT)} ({len(compiled)} chars, {time.time()-t0:.1f}s)")
    return True


def smoke_test() -> bool:
    """Quick import check: both compiled XSLTs must load without error."""
    print("  Smoke-testing compiled XSLTs...")
    import saxonche  # type: ignore[import-untyped]

    for path in (_EFACTURA_OUT, _ETRANSPORT_OUT):
        with saxonche.PySaxonProcessor(license=False) as proc:
            xslt = proc.new_xslt30_processor()
            xslt.compile_stylesheet(stylesheet_file=str(path))
    print("  OK.")
    return True


def main() -> int:
    if not _check_iso_xsls():
        return 1
    try:
        import saxonche  # type: ignore[import-untyped]
    except ImportError:
        print(
            "saxonche is required: uv add saxonche --group validation  (or pip install saxonche)",
            file=sys.stderr,
        )
        return 1

    ok = True
    with saxonche.PySaxonProcessor(license=False) as proc:
        ok = compile_etransport(proc) and ok
        ok = compile_efactura(proc) and ok

    if ok:
        smoke_test()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
