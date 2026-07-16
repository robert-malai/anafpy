# Raw sources (preserved verbatim)

Authoritative originals behind the compiled reference. **Do not edit.** When ANAF
publishes a new revision, add the new file (don't overwrite) and bump the citing doc's
frontmatter.

| File | Source URL | Revision | Retrieved |
|---|---|---|---|
| `Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf` | https://static.anaf.ro/static/10/Anaf/Informatii_R/API/Oauth_procedura_inregistrare_aplicatii_portal_ANAF.pdf | Instrucțiuni actualizate 23.06.2022 | 2026-06-28 |
| `efactura_prezentare_api.pdf` | https://mfinante.gov.ro/static/10/eFactura/prezentare%20api%20efactura.pdf | (undated; current as linked from informații-tehnice) | 2026-06-28 |
| `etransport_29072024.pdf` | https://mfinante.gov.ro/static/10/eTransport/etransport_29072024.pdf | 29.07.2024 | 2026-06-28 |
| `limiteApeluriAPI.txt` | https://mfinante.gov.ro/static/10/eFactura/limiteApeluriAPI.txt | (undated) | 2026-07-02 |
| `eTransport-validation_v.2.0.2_12082024.sch` | https://mfinante.gov.ro/static/10/eTransport/eTransport-validation_v.2.0.2_12082024.sch | v2.0.2, 12.08.2024 | 2026-07-03 |

## Swagger presentations (per-endpoint OpenAPI specs)

The "prezentări de tip swagger" the e-Factura API PDF's first line points to: official
per-endpoint Swagger UI pages, self-contained HTML with the OpenAPI 3.0.1 spec embedded
as a `var spec = {...}` JavaScript object (open in a browser, or extract the object —
some specs are JS objects with unquoted keys, not strict JSON). These are the only
official source for the **response schemas** (the PDFs cover URLs/params only). All
retrieved 2026-07-02; revision = the date shown next to the link on informații-tehnice.

| File | Source URL | Revision |
|---|---|---|
| `efactura-swagger/upload.html` | https://mfinante.gov.ro/static/10/eFactura/upload.html | actualizat 04.02.2025 |
| `efactura-swagger/staremesaj.html` | https://mfinante.gov.ro/static/10/eFactura/staremesaj.html | (undated) |
| `efactura-swagger/listamesaje.html` | https://mfinante.gov.ro/static/10/eFactura/listamesaje.html | (undated) |
| `efactura-swagger/descarcare.html` | https://mfinante.gov.ro/static/10/eFactura/descarcare.html | (undated) |
| `efactura-swagger/validare.html` | https://mfinante.gov.ro/static/10/eFactura/validare.html | (undated) |
| `efactura-swagger/validaresemnatura.html` | https://mfinante.gov.ro/static/10/eFactura/validaresemnatura.html | 03.09.2024 |
| `efactura-swagger/xmltopdf.html` | https://mfinante.gov.ro/static/10/eFactura/xmltopdf.html | (undated) |
| `etransport-swagger/upload_param.html` | https://mfinante.gov.ro/static/10/eTransport/upload_param.html | 02.07.2024 |
| `etransport-swagger/lista.html` | https://mfinante.gov.ro/static/10/eTransport/lista.html | 02.07.2024 |
| `etransport-swagger/stare.html` | https://mfinante.gov.ro/static/10/eTransport/stare.html | 02.07.2024 |
| `etransport-swagger/info_transportatori.html` | https://mfinante.gov.ro/static/10/eTransport/info_transportatori.html | 01.07.2024 |

> Note: `mfinante.gov.ro/static/...` blocks plain curl (connection reset); fetch with
> HTTP/2 + a full browser User-Agent, e.g.
> `curl --http2 -A "Mozilla/5.0 ... Chrome/126.0.0.0 Safari/537.36" <url>`.
> `static.anaf.ro` does **not** mirror these files.

## Public (no-auth) web services — `servicii-web/`

Official instruction files for ANAF's **unauthenticated** lookup services on
`webservicesp.anaf.ro` (fiscal registries + public financial statements). **No PDFs or
swagger presentations exist for these** — the `.txt`/`.html` instruction files below are
the only official documentation (checked 2026-07-02); the `servicii_*.html` index pages
are vendored too because they carry the service URLs and publication dates. All
retrieved 2026-07-02.

| File | Source URL | Revision |
|---|---|---|
| `servicii-web/servicii_web.html` | https://static.anaf.ro/static/10/Anaf/Informatii_R/servicii_web.html | (index page, undated) |
| `servicii-web/servicii_sincron.html` | https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/servicii_sincron.html | (index; carries per-service dates) |
| `servicii-web/servicii_asincron.html` | https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/servicii_asincron.html | (index) |
| `servicii-web/doc_WS_V9.txt` | https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/doc_WS_V9.txt | publicat 04.02.2025 |
| `servicii-web/docV1.txt` | https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/docV1.txt | publicat 05.11.2024 |
| `servicii-web/doc_WS_Bilant_V1.txt` | https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_Bilant_V1.txt | publicat 20.01.2021 |
| `servicii-web/documentatie_SWRARG_v2.txt` | https://static.anaf.ro/static/10/Anaf/Informatii_R/documentatie_SWRARG_v2.txt | (undated; "actualizate") |
| `servicii-web/index_cult_v2.html` | https://static.anaf.ro/static/10/Anaf/Informatii_R/index_cult_v2.html | (undated; "actualizate") |
| `servicii-web/doc_WS_Async_V8.txt` | https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/doc_WS_Async_V8.txt | actualizat 20.04.2023 |

> Note: unlike `mfinante.gov.ro`, `static.anaf.ro` serves these to plain curl.
> `index_cult_v2.html` has mojibake NBSP runs in the original — preserved verbatim.

## SPV web services — `clientspv/`

ANAF's **only** documentation for the SPV web services (`webserviced.anaf.ro/SPVWS2/rest/`
— mTLS with a qualified certificate) is the example Java client repository
[github.com/MfpAnaf/ClientSPV](https://github.com/MfpAnaf/ClientSPV) — no PDF, no
swagger. Vendored verbatim (README + MIT LICENSE, required when vendoring + the Java
sources, which carry the transport facts: PKCS#11 token mTLS, CookieManager). All files
pinned to the repo head commit **`949ea92c2b4abe99d531a5a094af288e6f662c26`**
(2019-05-07 — the upstream is dormant; on drift, re-fetch, diff, and update this
pin), retrieved 2026-07-12.

| File | Source URL (at pinned commit) |
|---|---|
| `clientspv/README.md` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/README.md |
| `clientspv/LICENSE` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/LICENSE |
| `clientspv/pom.xml` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/pom.xml |
| `clientspv/src/ApelSPV.java` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/src/main/java/sqw/apelspv/ApelSPV.java |
| `clientspv/src/CertificateChooserImpl.java` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/src/main/java/sqw/apelspv/CertificateChooserImpl.java |
| `clientspv/src/CertificateChooser.java` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/src/main/java/sqw/certificat/CertificateChooser.java |
| `clientspv/src/Sign.java` | https://github.com/MfpAnaf/ClientSPV/blob/949ea92c2b4abe99d531a5a094af288e6f662c26/src/main/java/sqw/certificat/Sign.java |

## StareD112 (filing status + recipisa) — `stared112/`

ANAF's public, unauthenticated filing-status page (`https://www.anaf.ro/StareD112/`)
has **no official documentation** — these live captures (curl, plain HTTP; the
service needs no session priming) are the only wire record, feeding
`declaratii/stared112.md`. All retrieved 2026-07-16 against a real F4109 filing
(index `1100000001`, CUI `99999909`).

| File | What it captures |
|---|---|
| `stared112/form-page.html` (+ `.headers.txt`) | the query form (`GET /StareD112/`): field names `ghiseu`/`id`/`cui`, the 200-declaration warning |
| `stared112/result-found.html` (+ `.headers.txt`) | `POST vizualizareStare.do`, matching pair: header line, six-column table (incl. a >60-day row with no recipisa link), the four documented states |
| `stared112/result-notfound.html` (+ `.headers.txt`) | same POST, valid shape but no match (also returned for a mismatched pair) |
| `stared112/result-invalid-input.html` | same POST, non-numeric input → "Nu ati introdus un index valid" |
| `stared112/recipisa-found.headers.txt` | `GET ObtineRecipisa?numefisier=<index>.pdf`, known index: 200 `application/pdf`, 9 078 bytes (PDF body itself not vendored — it is a real signed receipt) |
| `stared112/recipisa-empty.headers.txt` | same GET, unknown index `9999999999`: 200 `application/pdf`, `Content-Length: 0` |

## Related ANAF artifacts, deliberately not vendored here

- **CIUS-RO validation artifacts** — `ro16931-ubl-1.0.9.zip` (Schematron + XSD):
  `anafpy` has **no local validator** (validation is ANAF's server side; see
  `/DESIGN.md` §4), so these have no consumer in this repo. Listed for completeness
  only. The e-Transport Schematron (`eTransport-validation_v.2.0.2_12082024.sch`)
  *is* vendored above — not as a validator input, but as the only official statement
  of the business rules (`BR-*`) ANAF enforces on e-Transport upload. It is stricter
  than the XSD in places (no leading zero in `codDeclarant`, min 2 chars for
  locality/street names, enumerated UN/ECE unit codes, country list without `AN`);
  its *unconditional* rules are mirrored as flat-model field constraints in
  `src/anafpy/etransport/models.py`, and its BR-CL-003 unit-code list is carried
  verbatim in `src/anafpy/mcp/unitcodes.py` (see `/DESIGN.md` §5) — re-check both
  when ANAF revises the Schematron.
- `schema_ETR_v2_20230126.xsd` — already vendored at the repo top level under
  `/schemas/etransport/` (codegen input), not duplicated here.
- UBL example invoices: `exemple_Invoice_CreditNote.zip` (potential test fixtures).
