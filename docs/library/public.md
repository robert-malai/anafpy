# Public services

`PublicClient` covers ANAF's **unauthenticated** public services on
`webservicesp.anaf.ro` — no OAuth credentials, no certificate, no test/prod
split (the services exist only in production).

```python
from anafpy.public import PublicClient

async with PublicClient() as public:
    lookup = await public.lookup_taxpayers(["RO12345678"])
    if lookup.found:
        record = lookup.found[0]
        print(record.name, record.vat_registered, record.efactura_registered)
```

## Registry lookups

- `lookup_taxpayers` — the main taxpayer registry: name, address, VAT
  registration (plătitor de TVA), VAT-on-collection (TVA la încasare), split-VAT,
  inactive state, and RO e-Factura register membership — one call, in bulk if you
  like.
- `lookup_efactura_register` — RO e-Factura register membership alone.
- `lookup_farmers` — the farmers' register (RegAgric).
- `lookup_cult_entities` — the religious-entities register (RegCult).
- `get_financial_statement` — a company's filed financial statements (bilanț)
  for a given year.

Lookups return a `RegistryLookup` with `found` / `not_found` partitions. One
subtlety anafpy handles for you: **membership is read from the `registered`
booleans, never from presence in `found`** — RegAgric/RegCult return unknown CUIs
in `found` with empty fields, so presence alone means nothing.

## Stateless e-Factura document services

Two e-Factura utilities live here rather than on `EFacturaClient`, because they
are public, no-auth, and need no filing context:

- `validate_invoice` — ANAF's authoritative server-side `validare` (CIUS-RO /
  BR-RO rules). Validates only; files nothing. Findings come back as a typed
  `RemoteValidationResult`, not an exception.
- `render_invoice_pdf` — ANAF's official `transformare` PDF rendering of an
  invoice XML.

Both are prod-only on ANAF's side (their TEST paths answer 404), which is another
reason they live on `PublicClient`: they work regardless of how — or whether —
your OAuth credentials are configured.

## Request pacing

Unlike the OAuth clients (which never back off on their own), `PublicClient`
**paces its own requests** — `min_request_interval`, default one request per
second. ANAF states that limit as a usage *rule* rather than enforcing it with
429 responses, so the client observes it client-side.
