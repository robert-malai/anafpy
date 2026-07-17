"""SPV (Spațiul Privat Virtual) MCP tools — read-only mailbox access.

Everything here rides the cookie session established by ``anafpy spv login``
or the ``spv_login`` tool. Unlike the OAuth browser flow (which structurally
needs host-side UI and stays a CLI), the SPV login needs no host UI at all —
the human gate is the out-of-band PIN/2FA approval on the owner's device — so
it IS exposed as a tool (decided 2026-07-13, reversing the M2 stance: APM
sessions die in under an hour, and bouncing a Cowork user to a terminal every
hour would kill the feature). ``spv_login`` is explicitly gated: it requires
``confirm=true`` relaying the user's ask, so an agent cannot fire the owner's
2FA on its own initiative. Reads are freely callable;
``spv_descarca`` / ``spv_asteapta_raport`` carry the honest artifact-saving
annotations because they write PDFs at caller-given paths, and
``spv_select_certificate`` is the one deliberate local mutation (it persists
the certificate choice). A message's document is also the resource template
``spvmsg://{mesaj_id}/pdf`` (mirroring e-Factura's ``anafmsg://``, and simpler:
``descarcare`` already returns a PDF, no conversion) — a disk-free path for
hosts with resource UX; ``spv_descarca`` remains the save-to-disk path.

``spv_cerere`` files a report request with ANAF, so it carries mutating
(non-destructive, non-idempotent) hints — a host must not auto-invoke it as a
read — while staying freely callable: no declaration is filed, so the two-step
gate deliberately does not apply. It is guarded by an
**in-process same-day dedupe** (``AppContext.spv_request_log``): an agent loop
repeating an identical request gets the id it already got today instead of
filing again; ``force=true`` overrides. The dedupe is deliberately not
persisted — the library client stays stateless, and a repeat after a server
restart is harmless (a second inbox message).

``spv_nomenclature`` exposes the SPV code lists to the model — the report
types with their per-type parameters, and the fixed ``motiv`` list for
'Adeverinte Venit'. The model is MEANT to map the user's stated purpose onto
the closest motiv entry (decided 2026-07-13); MCP elicitation was considered
for a host-side picker and parked — Claude Desktop/Cowork answers
``elicitation/create`` with a synthetic instant cancel (claude-code#56243),
so a description-guided visible list is the portable design.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..._transport.base import ROMANIA_TZ
from ...exceptions import AnafAuthError, AnafConfigError, AnafError
from ...spv import (
    INCOME_CERTIFICATE_REASONS,
    CurlBootstrapper,
    FileSessionStore,
    MessageList,
    ReportRequest,
    SpvSessionProvider,
    discover_identities,
    identity_by_thumbprint,
    load_selected_identity,
    save_selected_identity,
)
from ..artifacts import (
    ARTIFACT_SAVING,
    MUTATING,
    READ_ONLY,
    REQUESTING,
    check_writable,
    write_artifact,
)
from ..config import ServerConfig
from ..context import AppContext
from .nomenclature import REPORT_TYPES_NOTE, report_type_entries, resolve_report_type

__all__ = ["register"]

_LOGIN_HINT = (
    "log in first: ask the user for approval and call spv_login with "
    "confirm=true (fires their certificate PIN/2FA), or have them run "
    "`anafpy spv login` in a terminal — then retry"
)

# One page of spv_lista_mesaje output; SPV inboxes can hold hundreds of entries
# and the model needs counts, not a context-flooding dump.
_PAGE_LIMIT = 50


def _identity_summary(listing: MessageList) -> dict[str, object]:
    """The certificate-identity fields every authenticated response carries."""
    return {
        "cnp": listing.cnp,
        "certificate_serial": listing.certificate_serial,
        # The authorization inventory: every CUI/CNP this certificate may query.
        "authorized_cuis": listing.authorized_cuis,
    }


def _save_target(save_as: str | None, dest_dir: str | None, default_name: str) -> str:
    """Resolve where a downloaded PDF goes (shared by both artifact tools)."""
    if save_as is not None:
        return save_as
    if dest_dir is None:
        raise AnafConfigError(
            "pass `save_as` (a file path) or `dest_dir` (a directory) so the "
            "PDF has somewhere to go"
        )
    return str(Path(dest_dir) / default_name)


def register(mcp: FastMCP, ctx: AppContext, config: ServerConfig) -> None:
    @mcp.tool(
        title="SPV: List certificates",
        annotations=READ_ONLY,
        description="Enumerate the qualified certificates usable for SPV in this "
        "machine's key store (macOS Keychain / Windows CertStore), including "
        "USB-token and cloud-HSM identities surfaced by their middleware. Shows "
        "which one is currently selected. Pick one with spv_select_certificate.",
    )
    async def spv_list_certificates() -> dict[str, object]:
        selected = load_selected_identity(config.spv_identity_path)
        # Key-store enumeration shells out to the OS tools and can stall on
        # slow token middleware — keep it off the event loop.
        identities = await asyncio.to_thread(discover_identities)
        return {
            "certificates": [i.model_dump(mode="json") for i in identities],
            "selected_thumbprint": selected.sha1_thumbprint if selected else None,
        }

    @mcp.tool(
        title="SPV: Select certificate",
        annotations=ARTIFACT_SAVING,
        description="Persist which certificate SPV logins should use, by SHA-1 "
        "thumbprint (see spv_list_certificates). Writes a local config file "
        "only — nothing is sent to ANAF, and an existing session still belongs "
        "to the previously used certificate. A session with the new one takes a "
        "login: spv_login (with the user's approval — it fires their PIN/2FA) "
        "or `anafpy spv login` in a terminal.",
    )
    async def spv_select_certificate(thumbprint: str) -> dict[str, object]:
        identity = await asyncio.to_thread(identity_by_thumbprint, thumbprint)
        selected = save_selected_identity(identity, config.spv_identity_path)
        return {
            "selected": selected.model_dump(mode="json"),
            "next_step": _LOGIN_HINT,
        }

    @mcp.tool(
        title="SPV: Log in",
        annotations=MUTATING,
        description="Establish a fresh SPV session with the selected certificate "
        "(spv_select_certificate / `anafpy spv select`). This FIRES THE USER'S "
        "PIN/2FA prompt on their token or phone — call it only when the user "
        "explicitly asked to log in (or approved doing so), and pass "
        "confirm=true to attest that. One attempt per call; the handshake is "
        "occasionally flaky on ANAF's side, so a failed attempt just means ask "
        "the user and try again (their prompt fires anew). On success reports "
        "the certificate's identity and `authorized_cuis`.",
    )
    async def spv_login(
        confirm: bool = False, timeout_s: float = 180.0
    ) -> dict[str, object]:
        if not confirm:
            raise AnafConfigError(
                "spv_login fires the user's certificate PIN/2FA prompt — get "
                "their explicit approval in the conversation, then call again "
                "with confirm=true"
            )
        selected = load_selected_identity(config.spv_identity_path)
        if selected is None:
            raise AnafConfigError(
                "no certificate selected — list them with spv_list_certificates "
                "and pick one with spv_select_certificate first"
            )
        # A throwaway provider over the SAME store: the long-lived client's
        # provider treats the store as the single source of truth, so it picks
        # the fresh session up on its next request.
        provider = SpvSessionProvider(
            store=FileSessionStore(config.spv_session_path),
            bootstrapper=CurlBootstrapper(
                selected.bootstrap_identity,
                timeout=min(max(timeout_s, 30.0), 300.0),
            ),
        )
        try:
            await provider.login()
        except AnafAuthError as exc:
            return {
                "logged_in": False,
                "detail": str(exc),
                "next_step": "the login is occasionally flaky on ANAF's side — "
                "confirm the user's certificate middleware is running, then "
                "(with their go-ahead) call spv_login again; their PIN/2FA "
                "prompt fires on every attempt",
            }
        # Best-effort identity probe: the login itself already succeeded and the
        # session is saved — a probe hiccup must not report it as failed
        # (observed live 2026-07-13: the probe raised right after a good login).
        result: dict[str, object] = {"logged_in": True, "identity": selected.name}
        try:
            listing = await ctx.spv().list_messages(60)
        except AnafError as exc:
            result["probe_error"] = (
                f"session established, but the identity probe failed: {exc} — "
                "spv_status will report the details"
            )
            return result
        result.update(_identity_summary(listing))
        return result

    @mcp.tool(
        title="SPV: Status",
        annotations=READ_ONLY,
        description="Smoke-test the SPV session: reports whether SPV is reachable "
        "with the stored cookie session, and for whom — the certificate holder's "
        "CNP, the certificate serial, and `authorized_cuis`, the full list of "
        "CUIs/CNPs this certificate has SPV rights for (the authorization "
        "inventory — any other CIF will be refused). Call this before other spv_* "
        "tools; if it reports no session, the user must log in host-side.",
    )
    async def spv_status() -> dict[str, object]:
        try:
            # 60-day window: ANAF's no-results shape omits the identity fields,
            # so the widest window gives the best chance of reporting them.
            listing = await ctx.spv().list_messages(60)
        except (AnafAuthError, AnafConfigError) as exc:
            return {
                "reachable": False,
                "session": "missing or expired",
                "detail": str(exc),
                "next_step": _LOGIN_HINT,
            }
        result: dict[str, object] = {
            "reachable": True,
            "session": "active",
            **_identity_summary(listing),
            "messages_last_60_days": len(listing.messages),
            "note": listing.note,
        }
        if listing.note is not None:
            result["detail"] = (
                "the window had no messages and ANAF omits the certificate "
                "identity fields on empty responses — the session is active"
            )
        return result

    @mcp.tool(
        title="SPV: List messages",
        annotations=READ_ONLY,
        description="List SPV inbox messages from the last `zile` days (receipts, "
        "payment notices, report deliveries, notifications). Optional filters: "
        "`cif` (one of the authorized CUIs/CNPs) and `tip` (message kind, e.g. "
        "RECIPISA, PLATA, 'RASPUNS SOLICITARE' — matched trimmed). Large inboxes "
        f"are paged: at most {_PAGE_LIMIT} messages per call, with `total` and "
        "`has_more` — page by increasing `offset`. Each message's `id` feeds "
        "spv_descarca; `request_id` links a delivered report to its spv_cerere.",
    )
    async def spv_lista_mesaje(
        zile: int,
        cif: str | None = None,
        tip: str | None = None,
        offset: int = 0,
        limit: int = _PAGE_LIMIT,
    ) -> dict[str, object]:
        listing = await ctx.spv().list_messages(zile, cif=cif)
        messages = listing.messages
        if tip is not None:
            wanted = tip.strip()
            messages = [m for m in messages if m.kind == wanted]
        limit = max(1, min(limit, _PAGE_LIMIT))
        offset = max(0, offset)
        page = messages[offset : offset + limit]
        return {
            "total": len(messages),
            "offset": offset,
            "returned": len(page),
            "has_more": offset + len(page) < len(messages),
            "messages": [m.model_dump(mode="json") for m in page],
            **_identity_summary(listing),
            "note": listing.note,
        }

    @mcp.tool(
        title="SPV: Download document",
        annotations=ARTIFACT_SAVING,
        description="Download one SPV message's document (PDF) to disk and return "
        "the saved path — the binary never enters the context. Name the file with "
        "`save_as` (full path), or pass `dest_dir` to use the generated name "
        "'spv-<mesaj_id>.pdf'. An existing file is never replaced unless "
        "overwrite=true. `mesaj_id` is a message `id` from spv_lista_mesaje. The "
        "document is also readable as the resource spvmsg://{mesaj_id}/pdf.",
    )
    async def spv_descarca(
        mesaj_id: str,
        save_as: str | None = None,
        dest_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        target = _save_target(save_as, dest_dir, f"spv-{mesaj_id}.pdf")
        document = await ctx.spv().download_document(mesaj_id)
        path = write_artifact(target, document.content, overwrite=overwrite)
        return {
            "saved_as": path,
            "bytes": len(document.content),
            "media_type": document.media_type,
            "is_pdf": document.is_pdf,
        }

    @mcp.resource(
        "spvmsg://{mesaj_id}/pdf",
        name="SPV message document",
        description="One SPV message's document (PDF, by `id` from "
        "spv_lista_mesaje), fetched on read. Needs an active SPV session — "
        "the read cannot trigger a login; spv_descarca saves to disk instead.",
        mime_type="application/pdf",
    )
    async def spv_message_pdf(mesaj_id: str) -> bytes:
        return (await ctx.spv().download_document(mesaj_id)).content

    @mcp.tool(
        title="SPV: Code lists",
        annotations=READ_ONLY,
        description="List one SPV nomenclature. `kind` is one of: report_types "
        "(every `tip` spv_cerere accepts, each with a description of what the "
        "report contains — use it to map the user's actual question onto the "
        "right type — and the parameters it requires), "
        "income_certificate_reasons (ANAF's fixed `motiv` list for 'Adeverinte "
        "Venit' — the filed text must match an entry EXACTLY, so map the user's "
        "stated purpose onto the closest entry; e.g. a health-insurance request "
        "is 'Sanatate', a bank loan is 'Institutie financiar bancara asigurare "
        "etc.').",
    )
    def spv_nomenclature(kind: str) -> dict[str, object]:
        result: dict[str, object] = {"kind": kind}
        match kind:
            case "report_types":
                result["entries"] = report_type_entries()
                result["note"] = REPORT_TYPES_NOTE
            case "income_certificate_reasons":
                result["entries"] = list(INCOME_CERTIFICATE_REASONS)
            case _:
                raise AnafConfigError(
                    f"unknown nomenclature {kind!r}; valid `kind` values: "
                    "report_types, income_certificate_reasons"
                )
        return result

    @mcp.tool(
        title="SPV: Request report",
        # Honest hints: a cerere files an additive request with ANAF (an inbox
        # message appears; an income certificate is issued with the motiv on
        # it) — not a read, even though no declaration is filed and the
        # two-step gate deliberately does not apply.
        annotations=REQUESTING,
        description="Ask ANAF to generate an official report/document (cerere). "
        "`tip` is the report name exactly as ANAF spells it — e.g. 'VECTOR "
        "FISCAL', 'Obligatii de plata', 'Istoric declaratii', 'D300', 'Duplicat "
        "Recipisa', 'Adeverinte Venit', 'NeconcordanteD394'; the full list with "
        "per-type parameters is spv_nomenclature('report_types'). Parameters "
        "vary per type (year `an`, month `luna`, reason `motiv`, "
        "`numar_inregistrare`, branch `cui_pui`, period `lunai`/`lunas`) and are "
        "validated before the wire call. For 'Adeverinte Venit', `motiv` must be "
        "one of ANAF's fixed reasons verbatim — it is printed on the issued "
        "certificate; get the list with "
        "spv_nomenclature('income_certificate_reasons') and pick the entry "
        "matching the user's stated purpose. The report is generated "
        "ASYNCHRONOUSLY (no SLA): the result "
        "returns an `id_solicitare` — wait for delivery with spv_asteapta_raport, "
        "or match it later against messages' `request_id`. An identical request "
        "already filed today returns the same id (deduped) unless force=true.",
    )
    async def spv_cerere(
        tip: str,
        cui: str | None = None,
        an: int | None = None,
        luna: int | None = None,
        motiv: str | None = None,
        numar_inregistrare: str | None = None,
        cui_pui: str | None = None,
        lunai: int | None = None,
        lunas: int | None = None,
        force: bool = False,
    ) -> dict[str, object]:
        request = ReportRequest(
            type_=resolve_report_type(tip),
            cui=config.require_cif(cui),
            year=an,
            month=luna,
            reason=motiv,
            registration_number=numar_inregistrare,
            branch_cui=cui_pui,
            start_month=lunai,
            end_month=lunas,
        )
        key = "&".join(f"{k}={v}" for k, v in sorted(request.wire_params().items()))
        today = datetime.now(tz=ROMANIA_TZ).date().isoformat()
        if not force and (logged := ctx.spv_request_log.get(key)) is not None:
            request_id, logged_day = logged
            if logged_day == today:
                return {
                    "id_solicitare": request_id,
                    "deduplicated": True,
                    "detail": "an identical request was already filed today; "
                    "reusing its id_solicitare (pass force=true to file again)",
                }
        result = await ctx.spv().request_report(request)
        ctx.spv_request_log[key] = (result.request_id, today)
        return {
            "id_solicitare": result.request_id,
            "deduplicated": False,
            "title": result.title,
            "parameters": result.parameters,
            "detail": "accepted — ANAF generates the report asynchronously; wait "
            "with spv_asteapta_raport or watch spv_lista_mesaje for a message "
            "with this request_id",
        }

    @mcp.tool(
        title="SPV: Await report",
        annotations=ARTIFACT_SAVING,
        description="Poll the SPV inbox until the report for `id_solicitare` (from "
        "spv_cerere) is delivered, then download it to disk and return the saved "
        "path. Polls gently (15s → 120s intervals) up to `timeout_s`. On timeout "
        "this returns status='pending' with instructions — the request stays "
        "valid, call again later; it is NOT an error. Name the file with "
        "`save_as`, or pass `dest_dir` for the generated name "
        "'spv-raport-<id_solicitare>.pdf'; existing files are never replaced "
        "unless overwrite=true.",
    )
    async def spv_asteapta_raport(
        id_solicitare: str,
        timeout_s: float = 600.0,
        cif: str | None = None,
        zile: int = 7,
        poll_interval_s: float = 15.0,
        save_as: str | None = None,
        dest_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        target = _save_target(save_as, dest_dir, f"spv-raport-{id_solicitare}.pdf")
        # Fail the collision BEFORE committing to a poll that can take minutes —
        # side-effect-free, so a poll that times out leaves no freshly-created
        # directory tree behind (write_artifact makes the parents on success).
        check_writable(target, overwrite=overwrite)
        timeout_s = min(timeout_s, 900.0)  # keep one tool call bounded
        try:
            document = await ctx.spv().wait_for_report(
                id_solicitare,
                cif=cif,
                days=zile,
                timeout=timeout_s,
                initial_wait=poll_interval_s,
            )
        except TimeoutError:
            return {
                "status": "pending",
                "id_solicitare": id_solicitare,
                "detail": f"not delivered within {timeout_s:.0f}s — ANAF generates "
                "reports asynchronously with no SLA; call spv_asteapta_raport "
                "again later with the same id_solicitare (do NOT re-file the "
                "cerere)",
            }
        try:
            path = write_artifact(target, document.content, overwrite=overwrite)
        except AnafError as exc:
            # The report IS delivered — don't discard that over a save problem.
            return {
                "status": "delivered",
                "id_solicitare": id_solicitare,
                "message_id": document.message_id,
                "save_error": str(exc),
                "detail": "the report was delivered but could not be saved — fix "
                "the path and save it with spv_descarca(mesaj_id=message_id) "
                "without re-polling",
            }
        return {
            "status": "delivered",
            "id_solicitare": id_solicitare,
            "message_id": document.message_id,
            "saved_as": path,
            "bytes": len(document.content),
            "is_pdf": document.is_pdf,
        }
