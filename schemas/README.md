# Vendored schemas

Source XSDs used **only at code-generation time** to produce the typed models under
`src/anafpy/`. They are intentionally *not* shipped in the wheel (the wheel packages
`src/anafpy` only); the generated Python models are what ship.

## `ubl-2.1/` — OASIS UBL 2.1

- **Source:** OASIS Universal Business Language (UBL) Version 2.1, OASIS Standard,
  04 November 2013 — <http://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.zip>
- **Retrieved:** 2026-06-28
- **License:** OASIS IPR Policy (RF on RAND terms); schemas redistributable.
- **Vendored subset:** the transitive closure of the e-Factura document roots only —
  `maindoc/UBL-Invoice-2.1.xsd` + `maindoc/UBL-CreditNote-2.1.xsd` plus the whole
  `common/` directory they import (CommonAggregate/Basic/Extension components and their
  data-type, signature and XAdES/xmldsig dependencies). The other ~63 UBL document
  types are not vendored.

Regenerate the models with:

```sh
uv run python scripts/generate_ubl.py
```
