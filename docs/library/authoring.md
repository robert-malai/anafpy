# Invoice authoring

`anafpy.efactura.authoring` composes complete CIUS-RO invoices and credit notes
from business fields — no invoicing software and no UBL knowledge required. The
models are **bidirectional**: the same `InvoiceDocument` authors a filing and
views a parsed one, with byte-stable round-trips.

If your invoicing software already exports UBL XML, strongly prefer the
[pass-through path](efactura.md#two-outbound-paths): its document is
authoritative, anafpy never re-composes it, and — the part that outlives the
filing — **ANAF's SPV is not invoice storage**: it purges filed messages after
~60 days, and an invoicing system is what keeps your durable record. Authoring
exists for everyone else — a freelancer, an agent drafting an invoice in a
chat, a script issuing a handful of invoices a month — with one obligation
attached: download and keep the signed ZIP of every filing, because your copy
is the one that lasts.

## Composing an invoice

```python
import datetime as dt
from decimal import Decimal

from anafpy.efactura.authoring import (
    InvoiceDocument, InvoiceLine, Party, PostalAddress, Seller,
)

address = PostalAddress(
    street="Str. Exemplu 1", city="Cluj-Napoca", county="RO-CJ", country="RO",
)
invoice = InvoiceDocument(
    number="INV-2026-0042",
    issue_date=dt.date(2026, 7, 8),
    due_date=dt.date(2026, 8, 7),
    currency="RON",
    seller=Seller(name="Furnizor SRL", vat_id="RO12345678", address=address),
    buyer=Party(name="Client SRL", vat_id="RO87654321", address=address),
    lines=[
        InvoiceLine(
            name="Servicii de consultanta",
            quantity=Decimal("10"),
            unit="H87",  # UN/ECE Rec 20/21: H87 = piece, KGM = kilogram
            unit_price=Decimal("150.00"),
            vat_category="S",
            vat_rate=Decimal("19"),
        ),
    ],
)
```

That is a complete, fileable document: the **totals and the VAT breakdown are
computed** from the lines, document-level allowances and charges (grouped by VAT
category and rate, EN 16931 rounding). Supply explicit values only to reproduce
an upstream document's own arithmetic — they are preserved on render and
cross-checked by `validate()`.

One semantic model covers both document types: pass `kind="credit_note"` (with a
`preceding_invoices` reference to the corrected invoice) and the same fields
render a UBL `CreditNote` instead, type code 381 and all.

The full EN 16931 surface is available when needed: payee and tax
representative, delivery details, payment instructions (credit transfers, card,
direct debit), document- and line-level allowances/charges, item
identifiers/classifications/attributes, attachments, periods, and every
reference term (contract, order, despatch, ...).

## Two-tier validation

Construction enforces what a single field or model can know unconditionally —
formats, the CIUS-RO length caps, the closed code lists (currencies, countries,
units, payment means, VATEX, ...), decimal budgets, per-category VAT rate
shapes, Romanian county/sector rules. Invalid data fails fast with a pointed
message; ANAF would reject it with certainty anyway.

The cross-cutting rules run on demand:

```python
from anafpy.efactura.authoring import validate

report = validate(invoice)
for finding in report.findings:
    print(finding.rule, finding.message)   # e.g. BR-CO-25, BR-S-08, BR-RO-120
```

`validate()` is a hand-translated port of the official EN 16931 + CIUS-RO
Schematron — totals arithmetic, VAT-regime identifier requirements, breakdown
consistency — reporting findings with the **official rule ids** and mirroring
the Schematron's own numeric tolerances. It is fast local feedback, not a
verdict: **ANAF's server-side `validare` stays authoritative**
([`PublicClient.validate_invoice`](public.md)).

## Rendering and filing

```python
from anafpy.efactura.authoring import render_invoice

xml = render_invoice(invoice)          # upload-ready UTF-8 bytes
# or file directly:
result = await efactura.upload_invoice(invoice, cif="12345678")
```

Both run `validate()` first and raise `InvoiceValidationError` (carrying the
report) on fatal findings; pass `skip_validation=True` to let ANAF be the only
judge.

## Reading wire XML back

```python
from anafpy.efactura.authoring import parse_invoice, read_invoice

document = parse_invoice(xml_bytes)        # from bytes
document = read_invoice(message.document)  # from a DownloadedMessage's UBL
```

The reader is strict and full-fidelity: every wire amount lands in the explicit
fields (never recomputed), so `render_invoice(parse_invoice(xml)) == xml` holds
and `validate()` can judge an upstream document's arithmetic. This is the
natural starting point for *drafting a credit note from a received invoice* —
and it is exactly what `DownloadedMessage.view` returns for a
[downloaded message](efactura.md#downloading-three-read-tiers), wrapped to yield
`None` instead of raising when the content is not a representable invoice.
