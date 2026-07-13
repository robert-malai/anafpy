"""e-Transport service package: MCP tools, input/return types, code lists.

The tools live in :mod:`.tools` (registered by the composition root), the
service-specific gate shapes and preview projection in :mod:`.models`, and the
nomenclatures the model can discover in :mod:`.nomenclature` (backed by the
generated XSD enums plus the UN/ECE unit codes in :mod:`.unitcodes`).
"""

from __future__ import annotations

from .tools import register

__all__ = ["register"]
