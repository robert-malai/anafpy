"""Declaration MCP tools — author, validate, render, sign, file, and track status.

The authoring flow is local: DUKIntegrator (ANAF's own validator/renderer) runs
``-v``/``-p`` in a subprocess, and the qualified signature is embedded with
pyHanko while the raw RSA op is delegated to the OS token middleware — no key
material or PIN ever enters this process (``DESIGN.md`` invariant). Filing the
signed PDF is automated over the ``WAS6DUS`` portal client — **opt-out** via
``ANAFPY_DECLARATII_UPLOAD`` (filing goes to the production portal; there is no
TEST environment for declarations), in which case the tools point the user at
manual portal filing instead. Status tracking rides ANAF's **public, no-auth**
StareD112 service: ``declaratie_status`` / ``declaratie_recipisa`` close the
confirmation loop (state + signed recipisa) with no login; these two work
without ``ANAFPY_DUK_DIR``.

Filing follows the shared two-step gate (``mcp/gate.py``) with the portal login
deliberately OUTSIDE the submit cycle: ``declaratie_portal_login`` is its own
confirm-gated tool (it fires the certificate PIN/2FA, mirroring ``spv_login``),
``declaratie_portal_status`` probes the session without any 2FA, and
``declaratie_submit`` re-probes before consuming the confirmation token — a
dead session never burns the human's approval. The token is bound to the exact
signed-PDF bytes and the multipart filename.

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
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ...declaratii import (
    obligation_evidence_number,
    payment_evidence_number,
    profit_tax_evidence_number,
    special_vat_evidence_number,
)
from ...declaratii.duk import fetch_feed_versions
from ...declaratii.models import DeclarationStatusList
from ...declaratii.signing import (
    KeychainRawSigner,
    default_signed_path,
    load_pdfsign,
    resolve_signing_label,
)
from ...declaratii.upload import PortalCurlBootstrapper
from ...exceptions import AnafAuthError, AnafConfigError, AnafError
from ...spv import load_selected_identity
from ..artifacts import (
    ARTIFACT_SAVING,
    LOCAL_READ_ONLY,
    MUTATING,
    READ_ONLY,
    ensure_writable,
    write_artifact,
)
from ..config import ServerConfig
from ..context import AppContext
from ..gate import TOKEN_USED_MESSAGE, ConfirmationError, issue_token, verify_token
from .models import (
    DeclarationXmlInput,
    NrEvidResult,
    PortalLoginResult,
    PortalStatusResult,
    PreparedUpload,
    ReceiptResult,
    RenderResult,
    SignResult,
    UploadSubmitResult,
    ValidationResult,
)

__all__ = ["register"]

_UPLOAD_KIND = "declaratie.upload"

_FILE_IT_PORTAL = (
    "file it from here: check the portal session with declaratie_portal_status "
    "(declaratie_portal_login with the user's approval if it lapsed), then "
    "declaratie_prepare → declaratie_submit; the returned upload index feeds "
    "declaratie_status and declaratie_recipisa (manual filing at anaf.ro → "
    "Depunere declarații remains possible)"
)

_FILE_IT_MANUAL = (
    "file the signed PDF manually at anaf.ro → Depunere declarații → Transmitere "
    "declarații (automated portal upload is opted out via "
    "ANAFPY_DECLARATII_UPLOAD); note the upload "
    "index the portal returns — declaratie_status tracks the processing with it, "
    "and declaratie_recipisa downloads the signed filing receipt"
)

_PORTAL_LOGIN_HINT = (
    "ask the user for approval and call declaratie_portal_login with "
    "confirm=true (it fires their certificate PIN/2FA prompt)"
)


def _looks_signed(pdf: bytes) -> bool:
    """Cheap local check that an embedded PKCS#7 PDF signature is present.

    Informational only (the portal's verdict is authoritative): pyHanko's
    incremental update always carries both markers, and an unsigned DUK
    rendering carries neither.
    """
    return b"/ByteRange" in pdf and b"adbe.pkcs7.detached" in pdf


def _upload_context(filename: str) -> str:
    """The submission parameter bound into a filing's confirmation token."""
    return f"filename={filename}"


def _no_findings_message(raw: str) -> str:
    """Explain a failed DUK run that yielded no parseable findings.

    The parser fails closed on output it does not understand (e.g. the empty
    err file a broken/mis-versioned dist leaves behind), so without this hint
    the model would loop rewriting possibly-valid XML.
    """
    hint = (
        "DUK reported failure but produced no parseable findings — the form's "
        "validator may be missing or broken; check declaratie_duk_status"
    )
    if text := raw.strip():
        return f"{hint} (raw DUK output: {text})"
    return hint


def _require_code(cod_oblig: str | None, form: str) -> str:
    if not cod_oblig:
        raise AnafConfigError(f"form {form} requires cod_oblig (the 3-digit code)")
    return cod_oblig


def _require_scadenta(scadenta: str | None, form: str) -> date:
    """Parse the scadență into a date, accepting `d.m.yyyy` or ISO `yyyy-mm-dd`."""
    if not scadenta:
        raise AnafConfigError(
            f"form {form} requires scadenta (payment due date, e.g. 25.07.2026)"
        )
    text = scadenta.strip()
    for day_first, sep in ((True, "."), (False, "-")):
        if sep in text:
            parts = text.split(sep)
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                day, month, year_ = parts if day_first else parts[::-1]
                try:
                    return date(int(year_), int(month), int(day))
                except ValueError as exc:
                    raise AnafConfigError(
                        f"invalid scadenta {scadenta!r}: {exc}"
                    ) from exc
    raise AnafConfigError(
        f"scadenta {scadenta!r} must be d.m.yyyy (e.g. 25.07.2026) or yyyy-mm-dd"
    )


def register(mcp: FastMCP, ctx: AppContext, config: ServerConfig) -> None:
    file_it = _FILE_IT_PORTAL if config.declaratii_upload else _FILE_IT_MANUAL

    @mcp.tool(
        title="Declarations: validate",
        annotations=READ_ONLY,
        description="Validate a tax declaration with ANAF's own DUKIntegrator "
        "validator (authoritative). `form` is the form name exactly as ANAF "
        "spells the validator (e.g. 'D300', 'D112'); pass the document as "
        '{"xml": ...} or {"path": ...}. Returns {ok, findings, warnings}: '
        "ok=false means DUK reported errors — `findings` are its own messages "
        "verbatim, fix the XML and call again (typical convergence is under 6 "
        "rounds). ok=true means the document is valid; `warnings` may still be "
        "non-empty (DUK's informational notices — e.g. D700's 'the form will be "
        "processed at the competent tax office' — which are NOT errors: relay "
        "them to the user but do not treat them as a failure). This is the "
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
        return ValidationResult(
            ok=result.ok,
            form=form,
            findings=result.findings,
            warnings=result.warnings,
            message=""
            if result.ok or result.findings
            else _no_findings_message(result.raw),
        )

    @mcp.tool(
        title="Declarations: render PDF",
        annotations=ARTIFACT_SAVING,
        description="Render the official multi-page PDF for a declaration (with "
        "the XML embedded) to disk via DUKIntegrator `-p`, and return the saved "
        "path. `form` and the document input are as for declaratie_validate; the "
        "document is validated first, so a validation failure writes NO PDF and "
        "returns the findings (ok=false), while a valid document with DUK "
        "warnings still renders (ok=true, `warnings` set — relay them). Name the "
        "file with `save_pdf_as` (a "
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
                    message=(
                        "validation failed"
                        if result.findings
                        else _no_findings_message(result.raw)
                    )
                    + "; no PDF was written",
                )
        except AnafConfigError:
            raise
        except AnafError as exc:
            return RenderResult(ok=False, form=form, message=str(exc))
        return RenderResult(
            ok=True, form=form, pdf_path=str(target), warnings=result.warnings
        )

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
        "completed; then " + file_it + ".",
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
            try:
                pdf_bytes = await asyncio.to_thread(source.read_bytes)
            except OSError as exc:
                return SignResult(
                    signed=False, guidance=f"cannot read {pdf_path}: {exc}"
                )
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
            # The source read has its own handler above — an OSError here is
            # write-side (target parent mkdir, or the final signed-PDF write
            # after the 2FA approval was already spent): name the target, not
            # the source, so the guided retry fixes the destination instead of
            # re-firing 2FA against a perfectly readable PDF.
            return SignResult(signed=False, guidance=f"cannot write {target}: {exc}")
        except AnafError as exc:
            return SignResult(signed=False, guidance=str(exc))
        guidance = file_it
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
        annotations=LOCAL_READ_ONLY,
        description="Compose the `nr_evid` (numărul de evidență a plății), the "
        "required 23-character payment-evidence number, for a self-assessed "
        "declaration. `month` is 1-12, `year` four digits. `form` selects the "
        "layout and its required inputs: `D300` (default) needs `tip_decont` "
        "(L monthly / T quarterly / S / A); `D100` and `D710` need the 3-digit "
        "`cod_oblig` and the `scadenta` (payment due date, `d.m.yyyy` — e.g. "
        "`25.07.2026`); `D101` needs `cod_oblig` (the obligation code) and "
        "`scadenta`, and takes `in_liquidation` for a liquidation-period "
        "return; `D301` needs neither and takes `mijl_trans` (set when the "
        "return reports an intra-EU acquisition of new means of transport). "
        "Always use this — never compute the number (its check digit) by hand.",
    )
    def declaratie_nr_evid(
        month: int,
        year: int,
        form: str = "D300",
        tip_decont: str | None = None,
        cod_oblig: str | None = None,
        scadenta: str | None = None,
        mijl_trans: bool = False,
        in_liquidation: bool = False,
    ) -> NrEvidResult:
        form = form.upper()
        try:
            if form == "D300":
                if tip_decont is None:
                    raise AnafConfigError("form D300 requires tip_decont (L/T/S/A)")
                number = payment_evidence_number(
                    tip_decont=tip_decont, month=month, year=year
                )
            elif form in {"D100", "D710"}:
                number = obligation_evidence_number(
                    cod_oblig=_require_code(cod_oblig, form),
                    month=month,
                    year=year,
                    due_date=_require_scadenta(scadenta, form),
                )
            elif form == "D101":
                number = profit_tax_evidence_number(
                    cod_obligatie=_require_code(cod_oblig, form),
                    month=month,
                    year=year,
                    due_date=_require_scadenta(scadenta, form),
                    in_liquidation=in_liquidation,
                )
            elif form == "D301":
                number = special_vat_evidence_number(
                    month=month, year=year, new_transport=mijl_trans
                )
            else:
                raise AnafConfigError(
                    f"unknown form {form!r}; expected one of: "
                    "D300, D100, D710, D101, D301"
                )
        except ValueError as exc:
            raise AnafConfigError(str(exc)) from exc
        return NrEvidResult(
            nr_evid=number,
            form=form,
            month=month,
            year=year,
            tip_decont=tip_decont if form == "D300" else None,
            cod_oblig=cod_oblig if form in {"D100", "D710", "D101"} else None,
            scadenta=scadenta if form in {"D100", "D710", "D101"} else None,
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

    if config.declaratii_upload:
        _register_upload_tools(mcp, ctx, config)


def _register_upload_tools(mcp: FastMCP, ctx: AppContext, config: ServerConfig) -> None:
    """The portal-filing tools — served unless ``ANAFPY_DECLARATII_UPLOAD`` opts out."""

    @mcp.tool(
        title="Declarations: portal session status",
        annotations=READ_ONLY,
        description="Probe whether the declaration-filing portal session is "
        "still alive: a plain page fetch with the stored cookies — NO PIN/2FA "
        "is ever fired. Call it before declaratie_submit (portal sessions die "
        "after ~10 idle minutes). session_active=false means a login is "
        "needed first: with the user's approval, declaratie_portal_login.",
    )
    async def declaratie_portal_status() -> PortalStatusResult:
        try:
            active = await ctx.declaration_upload().probe()
        except AnafError as exc:
            return PortalStatusResult(
                session_active=False,
                detail=f"the portal could not be probed: {exc}",
                next_step="retry when the portal is reachable",
            )
        if active:
            return PortalStatusResult(
                session_active=True,
                detail="portal session active — file promptly (~10-minute "
                "inactivity timeout)",
            )
        return PortalStatusResult(
            session_active=False,
            detail="no active portal session",
            next_step=_PORTAL_LOGIN_HINT,
        )

    @mcp.tool(
        title="Declarations: portal log in",
        annotations=MUTATING,
        description="Establish a fresh session on ANAF's declaration-filing "
        "portal with the selected certificate (spv_select_certificate). This "
        "FIRES THE USER'S PIN/2FA prompt on their token or phone — call it "
        "only when the user explicitly asked to log in (or approved doing "
        "so), and pass confirm=true to attest that. It is deliberately "
        "separate from declaratie_submit: log in once, then prepare and "
        "submit ride the session (probe it with declaratie_portal_status). "
        "One attempt per call; the handshake is occasionally flaky on ANAF's "
        "side, so logged_in=false just means ask the user and try again. "
        "Sessions die after ~10 idle minutes, so file promptly after.",
    )
    async def declaratie_portal_login(
        confirm: bool = False, timeout_s: float = 180.0
    ) -> PortalLoginResult:
        if not confirm:
            return PortalLoginResult(
                logged_in=False,
                guidance="declaratie_portal_login fires the user's certificate "
                "PIN/2FA prompt — get their explicit approval, warn them the "
                "prompt is coming, then call again with confirm=true",
            )
        selected = load_selected_identity(config.spv_identity_path)
        if selected is None:
            return PortalLoginResult(
                logged_in=False,
                guidance="no certificate selected — list them with "
                "spv_list_certificates and pick one with "
                "spv_select_certificate first",
            )
        bootstrapper = PortalCurlBootstrapper(
            selected.bootstrap_identity,
            timeout=min(max(timeout_s, 30.0), 300.0),
        )
        try:
            cookies = await bootstrapper.bootstrap()
        except AnafAuthError as exc:
            return PortalLoginResult(
                logged_in=False,
                identity=selected.name,
                guidance=f"{exc} — the handshake is occasionally flaky on "
                "ANAF's side; confirm the certificate middleware is running, "
                "then (with the user's go-ahead) call declaratie_portal_login "
                "again — their PIN/2FA prompt fires on every attempt",
            )
        ctx.declaration_upload().install_session(cookies)
        return PortalLoginResult(
            logged_in=True,
            identity=selected.name,
            guidance="session established — it dies after ~10 idle minutes, "
            "so proceed to declaratie_prepare / declaratie_submit promptly",
        )

    @mcp.tool(
        title="Declarations: prepare filing",
        annotations=MUTATING,
        description="STEP 1 of filing a SIGNED declaration PDF on ANAF's "
        "portal (anaf.ro → Depunere declarații — PRODUCTION; declaration "
        "filing has no test environment, so every submission is a real "
        "filing). `pdf_path` is the declaratie_sign output. Returns the "
        "file's metadata and a confirmation token bound to the exact bytes "
        "and the multipart `filename` (defaults to the file's own name; the "
        "conventional shape is '<form>_<cui>_<period>.pdf'). "
        "looks_signed=false warns that no embedded signature was detected "
        "(the portal would reject) but never withholds the token. Recap to "
        "the user WHAT will be filed (the form, period, and CUI of the PDF "
        "they reviewed) and get explicit approval, then call "
        "declaratie_submit with the same pdf_path, the token, and "
        "confirm=true. Does NOT file and needs no portal session.",
    )
    async def declaratie_prepare(
        pdf_path: str, filename: str | None = None
    ) -> PreparedUpload:
        source = Path(pdf_path).expanduser()
        try:
            pdf = await asyncio.to_thread(source.read_bytes)
        except OSError as exc:
            return PreparedUpload(valid=False, message=f"cannot read {pdf_path}: {exc}")
        resolved_name = filename or source.name
        token = issue_token(
            config.signing_key,
            kind=_UPLOAD_KIND,
            payload=pdf,
            context=_upload_context(resolved_name),
        )
        looks_signed = _looks_signed(pdf)
        note = (
            "ready"
            if looks_signed
            else "WARNING: no embedded signature detected — the portal will "
            "reject an unsigned PDF; sign it with declaratie_sign first"
        )
        return PreparedUpload(
            valid=True,
            confirmation_token=token,
            pdf_path=str(source),
            filename=resolved_name,
            size_bytes=len(pdf),
            looks_signed=looks_signed,
            message=f"{note}. Review the filing with the user, then call "
            "declaratie_submit with the same pdf_path, this token, and "
            "confirm=true (an active portal session is required — "
            "declaratie_portal_status).",
        )

    @mcp.tool(
        title="Declarations: submit filing",
        annotations=MUTATING,
        description="STEP 2 of filing: upload the signed declaration PDF to "
        "ANAF's production portal and return its verdict. Requires the "
        "confirmation_token from declaratie_prepare for the SAME file and "
        "confirm=true, plus an active portal session — the session is probed "
        "BEFORE the single-use token is spent, so a lapsed login costs "
        "nothing (declaratie_portal_login, then call again with the same "
        "token). accepted=true carries the upload_index: give it to the user "
        "and track processing with declaratie_status; the success page is "
        "NOT the registration confirmation — the signed recipisa is "
        "(declaratie_recipisa, ~60-day window). accepted=false carries the "
        "portal's rejection reason; accepted=null means the answer was not "
        "recognised — check declaratie_status before re-filing.",
    )
    async def declaratie_submit(
        pdf_path: str,
        confirmation_token: str,
        confirm: bool = False,
        filename: str | None = None,
    ) -> UploadSubmitResult:
        if not confirm:
            return UploadSubmitResult(
                accepted=False,
                message="confirm=False — set confirm=true only after the user "
                "approves filing the prepared PDF (declaratie_prepare).",
            )
        source = Path(pdf_path).expanduser()
        try:
            pdf = await asyncio.to_thread(source.read_bytes)
        except OSError as exc:
            return UploadSubmitResult(
                accepted=False, message=f"cannot read {pdf_path}: {exc}"
            )
        resolved_name = filename or source.name
        try:
            expires_at = verify_token(
                config.signing_key,
                confirmation_token,
                kind=_UPLOAD_KIND,
                payload=pdf,
                context=_upload_context(resolved_name),
            )
        except ConfirmationError as exc:
            return UploadSubmitResult(accepted=False, message=str(exc))
        client = ctx.declaration_upload()
        # Probe BEFORE consuming the token: a dead session is a deterministic
        # pre-condition failure and must not burn the human's approval.
        try:
            active = await client.probe()
        except AnafError as exc:
            return UploadSubmitResult(
                accepted=False,
                message=f"could not verify the portal session: {exc} — the "
                "confirmation token was NOT consumed; retry when the portal "
                "is reachable",
            )
        if not active:
            return UploadSubmitResult(
                accepted=False,
                message="no active portal session — the confirmation token "
                f"was NOT consumed; {_PORTAL_LOGIN_HINT}, then call "
                "declaratie_submit again with the same token",
            )
        if not ctx.token_ledger.consume(confirmation_token, expires_at):
            return UploadSubmitResult(accepted=False, message=TOKEN_USED_MESSAGE)
        # The token is consumed BEFORE the upload, deliberately: on an
        # ambiguous failure, replaying the same token must not be able to
        # double-file — the human re-approves instead.
        try:
            result = await client.upload(pdf, filename=resolved_name)
        except AnafAuthError as exc:
            return UploadSubmitResult(
                accepted=False,
                message=f"{exc} — the portal bounced the upload before "
                "accepting it, so NOTHING was filed. The confirmation token "
                f"is spent: {_PORTAL_LOGIN_HINT}, then run declaratie_prepare "
                "again",
            )
        except AnafError as exc:
            return UploadSubmitResult(
                accepted=None,
                message=f"the upload failed and the outcome is UNKNOWN — the "
                f"request may or may not have reached the portal: {exc}. The "
                "confirmation token is spent. Check declaratie_status (a "
                "valid index+CUI pair lists ALL the CUI's filings from the "
                "last 3 months) before preparing this filing again, so it is "
                "not filed twice.",
            )
        if result.accepted:
            index_note = (
                f"upload index {result.upload_index}"
                if result.upload_index is not None
                else "but the success page carried no parseable upload index — "
                "find it via declaratie_status or the portal"
            )
            return UploadSubmitResult(
                accepted=True,
                upload_index=result.upload_index,
                message=f"filed — {index_note}. The success page is NOT the "
                "registration confirmation: track processing with "
                "declaratie_status and download the signed recipisa with "
                "declaratie_recipisa (~60-day window; advise archiving it).",
            )
        if result.accepted is False:
            return UploadSubmitResult(
                accepted=False,
                reason=result.reason,
                message="the portal rejected the filing — fix the cause, then "
                "run declaratie_prepare again",
            )
        return UploadSubmitResult(
            accepted=None,
            message="the portal answered with an unrecognised page — treat "
            "the outcome as UNKNOWN and check declaratie_status before "
            "re-filing",
        )
