#!/usr/bin/env python
"""Regenerate the e-Transport Pydantic models from the vendored ANAF XSD.

The generated package (``anafpy.etransport.schema``) is the typed model for transport
declaration XML.  The XSD is ANAF-proprietary (not UBL); the single document root is
``eTransport`` of type ``eTransportType``.

After xsdata runs, the nomenclature enums are renamed from the opaque ``VALUE_<code>``
members to descriptive names taken from the XSD's own documentation annotations, so
the enums are self-describing: customs offices (``BVI_ALBA_IULIA``), counties
(``CLUJ``), border crossing points (``NADLAC_2_A1``), countries (``ROMANIA``),
operation types (``TRANSPORT_PE_TERITORIUL_NATIONAL``), operation purposes
(``COMERCIALIZARE``), confirmation types (``CONFIRMAT``) and document types (``CMR``).
Operation-type members additionally keep ANAF's original label (sigla + description)
as a trailing comment; elsewhere the member name already says it all.

Usage:
    uv run python scripts/generate_etransport.py

Requires the ``codegen`` dependency group (``uv sync --group codegen``).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
XSD = ROOT / "schemas" / "etransport" / "schema_ETR_v2_20230126.xsd"
OUT_PACKAGE = "anafpy.etransport.schema"
OUT_DIR = ROOT / "src" / "anafpy" / "etransport" / "schema"
XS = "{http://www.w3.org/2001/XMLSchema}"


# A nomenclature annotation is free text of ``"<code>" <label>`` pairs; a label runs
# until the next pair, the scopOperatiune "- pentru codTipOperatiune ..." separator,
# or the end.  Trailing parentheses (EU office codes, neighbour countries, "(UE)")
# are noise.
_LABEL_PAIRS = re.compile(r'"(\d+)"\s+(.+?)(?=\s+"\d+"|\s+-\s+pentru\b|\s*$)')
_ALPHA_LABEL_PAIRS = re.compile(r'"([A-Z]{2})"\s+(.+?)(?=\s+"[A-Z]{2}"|\s*$)')
# codTipOperatiune labels are ``<SIGLA> - <description>`` (AIC, TTN, ...); members
# are named after the description, the sigla survives in the trailing comment.
_SIGLA_PREFIX = re.compile(r"^[A-Z]{2,4}\s+-\s+")


class _EnumRename(NamedTuple):
    """How to rename one nomenclature enum from its XSD annotation."""

    marker: str  # unique substring locating the xs:documentation
    pairs: re.Pattern[str]  # code/label pair extractor
    keep_code: bool = False  # on an ambiguous label keep the code as the member
    # name instead of erroring — only sound for string enums whose codes are
    # already valid identifiers
    comment: bool = False  # keep the original label as a trailing comment


RENAMED_ENUMS: dict[str, _EnumRename] = {
    "CodBirouVamalType": _EnumRename("codBirouVamal", _LABEL_PAIRS),
    "CodJudetType": _EnumRename("câmpul codJudetType", _LABEL_PAIRS),
    "CodPtfType": _EnumRename("câmpul codPtf", _LABEL_PAIRS),
    "CodTaraType": _EnumRename(
        "Valori posibile pentru ţări", _ALPHA_LABEL_PAIRS, keep_code=True
    ),
    "CodTipOperatiuneType": _EnumRename(
        "câmpul codTipOperatiune:", _LABEL_PAIRS, comment=True
    ),
    "CodScopOperatiuneType": _EnumRename("codScopOperatiune ia valori", _LABEL_PAIRS),
    "TipConfirmareType": _EnumRename("câmpul tipConfirmare", _LABEL_PAIRS),
    "TipDocumentType": _EnumRename("câmpul tipDocument", _LABEL_PAIRS),
}


def _member_name(label: str) -> str:
    """``BVF Zona Liberă Curtici (ROTM2300)`` -> ``BVF_ZONA_LIBERA_CURTICI``."""
    label = _SIGLA_PREFIX.sub("", label)  # "TTN - Transport pe ..." -> description
    label = re.sub(r"\s*\([^)]*\)$", "", label)
    label = label.replace(".", "")  # abbreviations: "S.U.A" -> SUA, not S_U_A
    ascii_ = (
        unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_).strip("_").upper()


def _labels_from_doc(
    doc: str, pattern: re.Pattern[str], codes: set[str]
) -> dict[str, list[str]]:
    """Extract code -> distinct original labels for ``codes`` from annotation text.

    Pairs for codes outside ``codes`` are ignored (the scopOperatiune annotation
    interleaves codTipOperatiune values); repeats of the same label collapse, so
    only a genuinely ambiguous code (the country list carries "PS" twice) yields
    more than one label.
    """
    labels: dict[str, list[str]] = {}
    for code, label in pattern.findall(" ".join(doc.split())):
        if code in codes and label not in labels.setdefault(code, []):
            labels[code].append(label)
    return labels


def rename_enum_members(module: Path) -> None:
    """Rewrite the nomenclature enums' members to their documented names.

    Each renamed member carries the original ANAF label as a trailing comment.
    """
    docs = [
        el.text for el in ET.parse(XSD).getroot().iter(f"{XS}documentation") if el.text
    ]
    src = module.read_text(encoding="utf-8")
    for cls, spec in RENAMED_ENUMS.items():
        matching = [doc for doc in docs if spec.marker in doc]
        if len(matching) != 1:
            raise RuntimeError(
                f"Expected 1 annotation matching {spec.marker!r}, found {len(matching)}"
            )
        block = re.search(rf"class {cls}\(Enum\):\n((?:    \w+ = .+\n)+)", src)
        if block is None:
            raise RuntimeError(f"{cls} member block not found in output")
        members = re.findall(r"    \w+ = (.+)\n", block.group(1))
        codes = [value.strip('"') for value in members]
        labels = _labels_from_doc(matching[0], spec.pairs, set(codes))
        names = {
            code: _member_name(found[0])
            for code, found in labels.items()
            if len(found) == 1
        }
        missing = [code for code in codes if code not in names]
        if missing and not spec.keep_code:
            raise RuntimeError(f"{cls}: no unambiguous names for codes {missing}")
        if len({names.get(code, code) for code in codes}) != len(codes):
            raise RuntimeError(f"{cls}: member name collision")
        lines = []
        for code, value in zip(codes, members, strict=True):
            comment = " / ".join(labels.get(code, [])) if spec.comment else ""
            comment = f"  # {comment}" if comment else ""
            lines.append(f"    {names.get(code, code)} = {value}{comment}\n")
        src = src.replace(block.group(0), f"class {cls}(Enum):\n{''.join(lines)}")
    module.write_text(src, encoding="utf-8")


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

    rename_enum_members(OUT_DIR / "schema_etr_v2_20230126.py")

    # E501: the original-label comments may exceed the line length; the generated
    # package is excluded from the repo lint gate anyway.
    subprocess.run(
        ["ruff", "check", "--fix", "--quiet", "--ignore", "E501", str(OUT_DIR)],
        check=False,
    )
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
