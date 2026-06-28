# Raw sources (preserved verbatim)

Authoritative originals behind the compiled reference. **Do not edit.** When ANAF
publishes a new revision, add the new file (don't overwrite) and bump the citing doc's
frontmatter.

| File | Source URL | Revision | Retrieved |
|---|---|---|---|
| `Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf` | https://static.anaf.ro/static/10/Anaf/Informatii_R/API/Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf | Instrucțiuni actualizate 23.06.2022 | 2026-06-28 |
| `efactura_prezentare_api.pdf` | https://mfinante.gov.ro/static/10/eFactura/prezentare%20api%20efactura.pdf | (undated; current as linked from informații-tehnice) | 2026-06-28 |
| `etransport_29072024.pdf` | https://mfinante.gov.ro/static/10/eTransport/etransport_29072024.pdf | 29.07.2024 | 2026-06-28 |

> Note: `mfinante.gov.ro/static/...` blocks plain curl (connection reset); fetch with
> HTTP/2 + a full browser User-Agent. `static.anaf.ro` does **not** mirror these files.

## Not yet vendored (large; for the package build, not the docs)

- e-Factura validation artifacts: `ro16931-ubl-1.0.9.zip` (Schematron + XSD, CIUS-RO).
- e-Transport: `schema_ETR_v2_20230126.xsd`, `eTransport-validation_v.2.0.2_12082024.sch`.
- UBL example invoices: `exemple_Invoice_CreditNote.zip` (test fixtures).
