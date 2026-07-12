"""SPV (Spațiul Privat Virtual) MCP tools — read-only mailbox access.

Everything here rides the cookie session established host-side by
``anafpy spv login`` (the certificate/2FA step never runs from a tool — same
convention as the OAuth browser flow). Reads are freely callable;
``spv_descarca`` / ``spv_asteapta_raport`` carry the honest artifact-saving
annotations because they write PDFs at caller-given paths, and
``spv_select_certificate`` is the one deliberate local mutation (it persists
the certificate choice).

``spv_cerere`` files a report request with ANAF. It is guarded by an
**in-process same-day dedupe** (``AppContext.spv_request_log``): an agent loop
repeating an identical request gets the id it already got today instead of
filing again; ``force=true`` overrides. The dedupe is deliberately not
persisted — the library client stays stateless, and a repeat after a server
restart is harmless (a second inbox message).
"""

from __future__ import annotations

from datetime import datetime

from mcp.server.fastmcp import FastMCP

from ..._transport.base import ROMANIA_TZ
from ...exceptions import AnafAuthError, AnafConfigError
from ...spv import (
    MessageList,
    ReportRequest,
    ReportType,
    discover_identities,
    identity_by_thumbprint,
    load_selected_identity,
    save_selected_identity,
)
from ..config import ServerConfig
from ..context import AppContext
from ._shared import ARTIFACT_SAVING, READ_ONLY, write_artifact

__all__ = ["register"]

_LOGIN_HINT = (
    "run `anafpy spv login` host-side (interactive: certificate + PIN/2FA), then retry"
)

# One page of spv_lista_mesaje output; SPV inboxes can hold hundreds of entries
# and the model needs counts, not a context-flooding dump.
_PAGE_LIMIT = 50


def _report_type(tip: str) -> ReportType:
    """Resolve ``tip`` — exact wire value first, then enum member name."""
    try:
        return ReportType(tip)
    except ValueError:
        pass
    try:
        return ReportType[tip.strip().upper().replace(" ", "_").replace("-", "_")]
    except KeyError:
        valid = ", ".join(t.value for t in ReportType)
        raise AnafConfigError(
            f"unknown report type {tip!r}; valid `tip` values: {valid}"
        ) from None


def _identity_summary(listing: MessageList) -> dict[str, object]:
    """The certificate-identity fields every authenticated response carries."""
    return {
        "cnp": listing.cnp,
        "certificate_serial": listing.certificate_serial,
        # The authorization inventory: every CUI/CNP this certificate may query.
        "authorized_cuis": listing.authorized_cuis,
    }


def register(mcp: FastMCP, ctx: AppContext, config: ServerConfig) -> None:
    @mcp.tool(
        title="SPV: List certificates",
        annotations=READ_ONLY,
        description="Enumerate the qualified certificates usable for SPV in this "
        "machine's key store (macOS Keychain / Windows CertStore), including "
        "USB-token and cloud-HSM identities surfaced by their middleware. Shows "
        "which one is currently selected. Pick one with spv_select_certificate.",
    )
    def spv_list_certificates() -> dict[str, object]:
        selected = load_selected_identity(config.spv_identity_path)
        return {
            "certificates": [i.model_dump(mode="json") for i in discover_identities()],
            "selected_thumbprint": selected.sha1_thumbprint if selected else None,
        }

    @mcp.tool(
        title="SPV: Select certificate",
        annotations=ARTIFACT_SAVING,
        description="Persist which certificate `anafpy spv login` should use, by "
        "SHA-1 thumbprint (see spv_list_certificates). Writes a local config file "
        "only — nothing is sent to ANAF. The user must still run `anafpy spv "
        "login` host-side to establish a session (fires their PIN/2FA).",
    )
    def spv_select_certificate(thumbprint: str) -> dict[str, object]:
        identity = identity_by_thumbprint(thumbprint)
        selected = save_selected_identity(identity, config.spv_identity_path)
        return {
            "selected": selected.model_dump(mode="json"),
            "next_step": _LOGIN_HINT,
        }

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
        "overwrite=true. `mesaj_id` is a message `id` from spv_lista_mesaje.",
    )
    async def spv_descarca(
        mesaj_id: str,
        save_as: str | None = None,
        dest_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        if save_as is None and dest_dir is None:
            raise AnafConfigError(
                "pass `save_as` (a file path) or `dest_dir` (a directory) so the "
                "PDF has somewhere to go"
            )
        document = await ctx.spv().download_document(mesaj_id)
        target = save_as if save_as is not None else f"{dest_dir}/spv-{mesaj_id}.pdf"
        path = write_artifact(target, document.content, overwrite=overwrite)
        return {
            "saved_as": path,
            "bytes": len(document.content),
            "media_type": document.media_type,
            "is_pdf": document.is_pdf,
        }

    @mcp.tool(
        title="SPV: Request report",
        annotations=READ_ONLY,
        description="Ask ANAF to generate an official report/document (cerere). "
        "`tip` is the report name exactly as ANAF spells it — e.g. 'VECTOR "
        "FISCAL', 'Obligatii de plata', 'Istoric declaratii', 'D300', 'Duplicat "
        "Recipisa', 'Adeverinte Venit', 'NeconcordanteD394'. Parameters vary per "
        "type (year `an`, month `luna`, reason `motiv`, `numar_inregistrare`, "
        "branch `cui_pui`, period `lunai`/`lunas`) and are validated before the "
        "wire call. The report is generated ASYNCHRONOUSLY (no SLA): the result "
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
            type_=_report_type(tip),
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
        if save_as is None and dest_dir is None:
            raise AnafConfigError(
                "pass `save_as` (a file path) or `dest_dir` (a directory) so the "
                "report PDF has somewhere to go"
            )
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
        target = (
            save_as
            if save_as is not None
            else f"{dest_dir}/spv-raport-{id_solicitare}.pdf"
        )
        path = write_artifact(target, document.content, overwrite=overwrite)
        return {
            "status": "delivered",
            "id_solicitare": id_solicitare,
            "message_id": document.message_id,
            "saved_as": path,
            "bytes": len(document.content),
            "is_pdf": document.is_pdf,
        }
