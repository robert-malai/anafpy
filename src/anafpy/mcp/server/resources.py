"""The compiled ANAF reference (``docs/anaf-reference/``) as read-only resources."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..config import ServerConfig

__all__ = ["register"]


def register(mcp: FastMCP, cfg: ServerConfig) -> None:
    """Expose the compiled ANAF reference Markdown as read-only resources."""
    docs = _docs_dir(cfg)
    if docs is None:
        return
    for md in sorted(docs.rglob("*.md")):
        if md.name == "README.md" or "_sources" in md.parts:
            continue
        rel = md.relative_to(docs).with_suffix("")
        uri = f"anafref://{rel.as_posix()}"
        mcp.resource(
            uri,
            name=f"ANAF reference: {rel.as_posix()}",
            description=(
                "Compiled ANAF API reference (status may be draft; partly Romanian)."
            ),
            mime_type="text/markdown",
        )(_make_reader(md))


def _docs_dir(cfg: ServerConfig) -> Path | None:
    default = Path(__file__).resolve().parents[4] / "docs" / "anaf-reference"
    docs = cfg.docs_dir or default
    return docs if docs.is_dir() else None


def _make_reader(path: Path) -> Callable[[], str]:
    def read() -> str:
        return path.read_text(encoding="utf-8")

    return read
