#!/usr/bin/env python
"""Regenerate the UBL 2.1 Pydantic models from the vendored OASIS XSDs.

The generated package (`anafpy.efactura.ubl`) is the e-Factura client's public model
surface. Generation is scoped to the Invoice + CreditNote document roots, so xsdata
emits only their transitive closure rather than all ~65 UBL document types.

Usage:
    uv run python scripts/generate_ubl.py

Requires the ``codegen`` dependency group (``uv sync --group codegen``).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAINDOC = ROOT / "schemas" / "ubl-2.1" / "maindoc"
# The maindoc dir holds only the two e-Factura roots; pointing xsdata at it generates
# exactly their transitive closure (Invoice + CreditNote), nothing else.
ROOTS = (MAINDOC / "UBL-Invoice-2.1.xsd", MAINDOC / "UBL-CreditNote-2.1.xsd")
OUT_PACKAGE = "anafpy.efactura.ubl"
OUT_DIR = ROOT / "src" / "anafpy" / "efactura" / "ubl"

# xsdata-pydantic 24.5 emits a duplicated `default=None` for the `xs:any` wildcard
# fields in the XAdES schema (the `include: Any` "Ignore" fields), producing a Python
# syntax error. Collapse the duplicate. See module docstring / schemas/README.md.
_DUP_DEFAULT = re.compile(r"default=None,\s*\n\s*default=None,")


def _fixup_generated() -> int:
    """Repair the duplicated-`default` codegen bug. Returns the number of fixes."""
    fixes = 0
    for path in OUT_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        patched, n = _DUP_DEFAULT.subn("default=None,", text)
        if n:
            path.write_text(patched, encoding="utf-8")
            fixes += n
    return fixes


def main() -> int:
    missing = [p for p in ROOTS if not p.exists()]
    if missing:
        print(f"Missing vendored XSDs: {missing}", file=sys.stderr)
        return 1

    # Start from a clean slate so removed types don't linger.
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    cmd = [
        "xsdata",
        "generate",
        "--package",
        OUT_PACKAGE,
        "--output",
        "pydantic",
        "--structure-style",
        "filenames",
        "--relative-imports",
        str(MAINDOC),
    ]
    # cwd=src so the dotted package maps onto src/anafpy/efactura/ubl/. xsdata returns
    # non-zero when its own ruff-format pass trips over the codegen bug above; the
    # files are still written, so we repair and re-format them ourselves below.
    subprocess.run(cmd, cwd=ROOT / "src", check=False)

    if not OUT_DIR.exists():
        print("xsdata produced no output", file=sys.stderr)
        return 1

    fixes = _fixup_generated()
    print(f"Applied {fixes} duplicate-default fixup(s).")

    subprocess.run(["ruff", "check", "--fix", "--quiet", str(OUT_DIR)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(OUT_DIR)], check=False)

    # Smoke-test: the package must import and expose both document roots.
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            "from anafpy.efactura.ubl.maindoc import Invoice, CreditNote",
        ],
        cwd=ROOT / "src",
        check=False,
    )
    if check.returncode != 0:
        print("Generated package failed to import", file=sys.stderr)
        return 1
    print("OK: anafpy.efactura.ubl.maindoc imports Invoice and CreditNote.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
