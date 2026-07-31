# UIT presentation mockups

Design exploration for the UIT presentation artifacts (proposed `anafpy[cards]`
extra). Not shipped, not the future renderer — these pin down layout,
typography, and content before implementation.

Run: `uv run --with segno --with fpdf2 --with fonttools python design/mockup.py`

| File | What it shows |
| --- | --- |
| `uit-card.pdf` | **The card** — the driver's document, 90×195mm at the phone's own aspect ratio |
| `uit-card-expired.pdf` | Past `uit_expiry` — red banner, greyed code, red validity cell |
| `uit-card-no-trailer.pdf` | No trailer declared — the top row collapses to a full-width VEHICUL |
| `uit-card-two-trailers.pdf` | Both trailers declared — plates take three cells over two rows, QR yields the space |
| `uit-details.pdf` | The A4 detail document — the full filing, for the partner company or the caller's file |
| `uit-details-notes.pdf` | Same, with caller-supplied observations |
| `*-preview.png` | Raster previews, for viewing only |

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
  it and offer the string), and the sender can paste a **plain-text summary
  line** as the accompanying chat message, which is the one path that works on
  every phone. The renderer should return that string alongside the file.

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
- **The QR is sized last, from the space the table leaves** — clamped to
  560–860px. Sizing the table first is what keeps a rare shape from crowding
  the footer; the expired banner and the second trailer both pay for themselves
  the same way, out of QR rather than out of margin.
- **The footer is two lines, substance first**: `Depusă … · index încărcare …`
  in slate, then the disclaimer in grey. "Document informativ" already says the
  card is not proof, so the old separate "face dovada doar declarația
  înregistrată…" sentence was saying it twice — dropping it freed a line, which
  the adaptive QR absorbs.
- **2-module quiet zone** on the QR. The spec asks for 4, but the page is white
  all round, so it supplies the rest and the same footprint buys bigger, more
  scannable modules.
- **Expired state**: red banner under the header, the code greyed out, and the
  validity cell flipped to red with an `A EXPIRAT LA` caption. This is the local
  substitute for a Wallet pass's auto-expiry — a stale card announces itself.

## What the real-world references settled

Two real documents were studied: a minimal QR card produced by invoicing
software, and a fuller two-page declaration printout.

- **The QR carries the raw 16-character UIT and nothing else** — decoded from
  the real card on 2026-07-31 (`4U3L175219640180`, zxing-cpp). There is no
  official ANAF QR format; this is the de-facto convention, and the card
  follows it. The mockup's own QR round-trip-decodes.
- **Label the partner by direction.** The real card says *Furnizor* on an AIC,
  not "Partener". `PARTNER_LABEL` maps ANAF's operation code to the right noun:
  inbound (10/12/14/40/60) → *Furnizor*, outbound (20/22/24/50/70) → *Client*,
  domestic TTN (30) → *Partener*.
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
  section now takes an optional `notes` sequence and is omitted entirely when
  empty — the good use is a filing-specific fact the structured fields cannot
  carry, like a gross weight the shipper gave as approximate.
- **The two unbounded sections sit at the end** — the goods table, then the
  observations. Everything that identifies the filing (parties, vehicle, route,
  UIT, validity) is fixed-length and stays together on page 1; only the
  variable-length tail spills onto page 2. Notes read better after the table
  anyway, since they usually comment on what it lists.

## Standing decisions

Romanian-only labels, with proper diacritics (the reference card ASCII-folds
them — a font limitation we don't share). Both artifacts carry the "document
informativ — nu este emis de ANAF" disclaimer. macOS system fonts (Arial,
Menlo) stand in for the OFL Noto faces the real extra would bundle; Menlo has
to be extracted from a `.ttc` because fpdf2 won't load collections, which the
bundled fonts make moot.

All sample data is fictional — it mirrors the shape of a real AIC filing
(Hungarian supplier, Bulgarian carrier) without carrying anyone's real CIF or
UIT, per the repo's no-personal-data rule.
