"""Composition root: build the configured :class:`FastMCP` server.

Owns the model-facing server instructions, the lifespan (one :class:`AppContext`,
closed on shutdown) and the ``auth_status`` tool, and delegates everything else to
the service packages' and feature modules' ``register`` functions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from . import declaratii, efactura, etransport, prompts, public, reference, spv
from .artifacts import READ_ONLY
from .config import ServerConfig
from .context import AppContext, AuthStatus

__all__ = ["create_server", "main"]

_INSTRUCTIONS = """\
Typed access to Romania's ANAF e-Factura (e-invoicing) and e-Transport services.

Filing is a two-step, human-gated flow:
  1. call a prepare tool — it returns a preview, the exact XML, and a confirmation
     token;
  2. show the preview to the user, get explicit approval, then call the matching
     `*_submit*` tool with that token and confirm=True.

Both services file through that gate, and both take two input shapes:
- Ready-made XML: `efactura_prepare` / `etransport_prepare` take a complete
  document the user's software produced ({"xml": ...} or {"path": ...}). For
  invoices this is the RECOMMENDED path whenever invoicing software exists —
  never re-compose what an upstream system already exported.
- Structured fields, no XML needed: `efactura_prepare_invoice` composes a full
  CIUS-RO invoice or credit note from the flat invoice model (totals and the VAT
  breakdown are computed from the lines; local_findings reports anafpy's
  translated rule check, informationally). e-Transport composes with
  `etransport_prepare_declaration` (new declaration or, with correction_of_uit,
  a correction), `etransport_prepare_deletion`, `etransport_prepare_confirmation`
  and `etransport_prepare_vehicle_change`; enum-coded fields accept ANAF codes or
  member names ('TTN', 'CLUJ', 'NADLAC') — list them with
  `etransport_nomenclature`.
Each composing tool returns the exact XML it rendered — pass it back to the
matching `*_submit` tool verbatim as document={"xml": ...}. After an e-Factura
submit, poll `efactura_get_status` to `ok`/`nok`.

Confirmation tokens are single-use and bound to the exact document and the CIF — to
file again (or for another CIF), run the prepare step again.

`efactura_download` returns the invoice XML plus an easy-to-read flat `invoice`
view — work from the view. The binary artifacts are for the user, not the context:
pass `save_zip_as` / `save_pdf_as` (file paths) to have the server write the signed
archive ZIP and ANAF's official PDF rendering to disk — e.g. for "export last
month's invoices as PDFs named '<date> - <partner>.pdf'", list the messages, look
the partner names up, then call `efactura_download` once per invoice with
`save_pdf_as`. An existing file is never replaced unless `overwrite=true` — a name
collision comes back in `pdf_error`/`zip_error` instead of losing a file. The PDF
also exists as the resource `anafmsg://<message_id>/pdf`; never read it into
context when a file on disk is what the user wants.

To pre-check an invoice, `efactura_validate` runs ANAF's own server-side validator
without filing (authoritative; public and no-auth, so it needs no login). e-Transport
has no standalone validator — ANAF validates on upload. If a tool reports "not
authenticated", the user must run `anafpy auth login` host-side.

The `spv_*` tools read the taxpayer's SPV (Spațiul Privat Virtual) mailbox —
receipts, decisions, notifications — and request official reports (VECTOR FISCAL,
Obligatii de plata, Istoric declaratii, declaration duplicates, ...). SPV is
READ-ONLY here (no declaration submission) and authenticates with the user's
qualified certificate, not OAuth. SPV sessions are short-lived (under an hour
idle): when they lapse, ask the user for permission and call `spv_login` with
confirm=true — it fires THEIR PIN/2FA prompt, so never call it uninvited — or
have them run `anafpy spv login` in a terminal. Start with `spv_status` — it
also reports `authorized_cuis`, the CUIs/CNPs the certificate may query.
Reports are asynchronous: `spv_cerere` returns an `id_solicitare`,
`spv_asteapta_raport` waits and saves the PDF; a 'pending' answer is normal, not
an error. Downloads always go to disk at caller-given paths, never into context.
A message's document also exists as the resource `spvmsg://<mesaj_id>/pdf`;
never read it into context when a file on disk is what the user wants.

The `declaratie_*` tools author, validate, render, and sign Romanian tax
declarations (D300 first) entirely locally — nothing is filed with ANAF in this
release. Compose the XML from the form's XSD (attributes on a single root
element), then: `declaratie_validate` in a loop (findings are ANAF's own
DUKIntegrator messages — fix and retry until ok); compute `nr_evid` with
`declaratie_nr_evid`, never by hand; `declaratie_render` to write the official
PDF; ask the user to review it; then, only on their explicit go, warn them the
certificate PIN/2FA prompt is about to fire and call `declaratie_sign` with
confirm=true. Hand back the signed PDF path and tell the user to file it at
anaf.ro → Depunere declarații (portal upload is a later release), asking them to
note the upload index the portal returns. With that index, `declaratie_status`
checks the processing state (public no-auth service — works without any login;
`processing` means check again later, `valid` means accepted) and
`declaratie_recipisa` saves the signed filing receipt PDF to disk — recipisas
are only available ~60 days, so advise archiving it promptly.
`declaratie_duk_status` reports the DUKIntegrator install and validator
staleness. The authoring tools need ANAFPY_DUK_DIR set (signing is macOS-only
for now); the status/recipisa tools need nothing.

The `anaf_*` lookup tools query ANAF's PUBLIC no-auth services and work even without
a login: the taxpayer/VAT registry (`anaf_lookup_taxpayers` answers "is this CUI
VAT-registered / e-Factura-registered" and more, in one call — use it to sanity-check
a counterparty before filing), the RO e-Factura opt-in register, the farmers/cult
registers, and public annual financial statements. Registry membership must be read
from the `registered` booleans, not from presence in `found`. Requests are paced at
ANAF's 1 request/second rule, so large batches take time.
"""


def create_server(config: ServerConfig | None = None) -> FastMCP:
    """Build the configured :class:`FastMCP` server (stdio transport)."""
    cfg = config or ServerConfig.from_env()
    ctx = AppContext(cfg)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await ctx.aclose()

    mcp = FastMCP("anafpy", instructions=_INSTRUCTIONS, lifespan=lifespan)

    @mcp.tool(
        title="ANAF: Authentication status",
        annotations=READ_ONLY,
        description="Report whether a usable ANAF session is present, and when the "
        "tokens expire. Call this first; if not authenticated, ask the user to run "
        "`anafpy auth login` host-side. If credentials_configured is false, the "
        "authenticated tools are unavailable (set ANAFPY_CLIENT_ID / "
        "ANAFPY_CLIENT_SECRET) but the public anaf_* lookups still work.",
    )
    def auth_status() -> AuthStatus:
        return ctx.auth_status()

    efactura.register(mcp, ctx, cfg)
    etransport.register(mcp, ctx, cfg)
    public.register(mcp, ctx)
    spv.register(mcp, ctx, cfg)
    declaratii.register(mcp, ctx, cfg)
    reference.register(mcp, cfg)
    prompts.register(mcp, cfg)
    return mcp


def main() -> None:
    """Console entry point: run the server over stdio."""
    create_server().run("stdio")
