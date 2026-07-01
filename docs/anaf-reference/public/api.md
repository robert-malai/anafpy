---
title: Public (no-auth) Web Services — registries & financial statements (webservicesp.anaf.ro)
service: public
language: en
sources:
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/servicii_web.html
    title: "ANAF — Servicii web (index of public web services)"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/servicii_web.html
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/servicii_sincron.html
    title: "ANAF — Servicii web sincron (per-service URLs + publication dates)"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/servicii_sincron.html
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/doc_WS_V9.txt
    title: "Instrucțiuni serviciu web sincron registre TVA/inactivi/split/RO e-Factura, v9"
    source_revision: "publicat 04.02.2025"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/doc_WS_V9.txt
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/docV1.txt
    title: "Instrucțiuni serviciu web Registrul RO e-Factura, v1"
    source_revision: "publicat 05.11.2024"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/docV1.txt
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_Bilant_V1.txt
    title: "Instrucțiuni serviciu web bilanț (situații financiare anuale), v1"
    source_revision: "publicat 20.01.2021"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/doc_WS_Bilant_V1.txt
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/documentatie_SWRARG_v2.txt
    title: "Instrucțiuni serviciu web Registrul agricultorilor (regim special), v2"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/documentatie_SWRARG_v2.txt
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/index_cult_v2.html
    title: "Instrucțiuni serviciu web Registrul entităților/unităților de cult, v2"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/index_cult_v2.html
  - url: https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/doc_WS_Async_V8.txt
    title: "Instrucțiuni serviciu web asincron registre TVA, v8"
    source_revision: "actualizat 20.04.2023"
    retrieved: 2026-07-02
    local_copy: ../_sources/servicii-web/doc_WS_Async_V8.txt
compiled: 2026-07-02
compiled_by: claude-fable-5
last_verified: 2026-07-02
status: draft
---

# Public (no-auth) Web Services

ANAF's **unauthenticated** lookup services on `https://webservicesp.anaf.ro` — no
OAuth, no certificate, no registration. They cover the public fiscal **registries**
(VAT registration, VAT-on-collection, inactive taxpayers, split-VAT, RO e-Factura,
special-regime farmers, cult entities) and public **annual financial statements**.

These are a separate family from the OAuth-protected e-Factura / e-Transport APIs
(see [efactura/api.md](../efactura/api.md), [etransport/api.md](../etransport/api.md)).
Two e-Factura operations are *also* exposed no-auth on this host — `validare` and
`transformare` (and `validate/signature`) — those are documented with the rest of
e-Factura in [efactura/api.md](../efactura/api.md) §5–7.

> **Status:** draft, compiled from ANAF's official instruction files (vendored under
> [`_sources/servicii-web/`](../_sources/servicii-web/)). **No PDF or swagger
> presentations exist for these services** — the instruction files are the only
> official documentation (checked 2026-07-02). Unlike the e-Factura/e-Transport docs,
> every synchronous endpoint here **was confirmed with a live production call on
> 2026-07-02** (they are public); divergences between the instruction files and live
> behaviour are flagged per section.

## Common shape (registry services)

All registry services share one request convention:

```
POST https://webservicesp.anaf.ro/<service path>
Content-Type: application/json

[ {"cui": 12345678, "data": "2026-07-01"}, ... ]
```

- `cui` — fiscal code as a **number** (no `RO` prefix); `data` — the date the query is
  evaluated at (`yyyy-MM-dd`). Registry membership is answered *as of that date*.
- Batch: max **100 CUIs**/request (v9 TVA, RO e-Factura register, async) or **500**
  (RegAgric, RegCult). Max **1 request/second** per client; ANAF warns that hammering
  the server "va fi pedepsită conform reglementărilor în vigoare".
- Response: `found[]` + `notFound[]` (CUIs with no data). RegAgric/RegCult wrap this in
  a `{"cod": 200, "message": "SUCCESS", ...}` envelope; the v9 TVA service documents
  the same envelope but **does not send it** on live 200 responses (see §1).

## 1. Taxpayer / VAT registry — `POST /api/PlatitorTvaRest/v9/tva`

The workhorse lookup: one call answers, per CUI and date, registration per **art. 316
Cod Fiscal** (VAT-registered), **TVA la încasare** (VAT on collection), **inactive /
reactivated** status, **split-VAT**, and **RO e-Factura register** membership — plus
general company data (name, addresses, CAEN, trade-register number, competent fiscal
organ, IBAN).

Response (live-confirmed 2026-07-02; top level is `{"found": [...], "notFound": [...]}`):

| Group | Fields (abridged) |
|---|---|
| `date_generale` | `cui`, `data`, `denumire`, `adresa`, `nrRegCom`, `telefon`, `fax`, `codPostal`, `act`, `stare_inregistrare`, `data_inregistrare`, `cod_CAEN`, `iban`, `statusRO_e_Factura` (bool), `data_inreg_Reg_RO_e_Factura`, `organFiscalCompetent`, `forma_de_proprietate`, `forma_organizare`, `forma_juridica` |
| `inregistrare_scop_Tva` | `scpTVA` (bool — VAT-registered at `data`), `perioade_TVA[]` — **array** of `{data_inceput_ScpTVA, data_sfarsit_ScpTVA, data_anul_imp_ScpTVA, mesaj_ScpTVA}` |
| `inregistrare_RTVAI` | `dataInceputTvaInc`, `dataSfarsitTvaInc`, `dataActualizareTvaInc`, `dataPublicareTvaInc`, `tipActTvaInc`, `statusTvaIncasare` (bool) |
| `stare_inactiv` | `dataInactivare`, `dataReactivare`, `dataPublicare`, `dataRadiere`, `statusInactivi` (bool) |
| `inregistrare_SplitTVA` | `dataInceputSplitTVA`, `dataAnulareSplitTVA`, `statusSplitTVA` (bool) |
| `adresa_sediu_social` | `sdenumire_Strada`, `snumar_Strada`, `sdenumire_Localitate`, `scod_Localitate`, `sdenumire_Judet`, `scod_Judet`, `scod_JudetAuto`, `stara`, `sdetalii_Adresa`, `scod_Postal` |
| `adresa_domiciliu_fiscal` | same fields `d`-prefixed |

Absent-status semantics: the `status*` booleans are `false` and the date fields empty
strings when the CUI is not in the respective register at `data`.

**Live divergences from `doc_WS_V9.txt`** (all observed 2026-07-02, production):

- The documented `{"cod": 200, "message": "SUCCESS", ...}` wrapper is **not present**
  on a successful response — the body starts at `found`/`notFound`.
- `perioade_TVA` is an **array** of period objects (the instruction file's pseudo-JSON
  draws it as a single nested object).
- `date_generale.data_inreg_Reg_RO_e_Factura` (date of e-Factura register enrolment)
  is returned live but **not listed** in the instruction file (which only names
  `statusRO_e_Factura`).

> Provenance: `doc_WS_V9.txt` (publicat 04.02.2025); live call 2026-07-02.

## 2. RO e-Factura register — `POST /api/registruroefactura/v1/interogare`

Dedicated query of the **Registrul RO e-Factura** (the opt-in register created by
OG 120/2021; since the 2024 B2B mandate it mainly matters for B2G option dates and
edge cases — for a plain "is this CUI e-Factura-registered" check, §1's
`statusRO_e_Factura` answers it in the same call as everything else).

`found[]` entries: `cui`, `denumire`, `adresa`, `registru` (which register),
`categorie` (taxpayer category), `dataInscriere`, `dataRenuntare` (opt-out date),
`dataRadiere` (removal date), `dataOptiuneB2G`, `stare` (registered-or-not at the
requested date).

Status codes (documented, and live-confirmed for the 404 case): `200` data returned;
`400` bad payload or **too many CUIs**; **`404` when no data exists for *any* CUI in
the list** — with body `{"found": [], "notFound": [<cuis>]}`. Treat 404 here as a
business "not found", not a transport error. The `found` shape is **not yet
live-confirmed** (probed CUIs weren't in the register).

> Provenance: `docV1.txt` (publicat 05.11.2024); 404 semantics live-confirmed
> 2026-07-02.

## 3. Financial statements — `GET /bilant?an={year}&cui={cui}`

Public indicators from annual financial statements / accounting reports. Plain GET, one
CUI + one year per call.

Response: `{"an", "cui", "deni" (name), "caen", "den_caen", "i": [{"indicator":
"I1"..., "val_indicator": <number>, "val_den_indicator": "<label>"}, ...]}`. The
**indicator set varies by statement type** (the instruction file's example is an
insurance-company balance sheet; a commercial company returns the standard
active/capitaluri/venituri/cheltuieli/profit indicators, `I1`…`I33`-ish, plus average
employee count).

The instruction file says data covers **2014–2019**, but that's stale: a live call for
`an=2023` returned full data (2026-07-02). Rate limit 1 request/second.

> Provenance: `doc_WS_Bilant_V1.txt` (publicat 20.01.2021); live call 2026-07-02.

## 4. Farmers' special-regime register — `POST /RegAgric/api/v2/ws/agric`

Registrul agricultorilor care aplică regimul special (art. 315¹ Cod Fiscal). Batch max
**500 CUIs**. Response is wrapped: `{"cod": 200, "message": "SUCCESS", "found": [...]}`
— `found[]` entries carry `cui`, `data`, `denumire`, `adresa`, `nrRegCom`, `telefon`,
`fax`, `codPostal`, `act`, `stare_inregistrare`, `dataInceputRegAgric`,
`dataAnulareRegAgric`, `statusRegAgric` (bool).

**Live note (2026-07-02):** a CUI that is *not* in the register still comes back under
`found` — with empty strings and `statusRegAgric: false` — rather than in a `notFound`
list. Membership must be read from the `status*` boolean, not from presence in `found`.

> Provenance: `documentatie_SWRARG_v2.txt`; live call 2026-07-02.

## 5. Cult entities register — `POST /RegCult/api/v2/ws/cult`

Registrul entităților/unităților de cult (tax-credit-eligible religious entities).
Identical envelope and conventions to §4 (max **500 CUIs**, `cod`/`message` wrapper,
same live not-found-still-in-`found` behaviour): `found[]` carries the same general
fields plus `dataInceputRegCult`, `dataAnulareRegCult`, `statusRegCult` (bool). The
instruction file adds: if `data` is in the future, the answer reflects the current
date.

> Provenance: `index_cult_v2.html`; live call 2026-07-02.

## 6. Async variant of §1 — `POST /AsynchWebService/api/v8/ws/tva`

Same query and same response schema as §1, but job-based, for callers that batch:

1. `POST /AsynchWebService/api/v8/ws/tva` with the same JSON body → `{"cod": 200,
   "message": "Successful", "correlationId": "<uuid>"}`.
2. `GET /AsynchWebService/api/v7/ws/tva?id=<correlationId>` → the §1 response. (The
   download path really is **v7** while submit is v8 — that's what the instruction
   file documents.)

Rules: wait ≥ 2 s before the first GET and retry while not ready (use a ≥ 10 s client
timeout); the result can be downloaded **only once** and expires after **3 days**;
max 100 CUIs/request, 1 request/second. Not live-probed (single-download semantics
make a throwaway probe wasteful); shape shares §1's caveats.

> Provenance: `doc_WS_Async_V8.txt` (actualizat 20.04.2023).

## Notes for `anafpy`

- These endpoints are **not consumed by the phase-1 clients** (which are OAuth-only,
  `api.anaf.ro`). They are candidates for a zero-credential lookup surface — e.g. an
  MCP `anaf_lookup` tool answering "is this CUI VAT-registered / e-Factura-registered"
  before filing — with §1 covering nearly every practical question in one call.
- If implemented: honour the **1 req/s** limit client-side (unlike the OAuth clients'
  no-auto-backoff stance, ANAF states this limit as a usage *rule*, not via 429s),
  batch up to the documented CUI caps, and read membership from the `status*` booleans
  (§4/§5 live note). The empty-`data_inreg_Reg_RO_e_Factura` + `statusRO_e_Factura:
  false` combination in §1 is the common case for post-mandate companies that never
  joined the opt-in register — it does **not** mean they can't receive e-Factura.
