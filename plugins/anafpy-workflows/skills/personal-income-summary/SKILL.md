---
name: personal-income-summary
description: >-
  Summarize a person's realized income over one or more fiscal years from
  Romania's ANAF SPV, using the income certificates (Adeverință de venit) and
  the Declarația Unică duplicate (D212) filed under their CNP. ALWAYS use this
  skill when the user asks about their income / "veniturile mele" / "ce am
  câștigat" / "cât am făcut" over a year or period, asks to pull income from
  ANAF, the tax return, or the declarația unică, or asks for an income summary /
  income report / adeverință de venit. Defaults to PERSONAL income (the CNP on
  the certificate), picks the right SPV reports automatically, and optionally
  produces an Excel summary. Trigger even for casual phrasing like "cât am
  câștigat anul trecut" or "arată-mi veniturile pe ultimii ani".
---

# Personal income summary (ANAF)

Answer "what was my income?" for a Romanian natural person by pulling the
authoritative ANAF records, extracting the figures, and presenting a clean
per-year summary — with an optional Excel workbook.

Uses the `anafpy` MCP SPV tools. All amounts are in **lei (RON)**.

## When this applies

The user is asking about **their own personal income** over one or more years —
phrased in Romanian or English, formally or casually. This skill assumes
personal (natural-person) income by default; see "Whose income" below for the
company-income branch.

## Default tools & why

For personal income, two SPV reports are the right default — request **both**
for each year:

1. **`Adeverințe Venit`** (income certificate) — the PRIMARY source. It
   aggregates every realized income ANAF has on record for the person that year:
   salaries (from employer D112 filings), independent activity / intellectual
   property (from the Declarația Unică), interest (from D205), etc., each with
   gross income, taxable base, and tax. This one certificate usually answers the
   whole question.
2. **`D212`** (Declarația Unică duplicate) — SUPPORTING source. The person's own
   self-declared return; use it to confirm/detail the independent-activity
   portion. The adeverință already folds this in, so D212 is a cross-check, not
   the headline.

Do **not** default to company reports (D300, D101, bilanț, etc.) — those are for
legal entities, not personal income.

## Workflow

### 1. Confirm the SPV session
Call `auth_status`, then `spv_status`. `spv_status` returns the certificate
holder's `cnp` and `authorized_cuis`. If there is no active session, tell the
user to log in host-side (`anafpy spv login`) or, only if they explicitly ask,
call `spv_login(confirm=true)` (this fires their PIN/2FA). Do not proceed
without a session.

### 2. Pick the CNP and the years
- **Whose income (default = personal).** Use the personal CNP from
  `spv_status.cnp` as the `cui` for every request. If `authorized_cuis` also
  contains company CIFs and the user's wording is ambiguous about personal vs
  company income, ask once which they mean; otherwise assume personal.
- **Which years (default = last 3 completed fiscal years).** If the user names a
  year or range, use it. Otherwise default to the three most recent completed
  fiscal years. A fiscal year is "available" once its Declarația Unică deadline
  has passed (≈ 25 May of the following year); if today is before that, the most
  recent year may only have partial data — still request it and note the caveat.

### 3. Request the reports (async)
For each target year, call `spv_cerere`:
- `spv_cerere(tip="Adeverinte Venit", cui=<CNP>, an=<year>, motiv="Altele")`
- `spv_cerere(tip="D212", cui=<CNP>, an=<year>)`

`motiv` must match ANAF's fixed list exactly (`spv_nomenclature("income_certificate_reasons")`).
Default to **"Altele"** unless the user states a real purpose (loan → "Institutie
financiar bancara asigurare etc.", health → "Sanatate", etc.) — the motiv is
printed on the certificate. Each call returns an `id_solicitare`.

### 4. Wait for delivery and download
For each `id_solicitare`, call `spv_asteapta_raport(id_solicitare=..., save_as=<path>)`
to save the PDF to the outputs folder. **The handshake occasionally times out**
(MCP `-32001`) even though the request is still valid — just call
`spv_asteapta_raport` again for that id; it is not an error. Name files clearly,
e.g. `Adeverinta_<year>.pdf`, `DU_<year>.pdf`.

### 5. Extract the figures
Read each adeverință PDF. Each row has: category (`Categoria de venit`), source
document, income type (realizat/estimat — keep only **Realizat**), gross income
(`Venit brut`), taxable income (`Venit impozabil`), tax (`Impozit`). Capture
every row; the DU rows appear as "Decl.unica nr=...".

### 6. Present the summary (always)
Give a concise per-year answer in chat: a small table per year with the line
items and a TOTAL, plus a one-line trend across years. Note common quirks
plainly — e.g. some salary rows show taxable income 0 when the person had an
income-tax exemption (IT/construction). State that figures exclude CAS/CASS
contributions paid separately via the Declarația Unică.

### 7. Offer the Excel summary (optional)
After the chat summary, offer to build an Excel workbook: "Want this as an
Excel file?" Build it only if the user says yes (or asked for it up front).
When building, follow the **xlsx** skill and this layout:
- **`Sumar`** sheet: one row per year — An, Venit brut, Venit impozabil, Impozit,
  and gross split by Salarii / Activități independente / Dobânzi — with a TOTAL
  row. The brut/impozabil/impozit cells reference the per-year detail totals by
  formula; the category splits are summed from the line items.
- One **detail sheet per year** (`2023`, `2024`, ...): every line item with its
  source document and the three amount columns, ending in a `=SUM(...)` TOTAL row.
- Use formulas (never hardcoded totals), Arial, `#,##0` number format, and run
  `recalc.py` until it reports zero errors. Save as `Venituri_<first>-<last>.xlsx`
  and present it with `present_files`.

## Notes & pitfalls
- **Personal vs company** is the main branch point — default personal, confirm
  only if the account holds company CIFs and the ask is ambiguous.
- **The adeverință is authoritative**; D212 is confirmation. If the two disagree,
  surface it rather than silently picking one.
- **Amounts are lei**, gross unless the user asks for net (net requires
  subtracting deductible expenses and CAS/CASS — offer it, don't assume it).
- **Never expose internal sandbox paths** to the user; share files via
  `present_files`.
- Deliver the official PDFs alongside any summary so the user has the source.
