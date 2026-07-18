---
title: Method — generating and updating the per-form completion guides
service: declaratii
language: en
status: current
---

# Method: generating and updating the per-form completion guides

This is **anafpy's own methodology document**, not compiled ANAF reference:
it records how the per-form files in this folder (`dXXX.md`) are produced and
kept current, so any future update — human- or agent-driven — follows the same
procedure and quality bar. The [README](README.md) is the inventory; this file
is the playbook behind everything else in the folder.

## What a finished per-form file contains

Each hands-on form gets **one `dXXX.md`** covering two layers in a single
file — a technical quirk layer (XSD shape, DUK validator behaviour, minimal
instance) and a semantic completion-guide layer (purpose, filing rules,
row-by-row filling semantics). One file per form is deliberate: when an agent
composes a declaration it needs row semantics, XSD facts, and DUK gotchas in
the same session, and a single resource fetch must answer all of it. Combined
files land around 300–500 lines (~4–6k tokens), a cheap single read.

Fixed heading structure, identical across forms so agents and site search can
navigate reliably:

```
# DXXX — <name>
## Purpose & legal basis
## Who files & when          (deadlines, periodicity, rectificative rules)
## Filling guide             (row-by-row → XSD attribute mapping, scenarios)
## Special attention & gotchas   (researched pitfalls — see below)
## vN (current …)            (XSD facts, validator quirks, per-version)
##  … DUK behaviour, minimal instance …
```

**Annex files only for pure lookup tables past ~100 entries** (e.g.
`d112-nomenclatoare.md` for assured-person types and work-condition
indicatives). Annexes are linked from the main file and carry their own
provenance frontmatter. Everything else stays in the one file.

Language: English prose (`language: en`); Romanian official terms kept
verbatim and quoted ("decont de TVA", "Rândul 9"); wire names (attributes,
enum codes) verbatim. Every file carries the standard provenance frontmatter
(`sources` with URL/title/`retrieved`, `compiled`, `compiled_by`,
`last_verified`, `status`).

**ANAF stays authoritative.** Each guide states that the validator jar and
ANAF's published instructions are the authority; the guide is a distilled
bridge, never a re-implementation of the rules.

## Content requirements per guide

- **Purpose & legal basis** — what tax/obligation the form settles; the OPANAF
  order approving the *current* form version (D112 is a joint MF/CNPP/CNAS
  order); periodicity.
- **Who files & when** — obligated taxpayer categories; deadline day-of-month;
  monthly vs quarterly election rules where applicable; how corrections work
  (rectificative flag / resubmission semantics).
- **Row-by-row filling semantics mapped onto the XSD** — the key value-add.
  ANAF's official instructions speak in PDF-row terms ("Rândul 9 — livrări cu
  cota 21%"); anafpy authors XML attributes (`R9_1`/`R9_2`). The guide is the
  bridge. Every mapping must be cross-checked against the XSD version recorded
  in the quirk section — never trust the instructions PDF's row numbering
  blindly; verify the attribute exists in the current XSD.
- **Common scenarios** — nil return, typical SME cases, corrections — each
  anchored by a **DUK-validated example instance** where feasible.
- **Special attention & gotchas** — a dedicated, researched section (not just
  what falls out of reading the instructions PDF). Run the research sweep
  below and distill:
  - semantic pitfalls: mutually exclusive rows, sign conventions, rounding
    rules, fields that look optional but are conditionally required;
  - **cross-form consistency checks** ANAF is known to run — e.g. D300 vs
    D394 totals, D390 vs the VIES/D300 intra-EU rows, D100 vs D112 overlaps —
    so the agent can warn the user *before* filing when the numbers won't
    reconcile;
  - common rejection/correction causes and frequently-asked clarifications
    from ANAF's own guidance material;
  - recent legislative changes affecting the form (rate changes, new rows,
    deadline moves) with their effective dates.

  DUK mechanics stay in the version/quirk headings; don't duplicate them.

## Sources, in order of authority

1. **ANAF's official filling instructions** ("Instrucțiuni de completare"),
   bundled in the soft PDF linked from each form's static.anaf.ro soft page:
   `https://static.anaf.ro/static/10/Anaf/Declaratii_R/<number>.html`
   (off-pattern pages: D212 = `declaratie_unica.html`; D406 has its own SAF-T
   page — see the [README](README.md) conventions block). These are *the*
   per-row authority.
2. **The OPANAF orders** approving each form (legal basis, obligated-persons
   text). Prefer ANAF-hosted PDFs over third-party legal portals.
3. **ANAF's fiscal calendar / assistance pages** — the cross-check for
   deadlines, which move by amendment.
4. **ANAF's published guidance material** — the "Ghiduri curente" collection
   on anaf.ro (Asistență contribuabili), ANAF's published Q&A/clarification
   sheets, and press-released procedure notes. Authoritative for the
   gotchas/special-attention layer.
5. Codul fiscal (Legea 227/2015) — anchoring references only, not primary
   content.
6. **Secondary practitioner sources** (accounting portals, professional-body
   material such as CECCAR publications) — allowed **only** for discovering
   candidate gotchas, and only kept if corroborated by an authoritative source
   (tiers 1–5) or verified directly against the XSD/validator. Cite the
   authoritative confirmation, not the portal, in the frontmatter; never let
   an uncorroborated practitioner claim into a guide.

**Version-alignment trap (critical):** instructions must match the XSD version
recorded in the quirk section. Example: D300 v12 already reflects the August
2025 VAT-rate change (21% standard rate, row R9); an older cached instructions
PDF describing 19% rows would silently poison the guide. When the instructions
PDF and the current XSD disagree, the XSD + validator jar win — note the
discrepancy in the file.

## Per-form research sweep

Before writing a form's "Special attention & gotchas" section, run a web
research pass covering at least:

- the form's ANAF assistance/ghid pages and any official completion guide
  beyond the instructions PDF;
- ANAF clarifications and legislative-change notices touching the form
  (search Romanian terms: "declarația <nr>", "instrucțiuni completare",
  "modificare", "rectificativă", plus the current year);
- known cross-form consistency checks and notification letters ANAF sends
  (e.g. D394↔D300 discrepancy notices);
- deadline confirmations against the current fiscal calendar.

Record what was searched and kept in the frontmatter `sources`; discard
anything that fails the corroboration rule above. Time-box the sweep — the
goal is the top handful of load-bearing gotchas per form, not an exhaustive
literature review.

## When to run this method

- **A new form is promoted** into the hands-on buckets of the
  [README](README.md) inventory → produce its `dXXX.md` from scratch.
- **An XSD / validator-jar version bump** for a covered form (the DUK update
  feed — `fetch_feed_versions` / `declaratie_duk_status` — announces it) →
  re-verify the row→attribute mapping against the new XSD, re-validate the
  example instances, add a new `## vN` section, refresh `last_verified`.
- **A legislative change** (rate change, new rows, deadline move) → refresh
  the affected sections + the gotchas, with effective dates.
- **Aging**: a `last_verified` older than roughly a filing year deserves a
  deadline/instructions re-check even without a known trigger.

## Verification & gates

- Every example instance in a guide must validate clean (or warning-only)
  against the form's current validator jar via DUK — judge by the err file,
  never the exit code (see the [DUK reference](../duk.md)). Record the jar
  version used. The DUK dist conventionally lives at `~/.anafpy/duk-dist`
  (`ANAFPY_DUK_DIR`).
- Deadlines/periodicity facts must be confirmed by two independent sources
  (instructions PDF + fiscal calendar/assistance page); cite both.
- Every claim in "Special attention & gotchas" must trace to an authoritative
  source (tiers 1–5) or to direct XSD/validator verification — no
  uncorroborated practitioner-portal claims survive review.
- `uv run mkdocs build --strict` must stay green (broken internal links fail
  the build). Update the [README](README.md) table if links/descriptions
  change.
- Documentation work only: no code changes, no filing, no calls to ANAF's
  authenticated services — everything here is public static content + local
  DUK runs.
