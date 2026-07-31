---
name: etransport-declare
description: >
  File a Romanian RO e-Transport declaration and obtain a UIT code from transport
  data found in any source — an email, a PDF invoice, a CMR, a spreadsheet, or the
  conversation. Use when the user wants to declare a transport, get/generate a UIT,
  file an e-Transport declaration, correct an already-issued one, or asks whether a
  transport must be declared and what the law requires of them. Drives the anafpy
  MCP tools (etransport_prepare_declaration → etransport_submit).
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

## Step 0 — legal orientation: does this need declaring, and by whom?

Quick orientation (not legal advice — when unclear, state the rule and let the user
decide; the compiled legal reference is the `anafref://etransport/legal` resource).
RO e-Transport (OUG 41/2022, as amended; procedure in Ordinul ANAF/AVR
1337/1268/2024) is in full force since **1 January 2026** — non-declaration carries
fines of 20,000–100,000 RON for companies plus, on repeat offences within 12
months, graduated confiscation of the undeclared goods' value. It requires a UIT
for road transports in vehicles with a maximum authorized mass of **≥ 2.5 t**
carrying goods with total gross mass **> 500 kg** or total value **> 10,000 RON**
(excl. VAT), when the transport is:

- **domestic** (TTN) carrying goods on ANAF's **high-fiscal-risk list** (fruits &
  vegetables, alcohol, mineral products, clothing/footwear, iron & steel, etc.), or
- **international** — any goods: intra-community acquisition/delivery (AIC/LIC),
  import/export (IMP/EXP), lohn (LHI/LHE), call-off stock (SCI/SCE), or
  intra-community transit with storage/regrouping in Romania (DIN/DIE).

**Exemptions** — if one applies, say so and stop; do not declare what the law does
not ask to be declared:

- transports for diplomatic missions, consular offices, international
  organizations, NATO/EU/Partnership-for-Peace forces, or under
  security-classified contracts;
- excise goods moving through EMCS with an e-DA/e-DAS (duty suspension, or duty
  paid in the dispatch member state);
- postal parcels carried by postal service providers;
- agricultural products bought from producers on the *carnet de comercializare*,
  transports by individual agricultural producers to the point of sale, and
  vegetal agricultural products moved after harvest.

**Who must declare** is fixed by law per operation — check that the filing CIF (from
`auth_status`) is the obligated party, and flag a mismatch instead of filing past
it: the RO supplier (TTN, LIC, call-off stock out), the RO beneficiary/client (AIC,
call-off stock in), the consignee/shipper named in the customs declaration
(IMP/EXP), the RO service provider or beneficiary of the processing (lohn), the
depozitar (DIN/DIE).

Timing constraints the user must be able to meet:

- The UIT may be obtained at most **3 calendar days before** the declared
  `transport_date`, and no later than the border crossing on entry / the place of
  import, respectively **before the vehicle starts moving**, as the case may be.
- The UIT is valid **5 calendar days** from the declared transport date — **15
  days** for intra-community acquisitions (AIC), transit to storage (DIN), and the
  national nontransfer / call-off stock legs (LHI/LHE, SCI/SCE). Using a UIT past
  its window is a sanctioned contravention, not a formality.
- Once the vehicle starts moving (or crosses the border inbound), the declared
  data **can no longer be changed** — the one exception is the vehicle
  identification (see "After filing").

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
| `start_location` / `end_location` | yes | Exactly **one** of `address` (county + locality + street), `border_point`, or `customs_office` per end. Which combination each operation type expects is in the rules table below — ANAF rejects mismatches on upload. |
| `goods[]` | ≥ 1 line | per line: `name`, `operation_scope` (usually `COMERCIALIZARE`; `ACELASI_CU_OPERATIUNEA` when the scope is the operation itself), `quantity` + `unit_code` (UN/ECE: `KGM` kg, `LTR` litre, `H87` piece), `gross_weight` (kg), optional `net_weight`, `tariff_code` (NC, 4/6/8 digits — copy from the invoice, never guess), `value_ron` (excl. VAT). |
| `documents[]` | ≥ 1 | the accompanying document: `doc_type` `CMR` / `FACTURA` / `AVIZ_DE_INSOTIRE_A_MARFII` / `ALTELE`, with `date` and `number`. Cite the actual source document you extracted from. |
| `declarant_ref` | no | the user's own reference (order number, file id) — useful for finding the filing later via `etransport_lookup`. |
| `correction_of_uit` | no | set **only** when correcting an already-issued UIT (see below). |

ANAF enforces these **cross-field rules on upload** (prepare deliberately doesn't —
map the data so it survives them):

| `operation_type` | Partner country | `operation_scope` per goods line | Typical route |
|---|---|---|---|
| TTN (30) | RO only | `COMERCIALIZARE`, `TRANSFER_INTRE_GESTIUNI`, `BUNURI_PUSE_LA_DISPOZITIA_CLIENTULUI` or `ALTELE` | address → address |
| AIC (10) | EU, not RO | any scope except the two TTN-only transfers and 9999 | border point → address |
| LIC (20) | EU, not RO | `COMERCIALIZARE`, `GRATUITATI`, `OPERATIUNI_DE_LIVRARE_CU_INSTALARE`, `LEASING_FINANCIAR_OPERATIONAL`, `BUNURI_IN_GARANTIE` or `ALTELE` | address → border point |
| LHI / SCI (12/14) | EU, not RO | `ACELASI_CU_OPERATIUNEA` | border point → address |
| LHE / SCE (22/24) | EU, not RO | `ACELASI_CU_OPERATIUNEA` | address → border point |
| IMP (40) | outside the EU | `ACELASI_CU_OPERATIUNEA` | customs office or border point → address |
| EXP (50) | outside the EU | `ACELASI_CU_OPERATIUNEA` | address → customs office or border point |
| DIN / DIE (60/70) | EU, not RO | `ACELASI_CU_OPERATIUNEA` | like AIC / like LIC |

- Customs offices are **import/export only**: at the start of an IMP, at the end of
  an EXP — every other operation uses addresses and border points.
- `tariff_code`, `net_weight` and `value_ron` are **required on every goods line
  except for DIN/DIE**, where they may be omitted.
- `prior_notifications` only for the intra-community operations
  (AIC/LHI/SCI/LIC/LHE/SCE) — ANAF rejects them elsewhere.
- For TTN, the partner's fiscal code is required: a valid RO code, or `PF` for a
  private individual. A RO carrier always needs a valid `carrier_code` (`PF`
  accepted on TTN).

Helpers while mapping:

- `etransport_nomenclature` lists the accepted values for any enum-coded field
  (`operation_types`, `operation_scopes`, `counties`, `border_points`,
  `customs_offices`, `countries`, `document_types`). Fields accept the member name
  (`TTN`, `CLUJ`, `NADLAC`) or the ANAF numeric code. `kind="unit_codes"` lists
  the closed UN/ECE unit-code list ANAF accepts for goods lines — check it before
  guessing a unit (kilogram is `KGM`, piece is `H87`; `KG`/`PCS` don't exist).
- `anaf_lookup_taxpayers` (no auth needed) verifies a Romanian CUI and returns the
  registered company name — use it to check the partner/carrier instead of
  transcribing names from a scan.
- If values are in EUR or another currency, ask the user for the RON value — do not
  apply an exchange rate yourself.
- **Which weight a document states**: unless a document explicitly labels its
  figure otherwise, a weight on an *invoice* is the **net weight** of the goods,
  while a weight on a *transport document* (CMR, Aviz de însoțire a mărfii) is the
  **gross weight**. So an invoice-only source gives you `net_weight` — ask for the
  gross rather than reusing the figure, and treat identical gross and net copied
  from a single document as a red flag to raise in the summary.

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

Present the declaration with the fixed template below, filled **from
`transport_preview`** — the declaration parsed back from the XML that will actually
be filed — never from your own extraction notes, so the user reviews what ANAF will
receive. Then ask for explicit approval. Do not proceed on silence, on a vague
"looks good" about something else, or by inferring consent from the original
request.

```markdown
---

### 📋 e-Transport declaration `REVIEW BEFORE FILING`

<🟢 | 🔴> **Environment: <TEST — no real filing | PROD — this files a real declaration with ANAF>**
Filing CIF `<cif>` · Operation **<SIGLA> — <label from etransport_nomenclature>**
Correction of UIT `<uit>`

#### Transport

|---|---|
| Partner | <name> — <country>, <fiscal code> |
| Carrier | <carrier_name> — <carrier_country>, <carrier_code> |
| Vehicle | <plate> + trailer(s) <trailer1>, <trailer2> |
| Transport date | <YYYY-MM-DD> |
| From | <locality, county — street number | border point | customs office> |
| To | <locality, county — street number | border point | customs office> |
| Reference | <declarant_ref> |

#### Goods — <goods_count> line(s) · <total_gross_weight> kg gross · <total value> RON

| # | Goods | Quantity | Gross kg | Net kg | NC code | Value (RON) |
|---|---|---|---|---|---|---|
| 1 | <name> | <quantity> <unit_code> | <gross_weight> | <net_weight> | <tariff_code> | <value_ron> |

#### Documents

<document-type label> no. <number> / <date>; …

⚠️ <flags carried over from step 2, if any>

---

File this declaration with ANAF (<test | prod>)?
```

Template rules:

- **Drop, don't blank**: omit the *Correction of UIT* line, the *Reference* row, the
  trailer suffix, and the ⚠️ line entirely when unset; inside the goods table an
  unset optional cell is `—`.
- **Totals**: total value is the sum of `value_ron` over the lines that carry one —
  if some lines don't, write `<sum> RON (<n> of <goods_count> lines)`.
- **Frame**: the horizontal rules and the two-emoji vocabulary (📋 title, 🟢 test /
  🔴 prod) are the visual frame that sets the declaration apart from conversation —
  keep them exactly as templated, and keep the approval question *outside* the
  closing rule.
- **Scope**: when every goods line has the same `operation_scope`, append it once to
  the Goods heading (`… RON · scope Comercializare`); otherwise add a *Scope* column.
- **Post-incident**: if `post_incident` is true, add a bold
  `**Post-incident declaration (declPostAvarie)**` line under the environment line.
- **Human labels, not member names**: render enum-coded values with ANAF's labels
  from `etransport_nomenclature` — the operation sigla with its label, goods scopes
  (`Comercializare`, `Același cu operațiunea`), document types (`Factura`, `Aviz de
  însoțire a mărfii`), and border points / customs offices by name.
- Keep everything else verbatim from the preview (plates already normalized,
  dates ISO).

## Step 5 — submit and poll

On approval, call `etransport_submit` with `document={"xml": <the xml from prepare>}`,
the `confirmation_token`, the same `cif`, and `confirm=True`. A successful upload
returns the **UIT** immediately, but it only becomes valid once processing finishes:
poll `etransport_get_status` with the returned `upload_id` until the state leaves
`in prelucrare` (usually seconds).

- **`ok`** — report the UIT prominently, plus its validity window (step 0) and the
  legal obligations that now attach to it — relay them with the UIT, the user may
  not know them:
  - hand the UIT to the transport operator/driver **before the vehicle moves** (or
    by border entry); the driver must present it — in any intelligible form —
    together with the transport documents at a control (ANAF, customs, police);
  - the transport operator must keep the vehicle's GPS positioning data flowing
    for the whole route, and the driver must switch the positioning device on
    before departure and off only after delivery / leaving the country —
    sanctioned since 1 January 2026;
  - the declaration is now immutable except for a vehicle change (see "After
    filing") — a data mistake discovered later needs a correction filing.
- **Render the UIT card by default.** Call `etransport_lookup` on the UIT — it
  confirms the record and returns ANAF's `data_exp_uit` — then
  `etransport_uit_card` with the filed `xml`, the UIT, `uit_expiry` from the
  lookup (never computed yourself), and a `save_as` full path named after the
  code (e.g. `UIT-<code>.pdf`), in the folder the source documents came from or
  wherever the user keeps artifacts — ask when there is no natural place. Give
  the user the saved path with the returned `summary_text` as the accompanying
  message — that text is also how the driver copies the code on a phone whose
  PDF viewer won't select text.
- **Offer the detail document** — `etransport_uit_details`, the whole filing on
  A4 with the goods table, the copy for the partner company or the user's own
  records — and render it only if the user wants it (`notes` carry
  filing-specific observations only, never boilerplate). Both documents are
  generated locally, not issued by ANAF, and say so on their face; an existing
  file is never replaced unless the user asks for `overwrite=true`.
- **`nok`** — report ANAF's error messages verbatim, propose the fix, and go back to
  step 3: the token was consumed, so a corrected filing needs a fresh prepare **and a
  fresh approval**.
- **ANAF outage**: if the upload fails because the system is down **and ANAF/MF
  have announced the outage on their websites**, the legal deadline defers to the
  end of the next working day after service is restored — including for transports
  already completed by then. Tell the user; the transport itself is not blocked by
  an announced outage.

## After filing

- **Fix a mistake in an issued UIT**: re-run this flow with `correction_of_uit` set
  to that UIT (full declaration again, corrected).
- **Vehicle broke down / plate changed**: `etransport_prepare_vehicle_change` →
  `etransport_submit` (only the plate/trailers change; anything else needs a
  correction).
- **Transport cancelled**: `etransport_prepare_deletion` → `etransport_submit`.
- **Goods received** (beneficiary side): `etransport_prepare_confirmation` with
  `CONFIRMAT` / `CONFIRMAT_PARTIAL` / `INFIRMAT`.

After an accepted correction (new UIT) or vehicle change (new plates), any card
or detail document rendered earlier is stale — re-render it (step 5's flow) so
the driver carries the current data.

All of these are two-step gated the same way: preview, explicit user approval, then
submit with the token. Present them with step 4's frame, adapted:

```markdown
---

### 📋 e-Transport <deletion | vehicle change | confirmation> `REVIEW BEFORE FILING`

<🟢 | 🔴> **Environment: <TEST — no real filing | PROD — this files a real <action> with ANAF>**
Filing CIF `<cif>` · UIT **<uit>**

#### Declared transport

|---|---|
| Declarant | <declarant_name> (`<declarant_code>`) |
| Carrier | <carrier_name> — <carrier_country>, <carrier_code> |
| Vehicle | <plate> + trailer(s) |
| Transport date | <YYYY-MM-DD> |
| Route | <start> → <end> |
| UIT valid until | <uit_expiry> |

#### <operation-specific body — see below>

---

<operation-specific approval question, naming the UIT>
```

- **Declared transport** is context: fill it from a fresh `etransport_lookup` on the
  UIT — never from conversation memory. If the lookup returns nothing, drop the
  section and say so; do not reconstruct it.
- **Deletion** body is `#### Effect`: a bold one-liner — deleting makes the UIT
  invalid and the transport must not run under it. Question:
  `Delete UIT <uit> with ANAF (<test | prod>)?`
- **Vehicle change** body is `#### Vehicle change`: a *Current → New* table for the
  plate and trailers (current from the lookup, `—` if unknown; new values bold),
  plus `Changed at: <datetime | now>`. Drop the Vehicle row from the context table —
  it is the *Current* column. Question:
  `Change the vehicle on UIT <uit> with ANAF (<test | prod>)?`
- **Confirmation** body is `#### Confirmation`: the type's ANAF label in bold
  (**Confirmat**, **Confirmat parţial**, **Infirmat**), the note after a dash.
  Question: `File this confirmation for UIT <uit> with ANAF (<test | prod>)?`
- Step 4's rules apply unchanged: drop unset lines, human labels, frame kept
  verbatim, approval question outside the closing rule.
