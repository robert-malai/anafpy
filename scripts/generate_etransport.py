#!/usr/bin/env python
"""Regenerate the e-Transport Pydantic models from the vendored ANAF XSD.

The generated package (``anafpy.etransport.schema``) is the typed model for transport
declaration XML.  The XSD is ANAF-proprietary (not UBL); the single document root is
``eTransport`` of type ``eTransportType``.

Usage:
    uv run python scripts/generate_etransport.py

Requires the ``codegen`` dependency group (``uv sync --group codegen``).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XSD = ROOT / "schemas" / "etransport" / "schema_ETR_v2_20230126.xsd"
OUT_PACKAGE = "anafpy.etransport.schema"
OUT_DIR = ROOT / "src" / "anafpy" / "etransport" / "schema"


def main() -> int:
    if not XSD.exists():
        print(f"Missing vendored XSD: {XSD}", file=sys.stderr)
        return 1

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
        str(XSD),
    ]
    subprocess.run(cmd, cwd=ROOT / "src", check=False)

    if not OUT_DIR.exists():
        print("xsdata produced no output", file=sys.stderr)
        return 1

    subprocess.run(["ruff", "check", "--fix", "--quiet", str(OUT_DIR)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(OUT_DIR)], check=False)

    check = subprocess.run(
        [
            sys.executable,
            "-c",
            "from anafpy.etransport.schema.schema_etr_v2_20230126 import ETransport",
        ],
        cwd=ROOT / "src",
        check=False,
    )
    if check.returncode != 0:
        print("Generated package failed to import", file=sys.stderr)
        return 1
    print("OK: anafpy.etransport.schema imports ETransport.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
