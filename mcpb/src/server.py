"""MCP Bundle entry point — start the anafpy MCP server over stdio.

Claude Desktop runs this file with the bundle's uv-managed environment
(``pyproject.toml`` pins the anafpy release); it is the ``anafpy-mcp``
console script in bundle form.
"""

from __future__ import annotations

from anafpy.mcp import main

if __name__ == "__main__":
    main()
