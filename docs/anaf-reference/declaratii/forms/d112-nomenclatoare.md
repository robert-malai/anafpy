---
title: D112 nomenclatoare — code lists for payroll authoring (tip asigurat, cod obligatie, work-condition, sick-leave codes)
service: declaratii
language: en
sources:
  - url: https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/structura_D112_0126_030226.pdf
    title: "D112 structure annex, 2026 revision (v7) — the appendix nomenclatoare (Nomenclator 1–12, case de sănătate, coduri fiscale AJOFM/CASAN)"
    retrieved: 2026-07-17
  - url: https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/d112_10102024.xsd
    title: "D112 v6 XSD — Str_casaAngListSType (health-house sigla), Str_contractTypeSType, Str_codBoalaSType enumerations"
    retrieved: 2026-07-17
compiled: 2026-07-17
compiled_by: claude-opus-4-8
last_verified: 2026-07-17
status: draft
---

# D112 — nomenclatoare (code lists)

Lookup tables for D112 payroll authoring, split out of [d112.md](d112.md)
because together they run past 200 entries. Source of truth is the **appendix of
the D112 structure annex** (`structura_D112_0126_030226.pdf`, pages 78–87) plus
the enumerations vendored in the v6 XSD; ANAF's validator jar
(`D112Validator.jar`) is authoritative when a code list drifts from the XSD (see
[d112.md](d112.md#special-attention-gotchas)). Romanian labels are kept verbatim
(quoted where they are the form's own wording), with an English gloss.

## Nomenclator 3 — obligații de plată (`A_codOblig`)

The `angajatorA/@A_codOblig` values, each paired with a budget classification
code `A_codBugetar` (the app auto-fills it from the selected obligation). **This
is the v7 set from the structure annex — broader than the 22-code
`Str_A_cod_obligListSType` enum in the v6 XSD; the jar accepts the full list
below.** Budget code is `5503XXXXXX` unless noted; the two CAM budget codes are
`20470300XX` (general CAM) and `20A470600X` (constructions/agriculture CAM).

| `A_codOblig` | Budget code | Obligation (Romanian) | Gloss |
|---|---|---|---|
| `602` | `5503XXXXXX` | Impozit pe veniturile din salarii și asimilate | Wage income tax |
| `412` | `5503XXXXXX` | CAS datorată de asigurați | Employee pension (CAS 25%) |
| `432` | `5503XXXXXX` | CASS datorată de asigurați | Employee health (CASS 10%) |
| `480` | `20470300XX` | CAM — contribuția asiguratorie pentru muncă | Employer work-insurance (2.25%) |
| `481` | `5503XXXXXX` | CAS datorată de angajator, condiții deosebite | Employer CAS, hazardous (4%) |
| `482` | `5503XXXXXX` | CAS datorată de angajator, condiții speciale | Employer CAS, special (8%) |
| `483` | `5503XXXXXX` | CAS facilități construcții (art.60 pct.5 CF) | Construction CAS exemption |
| `484` | `20A470600X` | CAM construcții | Construction CAM |
| `486` | `5503XXXXXX` | CAS facilități agricultori (art.60 pct.7 CF) | Agriculture CAS exemption |
| `487` | `20A470600X` | CAM agricultori | Agriculture CAM |
| `488` | `5503XXXXXX` | CAS facilități IT (art.60 pct.2 CF) | IT CAS exemption |
| `458` | `5503XXXXXX` | CAS suportat de angajator (art.146 alin.(5⁶)) | Employer-borne CAS (min-wage top-up) |
| `459` | `5503XXXXXX` | CASS suportat de angajator (art.168 alin.(6¹)) | Employer-borne CASS |
| `611` | `5503XXXXXX` | Impozit pe ven. din drepturi de prop. intelectuală | IP-rights income tax |
| `451` | `5503XXXXXX` | CAS — PF cu ven. din drepturi de prop. intelectuală | IP-rights CAS |
| `461` | `5503XXXXXX` | CASS — PF cu ven. din drepturi de prop. intelectuală | IP-rights CASS |
| `619` | `5503XXXXXX` | Impozit pe ven. din arendarea bunurilor agricole | Farm-lease income tax |
| `469` | `5503XXXXXX` | CASS — ven. din arendare | Farm-lease CASS |
| `622` | `5503XXXXXX` | Impozit — asociere cu o PJ, titl. II L227/2015 | Title-II association tax |
| `471` | `5503XXXXXX` | CASS — asociere cu o PJ, titl. II | Title-II association CASS |
| `623` | `5503XXXXXX` | Impozit — asociere cu o PJ, titl. III L227/2015 | Title-III association tax |
| `464` | `5503XXXXXX` | CASS — asociere cu o PJ, titl. III | Title-III association CASS |
| `624` | `5503XXXXXX` | Impozit — asociere, impozit specific L170/2016 | Specific-tax association tax |
| `472` | `5503XXXXXX` | CASS — asociere, impozit specific | Specific-tax association CASS |
| `625` | `5503XXXXXX` | Impozit — contracte de activitate sportivă | Sports-contract income tax |
| `473` | `5503XXXXXX` | CAS — contracte de activitate sportivă | Sports-contract CAS |
| `474` | `5503XXXXXX` | CASS — contracte de activitate sportivă | Sports-contract CASS |
| `441` | `5503XXXXXX` | CASS pensionari (perioade anterioare 01.02.2017) | Pensioner CASS (back periods) |
| `607` | `5503XXXXXX` | Impozit pensii peste plafonul de 2000 lei | Pension tax over 2 000 lei |
| `457` | `5503XXXXXX` | CASS pensionari (partea peste 3000 lei) | Pensioner CASS over 3 000 lei |
| `627` | `5503XXXXXX` | Impozit — activități casnice (L111/2022) | Domestic-work income tax |
| `477` | `5503XXXXXX` | CAS — activități casnice | Domestic-work CAS |
| `492` | `5503XXXXXX` | CASS pentru șomeri | Unemployed CASS |
| `478` | `5503XXXXXX` | CASS pers. persecutate (Decret-lege 118/1990) | Politically-persecuted CASS |
| `479` | `5503XXXXXX` | CASS ajutor de incluziune (L196/2016) | Inclusion-aid CASS |
| `493` | `5503XXXXXX` | CASS creștere copil < 2/3 ani | Child-raising CASS (under 2/3) |
| `490` | `5503XXXXXX` | CASS creștere copil cu handicap 3–7 ani | Disabled-child-raising CASS |

## Nomenclator 5 — tip asigurat A/B (`A_1`, `B1_1`)

The insured-type code that classifies a salaried record by its employment
contract. The value drives which contributions the record owes (the
`eSalariat`/`dat_CAS`/`dat_CASS`/`dat_CAM`/`baza_AJS` flags in
[d112.md](d112.md#the-asigurat-per-insured-block)). Types **3, 34, 36** are
declared **only** in section A; types **16, 17, 23, 24** only in section B1;
**31, 42** may appear at most once per declaration; **2** (military) only in the
special reporting of public institutions. Y/N columns = owes CAS / CASS / CAM /
has an unemployment base.

| `A_1` | Mof. no. | Category (Romanian) | CAS | CASS | CAM | Șomaj |
|---|---|---|---|---|---|---|
| `1` | 1 | Salariat (normă întreagă, exclusiv 1.1) | Y | Y | Y | Y |
| `46` | 1.0 | Salariat — CAS în sistem propriu de pensii | N | Y | Y | Y |
| `26` | — | Salariat cu studii superioare, vechime > 1 an | Y | Y | Y | Y |
| `25` | 1.1 | Salariat în construcții (art.60 pct.5 CF) | Y* | Y* | Y | Y |
| `48` | — | Salariat în agricultură (art.60 pct.7 CF) | Y* | Y* | Y | Y |
| `54` | — | Salariat IT (art.60 pct.2 CF) | Y* | Y | Y | Y |
| `27` | 1.4 | Membru cooperator salariat | Y | Y | Y | Y |
| `31` | 1.5 | Părinți salariați — indemnizație L19/2020 (secț. B) | Y | Y | Y | Y |
| `42` | 1.5.1 | Idem, CAS în sistem propriu (secț. B) | N | Y | Y | Y |
| `8` | 1.7 | Personal român trimis în misiune în străinătate (HG) | Y | Y | Y | N |
| `51` | 1.11.2 | Salariat normă întreagă, beneficiar 200/300 lei netaxabil | Y | Y | Y | Y |
| `52` | 1.11.3 | Idem, CAS în sistem propriu | N | Y | Y | Y |
| `2` | 2 | Salariat militar (statut special) | N | Y | Y | N |
| `9` | 3.1 | PF cu funcții de demnitate publică | Y | Y | Y | Y |
| `10` | 3.2 | Consilieri locali/județeni (indemnizație de ședință) | Y | Y | Y | Y |
| `11` | 3.3 | PF alese în PJ fără scop patrimonial | Y | Y | Y | Y |
| `12` | 3.4 | Directori cu contract de mandat / directorat | Y | Y | Y | Y |
| `13` | 3.5 | Administratori/manageri cu sume din profit | Y | Y | Y | Y |
| `14` | 3.6 | Salariați cu sume pt. participarea la profit | Y | Y | Y | Y |
| `15` | 3.7 | Indemnizație de neconcurență (după CIM) | N | Y | N | N |
| `18` | 3.8 | Ven. din salarii după încetarea raportului juridic | Y | Y | Y | N |
| `16` | 3.9 | Raport suspendat — CM OUG158/2005, suportat de angajator (secț. B + D) | Y | Y | N | Y |
| `23` | 3.10 | Raport suspendat — incap. temp. din FNUASS (secț. B + D) | Y | Y | N | Y |
| `17` | 3.11 | Raport suspendat — incap. temp. din FAAMBP (secț. B + D) | N | N | N | Y |
| `24` | 3.12 | Raport suspendat — incap. temp. L346/2002 (secț. B + D) | N | N | Y | Y |
| `19` | 3.13 | Raport suspendat — indemniz. suportată de angajator | Y | Y | Y | Y |
| `20` | 3.14 | Reprezentanți în organisme tripartite | Y | Y | N | N |
| `4` | 4 | Membri comisii de cenzori/audit, asoc. de proprietari (mandat) | Y | Y | N | N |
| `5` | 5 | Beneficiari de plăți compensatorii din fondul de salarii | Y | Y | N | N |
| `40` | 5.1 | Concediere colectivă — plăți compensatorii | Y | Y | Y | N |
| `6` | 6 | Administratori/membri CA/CS, reprezentanți în AGA | Y | Y | Y | Y |
| `21` | 7 | Reîncadrarea activității (activități dependente) | Y | Y | Y | Y |
| `22` | 8 | Activități dependente, CAS în sist. propriu (avocați, etc.) | N | Y | Y | Y |
| `3` | 9 | Zilieri (exclusiv 9.1) (L52/2011) | Y | N | N | N |
| `28` | 10 | Contract de internship (L176/2018) | Y | Y | Y | Y |
| `29` | 11 | Avantaje/venituri de la terți | Y | Y | Y | N |
| `30` | 12 | PF nerezidentă, fără contribuții sociale în România | N | N | N | N |
| `34` | 1.8 | PF în misiuni diplomatice/consulare (secț. A) | N | N | N | N |
| `36` | 1.10 | PF cu CASS plătită pe perioada suspendării din funcție (secț. A) | N | Y | N | N |

`*` For construction/agriculture/IT (`25`/`48`/`54`) the employee CAS rate is
the **reduced** `Cipens` (see the exemption rules); CASS may be exempt. See
[d112.md](d112.md#special-attention-gotchas).

## Nomenclator 6 — tip asigurat "alte entități" C (`asiguratC/@C_1`)

Non-salaried insured on whose behalf someone else (ANOFM, CNPP, CNAS, MAE, …)
declares — the `asiguratC` block. Each carries its own obligation codes.

| `C_1` | Category (Romanian) | Declared by | Obligations |
|---|---|---|---|
| `2` | Șomer (**singurul tip C care poate avea secțiune D** pt. CM) | ANOFM | CAS 412, CASS 492 |
| `39`–`44` | Persecutați politic / veterani / revoluționari | ANOFM/CNPP | CASS 478 |
| `4` | Ajutor de incluziune | ANPIS | CASS 479 |
| `5` | Creștere copil < 2/3 ani | ANPIS | CASS 493 |
| `6` | Creștere copil cu handicap 3–7 ani | ANPIS | CASS 490 |
| `10` | Concedii și indemnizații OUG158/2005 | CNAS | CAS 412, CASS 432, imp. 602 |
| `11` | Preluați de la unități în faliment (incap. temp.) | CNPP | imp. 602 |
| `13` | Soț/soție personal român în misiune permanentă | primării | CAS 412, imp. 602 |
| `14` | Corp diplomatic/consular > 90 zile | MAE | CAS 412, imp. 602 |
| `15` | Disponibilizați cu plăți compensatorii din BAS | ANOFM | CAS 412, imp. 602 |
| `17` | Ven. din drepturi de proprietate intelectuală | plătitor | CAS 451, CASS 461, imp. 611 |
| `22` | Asociere cu o PJ, titl. III L227 | plătitor | CASS 464, imp. 623 |
| `26` | Arendare, reținere la sursă | plătitor | CASS 469, imp. 619 |
| `27` | Asociere cu o PJ, titl. II L227 | plătitor | CASS 471, imp. 622 |
| `28` | Pensionari (CASS suportată de contribuabil) | CNPP | CASS 441, imp. 602 |
| `30` | Contracte de activitate sportivă | plătitor | CAS 473, CASS 474, imp. 625 |
| `33` | Personal sanitar OUG3/2021 | plătitor | CAS 412, CASS 432, imp. 602 |
| `34` | Personal sanitar OUG3/2021, CAS în sist. propriu | plătitor | CASS 432, imp. 602 |
| `35` | Ven. din pensii peste plafon CASS | CNPP | CASS 457, imp. 607 |
| `36` | Activități casnice (L111/2022) | plătitor | CAS 477, imp. 627 |
| `37` | Rezerviști voluntari (dispăruți/captivi), din 03.2025 | unități militare | — |
| `38` | Rezerviști voluntari (fără instruire), din 03.2025 | unități militare | CAS 412, CASS 432, CAM 480, imp. 602 |

## Nomenclator 7 — indicativ condiții speciale/deosebite (`B2_1`, from 01.09.2024)

The hazardous-work indicative attached to sick-leave / special-condition income
(section B2). `0` = "Rest" (ordinary). `1`–`9` and `11`–`19` map to
art. 28 alin.(1)/art. 27 alin.(3–4) of L360/2023 (mining, radiation, aviation,
artists, arms, ship-building, transplant, electricity, machine-building,
mine-extraction, forestry, railway, …). The full per-value legal basis is on
page 84 of the structure annex; the enum accepted by the jar is
`{0,1,2,3,4,5,8,9,11,12,14,15,17,18,19}` (values 4-military, 10, 13, 16 are
struck for periods from 09.2024).

## Nomenclator 8 — loc prescriere certificat medical (`D_10`)

| `D_10` | Meaning |
|---|---|
| `1` | Medic de familie (family doctor) |
| `2` | Spital (hospital) |
| `3` | Ambulatoriu (outpatient) |
| `4` | CAS |
| `5` | CEX |

## Nomenclator 9 — cod indemnizație (boală) pe certificatul medical (`D_9`)

Drives the sick-leave computation in section D; the `Grupa` maps to Nomenclator
10 (which drives the funding source and the `D_28` percentage).

| `D_9` | Meaning (Romanian) | Grupa |
|---|---|---|
| `01` | Boală obișnuită | G1 |
| `02` | Accident în timpul deplasării la/de la muncă | G1 |
| `03` | Accident de muncă | G1 |
| `04` | Boală profesională | G1 |
| `05` | Boală infecto-contagioasă din grupa A | G1 |
| `51` | Boală infectocontagioasă pt. care se instituie izolarea | G1 |
| `06` | Urgență medico-chirurgicală | G1 |
| `07` | Carantină | G2 |
| `08` | Sarcină și lăuzie | G3 |
| `09` | Îngrijire copil bolnav < 7 ani / copil cu handicap | G4 |
| `91` | Îngrijire copil cu afecțiuni grave < 16 ani | G4 |
| `92` | Supraveghere copil < 18 ani în carantină/izolare | G4 |
| `10` | Reducerea cu 1/4 a duratei normale de lucru | G2 |
| `11` | Trecerea temporară în altă muncă | G2 |
| `12` | Tuberculoză | G1 |
| `13` | Boală cardio-vasculară | G1 |
| `14` | Cancer, HIV, SIDA | G1 |
| `15` | Risc maternal | G5 |
| `16` | Unele tipuri de arsuri | G1 |
| `17` | Îngrijirea pacientului cu afecțiuni oncologice | G4.1 |

## Nomenclator 10 — grupe de boală (OUG 158)

| Grupă | Meaning | `D_9` covered |
|---|---|---|
| G1 | Incapacitate temporară | 01–06, 12–14, 16, 51 |
| G2 | Prevenire îmbolnăvire / carantină | 07, 10, 11 |
| G3 | Sarcină și lăuzie | 08 |
| G4 | Îngrijire copil bolnav | 09, 91, 92 |
| G4.1 | Îngrijire pacient cu afecțiuni oncologice | 17 |
| G5 | Risc maternal | 15 |

## Nomenclator 12 — tip contract de muncă (timp de lucru) (`A_3`, `B1_3`)

The `Str_contractTypeSType` enum. Drives the hours-worked ceiling
(`A_6 ≤ NZL·A_4` for `N`, `A_6 ≤ NZL·i` for `Pi`).

| Code | Meaning |
|---|---|
| `N` | Cu normă întreagă (full-time) |
| `P1`…`P7` | Cu timp de lucru parțial de 1…7 ore/zi (part-time, 1–7 h/day) |

## N1 — justificare venit din altă perioadă (`E3_7`)

Filled only when `E3_4="A"` (income from a period other than the reporting one).

| `E3_7` | Meaning |
|---|---|
| `10` | Hotărâre judecătorească |
| `20` | Primă/bonus de natură ocazională |
| `30` | Sume din profitul net |
| `40` | Primă/bonus prevăzut prin CCM/CIM |
| `50` | Al 13-lea salariu |
| `60` | Restanțe de plată din perioade anterioare |
| `70` | Indemnizații suportate de ANOFM/ANPIS (OUG 36/2022) |
| `100` | Altele |

## Exemption fields on the `asigurat`

- **`asigScu`** — person exempt from income tax (`1`–`9`): `1` disabled;
  `2` software/IT; `3` R&D; `4` seasonal HoReCa (L170/2016);
  `5` farm-lease (L566/2004); `6` other legal exemptions; `7` construction
  (art.60 pct.5); `8` youth in agriculture (L336/2018); `9` agriculture
  (art.60 pct.7). Most `2`–`9` are struck in the current version — the surviving
  live categories are `1`, `7`, `9`. Set `null` when the person is not exempt.
- **`asigExc`** — exempt from CAS/CASS at the **minimum-wage level**
  (art.146 alin.(5⁶)/art.168 alin.(6¹)): `0`/null = not applicable, `1` = exempt,
  `2` = explicitly not exempt.
- **`motivExc`** (only when `asigExc=1`, values `1`–`5`): `1` pupils/students
  < 26; `2` apprentices < 18; `3` disabled / other categories with < 8 h/day;
  `4` employees who are also old-age pensioners; `5` income from several CIMs
  (cumulative ≥ minimum guaranteed gross wage).

## Nomenclator 2 — case de asigurări de sănătate (`casaAng`, `casaSn`)

The health-house code is the **2-char county sigla** and must match the county
of the employer's registered office (an `ATT` fires otherwise). The per-employee
`casaSn` normally repeats `casaAng`, except `_N` (neasigurat) for a `zilier`
(`A_1=3`) or a detached person who does not pay CASS here. Special houses:
`_B` = Bucharest, `_A` = defence (apărare), `_T` = transport.

Accepted sigla (`Str_casaAngListSType`): `_B _A _T AB AR AG BC BH BN BT BV BR BZ
CS CJ CT CV CL DB DJ GL GR GJ HR HD IL IS IF MM MH MS NT OT PH SM SJ SB SV TR TM
TL VS VL VN`.
