# Contributing to anafpy

Issues and pull requests are welcome — anafpy is free, as-is, and maintained
best-effort, so clear reports and focused changes help the most.

## Development setup

```bash
git clone https://github.com/robert-malai/anafpy && cd anafpy
uv sync --all-extras
```

## The four gates

Every change must keep all four green — CI runs the test suite on
Linux/macOS/Windows across Python 3.12 and 3.13, and ruff, mypy, the strict
docs build and the extension-manifest validation on the Linux legs:

```bash
uv run pytest -q                             # respx-mocked, credential-free
uv run ruff check . && uv run ruff format --check .
uv run mypy                                  # strict
uv run mkdocs build --strict                 # docs site; `serve` to preview
```

Client behavior changes come with respx tests (upload→poll→download, rejection
paths, 401-refresh, 429 surfacing) — the mocked suite is the gate, and it needs
no ANAF credentials.

## Live smokes (opt-in, never a gate)

```bash
ANAFPY_LIVE=1 uv run pytest -m live
```

The `live` marker re-confirms wire shapes against real ANAF endpoints and is
skipped by default. It covers the public services and BNR (no credentials
needed) plus, with `.env` credentials and an `anafpy auth login` token store,
the authenticated **TEST** environment, and read-only production smokes for SPV
and StareD112. Three tests file: the e-Factura and e-Transport roundtrips (TEST
only, never production) and the D406T no-fiscal-effect test declaration on the
production portal, behind its own `ANAFPY_LIVE_FILE_D406T=1`. Keep every other
live test read-only; the deliberate filing
exceptions are documented in [CLAUDE.md](CLAUDE.md).

## Generated code

Models under `src/anafpy/efactura/ubl/`, `src/anafpy/etransport/schema/` and
`src/anafpy/bnr/schema/` (and `efactura/authoring/_codelists.py`) are **generated** from vendored
schemas — never hand-edit them. To change them, edit the generating script or
re-vendor the schema and regenerate; [schemas/README.md](schemas/README.md) is
the provenance record and playbook.

## Where things are decided

- [CLAUDE.md](CLAUDE.md) — the current rules: layout, conventions, error
  model, testing boundaries.
- [DESIGN.md](DESIGN.md) — the decision record: rationale, dates, reversals.
- [docs/anaf-reference/](docs/anaf-reference/) — ANAF wire facts; when parsing
  code and this reference disagree, the reference wins (fix whichever is wrong,
  with provenance intact).

Each fact keeps **one home** — link instead of retelling, and update the
affected homes in the same change.
