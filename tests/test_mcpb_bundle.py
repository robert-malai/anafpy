"""Tripwires on the extension bundle's builder, which no gate otherwise runs.

``scripts/build_mcpb.py`` only executes on a native release runner, so the
parts that *are* checkable from any host are checked here: the generated
manifest's content (CI schema-validates it, which says nothing about whether
the right variables are in it) and the curl pin's shape. What stays unverified
until a Windows build runs is the compile itself.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).parent.parent


def _build_mcpb() -> ModuleType:
    """Import the builder by path — ``scripts/`` is not an importable package."""
    path = _ROOT / "scripts" / "build_mcpb.py"
    spec = importlib.util.spec_from_file_location("build_mcpb", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: the module's `from __future__ import annotations`
    # leaves the Target dataclass's field types as strings, and dataclasses
    # resolves them through sys.modules[cls.__module__].
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build_mcpb() -> ModuleType:
    return _build_mcpb()


def test_only_windows_bundles_a_curl(build_mcpb: ModuleType) -> None:
    # macOS's /usr/bin/curl is a working SecureTransport build; Windows ships
    # the curl the certificate logins trip over, so only that target pays the
    # compile (and the megabytes).
    bundling = {
        name: target.bundled_curl
        for name, target in build_mcpb._targets("3.13").items()
        if target.bundled_curl
    }
    assert bundling == {"win32-x64": "server/curl/curl.exe"}


def test_windows_manifest_names_the_bundled_curl(build_mcpb: ModuleType) -> None:
    targets = build_mcpb._targets("3.13")
    env = build_mcpb.manifest("1.2.3", targets["win32-x64"])["server"]["mcp_config"][
        "env"
    ]
    assert env["ANAFPY_BUNDLED_CURL"] == "${__dirname}/server/curl/curl.exe"
    # The user's own override is a SEPARATE variable and still wins in
    # default_curl_path — an empty setting must not erase the bundled path.
    assert env["ANAFPY_CURL"] == "${user_config.curl_path}"


def test_macos_manifest_has_no_bundled_curl(build_mcpb: ModuleType) -> None:
    targets = build_mcpb._targets("3.13")
    env = build_mcpb.manifest("1.2.3", targets["darwin-arm64"])["server"]["mcp_config"][
        "env"
    ]
    assert "ANAFPY_BUNDLED_CURL" not in env


def test_curl_pin_is_a_release_tag_and_a_full_commit(build_mcpb: ModuleType) -> None:
    # The tag alone is not a pin (tags move); the commit is what git verifies.
    tag: str = build_mcpb.CURL_TAG
    assert tag == "curl-" + build_mcpb.CURL_VERSION.replace(".", "_")
    assert re.fullmatch(r"[0-9a-f]{40}", build_mcpb.CURL_COMMIT)


def test_bundled_curl_is_built_against_the_windows_key_store(
    build_mcpb: ModuleType,
) -> None:
    # The single property the bundled curl exists for: an OpenSSL/LibreSSL
    # build cannot present `CurrentUser\MY\<thumbprint>`.
    options: list[str] = build_mcpb.CURL_CMAKE_OPTIONS
    assert "-DCURL_USE_SCHANNEL=ON" in options
    assert "-DCURL_USE_OPENSSL=OFF" in options
