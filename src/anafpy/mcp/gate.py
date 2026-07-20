"""The two-step gated filing flow shared by the filing services (``DESIGN.md`` §8).

A mutating skill is split in two: ``prepare`` validates a document, shows a preview, and
hands back a **confirmation token** — an HS256-signed JWT whose claims bind the
operation kind and a digest of the exact bytes that would be filed plus the submission
*context* (the CIF filing, the upload standard). ``submit`` will only proceed when
handed back a token that still verifies against the document and context it was given —
so the model cannot file something other than what the human reviewed (nor for a
different taxpayer), and cannot fabricate a token. Tokens expire (the JWT ``exp``
claim) so a stale preview can't be filed much later, and a :class:`TokenLedger` makes
each token single-use so a non-idempotent upload is never repeated on the same approval.

This is a *gate*, not a security boundary against the host: the signing key lives in the
same process. Its job is to force the prepare → human-review → submit ordering.

The gate is deliberately identical across e-Factura and e-Transport, so everything
both filing services share lives here: the token primitives, the :class:`XmlInput`
base the per-service pass-through inputs extend (``{xml|path}`` resolved to the
exact bytes), the shared :class:`PreparedSubmission` / :class:`SubmitResult`
shapes, and :func:`run_submit` — the whole STEP-2 skeleton, including its two
safety-critical orderings (client resolution *before* the token is consumed,
consumption *before* the upload). The service packages contribute only what
genuinely differs: the prepare tools, the preview projections, and the upload
call itself.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import jwt
from pydantic import BaseModel, Field

from ..exceptions import AnafConfigError, AnafError
from .config import ServerConfig

__all__ = [
    "TOKEN_USED_MESSAGE",
    "ConfirmationError",
    "PreparedSubmission",
    "SubmitResult",
    "TokenLedger",
    "XmlInput",
    "issue_token",
    "run_submit",
    "submission_context",
    "verify_token",
]

_ALGORITHM = "HS256"
_DEFAULT_TTL = 900.0  # seconds a preview stays fileable (15 min)

TOKEN_USED_MESSAGE = (
    "confirmation token already used — filing is never repeated on the same "
    "approval; run the prepare step again"
)


class ConfirmationError(Exception):
    """A confirmation token was missing, malformed, expired, or did not match."""


def _digest(kind: str, payload: bytes, context: str) -> str:
    h = hashlib.sha256()
    h.update(kind.encode("utf-8"))
    h.update(b"\x00")
    h.update(context.encode("utf-8"))
    h.update(b"\x00")
    h.update(payload)
    return h.hexdigest()


def issue_token(
    key: bytes,
    *,
    kind: str,
    payload: bytes,
    context: str = "",
    ttl: float = _DEFAULT_TTL,
) -> str:
    """Issue a confirmation token binding *kind*, *context*, and the *payload* bytes.

    *context* carries the submission parameters the human implicitly approves with
    the preview (e.g. ``cif=...;standard=...``); submitting with different values
    fails verification. Returns an opaque JWT to be passed back to the matching
    ``submit`` tool alongside the same document.
    """
    claims = {
        "kind": kind,
        "digest": _digest(kind, payload, context),
        "exp": int(time.time() + ttl),
    }
    return jwt.encode(claims, key, algorithm=_ALGORITHM)


def verify_token(
    key: bytes, token: str, *, kind: str, payload: bytes, context: str = ""
) -> int:
    """Verify a *token* against *kind*, *context*, and the resubmitted *payload*.

    Returns the token's expiry (epoch seconds) so the caller can record redemption
    (see :class:`TokenLedger`).

    Raises:
        ConfirmationError: if the token is malformed, for a different operation,
            expired, or does not match the bytes/context being submitted.
    """
    try:
        claims = jwt.decode(
            token, key, algorithms=[_ALGORITHM], options={"require": ["exp"]}
        )
    except jwt.ExpiredSignatureError as exc:
        raise ConfirmationError(
            "confirmation token has expired — run the prepare step again"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise ConfirmationError(
            "confirmation token is malformed or does not verify"
        ) from exc
    if (token_kind := claims.get("kind")) != kind:
        raise ConfirmationError(
            f"confirmation token is for {token_kind!r}, not {kind!r}"
        )
    if not hmac.compare_digest(
        str(claims.get("digest", "")), _digest(kind, payload, context)
    ):
        raise ConfirmationError(
            "confirmation token does not match the submission; the document, CIF, "
            "or standard changed since prepare — run prepare again"
        )
    return int(claims["exp"])


class TokenLedger:
    """Records redeemed confirmation tokens so each one files at most once.

    Uploads are non-idempotent; a replayed token would double-file. The ledger is
    in-memory (tokens are only valid within one server process anyway) and prunes
    entries as they pass their expiry.
    """

    def __init__(self) -> None:
        self._used: dict[str, float] = {}

    def consume(self, token: str, expires_at: float) -> bool:
        """Redeem *token*; ``False`` when it was already used."""
        now = time.time()
        self._used = {t: exp for t, exp in self._used.items() if exp > now}
        if token in self._used:
            return False
        self._used[token] = expires_at
        return True


def submission_context(cif: str) -> str:
    """The submission parameters bound into a filing's confirmation token."""
    return f"cif={cif}"


class XmlInput(BaseModel):
    """A complete document as XML — exactly one of ``xml`` / ``path``.

    The per-service pass-through inputs extend this with their own wording; the
    resolution to bytes is shared, and the bytes go to ANAF verbatim.
    """

    xml: str | None = Field(default=None, description="The document as XML text.")
    path: str | None = Field(default=None, description="Path to an XML file.")

    def resolve(self) -> bytes:
        """Read the input to UTF-8 bytes ready to upload.

        Raises :class:`AnafConfigError` when neither or both of ``xml`` / ``path``
        are set, or when ``path`` cannot be read — stay in the AnafError hierarchy
        instead of leaking a raw OS error out of a tool.
        """
        if self.xml and self.path:
            raise AnafConfigError("set only one of `xml` / `path`, not both")
        if self.xml:
            return self.xml.encode("utf-8")
        if self.path:
            try:
                return Path(self.path).expanduser().read_bytes()
            except OSError as exc:
                raise AnafConfigError(
                    f"cannot read XML file {self.path!r}: {exc}"
                ) from exc
        raise AnafConfigError("one of `xml` / `path` is required")


class PreparedSubmission(BaseModel):
    """Shared shape of a ``prepare`` step: the confirmation-token gate.

    ``valid`` is ``False`` (and ``confirmation_token`` ``None``) only when the input
    could not be resolved (bad ``xml``/``path``, invalid fields, no CIF). Otherwise
    pass the token (with the *same* document and ``cif``) to the matching ``submit``
    tool to file; the token is single-use and bound to both. ``cif`` echoes the
    fiscal code the filing was prepared for. For the composing tools
    (``etransport_prepare_*`` / ``efactura_prepare_invoice``), ``xml`` carries the
    exact document that will be filed — pass it back to the matching submit tool
    verbatim (the token is bound to those bytes).

    The per-service results (e-Factura's ``PreparedInvoice``, e-Transport's
    ``PreparedTransport``) add the matching preview, so each tool's output schema
    describes exactly what it returns.
    """

    valid: bool
    confirmation_token: str | None = None
    cif: str | None = None
    xml: str | None = None
    message: str = ""


class SubmitResult(BaseModel):
    """Result of a ``submit`` step."""

    accepted: bool
    upload_id: str | None = None
    uit: str | None = None
    errors: list[str] = []
    message: str = ""


async def run_submit[C](
    document: XmlInput,
    confirmation_token: str,
    *,
    confirm: bool,
    cif: str | None,
    cfg: ServerConfig,
    ledger: TokenLedger,
    kind: str,
    prepare_tools: str,
    check_hint: str,
    client: Callable[[], C],
    upload: Callable[[C, bytes, str], Awaitable[SubmitResult]],
) -> SubmitResult:
    """The STEP-2 skeleton every filing service's ``submit`` tool runs.

    Refuses without ``confirm``, verifies the token against the resubmitted bytes
    and CIF, redeems it single-use, and hands the upload to *upload* (which builds
    the service-specific success/rejection :class:`SubmitResult`). *prepare_tools*
    names the matching STEP-1 tool(s) for the refusal message; *check_hint* names
    the tools that can tell whether an upload of UNKNOWN outcome went through.
    *client* is resolved through the gate (rather than inside *upload*) so the
    ordering constraints below hold in one place for every service.
    """
    if not confirm:
        return SubmitResult(
            accepted=False,
            message="confirm=False — set confirm=True only after the user "
            f"approves the preview from {prepare_tools}.",
        )
    try:
        xml = document.resolve()
        resolved = cfg.require_cif(cif)
    except AnafError as exc:
        return SubmitResult(accepted=False, errors=[str(exc)])
    try:
        expires_at = verify_token(
            cfg.signing_key,
            confirmation_token,
            kind=kind,
            payload=xml,
            context=submission_context(resolved),
        )
    except ConfirmationError as exc:
        return SubmitResult(accepted=False, message=str(exc))
    # Resolve the client BEFORE consuming the token: missing credentials is a
    # deterministic config error, and must not burn the human's approval.
    service = client()
    if not ledger.consume(confirmation_token, expires_at):
        return SubmitResult(accepted=False, message=TOKEN_USED_MESSAGE)
    # The token is consumed BEFORE the upload, deliberately: on an ambiguous
    # failure (e.g. a timeout after the request was sent) replaying the same
    # token must not be able to double-file — the human re-approves instead.
    try:
        return await upload(service, xml, resolved)
    except AnafError as exc:
        return SubmitResult(
            accepted=False,
            errors=[str(exc)],
            message=(
                "the upload failed and the outcome is UNKNOWN — the request "
                "may or may not have reached ANAF. The confirmation token is "
                "spent. Before preparing this filing again, check whether it "
                f"went through ({check_hint}) so it is not filed twice."
            ),
        )
