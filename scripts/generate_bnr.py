#!/usr/bin/env python
"""Regenerate the BNR exchange-rate Pydantic models from the vendored XSD.

The generated package (``anafpy.bnr.schema``) is the typed wire model for BNR's
``nbrfxrates`` documents — ``DataSet`` with a ``Header`` and a ``Body`` of one
``Cube`` per banking day, each holding ``Rate`` elements.

**The vendored XSD needs one in-flight fix, applied here and never to the file
on disk.** BNR declares the XML Schema namespace as
``https://www.w3.org/2001/XMLSchema``; the canonical form is the ``http`` one,
and it is a fixed identifier rather than a URL, so schema tooling reads BNR's
elements as belonging to some unknown namespace and refuses the document::

    ParserError: Unknown property {http://…}schema:{https://…}complexType

Rewriting it in ``schemas/bnr/nbrfxrates.xsd`` would break that tree's promise
that a vendored file is byte-for-byte what the publisher serves, so the patch
happens on a temporary copy at generation time. Only the *XML Schema* namespace
is touched; BNR's own ``targetNamespace`` is left exactly as published.

Note for whoever re-vendors: the generated models bind BNR's target namespace
(``https://www.bnr.ro/xsd``) into their field metadata, while the archives
through 2025 are still served as ``http://www.bnr.ro/xsd``. The client
canonicalises the document namespace before parsing — see
``anafpy.bnr.client._canonical_namespace``.

Usage:
    uv run python scripts/generate_bnr.py

Requires the ``codegen`` dependency group (``uv sync --group codegen``).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XSD = ROOT / "schemas" / "bnr" / "nbrfxrates.xsd"
OUT_PACKAGE = "anafpy.bnr.schema"
OUT_DIR = ROOT / "src" / "anafpy" / "bnr" / "schema"

#: BNR writes the XML Schema namespace with an `https` scheme; the canonical
#: identifier is `http`. Rewritten on a temp copy, never in the vendored file.
_XSD_NS_AS_PUBLISHED = b"https://www.w3.org/2001/XMLSchema"
_XSD_NS_CANONICAL = b"http://www.w3.org/2001/XMLSchema"


def main() -> int:
    if not XSD.exists():
        print(f"Missing vendored XSD: {XSD}", file=sys.stderr)
        return 1

    source = XSD.read_bytes()
    if _XSD_NS_AS_PUBLISHED not in source:
        print(
            "The vendored XSD no longer declares the XML Schema namespace with "
            "an https scheme — BNR may have fixed it. Drop this patch (and the "
            "note in schemas/README.md) if so.",
            file=sys.stderr,
        )
    patched = source.replace(_XSD_NS_AS_PUBLISHED, _XSD_NS_CANONICAL)

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    with tempfile.TemporaryDirectory() as tmp:
        # The output module is named after the input file, so keep the name.
        staged = Path(tmp) / XSD.name
        staged.write_bytes(patched)
        subprocess.run(
            [
                "xsdata",
                "generate",
                "--package",
                OUT_PACKAGE,
                "--output",
                "pydantic",
                "--structure-style",
                "filenames",
                "--relative-imports",
                str(staged),
            ],
            cwd=ROOT / "src",
            check=False,
        )

    if not OUT_DIR.exists():
        print("xsdata produced no output", file=sys.stderr)
        return 1

    subprocess.run(
        ["ruff", "check", "--fix", "--quiet", "--ignore", "E501", str(OUT_DIR)],
        check=False,
    )
    subprocess.run(["ruff", "format", "--quiet", str(OUT_DIR)], check=False)

    check = subprocess.run(
        [sys.executable, "-c", "from anafpy.bnr.schema.nbrfxrates import DataSet"],
        cwd=ROOT / "src",
        check=False,
    )
    if check.returncode != 0:
        print("Generated package failed to import", file=sys.stderr)
        return 1
    print("OK: anafpy.bnr.schema imports DataSet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
