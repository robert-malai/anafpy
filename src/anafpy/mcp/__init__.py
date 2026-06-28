"""anafpy MCP server (phase 2): e-Factura / e-Transport operations as Cowork skills.

A local stdio connector built on the phase-1 async clients. Requires the
``anafpy[mcp]`` extra. Run with ``python -m anafpy.mcp`` (host-side, where the token
store written by ``anafpy auth login`` lives). See ``DESIGN.md`` §7.
"""

from __future__ import annotations

from .config import ServerConfig
from .server import create_server

__all__ = ["ServerConfig", "create_server"]
