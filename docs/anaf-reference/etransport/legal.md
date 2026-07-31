---
title: e-Transport — Legal framework (OUG 41/2022 and implementing acts)
service: etransport
language: en
sources:
  - url: https://static.anaf.ro/static/10/Anaf/AsistentaContribuabili_r/Ghid_RO_e_Transport_2025.pdf
    title: "ANAF — Ghid privind utilizarea Sistemului național RO e-Transport (2025)"
    source_revision: "2025 edition (reflects amendments through OUG 29/2025)"
    retrieved: 2026-08-01
    local_copy: ../_sources/Ghid_RO_e_Transport_2025.pdf
  - url: https://static.anaf.ro/static/10/Anaf/legislatie/OUG_41_2022.pdf
    title: "OUG nr. 41/2022 (initial text, M.Of. 356/11.04.2022)"
    retrieved: 2026-08-01
  - url: https://static.anaf.ro/static/10/Anaf/legislatie/OPANAF_1337_2024.pdf
    title: "Ordinul comun ANAF/AVR nr. 1337/1268/2024 — Procedura de utilizare și
      funcționare a sistemului RO e-Transport"
    retrieved: 2026-08-01
  - url: https://legislatie.just.ro/Public/DetaliiDocument/254608
    title: "OPANAF nr. 802/2022 — bunurile cu risc fiscal ridicat (M.Of. 430/03.05.2022)"
    retrieved: 2026-08-01
compiled: 2026-08-01
compiled_by: claude-fable-5
last_verified: 2026-08-01
status: draft
---

# e-Transport — Legal framework

The legal requirements behind the RO e-Transport system, compiled for the MCP
server's guidance surface (the `etransport-declare` skill's step 0 summarises this
page). The [API surface](api.md) is a separate doc. Compiled primarily from ANAF's
official 2025 guide (vendored — the most recent consolidated official statement of
the rules); article numbers refer to OUG 41/2022 as amended. **ANAF and the
Monitorul Oficial are authoritative on any discrepancy**; amounts and deadlines
below are the law as stated in the 2025 guide, last verified 2026-08-01.

## 1. Legislative stack

| Act | Role |
|---|---|
| **OUG nr. 41/2022** (M.Of. 356/11.04.2022), approved by **Legea nr. 375/2023** | establishes the system: scope, users, obligations, contraventions |
| OUG 115/2023 | extended declaration from high-fiscal-risk goods to **all international road transports** (from 15.12.2023) |
| OUG 43/2024, 87/2024, 129/2024, 138/2024 | 2024 amendment wave: AEO grace period, sanction rework (graduated confiscation), deferrals |
| OUG 29/2025 (M.Of. 365/24.04.2025) | suspended the GPS-related contraventions until **31.12.2025**; no further deferral found — the full regime applies from **01.01.2026** |
| **Ordinul comun ANAF/AVR nr. 1337/1268/2024** | the implementing procedure ("Procedura de utilizare și funcționare"); **replaces** Ordinul 2545/6316/2022 |
| **OPANAF nr. 802/2022**, as amended | the closed list of high-fiscal-risk goods (by NC code chapters) |

> Provenance: guide pp. 2 (amendment list), 4 (footnote 5 cites Ordin 1337/1268/2024
> art. 1 alin. (4)); the 2545→1337 replacement is stated in the 1337/1268/2024 order
> itself.

## 2. Scope and thresholds

Monitored: road vehicles with a maximum technically permissible mass of **≥ 2.5 t**,
loaded with goods of total gross mass **> 500 kg** or total value **> 10,000 lei**
(excl. VAT) belonging to at least one *partidă* (consignment) of the transport
(Ordin 1337/1268/2024 art. 1 alin. (4)). Within that envelope, a UIT is required
for:

- **domestic transports (TTN)** of goods on the **high-fiscal-risk list**
  (OPANAF 802/2022, as amended); and
- **all international road transports of goods** — intra-community acquisition and
  delivery, import/export, lohn in/out, call-off stock in/out, and intra-community
  transit with unloading/reloading for storage or forming a new consignment in
  Romania (art. 8^1).

> Provenance: guide p. 4 §I.2.

## 3. Who is obliged to declare (art. 8 and art. 8^1)

The declaring party is fixed by law per operation — filing under any other CIF does
not discharge the obligation. Mapped onto the operation types the API uses:

| Operation | Obligated declarant |
|---|---|
| TTN (domestic) | the **Romanian supplier** for internal transactions; the **operator economic** holding and transporting the goods between two places on national territory |
| AIC | the **Romanian beneficiary** of the intra-community acquisition |
| LIC | the **Romanian supplier** making the intra-community delivery |
| IMP | the **consignee** named in the customs import declaration |
| EXP | the **shipper** named in the customs export declaration |
| LHI / LHE (lohn, nontransfer) | the **Romanian service provider** (goods unloaded in RO for processing, and their re-dispatch); the **Romanian beneficiary** for goods sent from RO for processing in the EU and their return |
| SCI / SCE (call-off stock) | the **Romanian client** when RO is the destination member state (arrival, later delivery, or return); the **Romanian supplier** when RO is the dispatch member state |
| DIN / DIE (transit storage) | the **depozitar** — for goods unloaded in RO for storage or to form a new consignment, and for goods reloaded after it |

> Provenance: guide pp. 3–4 §I.1 (verbatim art. 8 / art. 8^1 lists) and pp. 6–7
> (operation-type ↔ user table).

## 4. Exemptions from declaration (art. 16 + procedure)

- transports for **diplomatic missions, consular offices, international
  organizations, armed forces** (NATO / EU / Partnership for Peace / states with
  bilateral agreements), and under classified or security-sensitive public
  procurement contracts;
- **excise goods moving under EMCS** — duty-suspension or duty paid in the dispatch
  member state, accompanied by the electronic **e-DA / e-DAS** documents (Legea
  227/2015 title VIII);
- goods carried by **postal service providers in postal parcels** (OUG 13/2013
  art. 2 pct. 16);
- via the procedure: **agricultural products bought from producers on the carnet de
  comercializare**, transports performed by **individual agricultural producers**
  from holding place to point of sale, and **vegetal agricultural products moved
  after harvest**.

> Provenance: art. 16 exemptions — guide pp. 4–5 §I.3; agricultural exemptions —
> Ordin 1337/1268/2024 (confirmed against secondary sources, not yet against the
> order's own text — see §8).

## 5. The UIT code — timing and immutability

- Obtainable at most **3 calendar days before** the declared transport start date,
  but **no later than** presentation at the border crossing point on entry / the
  place of import, or the moment the vehicle actually starts moving (art. 11).
- Valid **5 calendar days** from the declared transport start date — **15 calendar
  days** for intra-community acquisitions (AIC) and for the operations at art. 2
  pct. 9 lit. g) and j): intra-community transit to storage / new-consignment
  formation (DIN) and national nontransfer / call-off stock legs (lohn, SCI/SCE).
- Using a UIT **past its validity window is prohibited** and is a contravention.
- After border entry / the vehicle starts moving, the declared data **may no longer
  be modified**. Single exception: **vehicle identification** may be updated during
  the UIT's validity, but before the vehicle moves again (the *vehicle change*
  operation).
- Every consignment of the transport must be declared in full — declaring
  quantities different from those actually carried is a contravention.
- **System outage**: when ANAF/MF announce on their websites that the system is
  non-functional, the declaration duty is deferred to **the end of the next working
  day after service is restored**, including for transports already completed.

> Provenance: guide p. 11 (3-day window, validity, footnotes 9–10 quoting art. 2
> pct. 9 lit. g) and j)), p. 12 (prohibition past validity), pp. 24–25 (outage
> rule, immutability, all-goods rule as contraventions).

## 6. Post-issuance obligations (who must do what with the UIT)

- The **user** (declarant) puts the UIT at the disposal of the transport operator —
  directly or via the transport organizer — at the latest by border presentation on
  entry / effective start of movement.
- The **transport operator** gives the UIT to the driver, and must **ensure
  transfer of the vehicle's current positioning data for the whole route** —
  vehicles must be equipped with satellite-positioning telecom terminal devices
  (art. 8^2).
- The **driver** must **start the positioning device before** setting off on
  national territory and stop it only **after delivering at the declared place /
  leaving the country**, and must **present the accompanying documents together
  with the UIT** at the request of ANAF, the customs authority (AVR), or the
  Romanian Police. Any intelligible form of the UIT is acceptable.

> Provenance: guide pp. 3–4 §I.1 (operator and driver duties, control bodies).

## 7. Contraventions and sanctions (art. 13^1) — in force in full since 01.01.2026

Fines are **10,000–50,000 lei** for individuals / **20,000–100,000 lei** for legal
persons, per fact, for: non-declaration (transport not identifiable by UIT), use of
a UIT past validity, unloading intra-community transit goods in Romania other than
by the depozitar, declaring different quantities, failing to update vehicle data,
failing the outage-window redeclaration, not giving the UIT to the transport
operator in time, modifying data after movement start, not declaring all goods of a
consignment, and (operator) not ensuring GPS data transfer.

- **Graduated confiscation** (OUG 129/2024) attaches to the *core* declaration
  facts when repeated within **12 months of the first sanction**: 1st offence —
  fine only; 2nd — fine + confiscation of **15%** of the undeclared goods' value;
  3rd — **50%**; 4th onward — **100%**. More than 12 months after the first
  sanction, the counter resets (fine only).
- Confiscation is **waived** when post-transport checks find the goods duly
  recorded in the justificative documents and in the user's accounts (reception on
  *Nota de recepție și constatare diferențe* — Legea contabilității 82/1991, OMF
  2634/2015) for the period concerned.
- **Driver** contraventions (not starting/stopping the positioning device;
  not presenting documents + UIT at control): fine **5,000–10,000 lei**.
- The GPS-related contraventions (operator data transfer; driver device on/off)
  were suspended by OUG 29/2025 **until 31.12.2025** — they apply since
  **01.01.2026**.
- Sanctions are applied by empowered personnel of **ANAF**, the **Autoritatea
  Vamală Română**, and officers/agents of the **Poliția Română**.

> Provenance: guide pp. 22–25 §III (fact list, amounts, graduation, accounting
> waiver, driver fines, OUG 29/2025 footnotes 13–14, enforcement bodies).

## 8. Verification status

Compiled 2026-08-01 from the vendored official guide (read in full). Not yet
verified against the primary texts themselves: the agricultural exemptions'
exact wording in Ordin 1337/1268/2024, and the post-2025 absence of any further
sanction deferral (checked via press/UNTRR as of 2026-08-01 — none found; UNTRR's
request for a 01.07.2026 deferral was not granted as far as could be established).
When ANAF publishes a newer guide edition, re-vendor it and re-verify §§5–7.
