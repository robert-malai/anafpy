# UIT presentation gallery

Every state of the UIT card and the A4 detail document, rendered from the
**shipped** renderer (`src/anafpy/etransport/cardpdf.py`) over one fictional
filing. This folder is where the artifacts' layout, typography and content get
looked at as a set — the decisions below are the record, and `gallery.py` is how
you see them.

It started as a pre-implementation mockup carrying its own copy of the layout,
which was right while the layout was still being argued about and wrong the
moment a renderer existed: two implementations mean the gallery can show a card
the library never draws. It now imports the real one (that mockup is in git
history, up to the rename in this commit).

Run: `uv run python design/gallery.py` — needs the `cards` extra, which
`uv sync --all-extras` installs. Output is git-ignored; PNG previews need
poppler's `pdftoppm` and are skipped without it.

## The card, in every combination

Three plate shapes × four validity states, `uit-card-<shape>-<state>.pdf`:

| | `-anaf` | `-anaf-expired` | `-estimated` | `-estimated-expired` |
| --- | --- | --- | --- | --- |
| `uit-card-no-trailer-` | ✓ | ✓ | ✓ | ✓ |
| `uit-card-one-trailer-` | ✓ | ✓ | ✓ | ✓ |
| `uit-card-two-trailers-` | ✓ | ✓ | ✓ | ✓ |

Plus the content edges that move the layout:

| File | What it shows |
| --- | --- |
| `uit-card-ttn-estimated.pdf` | A domestic TTN — the 5-day statutory window rather than the AIC's 15 |
| `uit-card-long-names-estimated.pdf` | Party names long enough to exercise the fit-shrink in the cells |
| `uit-card-minimal-estimated.pdf` | Nothing optional supplied — declarant falls to an em dash, the footer loses its identifiers line |
| `uit-details.pdf` / `uit-details-notes.pdf` | The A4 detail document with ANAF's window, without and with caller notes |
| `uit-details-estimated.pdf` / `uit-details-estimated-expired.pdf` | The same with a derived window, live and lapsed |
| `summaries.txt` | `summary_text()` for the four validity states — the chat message that travels with the card |
| `*-preview.png` | Raster previews, for viewing only |

The sample is a fictional AIC filing — Hungarian supplier, Bulgarian carrier, no
real CIF, VAT number or UIT, per the repo's no-personal-data rule. `TODAY` and
the transport dates are pinned in the script so re-running it a fortnight later
cannot quietly turn a live card into an expired one.

## Validity: ANAF's date and the statutory estimate

The card's validity comes from one of two places, and **which one has to be
visible on the page**.

- **ANAF's `data_exp_uit`** — grey `UIT VALABIL PÂNĂ LA` while live, red
  `A EXPIRAT LA` plus the red banner once lapsed. Unchanged.
- **The statutory window**, derived from the declared transport date when ANAF
  never disclosed one — which is the *common* case, because `data_exp_uit` is
  served only by the `info` endpoint and ANAF scopes that to the transport
  organizer. A declarant who is not the carrier reads back nothing.

Before this, that case printed the transport date alone and the driver carried a
code with no date on it. Now it prints the window OUG 41/2022 art. 11 fixes —
5 calendar days from the transport date, 15 for AIC and the lohn / call-off /
DIN legs — in a treatment that cannot be mistaken for ANAF's:

- **Amber throughout** — band, caption and value — against grey/red for ANAF's
  own dates. Red stays reserved for a verdict ANAF backs.
- The caption says so: `VALABIL (ESTIMAT) PÂNĂ LA`, and `PROBABIL EXPIRAT DIN`
  once past. The banner softens to amber `PROBABIL EXPIRAT — verificați
  valabilitatea`.
- An amber **footer line names the rule** (`Valabilitate estimată: 15 zile de la
  data transportului (OUG 41/2022)`), so the date above can be checked rather
  than trusted. It buys its space from the QR, like every other variation.
- The A4 document opens the value with `ESTIMAT —` and spells out the count, the
  article, and why ANAF's own date is absent.

Where the sources leave room for doubt the **shorter** window is encoded (DIE
gets 5, since only DIN is named). The errors are not symmetric: an estimate
that runs long puts a driver on the road with a lapsed UIT — a contravention —
while one that runs short makes a card announce itself early and prompts a
check.

## The card is a PDF

Earlier rounds explored PNG cards (stacked, two-row, and full-screen variants).
The PDF supersedes all of them, because a PNG is pixels and **nothing on it can
be copied**. The PDF carries the same layout with every value as real
selectable text — long-press the UIT in a phone PDF viewer and copy it — and
draws the QR as vector rectangles rather than an embedded raster, so it stays
crisp at any zoom and prints properly for the cab.

- **Sized to a phone display**, 90×195mm — the same 19.5:9 as iPhone X-and-later
  and most Samsung/Xiaomi flagships, so a viewer fitting the page to the screen
  fills it. A 20:9 Android letterboxes by a hair, invisible against the white
  page. The driver opens it full-screen and the phone *is* the document.
- Content clears the **top ~130px** (status bar, notch) and **bottom ~90px**
  (home indicator), which viewers overlay on the page.
- Text selection depends on the viewer — iOS PDFKit and Google Drive allow it,
  some in-app viewers don't, and "open with" is the workaround. Two fallbacks
  cover that: **the QR is itself a copy mechanism** (both phone cameras decode
  it and offer the string), and the sender can paste the **plain-text summary**
  as the accompanying chat message, which is the one path that works on every
  phone. `UitCard.summary_text()` returns it alongside the file — see
  `summaries.txt`.

## Layout decisions

- **Every fact is a bordered cell** with a grey caption band, stacked flush into
  one continuous table — the treatment the plate and dates used, extended to
  the parties. The card reads as a form rather than a table plus loose text.
- **The code prints solid and uncaptioned**, one 16-character run across the
  full width (~98px). Both real-world references print it as one run, so
  grouping in fours would have been our invention, and nothing else on the card
  could be mistaken for it.
- **The short codes sit two per row, not three.** At a third of the width the
  values fit-shrink to ~55px; two columns is what buys near-UIT-sized digits
  (plate ~88px, dates ~70px). It also promotes the trailer from a sub-line to a
  cell of its own — the trailer plate gets checked too. **With no trailer that
  row collapses to a full-width VEHICUL cell**, rather than pairing the plate
  with a date and pushing validity onto its own row: the collapse keeps the
  plate as the anchor and keeps the two dates side by side, where they belong
  as comparable values. The plate then renders at the 98px cap instead of the
  ~88px a half-width cell allows — slightly larger, still never louder than the
  UIT above it.
- **Every plate is a peer, and gets its own cell at full size.** One trailer →
  `VEHICUL | REMORCĂ`. None → a full-width `VEHICUL`. Both → `VEHICUL` full
  width over `REMORCĂ 1 | REMORCĂ 2`. Three cells across would fit-shrink all
  the plates back to ~57px, and folding the second trailer into a sub-line
  would rank it below the first, which the law does not. The caption is bare
  `REMORCĂ` when there is only one and numbered only when there are two.
- **Captions fit-shrink like values.** `VALABIL (ESTIMAT) PÂNĂ LA` is six
  characters longer than what a caption used to have to hold; a caption that
  silently overran its cell would be a rendering bug waiting for the next long
  word. The A4 document's label column shrinks the same way.
- **The QR is sized last, from the space the table leaves** — clamped to
  560–860px. Sizing the table first is what keeps a rare shape from crowding
  the footer; the expired banner, the second trailer and the estimate's footer
  line all pay for themselves the same way, out of QR rather than out of margin.
- **The footer is two lines, substance first**: `Depusă … · index încărcare …`
  in slate, then the disclaimer in grey — three when a derived window has a rule
  to name. "Document informativ" already says the card is not proof, so the old
  separate "face dovada doar declarația înregistrată…" sentence was saying it
  twice.
- **2-module quiet zone** on the QR. The spec asks for 4, but the page is white
  all round, so it supplies the rest and the same footprint buys bigger, more
  scannable modules.
- **Expired state**: banner under the header, the code greyed out, and the
  validity cell flipped — red on ANAF's date, amber on an estimate. This is the
  local substitute for a Wallet pass's auto-expiry: a stale card announces
  itself.

## What the real-world references settled

Two real documents were studied: a minimal QR card produced by invoicing
software, and a fuller two-page declaration printout.

- **The QR carries the raw 16-character UIT and nothing else** — decoded from
  the real card on 2026-07-31 (`4U3L175219640180`, zxing-cpp). There is no
  official ANAF QR format; this is the de-facto convention, and the card
  follows it.
- **Label the partner by direction.** The real card says *Furnizor* on an AIC,
  not "Partener". `partner_label()` maps ANAF's operation code to the right
  noun: inbound (10/12/14/40/60) → *Furnizor*, outbound (20/22/24/50/70) →
  *Client*, domestic TTN (30) → *Partener*.
- **Show the declarant** — both references identify who filed.
- **Print the fiscal code verbatim, with no country name bolted on** — a foreign
  VAT number already carries its prefix (`HU11223344`), so "Ungaria (HU) ·
  HU11223344" says it twice. Note the asymmetry: a *Romanian* code carries no
  prefix of its own, so `country` stays a field in its own right and the partner
  PDF keeps a `Țara` row. Only the card drops it, where space is tight and the
  operation type already implies direction.
- **Operation type reads as code + Romanian name** ("10 — Achiziție
  intracomunitară"), matching ANAF's own tooling.
- The fuller reference contributed the detail document's spine: section bars, an
  identification block carrying `index încărcare` / ANAF state / UIT validity
  with its day count, an observations block, and a running footer repeating UIT
  + declarant + page numbers.

## The detail document (`uit-details`)

- **Documents are rendered by type, not assumed.** ANAF's `TipDocumentType` is
  CMR (10) / Factură (20) / Aviz de însoțire a mărfii (30) / Altele (9999), and
  a filing need not carry a CMR — the section lists whatever types are present,
  each labelled by its own. The model requires at least one document, so the
  section never renders empty. An `Altele` entry appends its mandatory note.
- **Observations are the caller's, or absent.** The canned legal boilerplate
  ("codul UIT trebuie comunicat conducătorului auto…") was the same on every
  document and told the reader nothing about *this* filing, so it is gone. The
  section takes an optional `notes` sequence and is omitted entirely when empty
  — the good use is a filing-specific fact the structured fields cannot carry,
  like a gross weight the shipper gave as approximate.
- **Both dates, each labelled.** The identification block prints the last usable
  day *and* the first expired day, because `data_exp_uit` is the latter and the
  record should show what ANAF actually said. A derived window adds the count
  and the article it was counted by.
- **The two unbounded sections sit at the end** — the goods table, then the
  observations. Everything that identifies the filing (parties, vehicle, route,
  UIT, validity) is fixed-length and stays together on page 1; only the
  variable-length tail spills onto page 2. Notes read better after the table
  anyway, since they usually comment on what it lists.

## Standing decisions

Romanian-only labels, with proper diacritics (the reference card ASCII-folds
them — a font limitation the vendored OFL Noto subsets don't share). Both
artifacts carry the "document informativ — nu este emis de ANAF" disclaimer.
