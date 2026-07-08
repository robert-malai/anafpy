#!/usr/bin/env python
"""Regenerate the e-Factura code lists from the vendored EN16931 Schematron.

The EN16931/CIUS-RO validation Schematron embeds every closed code list (ISO 4217
currencies, ISO 3166 countries, UN/ECE Rec 20/21 units, UNTDID 4461 payment means,
VATEX exemption codes, ...) as space-separated strings inside its ``BR-CL-*``
assertions. This script extracts them into
``src/anafpy/efactura/authoring/_codelists.py`` so the flat invoice models validate
code-list membership without a Schematron engine.

Sources (vendored under ``schemas/efactura/schematron/1.0.9/``):
- ``codelist/EN16931-UBL-codes.sch`` — the code-list binding rules; lists are keyed
  by their rule *context* below (contexts are unique; rule ids repeat).
- ``UBL/EN16931-UBL-model.sch`` — only for the UNCL 4451 note-subject list, which
  rides the ``BR-CL-08`` binding parameter instead of a codes rule.

Usage:
    uv run python scripts/generate_efactura_codelists.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCH_DIR = ROOT / "schemas" / "efactura" / "schematron" / "1.0.9"
CODES_SCH = SCH_DIR / "codelist" / "EN16931-UBL-codes.sch"
MODEL_SCH = SCH_DIR / "UBL" / "EN16931-UBL-model.sch"
OUT = ROOT / "src" / "anafpy" / "efactura" / "authoring" / "_codelists.py"

# rule context in EN16931-UBL-codes.sch -> (constant name, docstring line)
CONTEXT_LISTS: dict[str, tuple[str, str]] = {
    "//@currencyID": (
        "CURRENCY_CODES",
        "ISO 4217 alpha-3 currency codes (BR-CL-03/04/05).",
    ),
    "cac:Country/cbc:IdentificationCode": (
        "COUNTRY_CODES",
        "ISO 3166-1 alpha-2 country codes, EN16931 edition (BR-CL-14/15).",
    ),
    "cac:PaymentMeans/cbc:PaymentMeansCode": (
        "PAYMENT_MEANS_CODES",
        "UNTDID 4461 payment means codes (BR-CL-16).",
    ),
    "cac:TaxCategory/cbc:ID": (
        "TAX_CATEGORY_CODES",
        "UNCL 5305 duty/tax/fee category codes, EN16931 subset (BR-CL-17/18).",
    ),
    "cbc:TaxExemptionReasonCode": (
        "VAT_EXEMPTION_CODES",
        "VATEX VAT exemption reason codes (BR-CL-19).",
    ),
    "//@unitCode": (
        "UNIT_CODES",
        "UN/ECE Recommendation 20/21 unit-of-measure codes (BR-CL-23).",
    ),
    "cbc:EmbeddedDocumentBinaryObject[@mimeCode]": (
        "MIME_CODES",
        "Allowed attachment MIME codes (BR-CL-24).",
    ),
    "cbc:EndpointID[@schemeID]": (
        "ELECTRONIC_ADDRESS_SCHEMES",
        "EAS electronic address scheme identifiers (BR-CL-25).",
    ),
    "cac:PartyIdentification/cbc:ID[@schemeID]": (
        "ICD_SCHEMES",
        "ISO 6523 ICD identification scheme identifiers (BR-CL-10/11/26).",
    ),
    "cac:CommodityClassification/cbc:ItemClassificationCode[@listID]": (
        "ITEM_CLASSIFICATION_SCHEMES",
        "UNTDID 7143 item classification scheme identifiers (BR-CL-13).",
    ),
    (
        "cac:AdditionalDocumentReference[cbc:DocumentTypeCode = '130']/cbc:ID"
        "[@schemeID] | cac:DocumentReference[cbc:DocumentTypeCode = '130']/cbc:ID"
        "[@schemeID]"
    ): (
        "OBJECT_ID_SCHEMES",
        "UNTDID 1153 object identifier scheme identifiers (BR-CL-07).",
    ),
}

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RULE = re.compile(r'<rule context="([^"]*)"[^>]*>(.*?)</rule>', re.S)
# A code list is the longest space-delimited token run inside contains(' ... ', ...);
# the mime rule instead spells an or-chain of equality tests against quoted literals.
_TOKEN_RUN = re.compile(r"' ((?:[^\s']+ )+)'")
_EQUALITY_LITERAL = re.compile(r"= '([^']+)'")


def _looks_like_codes(tokens: list[str]) -> bool:
    return len(tokens) >= 2 and not any(
        token in ("or", "and", "=") or token.startswith("@") for token in tokens
    )


def _longest_token_run(text: str) -> list[str]:
    runs = [run.split() for run in _TOKEN_RUN.findall(text)]
    if runs := [run for run in runs if _looks_like_codes(run)]:
        return max(runs, key=len)
    return _EQUALITY_LITERAL.findall(text)


def _render(name: str, doc: str, tokens: list[str]) -> str:
    body = "\n".join(f'        "{token}",' for token in sorted(tokens))
    return f"#: {doc}\n{name}: frozenset[str] = frozenset(\n    (\n{body}\n    )\n)\n"


def main() -> int:
    for path in (CODES_SCH, MODEL_SCH):
        if not path.exists():
            print(f"Missing vendored Schematron: {path}", file=sys.stderr)
            return 1

    codes_src = _COMMENT.sub("", CODES_SCH.read_text(encoding="utf-8"))
    lists: dict[str, tuple[str, list[str]]] = {}
    for context, body in _RULE.findall(codes_src):
        context = " ".join(context.split())
        if context not in CONTEXT_LISTS:
            continue
        name, doc = CONTEXT_LISTS[context]
        tokens = _longest_token_run(body)
        if len(tokens) < 2:
            print(f"No code list found for context {context!r}", file=sys.stderr)
            return 1
        lists[name] = (doc, tokens)
    if missing := [n for n, _ in CONTEXT_LISTS.values() if n not in lists]:
        print(f"Contexts not found in codes.sch: {missing}", file=sys.stderr)
        return 1

    model_src = MODEL_SCH.read_text(encoding="utf-8")
    br_cl_08 = re.search(r'name="BR-CL-08" value="([^"]*)"', model_src)
    if br_cl_08 is None:
        print("BR-CL-08 parameter not found in UBL-model.sch", file=sys.stderr)
        return 1
    note_codes = _longest_token_run(br_cl_08.group(1))
    if len(note_codes) < 2:
        print("No code list inside the BR-CL-08 parameter", file=sys.stderr)
        return 1
    lists["NOTE_SUBJECT_CODES"] = (
        "UNCL 4451 note subject qualifiers (BR-CL-08).",
        note_codes,
    )

    blocks = "\n".join(
        _render(name, doc, tokens) for name, (doc, tokens) in sorted(lists.items())
    )
    all_lines = "\n".join(f'    "{name}",' for name in sorted(lists))
    OUT.write_text(
        '"""GENERATED by scripts/generate_efactura_codelists.py — do not hand-edit.\n'
        "\n"
        "Closed code lists extracted from the vendored EN16931/CIUS-RO 1.0.9\n"
        "Schematron (``schemas/efactura/schematron/1.0.9/``). Membership in these\n"
        "lists is what ANAF's validator enforces via its ``BR-CL-*`` rules.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        f"__all__ = [\n{all_lines}\n]\n"
        "\n"
        f"{blocks}",
        encoding="utf-8",
    )
    sizes = {name: len(tokens) for name, (_, tokens) in lists.items()}
    print(f"OK: wrote {OUT.relative_to(ROOT)} with {sizes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
