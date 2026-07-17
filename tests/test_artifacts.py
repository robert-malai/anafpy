"""Shared MCP artifact collision guard."""

from pathlib import Path

import pytest

from anafpy.exceptions import AnafConfigError
from anafpy.mcp.artifacts import check_writable, ensure_writable, write_artifact


def test_collision_message_is_shared(tmp_path: Path) -> None:
    target = tmp_path / "exists.pdf"
    target.write_bytes(b"old")
    expected = (
        f"refusing to overwrite existing file {target} — pick another name, "
        "or pass overwrite=true to replace it deliberately"
    )

    with pytest.raises(AnafConfigError, match="refusing") as ensure_error:
        ensure_writable(target, overwrite=False)
    with pytest.raises(AnafConfigError, match="refusing") as write_error:
        write_artifact(target, b"new", overwrite=False)

    assert str(ensure_error.value) == expected
    assert str(write_error.value) == expected


def test_write_artifact_refuses_file_created_after_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate the check-then-write race: with the ensure_writable collision
    # check fooled, the exclusive-create open must still refuse — the existing
    # file is never clobbered.
    target = tmp_path / "race.pdf"
    target.write_bytes(b"old")
    monkeypatch.setattr(
        "anafpy.mcp.artifacts.ensure_writable",
        lambda t, *, overwrite: Path(t),
    )

    with pytest.raises(AnafConfigError, match="refusing"):
        write_artifact(target, b"new", overwrite=False)

    assert target.read_bytes() == b"old"


def test_check_writable_is_side_effect_free(tmp_path: Path) -> None:
    # The pure pre-flight half: rejects collisions like ensure_writable but
    # never creates the parent directories.
    target = tmp_path / "deep" / "tree" / "new.pdf"
    assert check_writable(target, overwrite=False) == target
    assert not (tmp_path / "deep").exists()

    existing = tmp_path / "exists.pdf"
    existing.write_bytes(b"old")
    with pytest.raises(AnafConfigError, match="refusing"):
        check_writable(existing, overwrite=False)


def test_write_artifact_creates_new_file(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "new.pdf"
    assert write_artifact(target, b"data", overwrite=False) == str(target)
    assert target.read_bytes() == b"data"


def test_write_artifact_overwrite_replaces(tmp_path: Path) -> None:
    target = tmp_path / "exists.pdf"
    target.write_bytes(b"old")
    assert write_artifact(target, b"new", overwrite=True) == str(target)
    assert target.read_bytes() == b"new"
