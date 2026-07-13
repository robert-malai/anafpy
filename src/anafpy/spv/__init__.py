"""Read-only client for ANAF's SPV (Spațiul Privat Virtual) web services.

The certificate-authenticated session bootstrap is platform-specific
(:class:`CurlBootstrapper` over the OS-shipped curl); everything else is plain
httpx riding the APM cookies. See ``docs/anaf-reference/spv/api.md`` for the
compiled service reference.
"""

from __future__ import annotations

from .auth import SpvAuth, SpvSessionProvider
from .bootstrap import SPV_BASE_URL, CurlBootstrapper, SessionBootstrapper
from .certs import (
    SelectedIdentity,
    StoreIdentity,
    discover_identities,
    identity_by_thumbprint,
    list_keychain_identities,
    list_windows_identities,
    load_selected_identity,
    save_selected_identity,
)
from .client import SpvClient
from .models import (
    INCOME_CERTIFICATE_REASONS,
    REPORT_PARAMETER_WIRE_NAMES,
    MessageList,
    ReportRequest,
    ReportRequestResult,
    ReportType,
    SpvDocument,
    SpvEnvelope,
    SpvMessage,
    english_error_hint,
    optional_parameters,
    required_parameters,
)
from .session import (
    DEFAULT_SESSION_PATH,
    FileSessionStore,
    MemorySessionStore,
    SessionStore,
    SpvSession,
)

__all__ = [
    "DEFAULT_SESSION_PATH",
    "INCOME_CERTIFICATE_REASONS",
    "REPORT_PARAMETER_WIRE_NAMES",
    "SPV_BASE_URL",
    "CurlBootstrapper",
    "FileSessionStore",
    "MemorySessionStore",
    "MessageList",
    "ReportRequest",
    "ReportRequestResult",
    "ReportType",
    "SelectedIdentity",
    "SessionBootstrapper",
    "SessionStore",
    "SpvAuth",
    "SpvClient",
    "SpvDocument",
    "SpvEnvelope",
    "SpvMessage",
    "SpvSession",
    "SpvSessionProvider",
    "StoreIdentity",
    "discover_identities",
    "english_error_hint",
    "identity_by_thumbprint",
    "list_keychain_identities",
    "list_windows_identities",
    "load_selected_identity",
    "optional_parameters",
    "required_parameters",
    "save_selected_identity",
]
