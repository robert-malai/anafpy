"""Server configuration, resolved from the environment via ``pydantic-settings``.

The MCP server is a **local stdio connector** (see ``DESIGN.md`` §8). It reads the same
credentials and token store that ``anafpy auth login`` writes, so a running server picks
up an existing session and refreshes it headlessly. Nothing here drives the interactive
certificate flow — that stays host-side in the CLI.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from pydantic import Field, PrivateAttr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .._transport.base import Environment
from ..exceptions import AnafConfigError

__all__ = ["ServerConfig"]

_DEFAULT_STORE = "~/.anafpy/tokens.json"


class ServerConfig(BaseSettings):
    """Configuration for the MCP server, read from ``ANAFPY_*`` environment variables.

    Construct with :meth:`from_env` (the server entry point) to get a friendly
    :class:`~anafpy.exceptions.AnafConfigError` when required values are missing; the
    plain constructor accepts explicit values (used in tests).

    Attributes:
        client_id: ANAF OAuth client id (``ANAFPY_CLIENT_ID``).
        client_secret: ANAF OAuth client secret (``ANAFPY_CLIENT_SECRET``).
        store_path: token-store JSON file (``ANAFPY_TOKEN_STORE``).
        environment: ``test`` or ``prod`` (``ANAFPY_ENV``).
        default_cif: fiscal code used when a tool call omits ``cif`` (``ANAFPY_CIF``).
        docs_dir: directory of the compiled ANAF reference exposed as MCP resources
            (``ANAFPY_DOCS_DIR``); defaults to the repo's ``docs/anaf-reference/``
            when present.
        signing_key: per-process secret backing the confirmation tokens issued by the
            two-step ``prepare`` → ``submit`` flow. Defaults to a fresh random key, so
            tokens are only valid within the lifetime of one server process.
    """

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    client_id: str = Field(validation_alias="ANAFPY_CLIENT_ID")
    client_secret: str = Field(validation_alias="ANAFPY_CLIENT_SECRET")
    store_path: Path = Field(
        default=Path(_DEFAULT_STORE), validation_alias="ANAFPY_TOKEN_STORE"
    )
    environment: Environment = Field(
        default=Environment.PROD, validation_alias="ANAFPY_ENV"
    )
    default_cif: str | None = Field(default=None, validation_alias="ANAFPY_CIF")
    docs_dir: Path | None = Field(default=None, validation_alias="ANAFPY_DOCS_DIR")
    # A private attribute, not a settings field: BaseSettings populates fields from
    # the environment by name, and the signing key must never come from a stray
    # `SIGNING_KEY` env var — it is a fresh per-process secret each run.
    _signing_key: bytes = PrivateAttr(default_factory=lambda: secrets.token_bytes(32))

    @property
    def signing_key(self) -> bytes:
        """Per-process secret backing the confirmation tokens (never from env)."""
        return self._signing_key

    @field_validator("store_path", "docs_dir")
    @classmethod
    def _expand_path(cls, value: Path | None) -> Path | None:
        return value.expanduser() if value is not None else None

    @field_validator("default_cif", "docs_dir", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return value or None

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Build a config from the environment.

        Raises:
            AnafConfigError: if a required value (the OAuth client id/secret) is missing
                or invalid — the server cannot refresh tokens without them.
        """
        try:
            # BaseSettings populates required fields from the environment; mypy can't
            # see that without the pydantic plugin, hence the call-arg ignore.
            return cls()  # type: ignore[call-arg]
        except ValidationError as exc:
            raise AnafConfigError(
                "invalid MCP server configuration "
                "(ANAFPY_CLIENT_ID and ANAFPY_CLIENT_SECRET are required, "
                "ANAFPY_ENV must be 'test' or 'prod'): "
                f"{exc.errors(include_url=False)}"
            ) from exc

    def require_cif(self, cif: str | None) -> str:
        """Return *cif* if given, else the configured default, else raise."""
        resolved = cif or self.default_cif
        if not resolved:
            raise AnafConfigError(
                "no CIF supplied and ANAFPY_CIF is not set; pass `cif` explicitly"
            )
        return resolved
