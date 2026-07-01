---
title: e-Factura — Web Services API (FCTEL/rest)
service: efactura
language: en
sources:
  - url: https://mfinante.gov.ro/static/10/eFactura/prezentare%20api%20efactura.pdf
    title: "Prezentare servicii web — Sistemul național RO e-Factura (official PDF, 5 pp)"
    retrieved: 2026-06-28
    local_copy: ../_sources/efactura_prezentare_api.pdf
  - url: https://mfinante.gov.ro/ro/web/efactura/informatii-tehnice
    title: "MF — Informații tehnice e-Factura (index of current technical resources)"
    retrieved: 2026-06-28
  - title: "Validation artifacts package"
    url: https://mfinante.gov.ro/static/10/eFactura/ro16931-ubl-1.0.9.zip
    source_revision: "ro16931-ubl 1.0.9 (latest; 1.0.7/1.0.8 also published)"
    retrieved: 2026-06-28
  - title: "Swagger presentations (per-endpoint OpenAPI specs, 7 pages)"
    url: https://mfinante.gov.ro/static/10/eFactura/upload.html
    source_revision: "upload actualizat 04.02.2025; validaresemnatura 03.09.2024; others undated"
    retrieved: 2026-07-02
    local_copy: ../_sources/efactura-swagger/
  - title: "Limite Apeluri API (per-method rate limits)"
    url: https://mfinante.gov.ro/static/10/eFactura/limiteApeluriAPI.txt
    retrieved: 2026-07-02
    local_copy: ../_sources/limiteApeluriAPI.txt
compiled: 2026-06-28
compiled_by: claude-opus-4-8
last_verified: 2026-07-02
status: draft
---

# e-Factura — Web Services API

Operations for the RO e-Factura system. Authentication is the shared
[OAuth2 flow](../oauth/authentication.md) (Bearer token). Invoice **format** is UBL 2.1
/ CIUS-RO; **validation** is ANAF's server-side `validare` endpoint (§5) — `anafpy`
deliberately has no local rule engine (see `/DESIGN.md` §4). This doc is the
**transport/API surface**.

> **Status:** draft, compiled from the official 5-page API PDF (current as linked from
> the e-Factura *informații tehnice* page on 2026-06-28) plus the official per-endpoint
> **swagger presentations** (vendored 2026-07-02 under
> [`_sources/efactura-swagger/`](../_sources/efactura-swagger/)) — the PDF covers
> URLs/params, the swaggers are the authority on **response schemas**. Re-confirm
> endpoint behaviour with a live test-environment call during implementation.

## Access modes & base URLs

Every endpoint has **two access modes**, differing only by host:

| Mode | Host | How `anafpy` uses it |
|---|---|---|
| **OAuth2** (Bearer token) | `https://api.anaf.ro/{prod\|test}` | **This is what `anafpy` uses.** |
| Certificate-at-call-time | `https://webserviceapl.anaf.ro/{prod\|test}` | Not used (direct mTLS per call). |
| Public (no auth) — validate/PDF only | `https://webservicesp.anaf.ro/prod` | Optional, for `validare`/`transformare`. |

All paths below are shown for the **OAuth2** mode, e.g.
`https://api.anaf.ro/prod/FCTEL/rest/...`. Swap `prod`↔`test` for the environments —
with one caveat: the PDF documents `validare`, `transformare`, and
`validate/signature` for **producție only** (no test URLs shown); a `test` variant of
those three is an inference, not sourced.

> Provenance: PDF pp. 1–5 (each operation lists both `webserviceapl` cert mode and
> `api.anaf.ro` oauth2 mode).

`webservicesp.anaf.ro` also hosts ANAF's broader family of **public no-auth lookup
services** (VAT/taxpayer registry with `statusRO_e_Factura`, the RO e-Factura register
query, financial statements) — documented separately in
[public/api.md](../public/api.md).

## 1. Upload — `POST /FCTEL/rest/upload`

Submit an invoice/credit-note/message XML.

```
POST https://api.anaf.ro/prod/FCTEL/rest/upload?standard={std}&cif={cif}
     [&extern=DA][&autofactura=DA][&executare=DA]
Content-Type: text/plain        # XML as the raw body (accepted: swagger declares */*)
Authorization: Bearer <token>
```

| Param | Req | Values / meaning |
|---|---|---|
| `standard` | ✔ | `UBL` (invoice), `CN` (Credit Note), `CII`, or `RASP` (buyer→issuer message). |
| `cif` | ✔ | Numeric CIF that receives the error message if the seller can't be identified from the XML. You must have SPV rights for it. |
| `extern` | — | `DA` only — buyer is outside Romania (no CUI/NIF). |
| `autofactura` | — | `DA` only — self-billing (beneficiary issues on supplier's behalf). |
| `executare` | — | `DA` only — filed by an enforcement body on the debtor's behalf. |

**Response (200, `application/xml`)** — a `<header>` element with attributes
`dateResponse`, `ExecutionStatus` (0 = accepted, 1 = rejected), and on success
`index_incarcare` (the **upload index** used by `stareMesaj`); on rejection a nested
`Errors` list with `errorMessage` attributes. 400 returns a JSON `CustomErrorMessage`
(`timestamp`/`status`/`error`/`message`).

**B2C variant:** identical, at `POST /FCTEL/rest/uploadb2c?...`. Live on test + prod
since 01.01.2025; **mandatory for B2C filings since 31.03.2025** (informații-tehnice).

> Provenance: PDF pp. 1–2; response schema from the upload swagger
> ([upload.html](../_sources/efactura-swagger/upload.html), actualizat 04.02.2025).

## 2. Message status — `GET /FCTEL/rest/stareMesaj`

```
GET https://api.anaf.ro/prod/FCTEL/rest/stareMesaj?id_incarcare={index}
```

`id_incarcare` (✔) = the numeric upload index. Response field **`stare`**:

| `stare` | Meaning |
|---|---|
| `ok` | Validated & processed. Download = original invoice + MF e-signature. Invoice reaches the buyer. |
| `nok` | Errors found, not processed. Download = errors file + MF e-signature. Invoice does **not** reach the buyer. |
| `XML cu erori nepreluat de sistem` | Rejected at upload; the error was already returned in the upload response. |
| `in prelucrare` | Still processing — keep polling. |

**Response (200, `application/xml`)** — a `<header>` element: `stare`, and on
`ok`/`nok` an **`id_descarcare`** attribute (feeds `descarcare`). **Query failures**
(unknown/invalid `id_incarcare`, missing SPV rights, daily limit reached) come back as
`<Errors errorMessage="…"/>` **without** `stare` — they are errors about the query,
not a state of the document.

> `anafpy`: `ok`/`nok` are terminal; `in prelucrare` drives the `upload_and_wait` poll
> loop. `nok` is a typed business outcome (not an exception); an `Errors`-only
> response raises `AnafResponseError`.
>
> Provenance: PDF p. 2; response schema + error catalog from the stareMesaj swagger
> ([staremesaj.html](../_sources/efactura-swagger/staremesaj.html)).

## 3. Message lists

### 3a. `GET /FCTEL/rest/listaMesajeFactura` (by days)

```
GET .../listaMesajeFactura?zile={1..60}&cif={cif}[&filtru={E|T|P|R}]
```

### 3b. `GET /FCTEL/rest/listaMesajePaginatieFactura` (paginated, by time range)

```
GET .../listaMesajePaginatieFactura?startTime={ms}&endTime={ms}&cif={cif}&pagina={n}[&filtru=...]
```
`startTime`/`endTime` = **unix-timestamp milliseconds** (e.g. `1646037374000`).

**`filtru`** (optional): `E`=ERORI FACTURA, `T`=FACTURA TRIMISĂ, `P`=FACTURA PRIMITĂ,
`R`=MESAJ CUMPĂRĂTOR PRIMIT / MESAJ CUMPĂRĂTOR TRANSMIS (both directions).

**Response fields (per message):** `data_creare`, `cif`, `id_solicitare` (the upload
index), `detalii`, `cif_emitent` (seller), `cif_beneficiar` (buyer), `tip`
(`FACTURA TRIMISA` | `FACTURA PRIMITA` | `ERORI FACTURA` | `MESAJ CUMPARATOR …`), and
**`id`** (used by `descarcare`).

**Response envelope (paginated, 3b)** — alongside `mesaje[]`:
`numar_inregistrari_in_pagina`, `numar_total_inregistrari_per_pagina` (500),
`numar_total_inregistrari`, **`numar_total_pagini`**, `index_pagina_curenta`,
`serial`, `cui`, `titlu`. The non-paginated list (3a) caps at **500 messages** and
errors with "folositi endpoint-ul cu paginatie" beyond that.

**200-with-`eroare`**: both list endpoints return errors *and* the no-results note in
the same `eroare` field on HTTP 200. Known no-results wordings: `"Nu exista mesaje in
intervalul selectat"` (3b) / `"Nu exista mesaje in ultimele {N} zile"` (3a). Everything
else (`CIF … nu este un numar`, `Nu aveti drept in SPV pentru CIF=…`, invalid
`startTime`/`endTime`/`pagina`/`filtru`, page > total pages, daily call limit reached)
is a genuine error.

> Provenance: PDF pp. 2–4; envelope + `eroare` catalog from the lista swagger
> ([listamesaje.html](../_sources/efactura-swagger/listamesaje.html)).

## 4. Download — `GET /FCTEL/rest/descarcare`

```
GET https://api.anaf.ro/prod/FCTEL/rest/descarcare?id={id}
```
`id` (✔) = the `id` from a `listaMesaje` entry. Returns a **ZIP with two XML files**:
the original invoice **or** the identified errors (as applicable), and the **MF
electronic signature**.

> `anafpy`: this is the `DownloadedMessage` — preserve both raw XML bytes (the signed
> original is the legally valid artifact).
>
> Provenance: PDF p. 4.

## 5. Validate XML — `POST /FCTEL/rest/validare/{std}`

```
POST https://api.anaf.ro/prod/FCTEL/rest/validare/{FACT1|FCN}      # oauth2
POST https://webservicesp.anaf.ro/prod/FCTEL/rest/validare/{FACT1|FCN}   # no auth
Content-Type: text/plain        # XML in the body
```
`std` (✔): `FACT1` (invoice) or `FCN` (credit note). **Server-side** validation.
Available **without auth** on `webservicesp.anaf.ro`.

Response (JSON): `{"stare": "ok"|"nok", "Messages": [{"message": "..."}], "trace_id":
"..."}` — `Messages` present on `nok`.

> Provenance: PDF p. 4; response schema confirmed by the validare swagger
> ([validare.html](../_sources/efactura-swagger/validare.html)).

## 6. XML → PDF — `POST /FCTEL/rest/transformare/{std}[/{novld}]`

```
POST https://api.anaf.ro/prod/FCTEL/rest/transformare/{FACT1|FCN}[/DA]
Content-Type: text/plain        # XML in the body
```
`std` (✔): `FACT1` | `FCN`. Optional `novld=DA` skips validation (⚠️ ANAF does not
guarantee correctness of the PDF for unvalidated XML). Also available no-auth on
`webservicesp.anaf.ro`.

> Provenance: PDF p. 5.

## 7. Validate signature — `POST /api/validate/signature`

```
POST https://api.anaf.ro/api/validate/signature                  # oauth2
POST https://webservicesp.anaf.ro/api/validate/signature         # no auth
multipart/form-data:
  file      = invoice XML
  signature = signature XML
```
Both files come from the `descarcare` ZIP. **Response (200, JSON):** `{"msg": "…"}` for
**both** outcomes — valid and invalid are distinguished only by the wording (*"…au fost
validate cu succes…"* vs *"…NU au putut fi validate cu succes…"*); a technical error is
HTTP 400 with the same `{msg}` shape. Note the path sits at the **host root** — no
`FCTEL/rest` prefix and no test/prod segment.

> Provenance: PDF p. 5; response shape from the signature swagger
> ([validaresemnatura.html](../_sources/efactura-swagger/validaresemnatura.html),
> 03.09.2024).

## 8. Rate limits (per method)

Global (`api.anaf.ro`): **1000 requests/minute** (see the
[OAuth doc](../oauth/authentication.md) §8). On top of that, per-method daily limits:

| Method | Limit |
|---|---|
| `upload` | max **1000 RASP** (buyer-message) files/day/CUI; **no limit** for invoice files. |
| `stareMesaj` | max **100 queries per message**/day; no limit on total queries/day/CUI. |
| `listaMesajeFactura` (3a) | max **1500 queries**/day/CUI. |
| `listaMesajePaginatieFactura` (3b) | max **100 000 queries**/day/CUI. |
| `descarcare` | max **10 downloads per message**/day; no limit on total downloads/day/CUI. |

Limits can change; repeated over-limit calls can get the user (and, in serious cases,
the application) blocked. (An older lista swagger example mentions a 1000/day list
limit — the limits file is newer and is the authority.)

> Provenance: [limiteApeluriAPI.txt](../_sources/limiteApeluriAPI.txt)
> (retrieved 2026-07-02).

## `anafpy` endpoint map

| `anafpy` method | HTTP |
|---|---|
| `upload(xml, standard, cif, *, extern, autofactura, executare)` | `POST /FCTEL/rest/upload` |
| `upload(..., b2c=True)` | `POST /FCTEL/rest/uploadb2c` |
| `get_status(index)` | `GET /FCTEL/rest/stareMesaj` |
| `list_messages(cif, *, days \| start+end, filter=None)` → `AsyncIterator[MessageListItem]` | `GET /FCTEL/rest/listaMesajePaginatieFactura` (paged internally) |
| `download(id)` → `DownloadedMessage` | `GET /FCTEL/rest/descarcare` |
| `validate_remote(xml, standard)` | `POST /FCTEL/rest/validare/{std}` |
| `to_pdf(xml, standard, validate=True)` | `POST /FCTEL/rest/transformare/{std}` |
| `validate_signature(file, signature)` | `POST /api/validate/signature` |

**Implementation notes**

- Bodies are sent as **`Content-Type: text/plain`** with the XML as the raw body. The
  PDF mandates `text/plain` for `validare`/`transformare`; for `upload` it says nothing
  and the swagger declares the request body `*/*`, so `text/plain` is a safe uniform
  choice, not a requirement.
- **Listing**: `list_messages` is a single async iterator that pages
  `listaMesajePaginatieFactura` under the hood (`days` is converted to a `[now-days, now]`
  millisecond window; the non-paginated `listaMesajeFactura` (3a) is not used). It stops
  on the first empty page and honours the **`numar_total_pagini`** envelope field
  (confirmed by the lista swagger). ANAF returns the same `eroare` field for both "no
  messages in interval" and genuine errors — the former yields an **empty iterator**,
  the latter **raises `AnafResponseError`** (matched by wording; see
  `is_empty_result_message`; the official wordings are catalogued in §3).
- `download` returns a **ZIP** (binary) — handle as bytes, unzip to the two XML members.
- The public `webservicesp.anaf.ro` no-auth `validare`/`transformare` could power a
  zero-credential "lint my invoice" path; keep behind the same `Validator` seam.
