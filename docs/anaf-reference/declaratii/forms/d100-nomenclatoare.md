---
title: D100 nomenclatoare — the budget-obligation code list (cod_oblig → budget account, periodicity, scadență, completion model)
service: declaratii
language: en
sources:
  - url: http://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/structura_D100-D710_0126_170626.pdf
    title: "D100/D710 structure annex, 2026 revision — 'Nomenclatorul obligațiilor de plată la bugetul de stat' (code, legal basis, budget account, periodicity, term, scadență, completion model)"
    retrieved: 2026-07-17
  - url: http://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/d100_24022022.xsd
    title: "D100 v2 XSD — Int_listaCodObligSType (the frozen 72-code enum, superseded by the jar)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/legislatie/OPANAF_57_2026.pdf
    title: "OPANAF 57/2026 — added positions 113 (cod 702) and 114 (cod 247)"
    retrieved: 2026-07-17
compiled: 2026-07-17
compiled_by: claude-opus-4-8
last_verified: 2026-07-17
status: draft
---

# D100 — nomenclatoare (budget-obligation code list)

The `<obligatie>/@cod_oblig` values, split out of [d100.md](d100.md) because the
active list runs past 100 codes. Source of truth is the **"Nomenclatorul
obligațiilor de plată la bugetul de stat"** in the D100/D710 structure annex
(`structura_D100-D710_0126_170626.pdf`); ANAF's validator jar
(`D100Validator.jar`, `J21.0.6`) is authoritative and **carries a newer list
than the frozen 2022 XSD** — the XSD's `Int_listaCodObligSType` enumerates only
72 codes, the jar 100+ (verified: `cod 702`, added 01/2026, validates). Romanian
labels are kept verbatim, with an English gloss.

**How the columns work (verified against the jar):**

- **`cod_bugetar`** is jar-enforced per code (rule R14b). For the single-account
  ("contul unic") taxes the jar accepts **both** the current `5503` **and** the
  legacy `20470101` (both verified clean). Dedicated accounts (`20Axxxxxxx`,
  `26Axxxxxxx`, `5505`–`5509`, ...) are enforced to the exact value the R14b
  message names — put a placeholder, run DUK once, copy it. A trailing `X` in the
  annex means "pad with `X` to 10 characters"; the jar compares against the
  unpadded value (`702` → `20A333400`, not `20A333400X`).
- **Period** is the reporting-period cadence: **L** monthly, **T** quarterly
  (`luna` = last month of the quarter, `3`/`6`/`9`/`12`), **A** annual, **S**
  semiannual. Some codes flip to **L** when `d_dizolv=1` (dissolution).
- **Model** is the completion model (`1#`…`10#`) — the `suma_*` relationship the
  jar enforces (see [d100.md](d100.md#completion-models-the-suma_-relationship-per-code-family)).
- **Scad.** is the scadență shorthand; expand it with the legend at the bottom.

## Withholding on income paid to residents (monthly)

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `150` | Impozit pe dividende distribuite | Dividends distributed | `5503` | L | 25LU | 1# |
| `604` | Impozit venituri din dividende (PF) | Dividends to individuals | `5503` | L | 25LU | 1# |
| `605` | Impozit venituri din dobânzi | Interest | `5503` | L | 25LU | 1# |
| `606` | Impozit venituri din lichidarea unei PJ | Liquidation | `5503` | L | 25LU | 1# |
| `608` | Impozit venituri din premii | Prizes | `5503` | L | 25LU | 1# |
| `621` | Impozit venituri din jocuri de noroc | Gambling winnings | `5503` | L | 25LU | 1# |
| `620` | Impozit transfer proprietăți imobiliare (patrimoniu personal) | Real-estate transfer (individuals; set by notaries) | `20A031800` | L | 25LU | 1# |
| `629` | Impozit transfer dezmembrăminte drept proprietate (condiție suspensivă) | Dismemberment of property rights | `20A031800` | L | 25LU | 1# |
| `690` | Impozit venituri din alte surse | Other sources | `5503` | L | 25LU | 1# |
| `628` | Impozit venituri din cedarea folosinței bunurilor (non-agricole) | Rental (non-agricultural) | `5503` | L | 25LU | 1# |
| `626` | Plăți anticipate impozit venituri activități independente | Advance tax, independent activities | `5503` | L | 25LU | 1# |

## Corporate income tax / advance payments (quarterly)

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `102` | Plăți anticipate impozit pe profit (instituții de credit) | Advance profit tax, banks (trim. I–IV) | `5503` | T | 25LU / 25LS (trim IV) | 8# |
| `103` | Impozit pe profit / plăți anticipate (PJ române) | Profit tax, Romanian legal persons | `5503` | L/T | 25LU / 25LS | 8# |
| `105` | Impozit pe profit / plăți anticipate (PJ străine) | Profit tax, foreign legal persons | `5503` | T | 25LU / 25LS | 8# |
| `108` | Impozit pe profit datorat art. 40³ | Profit tax, art. 40³ | `20A020800X` | T | 25LU | 1# |

`103` carries the `d_modif` header flag (last quarter before a modified fiscal
year); `102`/`103`/`105` scadență for **quarter IV** is `25LS` = the 25th of the
fiscal-year-end month.

## Micro-enterprise (quarterly)

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `121` | Impozit pe veniturile microîntreprinderilor | Micro-enterprise income tax | `5503` | T | 25LU | 9# |
| `115` | Diferență impozit pe profit redirecționată în plus | Redirected profit-tax surplus | `20A010100` | L | (`an ≥ 2021`) | 1# |
| `125` | Diferență impozit micro redirecționată în plus | Redirected micro-tax surplus | `20A020600` | L (luna=12) | (`an ≥ 2021`) | 1# |

**`121` requires `cota="1"`** (1% rate) for `an ≥ 2026` — see
[d100.md](d100.md#special-attention-gotchas). `115`/`125` have a bespoke
scadență (`luna + 6/3/1` months; see the annex formula).

## Non-resident withholding (monthly)

| `cod_oblig` | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|
| `631` | Dividends (non-residents) | `5503` | L | 25LU | 1# |
| `632` | Interest (non-residents) | `5503` | L | 25LU | 1# |
| `633` | Royalties (non-residents) | `5503` | L | 25LU | 1# |
| `634` | Commissions (non-residents) | `5503` | L | 25LU | 1# |
| `635` | Sport/entertainment (non-residents) | `5503` | L | 25LU | 1# |
| `636` | Services rendered by non-residents | `5503` | L | 25LU | 1# |
| `637` | Prizes to non-resident individuals | `5503` | L | 25LU | 1# |
| `639` | Liquidation of a Romanian PJ by non-residents | `5503` | L | 25LU | 1# |
| `640` | Remuneration to non-resident administrators | `5503` | L | 25LU | 1# |
| `641` | Transfer of fiduciary patrimony | `5503` | L | 25LU | 1# |
| `642` | Transfer of securities / derivatives | `5503` | L | 25LU | 1# |

## Disability fund

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `810` | Vărsăminte de la PJ pentru persoanele cu handicap neîncadrate | Disability-employment levy | `5503` | L | 25LU | 1# |

## Excise (monthly; may repeat with different scadențe)

Model `5#` throughout. Budget codes are `20A140xxx`. Excise lines are the one
exception to the unique-`(cod_oblig, scadenta)` rule — several rows with the same
code but different scadențe are allowed.

| `cod_oblig` | Gloss | `cod_bugetar` |
|---|---|---|
| `211` | Beer | `20A140205` |
| `216` | Still wine | `20A140208` |
| `212` | Sparkling wine | `20A140203` |
| `217` | Still fermented beverages (other than wine) | `20A140207` |
| `213` | Sparkling fermented beverages | `20A140204` |
| `214` | Intermediate products | `20A140202` |
| `215` | Ethyl alcohol | `20A140201` |
| `221` | Cigarettes | `20A140301` |
| `222` | Cigars | `20A140302` |
| `224` | Fine-cut smoking tobacco | `20A140303` |
| `225` | Other smoking tobacco | `20A140304` |
| `231` | Leaded petrol | `20A140101` |
| `232` | Unleaded petrol | `20A140102` |
| `233` | Diesel | `20A140103` |
| `238` | Kerosene | `20A140108` |
| `235` | LPG | `20A140105` |
| `236` | Natural gas | `20A140106` |
| `234` | Heavy fuel oil | `20A140104` |
| `237` | Coal and coke | `20A140107` |
| `270` | Electricity | `20A140600` |
| `226` | Heat-not-burn tobacco products | `20A140306` |
| `228` | Heat-not-burn tobacco substitutes | `20A140307` |
| `229` | Nicotine products for oral use (no tobacco) | `20A140309` |
| `245` | Sugary non-alcoholic drinks (5–8 g/100 ml) | `20A141000` |
| `246` | Sugary non-alcoholic drinks (> 8 g/100 ml) | `20A141000` |
| `247` | Chewing / nasal tobacco (from 12/2025) | `20A140310X` |

## Gambling / gaming taxes

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `504` | Taxa anuală de autorizare a jocurilor de noroc | Annual gaming-authorization tax | `20A160103` | L | 25LU | 6# |
| `534` | Taxa aferentă autorizației de exploatare | Gaming-operation tax | `20A160108` | L | FREE* | 1# |
| `535` | Taxa de acces pentru jocurile de noroc | Gaming access tax | `20A160104` | L | 25LU | 1# |
| `536` | Taxa licență jocuri de noroc | Gaming license tax | `20A160107` | L | FREE* | 1# |
| `537` | Taxa autorizare jocuri (anuală/integrală) | Gaming authorization (annual) | `20A160108` | A | FREE* | 1# |
| `538` | Taxa pentru videoloterie | Video-lottery tax | `20A160109` | L | FREE* | 1# |
| `539` | Taxa de viciu | Vice tax (4 quarterly rates) | `20A160110` | L | FREE** | 1# |
| `541` | Taxa lunară jocuri de noroc online | Monthly online-gaming tax | `20A160113` | L | 25LU | 1# |
| `553` | Taxa de promovare a jocurilor de noroc | Gaming-promotion tax | `20A160114` | L | 25LU / FREE* | 1# |
| `551` | Taxă datorată Comitetului Olimpic și Sportiv Român | COSR levy | `5505` | L | FREE* | 1# |
| `552` | Taxă datorată Comitetului Național Paralimpic | CNP levy | `5506` | L | FREE* | 1# |

## Resource royalties / mining / oil

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `750` | Taxa pe activitatea de prospecțiune, explorare, exploatare | Prospecting/exploration tax | `20A160400` | L | 25LU / 2512AC | 1# |
| `755` | Redevențe miniere | Mining royalties | `20A300501` | T | 25LU | 1# |
| `756` | Redevențe petroliere | Oil royalties | `20A300502` | T | 25LU | 1# |
| `758` | Redevențe contracte concesiune terenuri agricole | Agricultural-land concession royalties | `20A300505` | L | 25LU | 1# |
| `766` | Redevență concesiune resurse la suprafață | Surface-resource concession royalty | `20A300501X` | L | 25LU | 1# |
| `767` | Redevență concesiune terenuri agricole (destinație agricolă) | Agricultural-land concession royalty | `20A300505X` | L | 25LU | 1# |
| `780` | Vărsăminte din profitul net al regiilor autonome | Autonomous-authority net-profit levy | `5503` | L (AC) | 2807/2907AC | 1# |
| `781` | Dividende de virat de autoritățile publice centrale | Dividends payable by central authorities | `20A300804` | L (AC) | 2807/2907AC | 1# |

## Energy / natural-resource special taxes

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `711` | Impozit venituri suplimentare dereglementare gaze | Gas price-deregulation surtax | `20A121100` | L | 25LU | 1# |
| `712` | Impozit venituri exploatare resurse naturale (altele decât gaze) | Natural-resource exploitation tax | `20A121200` | L | 25LU | 1# |
| `713` | Impozit monopol natural energie/gaze | Natural-monopoly tax | `20A121300` | L | 25LU | 1# |
| `708` | Contribuție la Fondul de Tranziție Energetică | Energy-transition fund contribution | `5508` | L | 25LU | 1# |
| `709` | Contribuție de solidaritate (OUG 186/2022) | Solidarity contribution (energy) | `5509` | A/L | 2506AU | 1# |
| `494` | Contribuție trimestrială temporară de solidaritate | Temporary quarterly solidarity contribution | `26A120900` | T | 25LU2 | 7# |
| `703` | Contribuție de solidaritate (OUG 24/2026) | Solidarity contribution (fuel, 04.2026–03.2027) | `20A122000` | L | 25LU | 1# |
| `702` | Taxa logistică pentru gestionarea fluxurilor de bunuri extracomunitare | Extra-EU goods logistics tax (from 01/2026) | `20A333400` | L | 25LU | 1# |

## Health contributions (quarterly)

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `450` | Contribuție trimestrială pentru medicamente (clawback) | Medicines clawback | `26A120900` | T | 25LU2 | 7# |
| `455` | Contribuție cost-volum / cost-volum-rezultat | Cost-volume contribution | `26A121400` | T | 25LU2 / FREE | 7# |
| `456` | Contribuție volume medicamente peste contract | Over-contract medicines volume | `26A121500` | T | 25LU2 | 7# |

## Specific / turnover taxes

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `117` | Impozit specific pe cifra de afaceri (instituții de credit — IMCA) | Turnover tax, credit institutions | `5503` / `20A122100` | T | 25LU / 25L3 (trim IV) | 7# |
| `116` | Impozit specific pe cifra de afaceri (petrol și gaze — ICAS) | Turnover tax, oil & gas | `5503` / `20A122200` | T | 25LU / 25L6 (trim IV) | 7# |
| `130` | Impozit specific unor activități (historical, ≤ 12.2023) | Specific-activity tax (HORECA) | `5503` | S | 25LU | 10# |

## Top-up tax (Pillar Two)

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `131` | Impozit suplimentar (an ≥ 2023) | Top-up tax (IIR/UTPR) | `20A020900` | A/L | 15LUNI/18LUNI | 1# |
| `132` | Impozit suplimentar național (an ≥ 2023) | Qualified domestic top-up tax (QDMTT) | `20A021000` | A/L | 15LUNI/18LUNI | 1# |

Scadență is `Data_I` (fiscal-year-end date) **+ 15 or 18 months**; these carry
the `Data_I` field.

## Building tax

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `701` | Impozit pe construcții (AC ≥ 2025) | Construction tax | `20A070400` | L | FREE*** | 6# |

Reintroduced for `AC ≥ 2025`; carries the `d_nInf` (newly-established) and
`d_bonif` (bonification) flags that shift its scadență.

## Offshore wind (Legea 121/2024; annual, months 01–03)

| `cod_oblig` | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|
| `714` | Offshore-wind concession royalty | `20A300506` | A | 3003AC | 1# |
| `715` | Concession-area tax | `20A165000` | A | 3003AC | 1# |
| `716` | Built-area tax | `20A165000` | A | 3003AC | 1# |
| `717` | Property-restriction compensation | `20A332600` | A | 3103AC / 25LU | 1# |
| `718` | Damage compensation | `20A332600` | A | 3103AC | 1# |
| `719` | Perimeter-exploitation tax | `20A161200` | A | 3003AC | 1# |

## Offshore petroleum (Legea 256/2018)

| `cod_oblig` | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|
| `128` | Offshore/onshore-deep additional-income tax | `500401XXXX` / `5507XXXXXX` | L | 25LU | 1# |
| `754` | Right-of-way compensation | `20A332600X` | L | 3103AC / 25LU | 1# |
| `759` | Right-of-way damage compensation | `20A332600X` | L | 25LU | 1# |

## Special annual tax (Legea 296/2023)

| `cod_oblig` | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|
| `707` | Advance payments, special annual tax | `20A363300` | T | 25LU | 1# |
| `706` | Special annual tax, regularized | `20A363300` | A | 3006AU | 1# |

## Other

| `cod_oblig` | Obligation (RO) | Gloss | `cod_bugetar` | Period | Scad. | Model |
|---|---|---|---|---|---|---|
| `162` | Impozit înstrăinare terenuri agricole în extravilan | Extra-urban agricultural-land sale | `20A121800X` | L | 25LU | 1# |
| `161` | Impozit venit suplimentar producători energie electrică (12.2021–03.2023) | Electricity-producer surtax (historical) | `20A121700X` | L | 25LU | 1# |
| `825` | Contribuție individuală la pensii militare | Military-pension individual contribution | `20A215000` | L | 25LU | 1# |

## Historical / repealed codes

Present in older filings, **not** in the current active list: `107`, `127`
(agricultural-cooperative exemptions, desființate 05.2018), `130` (specific tax,
≤ 12.2023), `763` (net-asset tax, desființat 03.2020), and the struck codes
`227`, `607`, `611`, `619`, `622`, `623`, `624`, `638`, `941`–`945`. `701`
(construction tax) was repealed 02.2017 and reintroduced for `AC ≥ 2025`. The
jar rejects a code outside its current window for a given `an`.

## Scadență shorthand legend

Verbatim from the annex ("Obs.") — expand each `Scad.` cell with this:

| Code | Meaning |
|---|---|
| `25LU` | 25th of the month **following** the reporting period |
| `25LLU` | 25th of the following month, **before** the modified-fiscal-year change (`103`, `d_modif=1`) |
| `25LU2` | 25th of the **second** month after the period (`450`, `456`, `494`) |
| `25L3` / `25L6` | 25th of the **3rd / 6th** month after quarter IV (`116`, `117`) |
| `25LS` | 25th of the **fiscal-year-end** month (`102`, `103`, `105`) |
| `2512AC` | 25 December of the reporting year (`750`, `luna=12`) |
| `2807AC` / `2907AC` | 28 / 29 July of the reporting year (`780`, `781`; leap vs non-leap) |
| `2505AC` | 25 May of the reporting year (`701`) |
| `3103AC` / `3003AC` | 31 / 30 March of the reporting year, for months 1/2/3 (`754`, `714`–`719`) |
| `15LUNI` / `18LUNI` | 15 / 18 months after the fiscal-year end (`131`, `132`) |
| `FREE` | (excise) any day within the reporting month, or `25LU` |
| `FREE*` | any day of the reporting month or `25LU` (`534`, `536`, `537`, `551`, `552`, `553`) |
| `FREE**` | one of four quarterly dates (`539`) |
| `FREE***` | `701`: `25.LL` (`d_nInf=1`), `25.L5` (`d_bonif=1/null`), or `ZZ.LL` (`d_dizolv=1`) |
