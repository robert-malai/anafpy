# Vendored schemas

Source XSDs and Schematron files used **only at code-generation time** to produce
artifacts under `src/anafpy/`. They are intentionally *not* shipped in the wheel
(the wheel packages `src/anafpy` only); the generated Python is what ships. This
file is the provenance record and the re-vendoring playbook — when ANAF or OASIS
revises a source, the steps below reproduce every generated artifact.

Codegen needs the `codegen` dependency group (`uv sync --group codegen`).
`xsdata[cli]` is pinned `<25`: the `xsdata-pydantic` plugin targets the 24.x
line, and newer core emits invalid fields.

## `ubl-2.1/` — OASIS UBL 2.1 XSDs

- **Source:** OASIS Universal Business Language (UBL) Version 2.1, OASIS Standard,
  04 November 2013 — <http://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.zip>
- **Retrieved:** 2026-06-28
- **License:** OASIS IPR Policy (RF on RAND terms); schemas redistributable.
- **Vendored subset:** the transitive closure of the e-Factura document roots only —
  `maindoc/UBL-Invoice-2.1.xsd` + `maindoc/UBL-CreditNote-2.1.xsd` plus the whole
  `common/` directory they import (CommonAggregate/Basic/Extension components and their
  data-type, signature and XAdES/xmldsig dependencies). The other ~63 UBL document
  types are not vendored.
- **Generates:** `src/anafpy/efactura/ubl/` (the generated UBL model package):

```sh
uv run python scripts/generate_ubl.py
```

UBL 2.1 is a finished OASIS standard — this source should never change. If it ever
must be re-vendored, drop the same subset from the ZIP into `ubl-2.1/` and rerun
the script (it post-fixes a known xsdata-pydantic 24.x codegen bug; see its
docstring).

## `efactura/schematron/1.0.9/` — EN 16931 + CIUS-RO validation Schematron

- **Source:** ANAF's CIUS-RO validation package **ro16931-ubl 1.0.9** —
  <https://mfinante.gov.ro/static/10/eFactura/ro16931-ubl-1.0.9.zip> (linked from
  the e-Factura *Informații tehnice* page; new editions appear as new ZIPs —
  1.0.7/1.0.8 are also published).
- **Retrieved:** 2026-06-28 (full package, git `ba4a592`); the current subset was
  re-vendored from that commit on 2026-07-08.
- **License:** European Union Public Licence (EUPL) v1.2, per the file headers —
  these are the CEN EN 16931 validation artefacts with ANAF's CIUS-RO
  modifications.
- **Vendored subset:** only the two files the code-list generator reads, at the
  ZIP's own relative paths:
  - `codelist/EN16931-UBL-codes.sch` — the `BR-CL-*` closed code lists
    (currencies, countries, units, payment means, VATEX, EAS, ...), embedded as
    space-separated strings inside the assertions;
  - `UBL/EN16931-UBL-model.sch` — only for the UNCL 4451 note-subject list, which
    rides the `BR-CL-08` binding parameter instead of a codes rule.

  The package's other files (`abstract/EN16931-model.sch`,
  `cius-ro/RO16931-rules.sch`, the syntax binding, ANAF's precompiled XSLT) are
  **not vendored** — they were, for the removed `anafpy[validation]` Schematron
  engine, and remain readable at git `ba4a592`. They matter again at every
  revision: they are the reference text for the **hand-translated rule set** in
  `src/anafpy/efactura/authoring/rules.py` and the construction-time checks in
  `authoring/models.py`.
- **Generates:** `src/anafpy/efactura/authoring/_codelists.py`:

```sh
uv run python scripts/generate_efactura_codelists.py
```

### When ANAF revises CIUS-RO

The signal is the live drift tripwire —
`tests/test_efactura_roundtrip_live.py::test_validare_agrees_with_local_rules`
asserts that local `authoring.validate()` verdicts track ANAF's `validare` both
ways, and stops holding when the server-side rules move. Then:

1. Download the new package ZIP from the URL pattern above and vendor the same
   two files under a new version directory, e.g.
   `efactura/schematron/1.0.10/codelist/...` (keep the ZIP's relative layout).
2. Point `SCH_DIR` in `scripts/generate_efactura_codelists.py` at the new
   directory and rerun it — `_codelists.py` is fully regenerated, never
   hand-edited. If a *new* code list appears in the `.sch`, add its rule context
   to the script's `CONTEXT_LISTS` map.
3. Diff the new package's `abstract/EN16931-model.sch`, `UBL/EN16931-UBL-model.sch`,
   and `cius-ro/RO16931-rules.sch` against the previous edition (old edition:
   this directory / git history) and re-align the hand-translated rules in
   `authoring/rules.py` and the construction checks in `authoring/models.py`.
   Keep the official rule ids honest, including ANAF divergences from the
   published text (e.g. BR-51 is enforced as a fatal length check — found live).
4. Update this file's version/retrieved lines, run the four gates, then
   `ANAFPY_LIVE=1 uv run pytest -m live tests/test_efactura_roundtrip_live.py`
   until the tripwire agrees with ANAF again.

## `etransport/` — ANAF e-Transport v2 XSD

- **Source:** <https://mfinante.gov.ro/static/10/eTransport/schema_ETR_v2_20230126.xsd>
  (proprietary ANAF schema, revision 2023-01-26, linked from the e-Transport
  *Informații tehnice* page).
- **Retrieved:** 2026-06-28.
- **Generates:** `src/anafpy/etransport/schema/`:

```sh
uv run python scripts/generate_etransport.py
```

The script post-processes the output: nomenclature enum members get descriptive
names derived from the XSD's own `xs:documentation` annotations (see its
docstring). A new XSD revision replaces the file here, then rerun the script and
review the enum-name diff.

Related but vendored elsewhere: the e-Transport **Schematron** (v2.0.2,
12.08.2024) lives at
`docs/anaf-reference/_sources/eTransport-validation_v.2.0.2_12082024.sch` — it
is not codegen input; its *unconditional* rules are hand-mirrored as
construction checks in `src/anafpy/etransport/models.py` (UIT check digits,
gross ≥ net, ...) and should be re-checked when ANAF revises it.

## `bnr/` — BNR exchange-rate XSD

- **Source:** <https://curs.bnr.ro/xsd/nbrfxrates.xsd> (Banca Națională a
  României's published schema for the `nbrfxrates` documents, linked from
  <https://curs.bnr.ro/> — *Cursurile pieței valutare în format XML*).
- **Retrieved:** 2026-08-30 (sha256
  `70809027c46e3cbad53d6c1526b36c98fda859c07ebeeb80112d3e70f8955951`).
- **Not an ANAF source** — the only publisher here that is not (DESIGN.md §17).
- **Generates:** `src/anafpy/bnr/schema/`:

```sh
uv run python scripts/generate_bnr.py
```

Two BNR quirks the re-vendoring playbook has to carry:

1. **The file is vendored verbatim and patched in flight.** BNR declares the
   XML Schema namespace as `https://www.w3.org/2001/XMLSchema`; the canonical
   identifier is the `http` spelling (it is a fixed string, not a URL), so
   xsdata refuses the file as published —
   `Unknown property {http://…}schema:{https://…}complexType`. The generator
   rewrites that one namespace on a temp copy so the file on disk stays
   byte-for-byte what BNR serves; it warns if a re-vendored copy no longer
   needs the patch, which is the signal to drop it.
2. **BNR serves two spellings of its own namespace.** The year archives through
   2025 declare `http://www.bnr.ro/xsd`, 2026 onwards `https://www.bnr.ro/xsd`
   — the same schema, and the client reads both (an early-January date falls
   back to the previous year's archive). The generated models can only bind
   one, so `anafpy.bnr.client._canonical_namespace` folds the legacy spelling
   onto the bound one before parsing. If a future re-vendor changes the
   `targetNamespace` itself, that function is what needs updating with it.

The generated tier is wire-shaped only; `anafpy.bnr.models` is the domain tier,
and it is where rate values become `Decimal` (BNR's XSD restricts a decimal with
a pattern, which xsdata renders as `str`) and where the multiplier and the
fiscal rounding are applied.
