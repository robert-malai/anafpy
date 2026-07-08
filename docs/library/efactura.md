# e-Factura

`EFacturaClient` covers Romania's electronic-invoicing service: filing invoices
(as ready-made XML or composed from the [authoring models](authoring.md)),
tracking processing, listing the message inbox, and downloading documents.

## Two outbound paths

**Pass-through is the strongly recommended path when you run invoicing
software**: bring the complete UBL XML your system exported and anafpy moves
it — validate, file, track, download — without ever re-composing it. Your
invoicing system's document is authoritative; re-deriving it could only add
drift. Just as important, **ANAF's SPV is not invoice storage**: it purges
filed messages after ~60 days, so the durable record must live in a system you
own — which an invoicing system gives you for free.

**Structured authoring** is the first-class alternative when there is no
upstream system: the [`anafpy.efactura.authoring`](authoring.md) models compose
a complete CIUS-RO invoice or credit note from business fields — totals and the
VAT breakdown computed for you — and `upload_invoice` files it in one call.
Archiving the signed documents is then on you: download each filing's ZIP and
keep it, because after the retention window ANAF won't have it either.

The generated UBL 2.1 / CIUS-RO models are available if you want typed access to
a parsed document:

```python
from anafpy.efactura import Invoice, CreditNote, parse_ubl_document
```

## Filing and tracking

```python
async with EFacturaClient(provider) as efactura:
    result = await efactura.upload(invoice_xml, cif="RO12345678")
    if result.accepted:
        status = await efactura.get_status(result.upload_id)
```

- `upload` files the XML and returns an `UploadResult` — a rejection (BR-RO
  findings and all) comes back as `accepted is False` with the findings attached,
  **not** as an exception (see the [error model](errors.md)).
- `upload_invoice` takes an authored
  [`InvoiceDocument`](authoring.md) instead of XML: it renders the document
  (running the local rule set first — `skip_validation=True` opts out) and
  uploads with the right `standard` for an invoice or credit note.
- `get_status` reports the processing state (`MessageStatus`).
- `upload_and_wait` combines upload and polling: it polls `get_status` until the
  message leaves the "processing" state, retrying only on that business state —
  never on transport errors.

## The inbox: `list_messages`

```python
async for message in efactura.list_messages(cif="RO12345678", days=30):
    print(message.message_id, message.message_type, message.details)
```

A single async iterator that pages ANAF's message list under the hood — window by
`days` or `start`/`end`. An empty window yields an **empty iterator**; a genuine
ANAF error **raises** `AnafResponseError` (ANAF overloads the same response note
for both cases; anafpy classifies them).

Note a production-confirmed quirk (2026-07-06): the list's `cif_emitent` /
`cif_beneficiar` fields are never actually emitted by ANAF despite being
documented — partner CIFs ride only inside the free-text `detalii`. See the
[e-Factura reference](../anaf-reference/efactura/api.md).

## Downloading: three read tiers

`download` returns a `DownloadedMessage` exposing the same document at three
levels:

1. **Raw signed bytes** — ANAF's ZIP archive, the authoritative artifact.
2. **The full UBL model** — the parsed, typed document.
3. **`InvoiceDocument`** — the flat **view** (`DownloadedMessage.view`):
   parties, lines, totals, references, projected from the UBL by the strict
   [authoring reader](authoring.md).

The view is **full-fidelity and renderable back** — the same model you author
with, so drafting a credit note from a received invoice is one step away. It is
strict on purpose: every inbox document already passed ANAF's validation, whose
rules the models mirror, so a representable document always reads. When the
content is not a representable invoice (a rejection-errors file, a buyer
message, rule drift), `view` is `None` — never an exception — and the raw bytes
plus the UBL model stay authoritative.

`validate_signature` checks the Ministry of Finance signature over a downloaded
archive.

## Validation and PDF rendering

ANAF's stateless document services — `validare` (authoritative server-side
validation, no filing) and `transformare` (the official PDF rendering) — are
public, no-auth, and prod-only on ANAF's side, so they live on
[`PublicClient`](public.md) as `validate_invoice` and `render_invoice_pdf`, not
on `EFacturaClient`. Use them freely: they work with no OAuth credentials
configured at all.

ANAF's validator is **authoritative by definition**. The
[authoring models](authoring.md) additionally run a translated EN 16931 +
CIUS-RO rule set locally (`validate()`, findings with the official BR-* rule
ids) for fast feedback while composing — a clean local report is a strong
signal, never a guarantee.
