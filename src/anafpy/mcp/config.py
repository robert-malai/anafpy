"""Server configuration, resolved from the environment via ``pydantic-settings``.

The MCP server is a **local stdio connector** (see ``DESIGN.md`` §8). It reads the same
credentials and token store that ``anafpy auth login`` writes, so a running server picks
up an existing session and refreshes it headlessly. Nothing here drives the interactive
certificate flow — that stays host-side in the CLI.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Literal

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
        client_id: ANAF OAuth client id (``ANAFPY_CLIENT_ID``). Optional: without
            credentials the server still starts and serves the public no-auth
            lookups; the authenticated e-Factura / e-Transport tools report how to
            enable themselves instead of working.
        client_secret: ANAF OAuth client secret (``ANAFPY_CLIENT_SECRET``).
        store_path: token-store JSON file (``ANAFPY_TOKEN_STORE``); used only by
            the ``file`` backend.
        store_backend: ``file`` (JSON at ``store_path``) or ``keyring`` (the OS
            credential store; needs the ``anafpy[keyring]`` extra)
            (``ANAFPY_TOKEN_STORE_BACKEND``).
        environment: ``test`` or ``prod`` (``ANAFPY_ENV``).
        default_cif: fiscal code used when a tool call omits ``cif`` (``ANAFPY_CIF``).
        docs_dir: directory of the compiled ANAF reference exposed as MCP resources
            (``ANAFPY_DOCS_DIR``); defaults to the repo's ``docs/anaf-reference/``
            when present.
        skills_dir: directory of workflow skills exposed as MCP prompts
            (``ANAFPY_SKILLS_DIR``); defaults to the repo's ``skills/`` when
            present.
        signing_key: per-process secret backing the confirmation tokens issued by the
            two-step ``prepare`` → ``submit`` flow. Defaults to a fresh random key, so
            tokens are only valid within the lifetime of one server process.
    """

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    client_id: str | None = Field(default=None, validation_alias="ANAFPY_CLIENT_ID")
    client_secret: str | None = Field(
        default=None, validation_alias="ANAFPY_CLIENT_SECRET"
    )
    store_path: Path = Field(
        default=Path(_DEFAULT_STORE), validation_alias="ANAFPY_TOKEN_STORE"
    )
    store_backend: Literal["file", "keyring"] = Field(
        default="file", validation_alias="ANAFPY_TOKEN_STORE_BACKEND"
    )
    environment: Environment = Field(
        default=Environment.PROD, validation_alias="ANAFPY_ENV"
    )
    default_cif: str | None = Field(default=None, validation_alias="ANAFPY_CIF")
    docs_dir: Path | None = Field(default=None, validation_alias="ANAFPY_DOCS_DIR")
    skills_dir: Path | None = Field(default=None, validation_alias="ANAFPY_SKILLS_DIR")
    # A private attribute, not a settings field: BaseSettings populates fields from
    # the environment by name, and the signing key must never come from a stray
    # `SIGNING_KEY` env var — it is a fresh per-process secret each run.
    _signing_key: bytes = PrivateAttr(default_factory=lambda: secrets.token_bytes(32))

    @property
    def signing_key(self) -> bytes:
        """Per-process secret backing the confirmation tokens (never from env)."""
        return self._signing_key

    @field_validator("store_path", "docs_dir", "skills_dir")
    @classmethod
    def _expand_path(cls, value: Path | None) -> Path | None:
        return value.expanduser() if value is not None else None

    @field_validator(
        "client_id",
        "client_secret",
        "default_cif",
        "docs_dir",
        "skills_dir",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return value or None

    @field_validator("store_backend", mode="before")
    @classmethod
    def _blank_backend_is_default(cls, value: object) -> object:
        return value or "file"

    @property
    def has_credentials(self) -> bool:
        """Whether an OAuth client id + secret pair is configured."""
        return self.client_id is not None and self.client_secret is not None

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Build a config from the environment.

        Missing OAuth credentials are not an error — the server starts with only
        the public no-auth lookups usable.

        Raises:
            AnafConfigError: if a supplied value is invalid (e.g. a bad
                ``ANAFPY_ENV``).
        """
        try:
            return cls()
        except ValidationError as exc:
            raise AnafConfigError(
                "invalid MCP server configuration "
                "(ANAFPY_ENV must be 'test' or 'prod'; "
                "ANAFPY_TOKEN_STORE_BACKEND 'file' or 'keyring'): "
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
