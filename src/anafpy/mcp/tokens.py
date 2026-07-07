"""Confirmation tokens for the two-step gated mutation flow (``docs/design.md`` §8).

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
"""

from __future__ import annotations

import hashlib
import hmac
import time

import jwt

__all__ = ["ConfirmationError", "TokenLedger", "issue_token", "verify_token"]

_ALGORITHM = "HS256"
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
