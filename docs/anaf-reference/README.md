# ANAF API Reference (local, compiled)

A version-pinned local reference for Romania's ANAF API services, compiled from ANAF's
scattered official sources (PDFs, technical pages, XSD/Schematron) via an agent-driven
process. **This is derived material** — the authoritative originals are preserved
verbatim under [`_sources/`](_sources/). Every page carries `sources`, revisions, and
dates in its frontmatter, and is `status: draft` until human-reviewed.

Compiled docs are in **English** for developer use; primary sources are Romanian and
are the authority on any discrepancy.

## Index

| Service | Doc | Status |
|---|---|---|
| OAuth (shared) | [oauth/authentication.md](oauth/authentication.md) | draft |
| e-Factura | [efactura/api.md](efactura/api.md) | draft |
| e-Transport | [etransport/api.md](etransport/api.md) | draft |
| Public no-auth services (registries, bilanț) | [public/api.md](public/api.md) | draft |

## Conventions

- `_sources/` — raw originals (PDFs/HTML/XSD/Schematron), never edited or LLM-rewritten.
- Each doc cites provenance **per section** so claims are spot-checkable.
- Regeneration: see the docs process in [`/DESIGN.md`](../../DESIGN.md) §6.
