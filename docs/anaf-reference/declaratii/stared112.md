---
title: StareD112 — public filing-status and recipisa service
service: declaratii
language: en
sources:
  - url: https://www.anaf.ro/StareD112/
    title: "Vizualizare documente (the query form page)"
    retrieved: 2026-07-16
  - url: https://www.anaf.ro/StareD112/vizualizareStare.do
    title: "Status query endpoint (POST; live-probed: found / not-found / invalid-input shapes)"
    retrieved: 2026-07-16
  - url: https://www.anaf.ro/StareD112/ObtineRecipisa
    title: "Recipisa PDF endpoint (live-probed: real and unknown-index responses)"
    retrieved: 2026-07-16
compiled: 2026-07-16
compiled_by: claude-fable-5
last_verified: 2026-07-17
status: draft
---

# StareD112 (filing status + recipisa download)

`https://www.anaf.ro/StareD112/` is ANAF's public "Vizualizare documente" page:
given a filed document's **upload index** (the number the portal returns on
submission — also the recipisa number) and the taxpayer's **CUI**, it reports
the processing state of the CUI's recent filings and serves the signed
**recipisa** (filing receipt) PDF. There is no official API documentation; this
reference is compiled from the page itself and live probes (2026-07-16, raw
captures under `_sources/stared112/`).

Despite the `D112` in the path, the service covers **all declaration forms**
(live-observed with `F4109` documents; the page's own copy speaks of
"documente depuse" generally) — **including `D406T` test filings**: a D406T
filed on the upload portal appeared here within a minute, form `D406T`, state
`In prelucrare` (live-observed 2026-07-17; the upload portal's success page
itself points recipisa tracking at this service).

## 1. Access model — public, unauthenticated

- **No certificate, no OAuth, no session priming**: a cold `POST` from a fresh
  client works (live-confirmed 2026-07-16). Cookies (`JSESSIONID`, an F5 `TS*`
  cookie) are set on the response but are not required for subsequent calls.
- The **(index, CUI) pair is the access key**: a matching pair returns the
  status of **every** document that CUI filed in the query window, not just
  the queried one.
- Stated limits (from the page copy):
  - queries cover documents filed in the **last three months**;
  - only the **last 200** submissions are visible — after each batch of ~200,
    ANAF asks filers to wait for processing and download the recipisas;
  - the recipisa PDF is downloadable for **60 days** from filing (older rows
    keep their status but lose the download link).

## 2. Status query

```
POST https://www.anaf.ro/StareD112/vizualizareStare.do
Content-Type: application/x-www-form-urlencoded

ghiseu=N&id=<index>&cui=<cui>
```

| field | meaning |
|---|---|
| `ghiseu` | `N` = filed over the internet (`id` is the upload index); `Y` = filed at an ANAF counter (`id` is the registration number) |
| `id` | internet leg: upload index, digits only; counter leg: registration number as issued (the service's text field permits dash/slash-shaped values; no counter capture yet proves a narrower grammar) |
| `cui` | the taxpayer's fiscal code, digits only |

The response is always **HTTP 200** `text/html;charset=ISO-8859-1` (diacritics
as numeric entities). Three page shapes exist:

### 2.1 Results page (pair matched)

Header line: `Documente depuse pentru cui: <cui> in perioada <dd.mm.yyyy> /
<dd.mm.yyyy>` — the window is the trailing three months ending today. Then a
six-column table (the header cells sit directly under `<thead>` with **no
`<tr>`**):

| column | content | example |
|---|---|---|
| Index | upload index (= recipisa number) | `1100000001` |
| Tip document | form/document type | `F4109` |
| Stare document | processing state, one of the four §2.3 texts | `Documentul este valid` |
| Data inregistrare | registration line | `INTERNT-1100000001-2026 din 16.07.2026` |
| Consultați | `recipisa` link (`/StareD112/ObtineRecipisa?numefisier=<index>.pdf`) — **absent once the 60-day window lapses** | |
| Data incarcare | upload date, ISO | `2026-07-16` |

### 2.2 Not-found page (pair matched nothing)

`Nu a fost identificata nicio declaratie cu datele introduse, ...` — a
**business outcome**, listing the possible reasons: wrong pair, the
declaration is not among the last 200 submissions, or more than 3 months have
passed. Same page shape for a valid index paired with the wrong CUI
(live-probed).

### 2.3 Invalid-input page

Non-numeric `id`/`cui` answers `Nu ati introdus un index valid` (HTTP 200).

The four documented states (the results page lists them with explanations):

| state text | meaning |
|---|---|
| `In prelucrare.` | still processing on the central servers — check again later |
| `Fişierul depus nu este un document valid.` | pre-validation failed (unknown type / unsigned / signature has no filing right for the CIF / no reporting period / no XML attached) — **not registered**; fix and refile |
| `Documentul are erori de validare.` | validation errors, detailed in the recipisa — fix and refile |
| `Documentul este valid.` | accepted; data forwarded to the beneficiary institutions |

## 3. Recipisa download

```
GET https://www.anaf.ro/StareD112/ObtineRecipisa?numefisier=<index>.pdf
```

- Known index within the 60-day window: `200`, `Content-Type: application/pdf`,
  `Content-Disposition: inline;filename=<index>.pdf`, the signed one-page
  recipisa (live: 9 078 bytes for a valid F4109).
- Unknown or expired index: **`200` with an empty body** (`Content-Length: 0`,
  still `application/pdf`) — emptiness is the only "not found" signal.
- No session or prior status query is required (live-confirmed cold).

## 4. anafpy mapping

`anafpy.declaratii.status.DeclarationStatusClient`:

- `check_status(index, cui, filed_at_counter=False)` → `DeclarationStatusList`
  (`found=False` for §2.2; §2.3 raises `AnafResponseError` since inputs are
  validated client-side first).
- `download_receipt(index)` → `bytes | None` (`None` for the empty-body case).

MCP: `declaratie_status`, `declaratie_recipisa`. CLI: `anafpy declaratii
status`, `anafpy declaratii recipisa`.
