# The clients at a glance

What the library ships today, client by client. Each entry links to its guide;
the [quickstart](quickstart.md) is the fastest way to a first call. The clients
are **async-only** (a sync facade was dropped as a goal) and are used as async
context managers.

- **OAuth2 auth layer** — Authorization-Code bootstrap (browser + qualified
  certificate), local token store, and headless refresh, exposed via the `anafpy` CLI
  and an `httpx2.Auth` integration for the clients. Guide:
  [authentication](auth.md).
- **`EFacturaClient`** — `upload` (ready-made XML) and `upload_invoice`
  (an authored `InvoiceDocument`), `get_status`, `download`,
  `validate_signature` (checks the MF signature over a downloaded invoice), the
  `upload_and_wait` poll-until-terminal helper, and `list_messages` — a single async
  iterator that pages the message list under the hood (window by `days` or `start`/`end`;
  empty window → empty iterator, real ANAF errors → raise). `download` exposes three read
  tiers: raw signed bytes, the full UBL model, and the flat `InvoiceDocument` **view**
  (the same authoring model, read full-fidelity from the wire). Guide:
  [e-Factura](efactura.md).
- **Invoice authoring** (`anafpy.efactura.authoring`) — bidirectional CIUS-RO
  models: one `InvoiceDocument` covers invoice and credit note, totals and the
  VAT breakdown are computed from the lines (explicit values preserved), and a
  hand-translated EN 16931 + CIUS-RO rule set (`validate()`) reports findings
  with the official BR-* ids before anything is filed. `render_invoice` emits
  upload-ready XML; `parse_invoice`/`read_invoice` map wire XML back into the
  same models with byte-stable round-trips. Guide:
  [invoice authoring](authoring.md).
- **`ETransportClient`** — `upload`, `get_status`, `info`, `upload_and_wait`,
  `list_notifications` (same async-iterator shape), and **`upload_document`**, which
  composes and files any of the four flat documents — a `FlatTransport`
  declaration/correction, `FlatDeletion`, `FlatConfirmation`, or `FlatVehicleChange` —
  without the caller touching XML. The flat models are **bidirectional**:
  `read_flat_transport` views a parsed document and `build_etransport` /
  `render_etransport` author one — full translation of ANAF's XSD, with
  enum-coded fields (counties, border points, customs offices, operation
  types...) accepted by name or code. Guide: [e-Transport](etransport.md).
- **`PublicClient`** — ANAF's **unauthenticated** public services on
  `webservicesp.anaf.ro`: `lookup_taxpayers` (VAT registration, VAT-on-collection,
  inactive, split-VAT, and RO e-Factura register membership in one call),
  `lookup_efactura_register`, `lookup_farmers`, `lookup_cult_entities`,
  `get_financial_statement` (public bilanț indicators) — plus the stateless
  e-Factura document services: `validate_invoice` (ANAF's authoritative
  server-side validation, no filing) and `render_invoice_pdf` (the official
  `transformare` PDF rendering); both are prod-only on ANAF's side and need no
  login. No credentials, no test/prod split; requests are paced client-side at
  ANAF's stated 1 req/s rule. Guide: [public services](public.md).
- **`SpvClient`** (read-only) — the taxpayer's **SPV mailbox** over the
  qualified certificate: `list_messages` (with the certificate's authorization
  inventory), `download_document` (PDF), `request_report` (the full `cerere`
  nomenclature — 35 report types with per-type parameter validation before any
  wire call), and `wait_for_report`. The certificate step is one interactive
  `anafpy spv login` (macOS Keychain/SecureTransport or Windows
  CertStore/Schannel via the OS-shipped curl — the keys are non-exportable, so
  Python's TLS stack never touches them); everything after rides an APM cookie
  session, prompt-free. Guide: [SPV](spv.md).
- **Declarations** (`anafpy.declaratii`, signing via `anafpy[declaratii]`) —
  local authoring/validation/signing of tax declarations, per-form generic
  across every DUK-validated form (173 today, with hands-on completion guides
  for the [twelve common SME forms](../anaf-reference/declaratii/forms/README.md)):
  a DUKIntegrator wrapper (`-v`/`-p`), the `nr_evid` payment-evidence-number
  composers (D300, D100/D710, D101, D301), and a pyHanko qualified-signature
  path where the raw op is delegated to the OS token (macOS Keychain /
  CryptoTokenKit; no key material in-process). Filing works two ways: manually
  on the portal, or through `DeclarationUploadClient` (certificate login +
  upload on ANAF's declaration portal), which the MCP server exposes as a
  two-step gated filing flow (opt-out via `ANAFPY_DECLARATII_UPLOAD=off`).
  Filing **status** and the signed recipisa are covered too
  (`DeclarationStatusClient` over ANAF's public no-auth StareD112 service).
  Guide: [declarations](declaratii.md).
- **Generated models** — UBL 2.1 / CIUS-RO (`from anafpy.efactura import Invoice,
  CreditNote`) and the proprietary e-Transport XSD, generated from vendored schemas.
- **MCP server** (`anafpy[mcp]`) — a local stdio connector exposing the operations
  above as Claude tools and skills: read-first, with two-step gated filing for
  every service that files. Its own track starts at
  [what you can do](../mcp/index.md).

Before shipping anything on top of these, read the
[error model](errors.md) — transport problems raise, business outcomes return
as typed values, and the difference is deliberate.
