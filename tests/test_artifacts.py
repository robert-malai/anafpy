"""Shared MCP artifact collision guard."""

from pathlib import Path

import pytest

from anafpy.exceptions import AnafConfigError
from anafpy.mcp.artifacts import ensure_writable, write_artifact


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
