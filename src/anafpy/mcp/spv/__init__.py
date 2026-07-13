"""SPV service package: read-only mailbox tools, report requests, code lists.

The tools live in :mod:`.tools` (registered by the composition root); the report
types and their per-type parameters — the SPV code lists the model can discover —
in :mod:`.nomenclature`.
"""

from __future__ import annotations

from .tools import register

__all__ = ["register"]
