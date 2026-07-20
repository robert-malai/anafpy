---
name: declaratie-prepare
description: >
  Build, validate, render, sign, and track a Romanian tax declaration starting
  from unstructured source data (an accountant's email, a spreadsheet, pasted
  numbers, "file my VAT return for March"). Identifies the right form, reads its
  completion guide, infers identification data via the public ANAF lookups (CUI →
  name, address, VAT status), asks the user for what cannot be inferred, and
  drives the declaration MCP tools (declaratie_validate loop → declaratie_render
  → declaratie_sign → declaratie_prepare/declaratie_submit filing, or manual
  filing when the portal tools are opted out → declaratie_status /
  declaratie_recipisa).
---

# Build and file a tax declaration from source data

You are preparing a legal tax declaration for Romania's tax authority (ANAF)
from whatever the user gives you — raw numbers, a document, or just a request.
The flow is local until the filing step: identify the form → read its completion
guide → infer what a lookup can answer → **ask for everything else** → author
the XML → validate until ANAF's validator agrees → render → user review → sign
→ file on the portal (or hand off for manual filing) → confirm with the status
tools.

Three rules override everything else:

- **Never invent a value.** Every amount, period, and election must trace to
  the source data, a lookup result, or the user's answer. When something is
  missing, ask — do not guess. ANAF's validator, not you, is the authority.
- **Infer before you ask, ask before you assume.** Identification data
  (company name, address, VAT status) comes from the CUI lookup, never from
  memory and never by asking the user to retype what ANAF publishes. Elections
  and amounts (settlement period, refund request, bank account, the numbers
  themselves) can never be inferred — always ask.
- **Never self-approve the signature — or the filing.** `declaratie_sign` and
  `declaratie_portal_login` fire the user's certificate PIN/2FA, and
  `declaratie_submit` files a real declaration on the production portal
  (declarations have no test environment). Call each only after the user
  explicitly approved that step here, never chained on a single earlier "yes".

## Step 1 — identify the form, orient the tooling

If the user already named the form (or it is unambiguous from their request),
do **not** ask again — state which form you are preparing ("Working on D300,
the VAT return for 06/2026") and move on. Otherwise infer it from the data and
situation using the inventory resource
`anafref://declaratii/forms/README` (173 forms, bucketed by SME usage) —
e.g. VAT numbers for a month → D300; per-partner domestic invoice lists →
D394; intra-EU lines → D390; payroll → D112; a prior-period correction of a
D100 → D710. Only when two forms remain plausible, present the candidates with
one line on who files each and ask.

Call `declaratie_duk_status`: it confirms DUKIntegrator is configured and
whether the form's validator jar is current. Stale jar → tell the user and
continue with a caveat (ANAF may reject what a stale validator passes). Not
configured → stop and point at the setup guide.

## Step 2 — read the form's completion guide

Fetch `anafref://declaratii/forms/d<nnn>` **before authoring anything**. It
is the map for the whole task: purpose and legal basis, who files and when
(sanity-check the user's situation and deadline), the row-by-row → XSD
attribute mapping, DUK-validated example instances to pattern-match against,
and the researched gotchas (control-sum formulas, mirror rules, cross-form
checks). Large code lists live in the sibling resource
`anafref://declaratii/forms/d<nnn>-nomenclatoare` where the guide links one.

Only if the form has no guide (outside the covered twelve): fall back to the
raw XSD from the form's soft page and converge through the validate loop.

## Step 3 — establish identity by lookup, not by asking

Take the CUI from the source data or the configured default. Call
`anaf_lookup_taxpayers` and use the answer to:

- fill the identification block (official name → `den`, fiscal address →
  `adresa`) — show the user what the lookup returned so they can catch a stale
  registry entry;
- **cross-check eligibility**: VAT registration status vs a form that requires
  it (D300) or forbids it (D301), cash-accounting (TVA la încasare) status for
  the fields that depend on it (D300 annex, D394 `sistemTVA`), inactive/radiat
  flags — surface a mismatch before wasting the user's time;
- validate partner CUIs the same way where the form carries them (D394). For
  D390 partner VAT codes, advise the user to verify them in VIES — an invalid
  partner code is the top rejection cause, and there is no local tool for it.

## Step 4 — extract, map, and ask

Map every fact in the source onto the guide's rows and show the mapping.
Then ask — in one batch, not a drip — for what remains:

- the reporting period and, where the form has one, the settlement type
  (`tip_decont` monthly/quarterly cannot be looked up — it is the taxpayer's
  election);
- any amount the source does not state (never extrapolate);
- the form's must-ask fields per the guide's identification-block table
  (D300: bank + IBAN, `solicit_ramb` refund election, the reverse-charge
  sector checkboxes; D112: quarterly-filer status; D101: liquidation status);
- the declarant's name and capacity if not already known.

## Step 5 — author the XML

Author from the guide's mapping and its validated example instances: derived
rows and cascades are computed per the guide's formulas (totals, control sums
like `totalPlata_A` — each form defines its own), enum conventions verbatim
(`D`/`N`, name-vs-code). Compute `nr_evid` with `declaratie_nr_evid`, passing
the right `form` (`D300` needs `tip_decont`; `D100`/`D710` need `cod_oblig` +
`scadenta`; `D101` adds `in_liquidation`; `D301` takes `mijl_trans`) — never
by hand, it has a check digit.

## Step 6 — validate in a loop

`declaratie_validate` with the form and XML. On `ok=false`, the findings are
DUK's own messages — precise enough (rule ids, attribute names, expected
values) to dictate each fix; iterate until `ok=true`. Some forms (D700) are
warning-only by design: `ok=true` with warnings is a pass — relay the notice,
don't chase a bare `ok`.

## Step 7 — pre-filing reconciliation

Before rendering, run through the guide's cross-form checks and say what ANAF
will reconcile this filing against (D300 ↔ D394 ↔ D390 totals, e-Factura,
SAF-T, the pre-filled e-TVA decont). Ask the user to confirm the numbers tie
out with the sibling declarations for the same period — a mismatch triggers a
conformity notification that cannot be un-filed.

## Step 8 — render and review

`declaratie_render` to a `save_pdf_as` path the user names. Summarise the
declaration (form, period, CUI, key amounts, amount payable / refundable) and
ask the user to open and review the PDF.

## Step 9 — sign (only on explicit go)

On explicit approval: warn that the certificate prompt (token PIN / phone 2FA)
is about to fire, then `declaratie_sign` with the PDF path and `confirm=true`.
One attempt per call; on `signed=false` relay the `guidance` and retry only
with the user's go-ahead.

## Step 10 — file (portal tools, or manual hand-off)

Filing is REAL: the portal is production-only. If `chain_complete` was false,
mention the signature is leaf-only and portal acceptance of that is
unverified.

With the portal tools available (`declaratie_submit` in the tool list):

1. `declaratie_portal_status` — no PIN/2FA fires. If the session lapsed, ask
   the user to approve a portal login, warn their certificate prompt is about
   to fire, then `declaratie_portal_login` with `confirm=true`. Sessions die
   after ~10 idle minutes, so do this right before filing, not earlier.
2. `declaratie_prepare` with the signed PDF path. Recap what is about to be
   filed — form, period, CUI, amount payable/refundable — and ask for explicit
   approval of the *filing* (the earlier signature approval does not carry
   over). Heed `looks_signed=false`: it means the PDF has no embedded
   signature and the portal will reject it.
3. On their go: `declaratie_submit` with the same path, the token, and
   `confirm=true`. The token is single-use and bound to the exact bytes; a
   lapsed session comes back as "token NOT consumed" — log in again and retry
   with the same token. Relay the verdict: `accepted=true` gives the **upload
   index** (tell the user to note it); `accepted=false` carries the portal's
   rejection reason — fix and re-prepare; `accepted=null` means the outcome is
   unknown — check `declaratie_status` before ever re-filing.

If the portal tools are absent (opted out via `ANAFPY_DECLARATII_UPLOAD`),
hand back the signed PDF; the user files it at **anaf.ro → Depunere
declarații** and notes the upload index the portal shows.

## Step 11 — confirm

With the upload index: `declaratie_status` (no login needed) — relay ANAF's
state verbatim: `In prelucrare` means check again later; `Documentul este
valid` means accepted; a validation-error state means fix and refile — say so
plainly. Once valid, offer `declaratie_recipisa` to save the signed receipt to
a path the user names and advise archiving it (ANAF keeps it downloadable only
~60 days).
