---
title: e-guvernare declaration inventory — every DUK-validated form, bucketed by SME usage
service: declaratii
language: en
sources:
  - url: http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml
    title: "DUKIntegrator update feed — the authoritative enumeration of electronically filable forms (173 on retrieval) with current validator/PDF jar versions"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Declaratii_R/descarcare_declaratii.htm
    title: "ANAF declaration-download catalog (per-form soft pages; titles for the niche families)"
    retrieved: 2026-07-17
compiled: 2026-07-17
compiled_by: claude-fable-5
last_verified: 2026-07-17
status: draft
---

# e-guvernare declaration inventory

Every form ANAF's DUKIntegrator update feed lists has a validator jar and is
therefore filable electronically (portal upload / e-guvernare). This page is the
full inventory — **173 forms** on 2026-07-17 — bucketed by how often a **typical
SME** (VAT-registered SRL with employees) files them. The buckets drive our
hands-on coverage: the top two buckets each get a per-form quirk file in this
folder (XSD location, authoring gotchas, DUK behaviour), the third is
inventory-only.

Conventions:

- **Validator (J/P)** is the feed's current `versiuneJ`/`versiuneP` — the
  *validator/PDF jar* versions, not the form's XSD version (D300's XSD is at
  `v12` while its jar is `J12.0.1`; the two usually track but are distinct).
- Per-form soft pages live at
  `https://static.anaf.ro/static/10/Anaf/Declaratii_R/<number>.html`
  (e.g. `300.html`); each version row there links the soft PDF, the validator
  zip, the structure PDF, and the XSD. **Newer XSDs are published with a `.xml`
  extension** (e.g. `d300_v12_11022026.xml`); older ones use `.xsd`.
  Known off-pattern pages: **D212** is `declaratie_unica.html` (`212.html`
  404s); **D700** links no standalone XSD — it ships inside the soft zip;
  **D406** (SAF-T) has its own page with `Ro_SAFT_Schema_*.xsd`.
- Validator jars install by dropping the feed's `JURL`/`PURL` jars into the DUK
  `dist/lib/` folder (CLI mode does not auto-update — see the
  [DUK reference](../duk.md) §1).

## Most used (hands-on: quirk file per form)

The recurring compliance calendar of a VAT-registered SRL with employees.

| Form | Purpose | Validator (J/P) | Quirks |
|---|---|---|---|
| D300 | VAT return (decont de TVA) — monthly/quarterly | `J12.0.1` / `P9.0.0` | [d300.md](d300.md) |
| D390 | EU recapitulative statement (VIES) — intra-EU supplies/acquisitions, monthly | `J4.1.2` / `P2.0.0` | [d390.md](d390.md) |
| D394 | Informative return on domestic supplies/purchases — follows the VAT period | `J8.0.2` / `P4.0.0` | [d394.md](d394.md) |
| D100 | Payment obligations to the state budget (withheld taxes, micro-enterprise tax, ...) — monthly/quarterly | `J21.0.6` / `P6.0.0` | [d100.md](d100.md) |
| D112 | Payroll: wage income tax + social contributions, per-employee detail — monthly (quarterly for some employers) | `J26.0.3` / `P3.0.1` | [d112.md](d112.md) |
| D101 | Annual corporate profit tax return | `J11.0.3` / `P10.0.0` | [d101.md](d101.md) |

## So-and-so (hands-on: quirk file per form)

Filed on specific events, specific taxpayer categories, or annually.

| Form | Purpose | Validator (J/P) | Quirks |
|---|---|---|---|
| D700 | Fiscal registration / fiscal-vector changes, the electronic path | `J5.0.3` / `P4.0.3` | [d700.md](d700.md) |
| D406 | SAF-T informative — monthly/quarterly by taxpayer category | `J2.2.18` / `P2.0.1` | [d406.md](d406.md) |
| D205 | Annual informative on income tax withheld at source, per beneficiary | `J9.0.5` / `P5.0.1` | [d205.md](d205.md) |
| D301 | Special VAT return — persons not VAT-registered who owe VAT (e.g. intra-EU acquisitions) | `J1.2.5` / `P1.1.0` | [d301.md](d301.md) |
| D710 | Rectifying declaration — corrects D100/D112 and siblings | `J20.0.6` / `P4.0.0` | [d710.md](d710.md) |
| D212 | Individuals' unified declaration — income tax + CAS/CASS | `J13.0.1` / `P10.0.0` | [d212.md](d212.md) |

## Rarely (inventory only)

Niche regimes, one-off events, historic (pre-D212) individual forms, and
device/institutional reporting. Purposes below are from ANAF's catalog page or
well-established form knowledge; **"—" means the purpose was not verified from
the retrieved sources** (the catalog lists many forms only as "Declarație
electronică") — verify on the form's own page before relying on it.

| Form | Purpose | Validator (J/P) | Notes |
|---|---|---|---|
| A4200 | XML validator app — Z reports and fiscal receipts | `J1.0.4` / `P1.0.4` |  |
| A4201 | XML validator app — currency-exchange activity | `J1.0.1` / `X1.0.0` |  |
| A4202 | XML validator app — taxi activity | `J1.0.0` / `X1.0.0` |  |
| A4203 | XML validator app — other activity types | `J1.0.7` / `X1.0.0` |  |
| B230 | Bulk submission slip (borderou) of D230 forms by NGOs | `J3.0.0` / `P3.0.0` |  |
| C168 | Registration of lease contracts | `J3.0.1` / `P3.0.0` |  |
| C310 | Request to approve transfers from the VAT account | `J1.0.0` / `P1.0.0` |  |
| C801 | Cash-register (AMEF) unique-ID assignment request | `J1.0.5` / `P1.0.0` |  |
| C802 | Cash-register online-mode transition profiles request | `J1.0.0` / `P1.0.0` |  |
| D092 | VAT period change (quarter → month after an intra-EU acquisition) | `J1.0.0` / `P1.0.0` |  |
| D10 | Retail prices per cigarette sort | `J1.0.0` / `P1.0.0` |  |
| D101G | Corporate profit tax — consolidated fiscal group | `J2.0.0` / `P2.0.0` |  |
| D107 | Informative on sponsorship beneficiaries | `J2.0.0` / `P1.0.2` |  |
| D120 | Annual excise return (decont de accize) | `J6.0.0` / `P6.0.0` |  |
| D130 | Tax on domestically produced crude oil | `J1.0.0` / `P1.0.0` |  |
| D163 | Registration in the registry of religious entities eligible for tax-deductible donations | `J1.0.2` / `P1.0.0` |  |
| D169 | Registration of fiducia contracts | `J1.0.0` / `P1.0.0` |  |
| D169n | Beneficial-owner information mismatches | `J1.0.0` / `P1.0.0` |  |
| D177 | Redirect of profit/micro tax toward sponsorships | `J2.0.3` / `P1.0.0` |  |
| D200 | Individuals' income realized in Romania (historic, pre-D212) | `J4.1.2` / `P4.0.0` |  |
| D201 | Individuals' income realized abroad (historic, pre-D212) | `J2.1.0` / `P2.0.0` |  |
| D204 | Associations without legal personality — annual income | `J3.0.14` / `P2.0.2` |  |
| D207 | Informative — tax withheld at source for non-residents | `J2.0.2` / `P2.0.0` |  |
| D208 | Notaries' informative on real-estate transfers (biannual) | `J7.0.1` / `P1.1.2` |  |
| D220 | Estimated income, individuals (historic, pre-D212) | `J2.1.0` / `P2.0.1` |  |
| D221 | Agricultural income on income norms (historic, pre-D212) | `J1.0.1` / `P1.0.1` |  |
| D223 | Estimated income for associations (historic, pre-D212) | `J1.1.0` / `P1.1.0` |  |
| D230 | Individuals' 3.5% income-tax redirect to NGOs | `J8.0.0` / `P7.0.0` |  |
| D307 | VAT resulting from adjustments (asset transfers etc.) | `J1.1.0` / `P1.0.0` |  |
| D311 | VAT owed by persons whose VAT code was cancelled | `J2.0.0` / `P1.0.1` |  |
| D318 | VAT refund claim from other EU member states (persons established in Romania) | `J1.3.0` / `P1.0.0` |  |
| D392 | Informative for small VAT payers (application suspended) | `J2.0.0` / `P1.2.0` |  |
| D393 | Informative — international passenger transport (application suspended) | `J1.0.0` / `P1.0.0` |  |
| D395 | CESOP — payment-service-provider reporting, quarterly | `J2.0.2` / `P1.0.0` |  |
| D5 | Payment-instalment (eșalonare) request | `J1.2.3` / `P1.2.2` |  |
| D6 | Budget-obligation restructuring request/notification | `J1.0.0` / `P1.0.0` |  |
| D600 | CAS calculation-base income (historic, pre-D212) | `J3.0.0` / `P3.0.0` |  |
| D603 | CASS calculation-base income (historic, pre-D212) | `J1.0.0` / `P1.0.0` |  |
| D7 | Simplified payment-instalment request | `J1.1.0` / `P1.1.0` |  |
| D8 | Payment-instalment request | `J2.0.1` / `P1.0.0` |  |
| D9 | Cigarette release-for-consumption situation | `J1.0.0` / `P1.0.0` |  |
| DAC6 | Cross-border arrangement reporting (DAC6) | `J1.2.2` / `P1.0.1` |  |
| F4101 | Cash registers — pre-operationalization registry declarations | `J2.0.0` / `P2.0.0` |  |
| F4102 | Cash registers — registration of installed devices | `J1.0.4` / `P1.0.0` |  |
| F4103 | Cash registers — state/situation changes | `J2.0.0` / `P2.0.0` |  |
| F4105 | Cash registers — device-situation notification | `J2.0.0` / `P1.0.0` |  |
| F4109 | Cash registers — unused-device declaration | `J1.0.2` / `P1.0.2` |  |
| L153 | Public-sector salary reporting (Law 153/2017) | `J1.1.5` / `P1.0.0` |  |
| N012 | Notification — switching the annual/quarterly profit-tax system | `J1.0.0` / `P1.0.0` |  |
| N014 | Notification — fiscal-year change | `J1.0.0` / `P1.0.0` |  |
| S1055 | Notice — financial-exercise change | `J1.0.0` / `P1.0.0` |  |

### Financial statements family (S-series)

Annual/half-year/interim financial statements and accounting reports; codes are
per reporting year and entity type (ANAF's yearly soft decides which code
applies). Individually annotated where the catalog states it.

| Form | Purpose | Validator (J/P) | Notes |
|---|---|---|---|
| S1001 | — | `J14.0.3` / `P2.0.4` |  |
| S1002 | Annual financial statements / annual reports, FY2024 | `J14.0.1` / `P2.0.3` |  |
| S1003 | — | `J14.0.0` / `P2.0.2` |  |
| S1004 | — | `J14.0.0` / `P2.0.3` |  |
| S1005 | — | `J14.0.3` / `P2.0.6` |  |
| S1006 | — | `J1.1.0` / `P1.0.0` |  |
| S1007 | — | `J1.1.0` / `P1.0.0` |  |
| S1008 | — | `J1.1.0` / `P1.0.0` |  |
| S1009 | — | `J1.1.0` / `P1.0.0` |  |
| S1010 | — | `J8.1.3` / `P3.1.0` |  |
| S1011 | — | `J8.1.1` / `P3.1.0` |  |
| S1012 | Half-year accounting reports, 2025–2026 | `J6.2.2` / `P3.0.0` |  |
| S1013 | — | `J6.1.3` / `P3.0.0` |  |
| S1014 | — | `J14.0.2` / `P1.0.2` |  |
| S1015 | — | `J14.0.1` / `P2.0.0` |  |
| S1016 | — | `J5.0.1` / `P2.0.0` |  |
| S1017 | — | `J5.0.1` / `P2.0.0` |  |
| S1018 | — | `J4.0.0` / `P1.1.2` |  |
| S1019 | — | `J12.0.1` / `P2.0.2` |  |
| S1020 | — | `J9.0.1` / `P4.1.0` |  |
| S1021 | — | `J9.0.1` / `P4.1.0` |  |
| S1022 | — | `J9.0.1` / `P4.1.0` |  |
| S1023 | — | `J10.0.1` / `P4.1.0` |  |
| S1024 | — | `J6.0.2` / `P3.1.0` |  |
| S1025 | — | `J5.2.0` / `P3.1.0` |  |
| S1026 | — | `J9.0.0` / `P2.0.0` |  |
| S1027 | — | `J14.0.0` / `P4.0.2` |  |
| S1028 | — | `J4.0.1` / `P3.0.1` |  |
| S1029 | — | `J7.0.0` / `P3.0.0` |  |
| S1030 | Annual financial statements / annual reports, FY2023 & FY2025 | `J2.0.7` / `P2.0.1` |  |
| S1031 | — | `J10.1.1` / `P4.0.0` |  |
| S1032 | — | `J10.1.1` / `P4.0.0` |  |
| S1033 | — | `J10.1.1` / `P4.0.0` |  |
| S1034 | — | `J9.1.0` / `P3.0.0` |  |
| S1035 | — | `J6.0.0` / `P1.0.0` |  |
| S1036 | — | `J6.1.1` / `P3.0.2` |  |
| S1037 | — | `J1.2.0` / `P1.0.0` |  |
| S1038 | — | `J3.0.1` / `P1.1.0` |  |
| S1039 | — | `J1.0.6` / `P1.0.2` |  |
| S1040 | — | `J11.0.8` / `P4.0.0` |  |
| S1041 | — | `J3.0.2` / `P3.0.0` |  |
| S1042 | — | `J7.2.1` / `P1.0.0` |  |
| S1043 | — | `J2.3.0` / `P1.2.0` |  |
| S1044 | — | `J8.0.1` / `P3.2.0` |  |
| S1045 | — | `J10.1.3` / `P3.1.0` |  |
| S1046 | — | `J1.2.0` / `P1.1.0` |  |
| S1047 | — | `J2.2.1` / `P2.0.0` |  |
| S1048 | — | `J2.2.1` / `P2.0.0` |  |
| S1049 | — | `J2.2.1` / `P2.0.0` |  |
| S1050 | — | `J11.0.0` / `P3.0.2` |  |
| S1051 | — | `J3.0.1` / `P1.0.0` |  |
| S1052 | — | `J3.0.1` / `P1.0.0` |  |
| S1053 | — | `J1.1.0` / `P1.0.0` |  |
| S1054 | — | `J1.1.0` / `P1.0.0` |  |
| S1055 | Notice — financial-exercise change | `J1.0.0` / `P1.0.0` |  |
| S1056 | Annual financial statements / annual reports, FY2022 | `J4.0.2` / `P1.0.0` |  |
| S1057 | — | `J3.1.5` / `P1.0.0` |  |
| S1058 | — | `J2.4.0` / `P1.0.0` |  |
| S1059 | Half-year accounting reports, 2024 | `J4.0.1` / `P1.0.0` |  |
| S1060 | Half-year accounting reports, 2024 | `J4.0.1` / `P1.0.0` |  |
| S1061 | — | `J2.1.3` / `P1.0.0` |  |
| S1070 | — | `J1.2.0` / `P1.0.2` |  |
| S1072 | — | `J2.0.1` / `P1.0.0` |  |
| S1073 | — | `J1.0.0` / `P1.0.0` |  |
| S1074 | — | `J2.0.0` / `P1.0.0` |  |
| S1075 | — | `J1.0.1` / `P1.0.0` |  |
| S1076 | — | `J1.0.1` / `P1.0.0` |  |
| S1077 | — | `J1.0.0` / `P1.0.0` |  |
| S1078 | — | `J1.0.0` / `P1.0.0` |  |
| S1100 | — | `J3.1.4` / `P1.0.0` |  |
| S1110 | — | `J3.0.0` / `P2.0.0` |  |
| S1120 | — | `J4.0.1` / `P2.0.1` |  |
| S1121 | — | `J4.0.4` / `P2.0.1` |  |
| S1122 | Quarterly interim financial statements, 2025+ | `J4.0.4` / `P2.0.2` |  |
| S1123 | — | `J1.0.2` / `P1.0.1` |  |
| S1124 | — | `J1.0.2` / `P1.0.1` |  |
| S1125 | Quarterly interim financial statements, up to 2024 | `J1.0.3` / `P1.0.1` |  |
| S1126 | — | `J1.0.1` / `P1.0.0` |  |
| S1127 | — | `J1.0.1` / `P1.0.0` |  |
| S1128 | — | `J1.0.1` / `P1.0.0` |  |

### Unverified-purpose forms

Listed in the feed (hence filable) but with no purpose stated in the retrieved
sources. P1000/P2000 are PATRIMVEN-system forms per the catalog; the rest need
their own page checked.

| Form | Purpose | Validator (J/P) | Notes |
|---|---|---|---|
| B900 | — | `J1.0.0` / `P1.0.0` |  |
| D017 | — | `J1.0.6` / `P1.0.0` |  |
| D085 | — | `J1.1.0` / `P1.0.0` |  |
| D104 | — | `J1.2.0` / `P1.0.0` |  |
| D106 | — | `J1.0.1` / `P1.0.0` |  |
| D108 | — | `J1.0.0` / `P1.0.0` |  |
| D110 | — | `J1.0.3` / `P1.0.0` |  |
| D114 | — | `J1.0.1` / `P1.0.0` |  |
| D119 | — | `J1.0.0` / `P1.0.0` |  |
| D179 | — | `J1.1.1` / `P1.0.0` |  |
| D180 | — | `J1.0.2` / `P1.0.0` |  |
| D213 | — | `J1.0.0` / `P1.0.0` |  |
| D214 | — | `J1.0.0` / `P1.0.0` |  |
| D216 | — | `J1.0.3` / `P1.0.2` |  |
| D397 | — | `J1.0.2` / `P1.0.0` |  |
| D398 | — | `J1.0.11` / `P1.0.2` |  |
| D399 | — | `J1.0.5` / `P1.0.0` |  |
| D401 | — | `J1.5.0` / `P1.0.0` |  |
| D402 | — | `J1.0.1` / `P1.0.0` |  |
| D403 | — | `J2.2.0` / `P1.0.0` |  |
| D407 | — | `J1.0.2` / `P1.0.2` |  |
| F3000 | — | `J5.1.1` / `P1.1.1` |  |
| F7000 | — | `J1.0.4` / `P1.0.0` |  |
| P1000 | — | `J3.0.0` / `P1.0.0` |  |
| P2000 | — | `J1.3.5` / `P1.0.0` |  |
| P4000 | — | `J3.0.1` / `P1.1.0` |  |
| P5000 | — | `J1.0.0` / `P1.0.0` |  |
| R404 | — | `J1.0.10` / `P1.0.2` |  |
| R405 | — | `J1.0.5` / `P1.0.0` |  |
| T100 | — | `J1.0.0` / `P1.0.0` |  |
| T101 | — | `J1.0.0` / `P1.0.0` |  |
