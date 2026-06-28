"""Confirmation tokens for the two-step gated mutation flow (``DESIGN.md`` §7).

A mutating skill is split in two: ``prepare`` validates a document, shows a preview, and
hands back a **confirmation token** that is an HMAC over the exact bytes that would be
filed. ``submit`` will only proceed when handed back a token that still verifies against
the document it was given — so the model cannot file something other than what the human
reviewed, and cannot fabricate a token. Tokens expire so a stale preview can't be filed
much later.

This is a *gate*, not a security boundary against the host: the signing key lives in the
same process. Its job is to force the prepare → human-review → submit ordering.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

__all__ = ["ConfirmationError", "issue_token", "verify_token"]

_VERSION = "v1"
_DEFAULT_TTL = 900.0  # seconds a preview stays fileable (15 min)


class ConfirmationError(Exception):
    """A confirmation token was missing, malformed, expired, or did not match."""


def _digest(kind: str, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(kind.encode("utf-8"))
    h.update(b"\x00")
    h.update(payload)
    return h.hexdigest()


def _sign(key: bytes, message: str) -> str:
    sig = hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def issue_token(
    key: bytes, *, kind: str, payload: bytes, ttl: float = _DEFAULT_TTL
) -> str:
    """Issue a confirmation token binding *kind* and the exact *payload* bytes.

    Returns an opaque ``v1.<kind>.<expiry>.<sig>`` string to be passed back to the
    matching ``submit`` tool alongside the same document.
    """
    expires_at = int(time.time() + ttl)
    digest = _digest(kind, payload)
    message = f"{_VERSION}.{kind}.{expires_at}.{digest}"
    return f"{_VERSION}.{kind}.{expires_at}.{_sign(key, message)}"


def verify_token(key: bytes, token: str, *, kind: str, payload: bytes) -> None:
    """Verify a confirmation *token* against *kind* and the resubmitted *payload*.

    Raises:
        ConfirmationError: if the token is malformed, for a different operation,
            expired, or does not match the bytes being submitted.
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
    digest = _digest(kind, payload)
    message = f"{_VERSION}.{kind}.{expires_at}.{digest}"
    expected = f"{_VERSION}.{kind}.{expires_at}.{_sign(key, message)}"
    if not hmac.compare_digest(expected, token):
        raise ConfirmationError(
            "confirmation token does not match the document being submitted; "
            "the document changed since prepare — run prepare again"
        )
