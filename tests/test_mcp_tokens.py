"""Confirmation-token gating for the two-step MCP mutation flow."""

from __future__ import annotations

import time

import pytest

from anafpy.mcp.tokens import (
    ConfirmationError,
    TokenLedger,
    issue_token,
    verify_token,
)

KEY = b"k" * 32


def test_roundtrip_verifies() -> None:
    token = issue_token(KEY, kind="efactura.invoice", payload=b"<Invoice/>")
    # Same key + kind + payload verifies with no exception.
    verify_token(KEY, token, kind="efactura.invoice", payload=b"<Invoice/>")


def test_tampered_payload_is_rejected() -> None:
    token = issue_token(KEY, kind="efactura.invoice", payload=b"<Invoice/>")
    with pytest.raises(ConfirmationError, match="does not match"):
        verify_token(
            KEY, token, kind="efactura.invoice", payload=b"<Invoice>X</Invoice>"
        )


def test_wrong_kind_is_rejected() -> None:
    token = issue_token(KEY, kind="efactura.invoice", payload=b"x")
    with pytest.raises(ConfirmationError, match="is for"):
        verify_token(KEY, token, kind="etransport.declaration", payload=b"x")


def test_wrong_key_is_rejected() -> None:
    token = issue_token(KEY, kind="efactura.invoice", payload=b"x")
    with pytest.raises(ConfirmationError, match="does not match"):
        verify_token(b"j" * 32, token, kind="efactura.invoice", payload=b"x")


def test_expired_token_is_rejected() -> None:
    token = issue_token(KEY, kind="efactura.invoice", payload=b"x", ttl=-1.0)
    with pytest.raises(ConfirmationError, match="expired"):
        verify_token(KEY, token, kind="efactura.invoice", payload=b"x")


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(ConfirmationError, match="malformed"):
        verify_token(KEY, "not-a-token", kind="efactura.invoice", payload=b"x")


def test_changed_context_is_rejected() -> None:
    # The context binds the submission parameters (CIF, standard) the human approved.
    ctx = "cif=123;standard=UBL"
    token = issue_token(KEY, kind="efactura.invoice", payload=b"x", context=ctx)
    verify_token(KEY, token, kind="efactura.invoice", payload=b"x", context=ctx)
    with pytest.raises(ConfirmationError, match="does not match"):
        verify_token(
            KEY,
            token,
            kind="efactura.invoice",
            payload=b"x",
            context="cif=999;standard=UBL",
        )


def test_ledger_makes_tokens_single_use() -> None:
    ledger = TokenLedger()
    expires = time.time() + 900
    assert ledger.consume("tok-1", expires) is True
    assert ledger.consume("tok-1", expires) is False  # replay
    assert ledger.consume("tok-2", expires) is True  # unrelated token unaffected


def test_ledger_prunes_expired_entries() -> None:
    ledger = TokenLedger()
    assert ledger.consume("tok-1", time.time() - 1) is True
    # Expired entries are pruned; the (now unverifiable-anyway) token frees its slot.
    assert ledger.consume("tok-1", time.time() + 900) is True
