"""Token persistence.

``TokenStore`` is the abstraction the rest of the library depends on; ``FileTokenStore``
is the batteries-included default (a JSON file with owner-only permissions, suitable for
mounting as a Docker volume).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import TokenSet

__all__ = ["FileTokenStore", "MemoryTokenStore", "TokenStore"]


@runtime_checkable
class TokenStore(Protocol):
    """Where token sets are loaded from and saved to."""

    def load(self) -> TokenSet | None: ...

    def save(self, tokens: TokenSet) -> None: ...


class MemoryTokenStore:
    """In-process token store (tests, ephemeral runtimes)."""

    def __init__(self, tokens: TokenSet | None = None) -> None:
        self._tokens = tokens

    def load(self) -> TokenSet | None:
        return self._tokens

    def save(self, tokens: TokenSet) -> None:
        self._tokens = tokens


class FileTokenStore:
    """JSON-file token store, written atomically with ``0o600`` permissions."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> TokenSet | None:
        if not self.path.exists():
            return None
        return TokenSet.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, tokens: TokenSet) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = tokens.model_dump_json(indent=2)
        # Write to a temp file in the same dir, fix perms, then atomically replace.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=".tok-", suffix=".json"
        )
        tmp = Path(tmp_name)
        try:
            os.write(fd, data.encode("utf-8"))
        finally:
            os.close(fd)
        tmp.chmod(0o600)
        tmp.replace(self.path)
