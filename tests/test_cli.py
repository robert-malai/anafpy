"""Tests for the ``anafpy`` CLI (`auth status`; no network, no browser)."""

from __future__ import annotations

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
    FileTokenStore(store).save(
        TokenSet(
            access_token="a",
            refresh_token="r",
            access_expires_at=time.time() + 90 * 86400,
            refresh_expires_at=time.time() + 365 * 86400,
        )
    )
    assert main(["auth", "status", "--store", str(store)]) == 0
    out = capsys.readouterr().out
    assert "authenticated" in out
    assert "~90 days left" in out


def test_status_tolerates_missing_expiry_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A store written without the computed expiry timestamps (older / hand-migrated
    # file) must report, not crash formatting None.
    store = tmp_path / "tokens.json"
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", "--store", str(store)]) == 0
    assert "unknown expiry" in capsys.readouterr().out


def test_status_corrupt_store_is_a_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "status", "--store", str(store)]) == 1
    assert "token store" in capsys.readouterr().err
