---
name: etransport-declare
description: >
  File a Romanian RO e-Transport declaration and obtain a UIT code from transport
  data found in any source — an email, a PDF invoice, a CMR, a spreadsheet, or the
  conversation. Use when the user wants to declare a transport, get/generate a UIT,
  file an e-Transport declaration, or correct an already-issued one. Drives the
  anafpy MCP tools (etransport_prepare_declaration → etransport_submit).
---

# File an e-Transport declaration

You are filing a legal declaration with Romania's tax authority (ANAF). The flow is:
extract the transport data from whatever source the user has → map it onto the
structured declaration → `etransport_prepare_declaration` (composes the XML, returns
a preview + confirmation token) → **show the preview and get the user's explicit
approval** → `etransport_submit` → poll `etransport_get_status` → report the UIT.

Two rules override everything else:

- **Never invent a value.** Every field on the declaration must come from the source
  document or the user. If a required field is missing, ask — do not guess plates,
  weights, tariff codes, dates, or fiscal codes.
- **Never self-approve.** `etransport_submit` files with ANAF. Only call it after the
  user has seen the preview from `prepare` and explicitly approved it in this
  conversation. The confirmation token is single-use and bound to the exact XML —
  pass back the `xml` the prepare tool returned, verbatim.

## Step 0 — does this transport need declaring at all?

Quick orientation (not legal advice — when unclear, state the rule and let the user
decide). RO e-Transport (OUG 41/2022, as amended) requires a UIT for road transports
in vehicles with a maximum authorized mass of **≥ 2.5 t** carrying goods with total
gross mass **> 500 kg** or total value **> 10,000 RON** (excl. VAT), when the
transport is:

- **domestic** (TTN) carrying goods on ANAF's **high-fiscal-risk list** (fruits &
  vegetables, alcohol, mineral products, clothing/footwear, iron & steel, etc.), or
- **international** — any goods: intra-community acquisition/delivery (AIC/LIC),
  import/export (IMP/EXP), lohn (LHI/LHE), call-off stock (SCI/SCE), or
  intra-community transit with storage/regrouping in Romania (DIN/DIE).

Timing constraints the user must be able to meet:

- The UIT may be obtained at most **3 calendar days before** the declared
  `transport_date`, and **before the vehicle starts moving** on national roads.
- The UIT is valid **5 calendar days** from the declared transport date
  (**15 days** for intra-community acquisitions and call-off stock operations).

## Step 1 — check the connection

Call `auth_status` first. It tells you whether a token is available and — critically —
whether the server is on the **test** or **prod** environment. On `prod` this files a
real declaration; say so in the approval prompt. If there is no token, stop and tell
the user to run `anafpy auth login` in a terminal (the server cannot do it).

## Step 2 — extract and map the data

The source can be anything: a supplier email, an invoice (PDF or e-Factura XML — the
`efactura_download` view exposes parties, lines, quantities, and values), a CMR, a
delivery note, a spreadsheet. Read it and fill the declaration below. What each part
means:

| Field | Required | Notes |
|---|---|---|
| `operation_type` | yes | `TTN` domestic, `AIC`/`LIC` intra-EU in/out, `IMP`/`EXP`, `LHI`/`LHE` lohn, `SCI`/`SCE` call-off stock, `DIN`/`DIE` transit storage. Infer from the route (where the goods enter/leave Romania) and **confirm with the user**. |
| `partner` | yes | name, country, fiscal code. Who this is depends on the operation: the *foreign seller* for AIC/IMP, the *foreign buyer* for LIC/EXP, the *commercial counterparty* for TTN. |
| `vehicle` | yes | `plate`, `carrier_name`/`carrier_country`/`carrier_code`, `transport_date`; `trailer1`/`trailer2` if any. Plates are normalized automatically (spaces/dashes stripped). |
| `start_location` / `end_location` | yes | Exactly **one** of `address` (county + locality + street), `border_point`, or `customs_office` per end. TTN: address → address. AIC: border point or customs office → address. LIC: address → border point. IMP: customs office → address. EXP: address → customs office/border point. ANAF rejects mismatches on upload. |
| `goods[]` | ≥ 1 line | per line: `name`, `operation_scope` (usually `COMERCIALIZARE`; `ACELASI_CU_OPERATIUNEA` when the scope is the operation itself), `quantity` + `unit_code` (UN/ECE: `KGM` kg, `LTR` litre, `H87` piece), `gross_weight` (kg), optional `net_weight`, `tariff_code` (NC, 4/6/8 digits — copy from the invoice, never guess), `value_ron` (excl. VAT). |
| `documents[]` | ≥ 1 | the accompanying document: `doc_type` `CMR` / `FACTURA` / `AVIZ_DE_INSOTIRE_A_MARFII` / `ALTELE`, with `date` and `number`. Cite the actual source document you extracted from. |
| `declarant_ref` | no | the user's own reference (order number, file id) — useful for finding the filing later via `etransport_lookup`. |
| `correction_of_uit` | no | set **only** when correcting an already-issued UIT (see below). |

Helpers while mapping:

- `etransport_nomenclature` lists the accepted values for any enum-coded field
  (`operation_types`, `operation_scopes`, `counties`, `border_points`,
  `customs_offices`, `countries`, `document_types`). Fields accept the member name
  (`TTN`, `CLUJ`, `NADLAC`) or the ANAF numeric code.
- `anaf_lookup_taxpayers` (no auth needed) verifies a Romanian CUI and returns the
  registered company name — use it to check the partner/carrier instead of
  transcribing names from a scan.
- If values are in EUR or another currency, ask the user for the RON value — do not
  apply an exchange rate yourself.

Before preparing, show the user a short summary of what you extracted and which
fields came from where, flagging anything you had to ask about or that looks off
(e.g. gross weight lower than net weight, transport date in the past or more than 3
days ahead).

## Step 3 — prepare

Call `etransport_prepare_declaration` with the declaration (and `cif` if the filing
CIF differs from the configured default). It composes the exact ANAF XML and returns:

- `transport_preview` — the parsed-back declaration, with computed `goods_count` and
  `total_gross_weight`;
- `xml` — the exact document that will be filed;
- `confirmation_token` — single-use, bound to those XML bytes and the CIF.

If `valid` is `false`, fix the reported field problems and prepare again. Nothing has
been filed yet, and prepare does **not** validate against ANAF's business rules —
there is no standalone validator; ANAF validates on upload.

## Step 4 — human approval (hard gate)

Present the preview to the user: operation type, partner, carrier + plate, transport
date, route, each goods line with weight/value, totals, the documents, and **which
environment** (test/prod) it will be filed to. Then ask for explicit approval. Do not
proceed on silence, on a vague "looks good" about something else, or by inferring
consent from the original request.

## Step 5 — submit and poll

On approval, call `etransport_submit` with `document={"xml": <the xml from prepare>}`,
the `confirmation_token`, the same `cif`, and `confirm=True`. A successful upload
returns the **UIT** immediately, but it only becomes valid once processing finishes:
poll `etransport_get_status` with the returned `upload_id` until the state leaves
`in prelucrare` (usually seconds).

- **`ok`** — report the UIT prominently, plus: the declarant must communicate it to
  the transporter/driver before departure, and its validity window (step 0).
  Optionally confirm the record via `etransport_list` or `etransport_lookup`.
- **`nok`** — report ANAF's error messages verbatim, propose the fix, and go back to
  step 3: the token was consumed, so a corrected filing needs a fresh prepare **and a
  fresh approval**.

## After filing

- **Fix a mistake in an issued UIT**: re-run this flow with `correction_of_uit` set
  to that UIT (full declaration again, corrected).
- **Vehicle broke down / plate changed**: `etransport_prepare_vehicle_change` →
  `etransport_submit` (only the plate/trailers change; anything else needs a
  correction).
- **Transport cancelled**: `etransport_prepare_deletion` → `etransport_submit`.
- **Goods received** (beneficiary side): `etransport_prepare_confirmation` with
  `CONFIRMAT` / `CONFIRMAT_PARTIAL` / `INFIRMAT`.

All of these are two-step gated the same way: preview, explicit user approval, then
submit with the token.
