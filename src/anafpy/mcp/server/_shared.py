"""Tool annotations shared by the server's tool modules."""

from __future__ import annotations

from mcp.types import ToolAnnotations

__all__ = ["ARTIFACT_SAVING", "MUTATING", "READ_ONLY"]

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
MUTATING = ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=True)
# Reads from ANAF but may write local files at caller-given paths — honest hints
# (not readOnlyHint), yet freely callable: the two-step gate is for ANAF filings only.
ARTIFACT_SAVING = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
