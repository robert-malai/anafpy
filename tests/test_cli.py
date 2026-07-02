"""Tests for the ``anafpy`` CLI (`auth status`; no network, no browser)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from anafpy.auth import FileTokenStore, TokenSet
from anafpy.cli.main import main


def test_status_not_authenticated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["auth", "status", "--store", str(tmp_path / "tokens.json")]) == 1
    assert "not authenticated" in capsys.readouterr().out


def test_status_reports_token_validity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    # Non-JWT tokens: expiry falls back to the documented 90/365-day TTLs.
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", "--store", str(store)]) == 0
    out = capsys.readouterr().out
    assert "authenticated" in out
    assert "~90 days left" in out
    assert "~365 days left" in out


def test_status_ignores_stored_expiry_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Expiries are computed from the tokens, so stale `*_expires_at` keys in an
    # older store must be ignored, not trusted.
    store = tmp_path / "tokens.json"
    store.write_text(
        json.dumps(
            {
                "access_token": "a",
                "refresh_token": "r",
                "obtained_at": time.time(),
                "access_expires_at": time.time() - 86400,  # stale: claims expired
                "refresh_expires_at": time.time() - 86400,
            }
        ),
        encoding="utf-8",
    )
    assert main(["auth", "status", "--store", str(store)]) == 0
    assert "~90 days left" in capsys.readouterr().out


def test_status_corrupt_store_is_a_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "status", "--store", str(store)]) == 1
    assert "token store" in capsys.readouterr().err
