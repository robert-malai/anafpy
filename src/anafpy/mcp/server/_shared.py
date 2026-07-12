"""Tool annotations and small helpers shared by the server's tool modules."""

from __future__ import annotations

from pathlib import Path

from mcp.types import ToolAnnotations

from ...exceptions import AnafConfigError

__all__ = ["ARTIFACT_SAVING", "MUTATING", "READ_ONLY", "write_artifact"]

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
MUTATING = ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=True)
# Reads from ANAF but may write local files at caller-given paths — honest hints
# (not readOnlyHint), yet freely callable: the two-step gate is for ANAF filings only.
ARTIFACT_SAVING = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)


def write_artifact(target: str, data: bytes, *, overwrite: bool) -> str:
    """Write a downloaded artifact to a caller-given path, creating parent dirs.

    An existing file is never silently replaced: a batch flow naming files from
    document metadata ("<date> - <partner>.pdf") must not lose one document to a
    name collision. Raises :class:`AnafConfigError` unless ``overwrite`` is set.
    """
    path = Path(target).expanduser()
    if path.exists() and not overwrite:
        raise AnafConfigError(
            f"refusing to overwrite existing file {path} — pick another name, or "
            "pass overwrite=true to replace it deliberately"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)
