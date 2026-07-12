"""Tests for the SPV session store."""

from __future__ import annotations

import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from anafpy.exceptions import AnafConfigError
from anafpy.spv import FileSessionStore, SpvSession


def _session() -> SpvSession:
    return SpvSession(
        cookies={"MRHSession": "abc", "F5_ST": "1z"},
        established_at=datetime(2026, 7, 12, 12, 0, tzinfo=UTC),
    )


# --- session store --------------------------------------------------------------------


def test_file_store_roundtrip_with_owner_only_permissions(tmp_path: Path) -> None:
    store = FileSessionStore(tmp_path / "spv-session.json")
    assert store.load() is None
    store.save(_session())
    mode = stat.S_IMODE(store.path.stat().st_mode)
    assert mode == 0o600
    loaded = store.load()
    assert loaded is not None
    assert loaded.cookies == {"MRHSession": "abc", "F5_ST": "1z"}
    assert loaded.is_authenticated_shape
    store.clear()
    assert store.load() is None


def test_file_store_corrupt_file_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "spv-session.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AnafConfigError, match="unreadable SPV session store"):
        FileSessionStore(path).load()
