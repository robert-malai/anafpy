"""e-Factura service package: MCP tools, input/return types, document helpers.

The tools live in :mod:`.tools` (registered by the composition root), the
service-specific gate shapes in :mod:`.models`, and the XML projections
(previews, upload standards, PDF rendering) in :mod:`.documents`.
"""

from __future__ import annotations

from .tools import register

__all__ = ["register"]
