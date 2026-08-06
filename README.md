<p align="center">
  <a href="https://anafpy.readthedocs.io">
    <img src="https://raw.githubusercontent.com/robert-malai/anafpy/main/imgs/anafpy-social-preview.png"
         alt="anafpy — typed Python clients for Romania's ANAF tax web services" width="720">
  </a>
</p>

<p align="center">
  <a href="https://github.com/robert-malai/anafpy/actions/workflows/ci.yml"><img
    src="https://img.shields.io/github/actions/workflow/status/robert-malai/anafpy/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://codecov.io/gh/robert-malai/anafpy"><img
    src="https://img.shields.io/codecov/c/github/robert-malai/anafpy?branch=main" alt="Coverage"></a>
  <a href="https://pypi.org/project/anafpy/"><img
    src="https://img.shields.io/pypi/v/anafpy" alt="PyPI version"></a>
  <a href="https://pepy.tech/project/anafpy"><img
    src="https://img.shields.io/pepy/dt/anafpy" alt="Downloads"></a>
  <a href="https://pypi.org/project/anafpy/"><img
    src="https://img.shields.io/pypi/pyversions/anafpy" alt="Python versions"></a>
  <a href="https://anafpy.readthedocs.io/en/latest/"><img
    src="https://app.readthedocs.org/projects/anafpy/badge/?version=latest" alt="Docs"></a>
  <a href="https://github.com/robert-malai/anafpy/blob/main/LICENSE"><img
    src="https://img.shields.io/pypi/l/anafpy" alt="License"></a>
</p>

# anafpy

Typed Python clients for Romania's **ANAF** tax-authority web services —
**e-Factura** (electronic invoicing), **e-Transport** (goods transport), the
**SPV mailbox** (certificate-authenticated, read-only), **tax declarations**
(declarații — local authoring, validation, qualified signing, filing), and the
**public no-auth registries** (VAT/taxpayer lookups, financial statements) —
plus a local MCP server that puts all of it inside
[Claude](https://claude.com).

anafpy is a **thin transport client** — no persistence, no accounting logic.
Invoices file either as the XML your invoicing software produced (the
strongly recommended path — anafpy never re-composes it) or composed from
plain business fields by the built-in CIUS-RO authoring models. Either way,
ANAF's SPV is **not** invoice storage (it purges filed messages after ~60
days) — the durable record stays on your side.

> Status: **beta** (`0.x`), on PyPI as
> [`anafpy`](https://pypi.org/project/anafpy/); the design rationale lives in
> [`DESIGN.md`](DESIGN.md). Requires **Python 3.12+**; built on **httpx2**
> and **Pydantic v2**.

**Documentation: [anafpy.readthedocs.io](https://anafpy.readthedocs.io)** — the
end-user setup walkthrough, the library guides, and the API reference.

## Use it with Claude

With the MCP server connected, an accountant can ask Claude to:

- **Verify business partners** — VAT status, e-Factura enrollment, financial
  statements — with no login at all.
- **Work the e-Factura inbox**: list messages, save signed ZIPs and rendered
  PDFs to disk in batch, and **file invoices** — from your software's XML or
  composed from plain fields.
- **Declare goods transport in e-Transport** and get the UIT code — from an
  email, a PDF invoice, a CMR — then correct, delete, confirm, or change the
  vehicle.
- **Read the SPV mailbox** and pull official reports (fiscal vector,
  outstanding obligations, filing history, income certificates...).
- **Prepare, validate, sign, and file tax declarations** — validated by ANAF's
  own DUKIntegrator, signed with your qualified certificate.

Every ANAF filing is **two-step gated**: Claude shows a preview and nothing is
submitted until you explicitly confirm. The server runs **locally** on your
machine; artifacts land on your own disk.

Start with the full tour — [what you can
do](https://anafpy.readthedocs.io/en/latest/mcp/) — then the [setup
walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/) (also [in
Romanian](https://anafpy.readthedocs.io/en/latest/mcp/setup.ro/)). Each
release also attaches one-click [Claude Desktop
extensions](https://github.com/robert-malai/anafpy/releases) — pick the one
for your machine (`anafpy-darwin-arm64.mcpb` for Apple silicon,
`anafpy-darwin-x64.mcpb` for Intel Macs, `anafpy-win32-x64.mcpb` for Windows)
and drag it into Claude Desktop's Settings → Extensions instead of editing
configuration files. The bundle is self-contained: it carries its own Python,
so nothing else needs to be installed.

## Install

```bash
pip install anafpy               # or: uv add anafpy
pip install 'anafpy[mcp]'        # with the MCP server
pip install 'anafpy[declaratii]' # with declaration signing (pyHanko)
```

For the MCP server outside the desktop extension, install it as a **uv tool**
(what the setup walkthrough does): `uv tool install "anafpy[mcp]"` — this puts
the `anafpy` CLI and the `anafpy-mcp` server on the machine without touching
any project environment.

## Use it as a Python library

ANAF uses OAuth2 gated by a **qualified digital certificate**; a one-time
`anafpy auth login` opens the browser for the certificate step, then tokens
refresh headlessly for ~a year from the OS credential store — the
[authentication guide](https://anafpy.readthedocs.io/en/latest/library/auth/)
has the details. From there the clients are async context managers:

```python
from anafpy.auth import KeyringTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient

provider = TokenProvider(
    client_id="<ID>",
    client_secret="<SECRET>",
    store=KeyringTokenStore(),  # OS credential store (the default backend)
)

async with EFacturaClient(provider) as efactura:
    result = await efactura.upload(invoice_xml, cif="RO12345678")
    status = await efactura.get_status(result.upload_id)
    # or, in one call: status = await efactura.upload_and_wait(invoice_xml, cif=...)
```

Discrete methods make a single call (no transport retry). HTTP/auth problems
raise `AnafError` subclasses; **business outcomes** (a `nok` rejection, BR-RO
findings) come back as typed values, not exceptions.

The [clients at a
glance](https://anafpy.readthedocs.io/en/latest/library/) page inventories
every client; the worked examples live in the per-service guides —
[e-Factura](https://anafpy.readthedocs.io/en/latest/library/efactura/),
[invoice authoring](https://anafpy.readthedocs.io/en/latest/library/authoring/),
[e-Transport](https://anafpy.readthedocs.io/en/latest/library/etransport/),
[public services](https://anafpy.readthedocs.io/en/latest/library/public/),
[SPV](https://anafpy.readthedocs.io/en/latest/library/spv/),
[declarations](https://anafpy.readthedocs.io/en/latest/library/declaratii/),
and the [error model](https://anafpy.readthedocs.io/en/latest/library/errors/).

## MCP server

The `anafpy[mcp]` extra ships a **local stdio MCP server** wrapping the
clients. The surface is **read-first**: the public lookups and
`efactura_validate` need no credentials at all, reads need the one-time login,
and every filing goes through the two-step prepare→submit confirmation gate.
The compiled ANAF reference is served as resources and the workflow playbooks
as prompts. Register it with any MCP client — e.g. with Claude Code:

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- anafpy-mcp
```

The [tools overview](https://anafpy.readthedocs.io/en/latest/mcp/tools/) and
[workflow skills](https://anafpy.readthedocs.io/en/latest/mcp/skills/) document
the full surface. The server is **best-effort**: configuring it — including
registering your own OAuth application on ANAF's portal — is your
responsibility, and the setup walkthrough covers every step.

## Contributing

Dev setup, the four gates, live smokes, and the generated-code rules are in
[CONTRIBUTING.md](CONTRIBUTING.md); repository conventions live in
[CLAUDE.md](CLAUDE.md).

## Privacy Policy

anafpy runs entirely on your own computer and collects **nothing** — no
telemetry, no analytics, no author-operated server. Your data moves only
between your machine and ANAF; tokens and downloaded documents are stored
locally, and your certificate's private key is never touched. When used
through an AI assistant, tool results become part of that conversation under
your AI provider's own policy. The full policy:
[anafpy.readthedocs.io/en/latest/privacy/](https://anafpy.readthedocs.io/en/latest/privacy/).

## License

[Apache-2.0](LICENSE). Independent / unofficial — not affiliated with ANAF.

anafpy is free to use and provided **as-is**, with no warranty: it moves documents
to and from ANAF, it does not give tax advice, and filing outcomes are your
responsibility. The MCP server is **best-effort** — configuring it, provisioning
your own OAuth application on ANAF's portal, and holding the qualified certificate
are up to you (the
[setup walkthrough](https://anafpy.readthedocs.io/en/latest/mcp/setup/) covers all
of it).
