"""Server configuration, resolved from the environment via ``pydantic-settings``.

The MCP server is a **local stdio connector** (see ``DESIGN.md`` §8). It reads
the same credentials and token store that ``anafpy auth login`` writes, so a running
server picks up an existing session and refreshes it headlessly. Nothing here drives
the interactive certificate flow — that stays host-side in the CLI.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    Field,
    ModelWrapValidatorHandler,
    PrivateAttr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from .._transport.base import Environment
from ..exceptions import AnafConfigError

__all__ = ["ServerConfig", "bundled_dir"]

_DEFAULT_STORE = "~/.anafpy/tokens.json"


def bundled_dir(configured: Path | None, *candidates: Path) -> Path | None:
    """Resolve a directory the server serves content from, or ``None``.

    The rule both bundled trees follow (the ANAF reference in
    :mod:`~anafpy.mcp.reference`, the workflow skills in
    :mod:`~anafpy.mcp.prompts`): an explicitly configured directory wins and is
    used **only** if it exists — a stale ``ANAFPY_DOCS_DIR`` silently serving the
    packaged copy instead would be worse than serving nothing — otherwise the
    first existing *candidate* (the repo checkout's live tree, then the copy the
    wheel packages) is taken.
    """
    if configured is not None:
        return configured if configured.is_dir() else None
    return next((path for path in candidates if path.is_dir()), None)


class ServerConfig(BaseSettings):
    """Configuration for the MCP server, read from ``ANAFPY_*`` environment variables.

    Every field defaults from its ``ANAFPY_*`` variable, so ``ServerConfig()`` is
    the environment (the server entry point); keyword arguments override it, which
    is how the tests supply explicit values. Nothing here is required — see
    ``client_id`` below.

    Attributes:
        client_id: ANAF OAuth client id (``ANAFPY_CLIENT_ID``). Optional: without
            credentials the server still starts and serves the public no-auth
            lookups; the authenticated e-Factura / e-Transport tools report how to
            enable themselves instead of working.
        client_secret: ANAF OAuth client secret (``ANAFPY_CLIENT_SECRET``).
        store_path: token-store JSON file (``ANAFPY_TOKEN_STORE``); used only by
            the ``file`` backend.
        store_backend: ``keyring`` (the OS credential store, the default) or
            ``file`` (JSON at ``store_path`` — for Docker/headless hosts without
            a credential store) (``ANAFPY_TOKEN_STORE_BACKEND``).
        environment: ``test`` or ``prod`` (``ANAFPY_ENV``).
        default_cif: fiscal code used when a tool call omits ``cif`` (``ANAFPY_CIF``).
        docs_dir: directory of the compiled ANAF reference exposed as MCP resources
            (``ANAFPY_DOCS_DIR``); defaults to the repo's ``docs/anaf-reference/``
            when present, else the copy packaged into the wheel.
        skills_dir: directory of workflow skills exposed as MCP prompts
            (``ANAFPY_SKILLS_DIR``); defaults to the ``anafpy-workflows`` plugin's
            ``plugins/anafpy-workflows/skills/`` when present, else the copy
            packaged into the wheel.
        spv_session_path: the SPV cookie-session store written by
            ``anafpy spv login`` (``ANAFPY_SPV_SESSION``).
        spv_identity_path: the persisted certificate selection written by
            ``spv_select_certificate`` / ``anafpy spv login``
            (``ANAFPY_SPV_IDENTITY_FILE``).
        duk_dir: an extracted DUKIntegrator ``dist/`` folder (``ANAFPY_DUK_DIR``);
            overrides the managed dist that ``declaratie_duk_install`` maintains
            at ``~/.anafpy/duk-dist``. With neither, the declaration tools
            report how to enable themselves, like the authenticated tools
            without OAuth credentials.
        duk_java: the ``java`` binary DUKIntegrator runs under (``ANAFPY_DUK_JAVA``);
            optional — falls back to ``java`` on ``PATH``, then to ``JAVA_HOME``.
        sign_identity: the platform-store certificate to sign declarations with
            (``ANAFPY_SIGN_IDENTITY``) — the Keychain identity name on macOS, the
            SHA-1 thumbprint on Windows; optional — falls back to the persisted
            SPV certificate selection (the same qualified certificate).
        declaratii_upload: whether the declaration portal-upload tools
            (``declaratie_portal_login`` / ``declaratie_portal_status`` /
            ``declaratie_prepare`` / ``declaratie_submit``) are served
            (``ANAFPY_DECLARATII_UPLOAD``). **On by default**; set it to
            ``off``/``0``/``false`` to opt out — the server then serves the
            local authoring tools only and ``declaratie_sign`` points the user
            at manual portal filing. Filing goes to the PRODUCTION portal
            (declaration filing has no TEST environment), which is why the
            opt-out exists.
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
        default="keyring", validation_alias="ANAFPY_TOKEN_STORE_BACKEND"
    )
    environment: Environment = Field(
        default=Environment.PROD, validation_alias="ANAFPY_ENV"
    )
    default_cif: str | None = Field(default=None, validation_alias="ANAFPY_CIF")
    docs_dir: Path | None = Field(default=None, validation_alias="ANAFPY_DOCS_DIR")
    skills_dir: Path | None = Field(default=None, validation_alias="ANAFPY_SKILLS_DIR")
    spv_session_path: Path = Field(
        default=Path("~/.anafpy/spv-session.json"),
        validation_alias="ANAFPY_SPV_SESSION",
    )
    spv_identity_path: Path = Field(
        default=Path("~/.anafpy/spv-identity.json"),
        validation_alias="ANAFPY_SPV_IDENTITY_FILE",
    )
    duk_dir: Path | None = Field(default=None, validation_alias="ANAFPY_DUK_DIR")
    duk_java: str | None = Field(default=None, validation_alias="ANAFPY_DUK_JAVA")
    sign_identity: str | None = Field(
        default=None, validation_alias="ANAFPY_SIGN_IDENTITY"
    )
    declaratii_upload: bool = Field(
        default=True, validation_alias="ANAFPY_DECLARATII_UPLOAD"
    )
    # A private attribute, not a settings field: BaseSettings populates fields from
    # the environment by name, and the signing key must never come from a stray
    # `SIGNING_KEY` env var — it is a fresh per-process secret each run.
    _signing_key: bytes = PrivateAttr(default_factory=lambda: secrets.token_bytes(32))

    @model_validator(mode="wrap")
    @classmethod
    def _config_errors_are_anaf_errors(
        cls, data: Any, handler: ModelWrapValidatorHandler[ServerConfig]
    ) -> ServerConfig:
        """Fail in the ``AnafError`` hierarchy, not pydantic's.

        A wrap validator rather than an ``__init__`` override: it covers the same
        construction paths, but leaves the constructor pydantic synthesizes alone,
        so a wrong keyword argument stays a *static* type error instead of only a
        runtime one.

        Raises:
            AnafConfigError: if a value is invalid (e.g. a bad ``ANAFPY_ENV``).
        """
        try:
            return handler(data)
        except ValidationError as exc:
            # Every field carries a `validation_alias`, so pydantic already names
            # the offending variable and its accepted values per error — restate
            # neither here (a hand-written hint drifts as fields are added).
            raise AnafConfigError(f"invalid MCP server configuration:\n{exc}") from exc

    @property
    def signing_key(self) -> bytes:
        """Per-process secret backing the confirmation tokens (never from env)."""
        return self._signing_key

    @field_validator(
        "store_path",
        "docs_dir",
        "skills_dir",
        "spv_session_path",
        "spv_identity_path",
        "duk_dir",
    )
    @classmethod
    def _expand_path(cls, value: Path | None) -> Path | None:
        return value.expanduser() if value is not None else None

    @field_validator(
        "client_id",
        "client_secret",
        "default_cif",
        "docs_dir",
        "skills_dir",
        "duk_dir",
        "duk_java",
        "sign_identity",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return value or None

    @field_validator("store_backend", mode="before")
    @classmethod
    def _blank_backend_is_default(cls, value: object) -> object:
        return value or "keyring"

    @field_validator("declaratii_upload", mode="before")
    @classmethod
    def _blank_upload_is_default(cls, value: object) -> object:
        return True if value == "" else value

    @property
    def has_credentials(self) -> bool:
        """Whether an OAuth client id + secret pair is configured."""
        return self.client_id is not None and self.client_secret is not None

    def require_cif(self, cif: str | None) -> str:
        """Return *cif* if given, else the configured default, else raise."""
        resolved = cif or self.default_cif
        if not resolved:
            raise AnafConfigError(
                "no CIF supplied and ANAFPY_CIF is not set; pass `cif` explicitly"
            )
        return resolved
