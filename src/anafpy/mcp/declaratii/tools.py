"""Declaration MCP tools — author, validate, render, sign, and track status.

The authoring flow is local: DUKIntegrator (ANAF's own validator/renderer) runs
``-v``/``-p`` in a subprocess, and the qualified signature is embedded with
pyHanko while the raw RSA op is delegated to the OS token middleware — no key
material or PIN ever enters this process (``DESIGN.md`` invariant). Filing the
signed PDF with ANAF is manual in this milestone (point the user at the portal);
a later milestone automates the upload. Status tracking is already automated:
``declaratie_status`` / ``declaratie_recipisa`` ride ANAF's **public, no-auth**
StareD112 service, so once the user filed manually and has the upload index,
the confirmation loop (state + signed recipisa) needs no login. These two tools
work without ``ANAFPY_DUK_DIR``.

Validation authority is ANAF's: ``declaratie_validate`` runs DUK's per-form
validator and returns its findings verbatim — the model's iteration loop is
"validate → fix the XML → validate again" until ``ok``. Signing is
consequential, so ``declaratie_sign`` is gated on ``confirm=true`` and fires the
user's out-of-band approval; it mirrors ``spv_login``'s contract (failures come
back as ``signed=false`` + guidance, never as exceptions). PDFs are written to
caller-given paths through the shared ``write_artifact`` collision guard, never
returned as base64.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ...declaratii import payment_evidence_number
from ...declaratii.duk import fetch_feed_versions
from ...declaratii.models import DeclarationStatusList
from ...declaratii.signing import (
    KeychainRawSigner,
    default_signed_path,
    load_pdfsign,
    resolve_signing_label,
)
from ...exceptions import AnafConfigError, AnafError
from ..artifacts import (
    ARTIFACT_SAVING,
    MUTATING,
    READ_ONLY,
    ensure_writable,
    write_artifact,
)
from ..config import ServerConfig
from ..context import AppContext
from .models import (
    DeclarationXmlInput,
    NrEvidResult,
    ReceiptResult,
    RenderResult,
    SignResult,
    ValidationResult,
)

__all__ = ["register"]

_FILE_IT = (
    "file the signed PDF manually at anaf.ro → Depunere declarații → Transmitere "
    "declarații (portal upload is automated in a later release); note the upload "
    "index the portal returns — declaratie_status tracks the processing with it, "
    "and declaratie_recipisa downloads the signed filing receipt"
)


def register(mcp: FastMCP, ctx: AppContext, config: ServerConfig) -> None:
    @mcp.tool(
        title="Declarations: validate",
        annotations=READ_ONLY,
        description="Validate a tax declaration with ANAF's own DUKIntegrator "
        "validator (authoritative). `form` is the form name exactly as ANAF "
        "spells the validator (e.g. 'D300', 'D112'); pass the document as "
        '{"xml": ...} or {"path": ...}. Returns {ok, findings}: on ok=false, '
        "`findings` are DUK's own error/warning messages verbatim — fix the XML "
        "and call again (typical convergence is under 6 rounds). This is the "
        "authoring loop; nothing is filed.",
    )
    async def declaratie_validate(
        document: DeclarationXmlInput, form: str, option: int = 0
    ) -> ValidationResult:
        try:
            xml = document.resolve()
            result = await ctx.duk().validate(form, xml, option=option)
        except AnafConfigError:
            raise
        except AnafError as exc:
            return ValidationResult(ok=False, form=form, message=str(exc))
        return ValidationResult(ok=result.ok, form=form, findings=result.findings)

    @mcp.tool(
        title="Declarations: render PDF",
        annotations=ARTIFACT_SAVING,
        description="Render the official multi-page PDF for a declaration (with "
        "the XML embedded) to disk via DUKIntegrator `-p`, and return the saved "
        "path. `form` and the document input are as for declaratie_validate; the "
        "document is validated first, so a validation failure writes NO PDF and "
        "returns the findings (ok=false). Name the file with `save_pdf_as` (a "
        "full path); an existing file is never replaced unless overwrite=true. "
        "The binary never enters the context — sign it next with declaratie_sign.",
    )
    async def declaratie_render(
        document: DeclarationXmlInput,
        form: str,
        save_pdf_as: str,
        option: int = 0,
        overwrite: bool = False,
    ) -> RenderResult:
        try:
            xml = document.resolve()
            # Fail a name collision BEFORE running DUK.
            target = ensure_writable(save_pdf_as, overwrite=overwrite)
            result = await ctx.duk().render(form, xml, target, option=option)
            if not result.ok:
                return RenderResult(
                    ok=False,
                    form=form,
                    findings=result.findings,
                    message="validation failed; no PDF was written",
                )
        except AnafConfigError:
            raise
        except AnafError as exc:
            return RenderResult(ok=False, form=form, message=str(exc))
        return RenderResult(ok=True, form=form, pdf_path=str(target))

    @mcp.tool(
        title="Declarations: sign",
        annotations=MUTATING,
        description="Sign a rendered declaration PDF with the user's qualified "
        "certificate (macOS only in this release). THIS FIRES THE USER'S "
        "PIN/2FA APPROVAL PROMPT on their token or phone — warn them it is coming, "
        "and call this only after they explicitly approve, passing confirm=true. "
        "`pdf_path` is a declaratie_render output; the signed PDF defaults to "
        "'<name>-semnat.pdf' next to it, or set `save_as`. One attempt per call; "
        "a dismissed/timed-out approval or a missing certificate returns "
        "signed=false + guidance (not an error) — ask the user and retry. On "
        "success reports the signed path and whether the issuer chain was "
        "completed; then " + _FILE_IT + ".",
    )
    async def declaratie_sign(
        pdf_path: str,
        save_as: str | None = None,
        confirm: bool = False,
        overwrite: bool = False,
    ) -> SignResult:
        if not confirm:
            return SignResult(
                signed=False,
                guidance="declaratie_sign fires the user's certificate PIN/2FA "
                "prompt — get their explicit approval, warn them the prompt is "
                "coming, then call again with confirm=true",
            )
        source = Path(pdf_path).expanduser()
        target = Path(save_as).expanduser() if save_as else default_signed_path(source)
        try:
            # Fail before certificate discovery/2FA, including the natural retry
            # state where the default signed target already exists.
            target = ensure_writable(target, overwrite=overwrite)
            pdf_bytes = await asyncio.to_thread(source.read_bytes)
            pdfsign = load_pdfsign()
            label = resolve_signing_label(
                config.sign_identity, identity_path=config.spv_identity_path
            )
            signer = await asyncio.to_thread(KeychainRawSigner, label)
            signed = await pdfsign.sign_pdf(pdf_bytes, signer)
            path = await asyncio.to_thread(
                write_artifact, target, signed.pdf, overwrite=overwrite
            )
        except OSError as exc:
            return SignResult(signed=False, guidance=f"cannot read {pdf_path}: {exc}")
        except AnafError as exc:
            return SignResult(signed=False, guidance=str(exc))
        guidance = _FILE_IT
        if signed.warning is not None:
            guidance = f"{signed.warning}; {guidance}"
        return SignResult(
            signed=True,
            pdf_path=path,
            chain_complete=signed.chain_complete,
            guidance=guidance,
        )

    @mcp.tool(
        title="Declarations: filing status",
        annotations=READ_ONLY,
        description="Check the processing status of a filed declaration on ANAF's "
        "public StareD112 service (no login needed). `index` is the upload index "
        "the portal returned on submission (= the recipisa number); `cui` defaults "
        "to the configured fiscal code; pass filed_at_counter=true for documents "
        "filed at an ANAF counter (`index` is then the registration number). A "
        "matching pair returns ALL the CUI's documents from the last 3 months "
        "(max 200), each with `state` in ANAF's verbatim Romanian wording: "
        "'Documentul este valid' = accepted; 'In prelucrare' = still processing, "
        "check again later; 'Documentul are erori de validare' and 'Fişierul "
        "depus nu este un document valid' = must be fixed and refiled. "
        "found=false means the pair matched nothing (wrong pair, older than 3 "
        "months, or beyond the last 200 submissions).",
    )
    async def declaratie_status(
        index: str, cui: str | None = None, filed_at_counter: bool = False
    ) -> DeclarationStatusList:
        try:
            return await ctx.declaration_status().check_status(
                index, config.require_cif(cui), filed_at_counter=filed_at_counter
            )
        except AnafError as exc:
            return DeclarationStatusList(found=False, cui=cui or "", message=str(exc))

    @mcp.tool(
        title="Declarations: download recipisa",
        annotations=ARTIFACT_SAVING,
        description="Download the signed recipisa (filing receipt) PDF for an "
        "upload index from ANAF's public StareD112 service, and write it to "
        "`save_pdf_as` (a full path) — the binary never enters the context. "
        "Recipisas are only available ~60 days from filing: ok=false with an "
        "explanation means the index is unknown or the window has lapsed "
        "(declaratie_status reports availability per document as "
        "receipt_available). An existing file is never replaced unless "
        "overwrite=true. Advise the user to archive the recipisa — it is the "
        "digitally signed proof of filing and ANAF does not keep it accessible.",
    )
    async def declaratie_recipisa(
        index: str, save_pdf_as: str, overwrite: bool = False
    ) -> ReceiptResult:
        try:
            pdf = await ctx.declaration_status().download_receipt(index)
            if pdf is None:
                return ReceiptResult(
                    ok=False,
                    index=index,
                    message="no recipisa available for this index — it is unknown, "
                    "or its ~60-day availability window has lapsed",
                )
            path = write_artifact(save_pdf_as, pdf, overwrite=overwrite)
        except AnafError as exc:
            return ReceiptResult(ok=False, index=index, message=str(exc))
        return ReceiptResult(ok=True, index=index, pdf_path=path)

    @mcp.tool(
        title="Declarations: payment-evidence number",
        annotations=READ_ONLY,
        description="Compose the D300 `nr_evid` (numărul de evidență a plății), "
        "the required 23-character payment-evidence number, from the settlement "
        "type and reporting period. `tip_decont` is one of L (monthly), T "
        "(quarterly), S, A; `month` is 1-12; `year` is four digits. Always "
        "use this — never compute the number (its check digit) by hand.",
    )
    def declaratie_nr_evid(tip_decont: str, month: int, year: int) -> NrEvidResult:
        try:
            number = payment_evidence_number(
                tip_decont=tip_decont, month=month, year=year
            )
        except ValueError as exc:
            raise AnafConfigError(str(exc)) from exc
        return NrEvidResult(
            nr_evid=number, tip_decont=tip_decont, month=month, year=year
        )

    @mcp.tool(
        title="Declarations: DUKIntegrator status",
        annotations=READ_ONLY,
        description="Report the DUKIntegrator installation: its directory, the "
        "Java version, and the per-form validators installed versus ANAF's update "
        "feed (a staleness table). CLI-mode DUK does NOT auto-update, so an "
        "installed validator can lag ANAF's current one — surface that to the "
        "user. The feed fetch is best-effort; offline, only the installed "
        "versions are reported.",
    )
    async def declaratie_duk_status() -> dict[str, object]:
        try:
            duk = ctx.duk()
        except AnafConfigError as exc:
            result: dict[str, object] = {
                "installed_forms": {},
                "install_error": str(exc),
            }
            try:
                feed = await fetch_feed_versions()
            except AnafError as feed_exc:
                result["feed_error"] = str(feed_exc)
                return result
            result["forms"] = [
                {
                    "form": form,
                    "installed": "not installed",
                    "current": version,
                    "stale": True,
                }
                for form, version in sorted(feed.items())
            ]
            return result

        installed = duk.installed_forms()
        java_result, feed_result = await asyncio.gather(
            duk.java_version(), fetch_feed_versions(), return_exceptions=True
        )
        result = {
            "duk_dir": str(duk.duk_dir),
            "java": java_result if isinstance(java_result, str) else "unknown",
            "installed_forms": installed,
        }
        if isinstance(feed_result, BaseException):
            result["feed_error"] = str(feed_result)
            result["note"] = (
                "could not reach ANAF's update feed; showing installed versions only"
            )
            return result
        feed = feed_result
        result["forms"] = [
            {
                "form": form,
                "installed": installed.get(form, "not installed"),
                "current": feed.get(form, "unknown"),
                "stale": form in feed and installed.get(form) != feed[form],
            }
            for form in sorted(installed.keys() | feed.keys())
        ]
        return result
