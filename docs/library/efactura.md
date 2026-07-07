# e-Factura

`EFacturaClient` covers Romania's electronic-invoicing service: filing invoice
XML, tracking its processing, listing the message inbox, and downloading
documents.

## Pass-through, not composition

anafpy does **not compose invoices**. e-Factura is a filing endpoint — Romanian
law presumes you already run an invoicing system — so the client takes the
complete UBL XML your own system produced and moves it: validate, file, track,
download. There is no "invoice builder" and no flat→UBL write path, by design.

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
- `get_status` reports the processing state (`MessageStatus`).
- `upload_and_wait` combines the two: it polls `get_status` until the message
  leaves the "processing" state, retrying only on that business state — never on
  transport errors.

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
3. **`FlatInvoice`** — an easy-to-read **view** (`DownloadedMessage.view`):
   parties, lines, totals, references, projected from the UBL by
   `read_flat_invoice`.

`FlatInvoice` is **lossy by design** — it is a read view for display and
extraction, never a source to regenerate XML from. When it can't represent
something it says so: check `complete` and `dropped_fields`. The raw bytes and
the UBL model stay authoritative.

`validate_signature` checks the Ministry of Finance signature over a downloaded
archive.

## Validation and PDF rendering

ANAF's stateless document services — `validare` (authoritative server-side
validation, no filing) and `transformare` (the official PDF rendering) — are
public, no-auth, and prod-only on ANAF's side, so they live on
[`PublicClient`](public.md) as `validate_invoice` and `render_invoice_pdf`, not
on `EFacturaClient`. Use them freely: they work with no OAuth credentials
configured at all.

There is deliberately **no local rule engine** — validation verdicts come from
ANAF's own validator, which is authoritative by definition.
