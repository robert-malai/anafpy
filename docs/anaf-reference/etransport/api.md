---
title: e-Transport — Web Services API (ETRANSPORT/ws/v1)
service: etransport
language: en
sources:
  - url: https://mfinante.gov.ro/static/10/eTransport/etransport_29072024.pdf
    title: "Serviciile Etransport (official API PDF, 4 pp)"
    source_revision: "29.07.2024"
    retrieved: 2026-06-28
    local_copy: ../_sources/etransport_29072024.pdf
  - url: https://mfinante.gov.ro/ro/web/etransport/informatii-tehnice
    title: "MF — Informații tehnice e-Transport"
    retrieved: 2026-06-28
  - url: https://mfinante.gov.ro/static/10/eTransport/schema_ETR_v2_20230126.xsd
    title: "e-Transport v2 XSD"
    source_revision: "2023-01-26"
    retrieved: 2026-06-28
  - url: https://mfinante.gov.ro/static/10/eTransport/eTransport-validation_v.2.0.2_12082024.sch
    title: "e-Transport Schematron"
    source_revision: "v2.0.2, 12.08.2024"
    retrieved: 2026-07-03
    local_copy: ../_sources/eTransport-validation_v.2.0.2_12082024.sch
  - title: "Swagger presentations (per-endpoint OpenAPI specs, 4 pages)"
    url: https://mfinante.gov.ro/static/10/eTransport/upload_param.html
    source_revision: "upload_param/lista/stare 02.07.2024; info_transportatori 01.07.2024"
    retrieved: 2026-07-02
    local_copy: ../_sources/etransport-swagger/
compiled: 2026-06-28
compiled_by: claude-opus-4-8
last_verified: 2026-07-02
status: draft
---

# e-Transport — Web Services API

Operations for the RO e-Transport system (declaring road transport of goods).
Authentication is the shared [OAuth2 flow](../oauth/authentication.md). The declaration
**schema** is ANAF-proprietary XSD v2 (not UBL; vendored under `/schemas/etransport/`
for codegen). There is **no standalone validator** — ANAF validates on upload; the
business rules it enforces there are ANAF's official **Schematron** (vendored:
[`_sources/eTransport-validation_v.2.0.2_12082024.sch`](../_sources/eTransport-validation_v.2.0.2_12082024.sch),
v2.0.2 — reference only, `anafpy` runs no local validation). This doc is the
**transport/API surface**.

> **Status:** draft, from the official **29.07.2024** API PDF — the current version,
> which **supersedes** older 2023 specs — plus the official per-endpoint **swagger
> presentations** (vendored 2026-07-02 under
> [`_sources/etransport-swagger/`](../_sources/etransport-swagger/upload_param.html)), which supply the
> response schemas the PDF omits. It corrected two earlier assumptions (see
> "Corrections" below).
> **First live TEST confirmation 2026-07-02**: `lista/60/{cif}` on an empty window
> returned HTTP 200 `{"Errors":[{"errorMessage":"Nu exista mesaje in ultimele 60
> zile"}],"dateResponse":"…","ExecutionStatus":1,"trace_id":"…"}` — the documented
> no-results shape (note `ExecutionStatus: 1`, same as genuine errors; the message
> text is the discriminator).
> **Full roundtrip confirmed 2026-07-02** (TEST, tip_op 30 domestic): `upload` →
> `stareMesaj` (`in prelucrare` → `ok`) → `lista` (record present) → `info`. Upload,
> status, lista-with-results, and info are now live-confirmed (shapes below). The one
> surprise was `info`'s no-results shape (see §4).

## Access modes & base URLs

| Mode | Host | Used by `anafpy` |
|---|---|---|
| **OAuth2** (Bearer) | `https://api.anaf.ro/{prod\|test}` | **Yes** |
| Certificate-at-call-time | `https://webserviceapl.anaf.ro/{prod\|test}` | No |

Path prefix: **`/ETRANSPORT/ws/v1/`** (the `ws/v1` is the web-service version and is
constant; the *data-schema* version is a separate `{versiune}` path segment — see
Upload v2). Request bodies are **`Content-Type: application/xml`** (note: e-Factura
uses `text/plain`; e-Transport uses `application/xml`); there is **no JSON request
format** — the declaration is defined by the XSD, and the upload swagger's request
body is XML-only. **Responses are JSON** on every endpoint (unlike e-Factura's XML
`<header>` responses), with errors in an `Errors: [{errorMessage}]` array.

> Provenance: PDF pp. 1–3.

## 1. Upload — `POST /ETRANSPORT/ws/v1/upload/...`

**v1 form:**
```
POST https://api.anaf.ro/prod/ETRANSPORT/ws/v1/upload/{standard}/{cif}
```
**v2 form (adds schema version):**
```
POST https://api.anaf.ro/prod/ETRANSPORT/ws/v1/upload/{standard}/{cif}/{versiune}
```

| Path seg | Req | Values |
|---|---|---|
| `standard` | ✔ | **`ETRANSP`** (string). |
| `cif` | ✔ | Numeric fiscal code, max 13 digits. |
| `versiune` | ✔ (v2 form) | `1` or `2` (data-schema version). **`anafpy` uses `2`.** |

Body = the transport declaration **XML**; `Content-Type: application/xml`.

**Response (200, JSON):** `dateResponse`, `ExecutionStatus` (0 = success), an
**`index_incarcare`** (the upload index for `stareMesaj`), the **`UIT`** code,
`trace_id`, and `ref_declarant`; on rejection an `Errors[]` list with `errorMessage`
entries (e.g. *"Valoarea acceptata pentru parametrul standard este ETRANSP"*).
Live-confirmed 2026-07-02 (TEST): a successful upload returned
`{"dateResponse":"…","ExecutionStatus":0,"index_incarcare":<num>,"UIT":"…",` `
"trace_id":"…","ref_declarant":"…","atentie":"Verificati starea XML-ului transmis.
Codul UIT este valabil din momentul in care apare ca valid dupa apelul de stare"}` —
i.e. the UIT is issued immediately but only becomes valid once `stareMesaj` reports
`ok` (note the `atentie` advisory; `index_incarcare` came back as a JSON **number**).

> `anafpy`: use the **v2 form with `versiune=2`** (decided). `standard` is `ETRANSP`
> (not the 2022 OAuth PDF's stale `ETRANSPORT`).
>
> Provenance: PDF p. 1; response schema from the upload swagger
> ([upload_param.html](../_sources/etransport-swagger/upload_param.html), 02.07.2024).

## 2. Status — `GET /ETRANSPORT/ws/v1/stareMesaj/{id_incarcare}`

```
GET https://api.anaf.ro/prod/ETRANSPORT/ws/v1/stareMesaj/{id_incarcare}
```
`id_incarcare` = the numeric `index_incarcare` from the Upload response.

**Response (200, JSON):** `stare` (`ok` | `nok`), `dateResponse`, `ExecutionStatus`,
`trace_id`; on `nok` an `Errors[]` list with `errorMessage` entries (e.g. *"UIT-ul nu
poate fi identificat."*). Live-confirmed 2026-07-02 (TEST): immediately after a valid
upload `stare` was **`in prelucrare`** (the processing state — poll until terminal),
then `ok` within seconds: `{"stare":"ok","dateResponse":"…","ExecutionStatus":0,
"trace_id":"…"}`.

> Provenance: PDF pp. 2–3; response schema from the stare swagger
> ([stare.html](../_sources/etransport-swagger/stare.html), 02.07.2024).

## 3. List — `GET /ETRANSPORT/ws/v1/lista/{zile}/{cif}`

```
GET https://api.anaf.ro/prod/ETRANSPORT/ws/v1/lista/{zile}/{cif}
```
`zile` = 1..60, `cif` = numeric. Returns **final** states of valid notifications +
valid vehicle changes + any error notifications. Intermediate states (corrections,
deletions) of valid notifications are **not** returned. Records are **not sorted** —
sort locally by `data_creare`.

**Notification types (`tip`):** `NOT` (notification), `COR` (correction), `DEL`
(deletion), `CON` (confirmation), `MVH` (vehicle change).

**Key returned fields:** `tip`, `stare` (`OK` valid / `ERR` error), `uit`, `cod_decl`,
`ref_decl`, `post_avarie` (D/N), `sursa` (A=api / I=web app), `id_incarcare`,
`data_creare`, `data_modif`, **`tip_op`** (operation type — see code list), `data_transp`,
partner `pc_tara`/`pc_cod`/`pc_den`, transporter `tr_tara`/`tr_cod`/`tr_den`, vehicle
`nr_veh`/`nr_rem1`/`nr_rem2`, `modif_veh[]`, `nr_linii`, `gr_tot_neta`, `gr_tot_bruta`,
`val_tot`, `confirmare{}` (`tip_conf`: `10`=confirmat, `20`=confirmat parțial,
`30`=infirmat; plus `obs`, `post_avarie`, `sursa`, `data_decl`, `id_incarcare`), and
`mesaje[]` (`{tip: ERR|WARN|INFO, mesaj}` — for error records at least one `ERR`).

**`tip_op` codes:** `10`=AIC, `12`=LHI, `14`=SCI, `20`=LIC, `22`=LHE, `24`=SCE,
`30`=TTN, `40`=IMP, `50`=EXP, `60`=DIN, `70`=DIE (see XSD for details).

**Response envelope (200, JSON):** notifications under **`mesaje[]`**, alongside
`serial`, `cui`, `titlu`. Errors *and* the no-results note come as
**`Errors: [{errorMessage}]`** (not e-Factura's `eroare` field): e.g.
`"Nu exista mesaje in ultimele 60 zile"` (benign no-results) vs `"Numarul de zile
introdus= 60a nu este un numar intreg"`, `"Nu exista niciun CIF petru care sa aveti
drept in SPV"`, or the daily-limit note (genuine errors).

> Provenance: PDF pp. 1–2; envelope + error catalog from the lista swagger
> ([lista.html](../_sources/etransport-swagger/lista.html), 02.07.2024).

## 4. Info for transporters — `GET /ETRANSPORT/ws/v1/info`

```
GET .../ETRANSPORT/ws/v1/info?cui_op={cui_op}[&cui_decl=][&uit=][&ref_decl=]
```
For transport organizers: active notifications where `cui_op` is the declared organizer.

| Param | Req | Meaning |
|---|---|---|
| `cui_op` | ✔ | Transport organizer/transporter fiscal code (numeric). |
| `cui_decl` | — | Original declarant's fiscal code. |
| `uit` | — | UIT of interest. |
| `ref_decl` | — | Declarant's reference supplied when the UIT was obtained. |

Returns per record: `uit`, `cod_decl`, `den_decl`, `ref_decl`, `data_transp`,
**`data_exp_uit`** (UIT expiry), transporter, vehicle, `modif_veh[]`,
`loc_start`/`loc_final` (`tip_loc`: `PTF` border point / `BV` customs office / `ADR`
national address; with `judet`, `localitate`, `strada`, `numar`, …), and `documente[]`.
The swagger example additionally shows a numeric `id` per record (not in the PDF).

**No-results shape (live-confirmed 2026-07-02, TEST):** unlike every other endpoint,
`info` does **not** use `Errors[]` — a query with no matching records answers HTTP 200
with a **top-level singular `error` string**:
`{"trace_id":"…","dateResponse":"…","error":"Nu exista informatii pentru aceasta
solicitare"}`. (Observed even for a UIT that was just accepted and is listed by
`lista`: `info` is scoped to the *transport organizer's* right to look up others' UITs,
so a self-declared domestic notification returns no `info` record.) `anafpy` surfaces
this via `InfoList.error`, tolerating both `error` and `Errors[]`.

> Provenance: PDF pp. 3–4; example response in the info swagger
> ([info_transportatori.html](../_sources/etransport-swagger/info_transportatori.html),
> 01.07.2024).

## Corrections to earlier assumptions (surfaced by this doc)

1. **OAuth host is `api.anaf.ro` — same as e-Factura**, *not* a different host. The
   per-service difference is the **path** (`/ETRANSPORT/ws/v1/` vs `/FCTEL/rest/`).
   (`webserviceapl.anaf.ro` is only the *certificate-direct* host, which `anafpy`
   doesn't use.) → the shared `_transport` varies the **path prefix**, not the host.
2. **No `descarcare`/ZIP endpoint** in the current e-Transport API. The 2022 OAuth PDF
   (p. 30) still listed one; the informații-tehnice page confirms *"Serviciul de
   Descărcare a fost eliminat de pe mediul de test și de producție"*. e-Transport
   returns the **UIT at upload time** and exposes state via `lista`/`stareMesaj` —
   there is no separate signed-ZIP download. So e-Transport does **not** mirror
   e-Factura's `download`→`DownloadedMessage`; adjust the client design.
3. `standard` = **`ETRANSP`** (the 2022 OAuth PDF's `ETRANSPORT` was stale), and the
   `{versiune}` (data-schema, 1|2) is appended in the v2 upload form.

## `anafpy` endpoint map

| `anafpy` method | HTTP |
|---|---|
| `upload(xml, cif, *, version=2)` | `POST /ETRANSPORT/ws/v1/upload/ETRANSP/{cif}/{version}` |
| `get_status(index)` | `GET /ETRANSPORT/ws/v1/stareMesaj/{index}` |
| `list(days, cif)` | `GET /ETRANSPORT/ws/v1/lista/{days}/{cif}` |
| `info(cui_op, *, cui_decl=None, uit=None, ref_decl=None)` | `GET /ETRANSPORT/ws/v1/info` |

(No `download` — see Corrections #2.)
