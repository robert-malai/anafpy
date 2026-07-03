"""Token persistence.

``TokenStore`` is the abstraction the rest of the library depends on; ``FileTokenStore``
is the batteries-included default (a JSON file with owner-only permissions, suitable for
mounting as a Docker volume). ``KeyringTokenStore`` keeps the tokens in the OS
credential store instead (macOS Keychain, Windows Credential Manager, Linux Secret
Service/KWallet) and needs the ``anafpy[keyring]`` extra.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from ..exceptions import AnafConfigError
from .models import TokenSet

__all__ = ["FileTokenStore", "KeyringTokenStore", "MemoryTokenStore", "TokenStore"]


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
        """The stored token set, or ``None`` when no store file exists.

        Raises:
            AnafConfigError: the file exists but cannot be read or parsed — stay in
                the AnafError hierarchy instead of leaking a raw pydantic/OS error.
        """
        if not self.path.exists():
            return None
        try:
            return TokenSet.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise AnafConfigError(
                f"unreadable token store {self.path}: {exc} — "
                "delete it and run `anafpy auth login` again"
            ) from exc

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


_KEYRING_HINT = "install the keyring extra: pip install 'anafpy[keyring]'"

#: Windows Credential Manager caps a secret blob at 2560 bytes and the keyring
#: backend writes UTF-16, so a token set only fits split into ≤1280-character
#: entries; 1200 leaves margin.
_WINDOWS_CHUNK_CHARS = 1200


class KeyringTokenStore:
    """Token store in the OS credential store, via the ``keyring`` library.

    Uses the platform's native secret store — macOS Keychain, Windows Credential
    Manager, or a Linux Secret Service/KWallet daemon. The token set is stored as
    JSON under ``(service, username)``; a set longer than ``chunk_size`` characters
    is split across continuation entries (``username#1``, ``#2``, ...), which is
    what makes Windows work at all (its blob cap is smaller than one ANAF JWT).
    ``chunk_size=None`` picks the platform default: split on Windows, one entry
    everywhere else.

    Requires the ``anafpy[keyring]`` extra; construction fails with
    :class:`~anafpy.exceptions.AnafConfigError` when the package or a usable OS
    backend is missing.
    """

    def __init__(
        self,
        service: str = "anafpy",
        username: str = "tokens",
        *,
        chunk_size: int | None = None,
    ) -> None:
        try:
            import keyring
            from keyring.backends import fail
        except ImportError as exc:
            raise AnafConfigError(
                f"the keyring token store needs the `keyring` package — {_KEYRING_HINT}"
            ) from exc
        if isinstance(keyring.get_keyring(), fail.Keyring):
            raise AnafConfigError(
                "no usable OS credential store found (keyring resolved to its fail "
                "backend) — use the file token store, or install a Secret "
                "Service/KWallet daemon on Linux"
            )
        self.service = service
        self.username = username
        if chunk_size is None and sys.platform == "win32":
            chunk_size = _WINDOWS_CHUNK_CHARS
        self.chunk_size = chunk_size

    def _entry(self, index: int) -> str:
        return self.username if index == 0 else f"{self.username}#{index}"

    def load(self) -> TokenSet | None:
        """The stored token set, or ``None`` when the credential store has none.

        Raises:
            AnafConfigError: entries exist but cannot be read or parsed — stay in
                the AnafError hierarchy instead of leaking a keyring/pydantic error.
        """
        import keyring
        from keyring.errors import KeyringError

        try:
            first = keyring.get_password(self.service, self._entry(0))
            if first is None:
                return None
            parts = [first]
            while (
                chunk := keyring.get_password(self.service, self._entry(len(parts)))
            ) is not None:
                parts.append(chunk)
        except KeyringError as exc:
            raise AnafConfigError(
                f"cannot read the OS credential store (service {self.service!r}): {exc}"
            ) from exc
        try:
            return TokenSet.model_validate_json("".join(parts))
        except ValidationError as exc:
            raise AnafConfigError(
                f"unreadable token set in the OS credential store (service "
                f"{self.service!r}): {exc} — delete its {self.username!r} entries "
                "and run `anafpy auth login` again"
            ) from exc

    def save(self, tokens: TokenSet) -> None:
        import keyring
        from keyring.errors import KeyringError

        data = tokens.model_dump_json()
        size = self.chunk_size or len(data)
        chunks = [data[i : i + size] for i in range(0, len(data), size)]
        try:
            for index, chunk in enumerate(chunks):
                keyring.set_password(self.service, self._entry(index), chunk)
            # Drop stale continuation entries left over by a longer previous set,
            # so load() can never reassemble a mixed-generation token set.
            index = len(chunks)
            while keyring.get_password(self.service, self._entry(index)) is not None:
                keyring.delete_password(self.service, self._entry(index))
                index += 1
        except KeyringError as exc:
            raise AnafConfigError(
                f"cannot write the OS credential store (service {self.service!r}): "
                f"{exc}"
            ) from exc
