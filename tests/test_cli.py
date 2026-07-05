"""Tests for the ``anafpy`` CLI (`auth status`/`logout`; no network, no browser)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from anafpy.auth import FileTokenStore, KeyringTokenStore, TokenSet
from anafpy.cli.main import main
from conftest import FakeKeyring


def _file_args(store: Path) -> list[str]:
    return ["--store-backend", "file", "--store", str(store)]


def test_status_not_authenticated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["auth", "status", *_file_args(tmp_path / "tokens.json")]) == 1
    assert "not authenticated" in capsys.readouterr().out


def test_status_reports_token_validity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    # Non-JWT tokens: expiry falls back to the documented 90/365-day TTLs.
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", *_file_args(store)]) == 0
    out = capsys.readouterr().out
    assert "authenticated" in out
    assert "~90 days left" in out
    assert "~365 days left" in out


def test_store_env_is_read_at_parse_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # ANAFPY_TOKEN_STORE / ANAFPY_TOKEN_STORE_BACKEND must be honoured even when
    # set after module import, so wrappers and tests can configure them.
    store = tmp_path / "tokens.json"
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    monkeypatch.setenv("ANAFPY_TOKEN_STORE", str(store))
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "file")
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


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
    assert main(["auth", "status", *_file_args(store)]) == 0
    assert "~90 days left" in capsys.readouterr().out


def test_status_corrupt_store_is_a_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "status", *_file_args(store)]) == 1
    assert "token store" in capsys.readouterr().err


def test_keyring_is_the_default_backend(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # No flags, no env: tokens come from the (fake, autouse) OS credential store.
    monkeypatch.delenv("ANAFPY_TOKEN_STORE_BACKEND", raising=False)
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_status_reads_the_keyring_backend(
    fake_keyring: FakeKeyring, capsys: pytest.CaptureFixture[str]
) -> None:
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", "--store-backend", "keyring"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_status_env_selects_the_keyring_backend(
    fake_keyring: FakeKeyring,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "keyring")
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_unknown_store_backend_from_env_is_a_cli_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # argparse never validates defaults, so a bad env value must be caught later.
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "vault")
    assert main(["auth", "status"]) == 1
    assert "backend" in capsys.readouterr().err


# --- auth logout ------------------------------------------------------------------


def _saved_store(tmp_path: Path) -> Path:
    path = tmp_path / "tokens.json"
    FileTokenStore(path).save(TokenSet(access_token="acc", refresh_token="ref"))
    return path


def test_logout_not_authenticated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["auth", "logout", *_file_args(tmp_path / "tokens.json")]) == 0
    assert "nothing to remove" in capsys.readouterr().out


def test_logout_clears_the_store_without_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Logout is purely local (ANAF's /revoke is not reachable headlessly —
    # live-probed 2026-07-05): no respx mock is active, so any HTTP attempt
    # would hit the real network and fail loudly.
    store = _saved_store(tmp_path)
    assert main(["auth", "logout", *_file_args(store)]) == 0
    assert not store.exists()
    assert "Logged out" in capsys.readouterr().out


def test_logout_corrupt_store_is_still_cleared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Logout must be able to get rid of a store that status/login cannot even read.
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "logout", *_file_args(store)]) == 0
    assert not store.exists()
    assert "unreadable" in capsys.readouterr().err


def test_logout_clears_the_keyring_backend(
    fake_keyring: FakeKeyring, capsys: pytest.CaptureFixture[str]
) -> None:
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "logout", "--store-backend", "keyring"]) == 0
    assert fake_keyring.entries == {}
    assert "Logged out" in capsys.readouterr().out
