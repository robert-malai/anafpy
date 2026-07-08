# `anafpy.efactura` — how the pieces fit

Three representations of the same invoice, one conversion layer between each,
and a client that moves the bytes. Deep detail lives in the
[docs site](https://anafpy.readthedocs.io) and `DESIGN.md` §4; this is the map.

## The model stack

```mermaid
flowchart LR
    subgraph FLAT["authoring/ — flat layer (ergonomic, CIUS-RO-scoped)"]
        ID["InvoiceDocument<br/>Seller / Party / InvoiceLine / Totals / VatBreakdownEntry ...<br/>totals + VAT breakdown computed; validate() = BR-* rule set"]
    end
    subgraph GEN["ubl/ — generated layer (schema-complete)"]
        UBL["Invoice / CreditNote + cac:/cbc: components<br/>xsdata-pydantic, mirrors UBL 2.1 one-to-one"]
    end
    subgraph WIRE["the wire (what ANAF sees; the legal artifact)"]
        XML["UBL XML bytes"]
    end

    ID -- "build.py: build_invoice()" --> UBL
    UBL -- "read.py: read_invoice()" --> ID
    UBL -- "XmlSerializer" --> XML
    XML -- "XmlParser (parse_ubl_document)" --> UBL
```

- **`render_invoice(doc)`** = `build_invoice` + `XmlSerializer` (validates first
  unless `skip_validation=True`).
- **`parse_invoice(xml)`** = `parse_ubl_document` + `read_invoice`.
- Round-trips are **byte-stable**: `render(parse(render(doc))) == render(doc)`.
- The generated layer is the only place XML is touched — the flat models never
  serialize themselves, and nothing here is hand-written serializer code.

## Outbound: two ways in, one upload

```mermaid
flowchart TD
    SW["Invoicing software's own UBL XML<br/>(recommended when you have one — never re-composed)"]
    AU["InvoiceDocument authored from business fields<br/>(no upstream system needed)"]
    AU -- "local rule check: authoring.validate()<br/>findings with official BR-* ids (informational)" --> AU
    SW -- "EFacturaClient.upload(xml)" --> UP["ANAF /upload → UploadResult (upload_id)"]
    AU -- "EFacturaClient.upload_invoice(doc)<br/>(render + standard UBL/CN)" --> UP
    UP --> ST["get_status(upload_id)<br/>'in prelucrare' → ok / nok"]
    VAL["PublicClient.validate_invoice — ANAF's validare,<br/>authoritative, no-auth, files nothing"]
    SW -.optional pre-check.-> VAL
    AU -.optional pre-check.-> VAL
```

Through MCP the same two shapes are `efactura_prepare` (XML pass-through) and
`efactura_prepare_invoice` (composed), both behind the two-step confirmation
gate, then `efactura_submit` → `efactura_get_status`.

## Inbound: one download, three read tiers

```mermaid
flowchart TD
    DL["EFacturaClient.download(id)"] --> DM["DownloadedMessage"]
    DM --> T1["tier 1 — raw_zip / content_xml / signature_xml<br/>authoritative, legally archivable"]
    DM --> T2["tier 2 — document: ubl.Invoice | CreditNote<br/>full parsed model (lazy)"]
    DM --> T3["tier 3 — view: InvoiceDocument | None<br/>strict authoring reader, never raises"]
    T3 -. "None ⇒ not a representable invoice<br/>(nok errors file, buyer message, rule drift)<br/>fall back to tier 2 / tier 1" .-> T2
```

Tier 3 is the same flat model you author with, read full-fidelity from the wire
(amounts land in the explicit fields, never recomputed) — so a received invoice
is one edit away from a drafted credit note, and `validate()` can judge an
upstream document's arithmetic. Strictness is safe here: everything in the
inbox already passed ANAF's validation, whose rules the flat models mirror.

## Who owns what

| Piece | Source of truth | Regenerate / edit |
|---|---|---|
| `ubl/` | vendored OASIS UBL 2.1 XSDs (`schemas/ubl-2.1/`) | `scripts/generate_ubl.py` — never hand-edit |
| `authoring/_codelists.py` | vendored EN 16931 Schematron (`schemas/efactura/schematron/`) | `scripts/generate_efactura_codelists.py` — never hand-edit |
| `authoring/` (rest) | hand-written; rules translated from the CIUS-RO 1.0.9 Schematron | edit normally, keep rule ids honest |
| `client.py`, `models.py` | hand-written transport + value types | edit normally |
