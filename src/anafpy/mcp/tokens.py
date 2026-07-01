"""Confirmation tokens for the two-step gated mutation flow (``DESIGN.md`` §7).

A mutating skill is split in two: ``prepare`` validates a document, shows a preview, and
hands back a **confirmation token** that is an HMAC over the exact bytes that would be
filed plus the submission *context* (the CIF filing, the upload standard). ``submit``
will only proceed when handed back a token that still verifies against the document and
context it was given — so the model cannot file something other than what the human
reviewed (nor for a different taxpayer), and cannot fabricate a token. Tokens expire so
a stale preview can't be filed much later, and a :class:`TokenLedger` makes each token
single-use so a non-idempotent upload is never repeated on the same approval.

This is a *gate*, not a security boundary against the host: the signing key lives in the
same process. Its job is to force the prepare → human-review → submit ordering.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

__all__ = ["ConfirmationError", "TokenLedger", "issue_token", "verify_token"]

_VERSION = "v1"
_DEFAULT_TTL = 900.0  # seconds a preview stays fileable (15 min)


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


def _sign(key: bytes, message: str) -> str:
    sig = hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


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
    fails verification. Returns an opaque ``v1.<kind>.<expiry>.<sig>`` string to be
    passed back to the matching ``submit`` tool alongside the same document.
    """
    expires_at = int(time.time() + ttl)
    digest = _digest(kind, payload, context)
    message = f"{_VERSION}.{kind}.{expires_at}.{digest}"
    return f"{_VERSION}.{kind}.{expires_at}.{_sign(key, message)}"


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
    parts = token.split(".")
    if len(parts) < 4:
        raise ConfirmationError("confirmation token is malformed")
    # The kind may itself contain dots; it is the middle, between version and the
    # trailing <expiry>.<sig> pair.
    version = parts[0]
    token_kind = ".".join(parts[1:-2])
    expiry_str = parts[-2]
    if version != _VERSION:
        raise ConfirmationError("confirmation token has an unsupported version")
    if token_kind != kind:
        raise ConfirmationError(
            f"confirmation token is for {token_kind!r}, not {kind!r}"
        )
    try:
        expires_at = int(expiry_str)
    except ValueError as exc:
        raise ConfirmationError("confirmation token has a malformed expiry") from exc
    if time.time() > expires_at:
        raise ConfirmationError(
            "confirmation token has expired — run the prepare step again"
        )
    digest = _digest(kind, payload, context)
    message = f"{_VERSION}.{kind}.{expires_at}.{digest}"
    expected = f"{_VERSION}.{kind}.{expires_at}.{_sign(key, message)}"
    if not hmac.compare_digest(expected, token):
        raise ConfirmationError(
            "confirmation token does not match the submission; the document, CIF, "
            "or standard changed since prepare — run prepare again"
        )
    return expires_at


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
