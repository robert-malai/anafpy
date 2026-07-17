"""Tool annotations and the artifact-writing helper shared by the service packages."""

from __future__ import annotations

from pathlib import Path

from mcp.types import ToolAnnotations

from ..exceptions import AnafConfigError

__all__ = [
    "ARTIFACT_SAVING",
    "LOCAL_READ_ONLY",
    "MUTATING",
    "READ_ONLY",
    "REQUESTING",
    "check_writable",
    "ensure_writable",
    "write_artifact",
]

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
# Pure local computation — no network, no subprocess, no filesystem: a closed
# world, unlike the ANAF-backed reads above (e.g. declaratie_nr_evid).
LOCAL_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
MUTATING = ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=True)
# Files an additive request with ANAF: nothing is overwritten or deleted, but a
# repeat files again — honest hints for a mutating, non-idempotent, non-destructive
# operation (a host must not treat it as an auto-invokable read).
REQUESTING = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
)
# Reads from ANAF but may write local files at caller-given paths — honest hints
# (not readOnlyHint), yet freely callable: the two-step gate is for ANAF filings only.
ARTIFACT_SAVING = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)


def _collision_error(path: Path) -> AnafConfigError:
    return AnafConfigError(
        f"refusing to overwrite existing file {path} — pick another name, or "
        "pass overwrite=true to replace it deliberately"
    )


def check_writable(target: str | Path, *, overwrite: bool) -> Path:
    """Resolve an artifact target and reject a collision — with NO side effects.

    The pure pre-flight half of :func:`ensure_writable`: use it before
    committing to a long wait (a poll, a 2FA prompt) so a failed or abandoned
    run leaves no freshly-created directory tree behind. Parents are created
    only at actual write time.
    """
    path = Path(target).expanduser()
    if path.exists() and not overwrite:
        raise _collision_error(path)
    return path


def ensure_writable(target: str | Path, *, overwrite: bool) -> Path:
    """Resolve an artifact target, reject collisions, and create its parent."""
    path = check_writable(target, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_artifact(target: str | Path, data: bytes, *, overwrite: bool) -> str:
    """Write a downloaded artifact without silently replacing an existing file.

    Without ``overwrite`` the write is atomic (exclusive create), so a file that
    appears after the :func:`ensure_writable` check is still refused, never
    clobbered.
    """
    path = ensure_writable(target, overwrite=overwrite)
    if overwrite:
        path.write_bytes(data)
        return str(path)
    try:
        with path.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise _collision_error(path) from exc
    return str(path)
