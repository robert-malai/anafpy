"""Owner-only, atomic JSON persistence for a single pydantic model.

The custody treatment anafpy's two bearer credentials share: the OAuth
:class:`~anafpy.auth.models.TokenSet` (:class:`~anafpy.auth.store.FileTokenStore`)
and the SPV APM cookie set
(:class:`~anafpy.spv.session.FileSessionStore`). Both are secrets that fully
stand in for the taxpayer, so both are written the same way — to a temp file in
the destination directory, chmod ``0o600``, then atomically replaced into place,
so the file is never briefly world-readable and never half-written.

Subclasses supply only what differs: the model, and the wording of the two
error messages (which store, and how the user recovers from a corrupt one).
Reads and writes stay in the ``AnafError`` hierarchy — a raw ``OSError`` or
pydantic ``ValidationError`` must never escape a store.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .exceptions import AnafConfigError

__all__ = ["JsonFileStore"]


class JsonFileStore[ModelT: BaseModel]:
    """A ``0o600`` JSON file holding one *model* instance.

    Args:
        path: the JSON file (``~`` is expanded).
        model: the pydantic model persisted in it.
        label: how the file is named in error messages ("token store").
        recovery: what the user should do about an unreadable one, completing
            the sentence "delete it and ..." ("run ``anafpy auth login`` again").
        prefix: temp-file prefix used while writing, for recognisability.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        model: type[ModelT],
        label: str,
        recovery: str,
        prefix: str,
    ) -> None:
        self.path = Path(path).expanduser()
        self._model = model
        self._label = label
        self._recovery = recovery
        self._prefix = prefix

    def load(self) -> ModelT | None:
        """The stored value, or ``None`` when no store file exists.

        Raises:
            AnafConfigError: the file exists but cannot be read or parsed.
        """
        if not self.path.exists():
            return None
        try:
            return self._model.model_validate_json(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as exc:
            raise AnafConfigError(
                f"unreadable {self._label} {self.path}: {exc} — "
                f"delete it and {self._recovery}"
            ) from exc

    def save(self, value: ModelT) -> None:
        """Write *value*, owner-only and atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = value.model_dump_json(indent=2)
        # Write to a temp file in the same dir, fix perms, then atomically replace.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=self._prefix, suffix=".json"
        )
        tmp = Path(tmp_name)
        try:
            os.write(fd, data.encode("utf-8"))
        finally:
            os.close(fd)
        tmp.chmod(0o600)
        tmp.replace(self.path)

    def clear(self) -> None:
        """Delete the store file; a no-op when none exists.

        Raises:
            AnafConfigError: the file exists but cannot be removed.
        """
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise AnafConfigError(
                f"cannot remove {self._label} {self.path}: {exc}"
            ) from exc
