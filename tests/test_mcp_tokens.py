"""Confirmation-token gating for the two-step MCP mutation flow."""

from __future__ import annotations

import pytest

from anafpy.mcp.tokens import ConfirmationError, issue_token, verify_token

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
