"""Qualified-certificate discovery in the platform key stores.

Both platforms enumerate identities the OS considers usable for TLS client
auth — certificate + private key present, ``clientAuth`` EKU, not expired —
including token/cloud-HSM ones surfaced through their middleware (SafeNet,
certSIGN vToken, ...):

* macOS — ``security find-identity -v -p ssl-client`` (file-based Keychain
  identities) **merged with** ``sc_auth identities`` (smartcard/CryptoTokenKit
  identities — USB tokens and cloud vTokens; ``find-identity`` cannot see
  these at all, live-verified 2026-07-12 with a certSIGN vToken);
* Windows — a PowerShell one-liner over ``Cert:\\CurrentUser\\My``.

The two macOS tools hash differently (``find-identity`` prints the
certificate's SHA-1; ``sc_auth`` prints its own identity hash), so treat
``sha1_thumbprint`` as an opaque selector that is only compared against the
same discovery output — which is all :func:`identity_by_thumbprint` does.

:attr:`StoreIdentity.bootstrap_identity` is what
:class:`~anafpy.spv.bootstrap.CurlBootstrapper` needs: the Keychain **name** on
macOS (curl's SecureTransport selects by name), the SHA-1 **thumbprint** on
Windows (Schannel's cert-store syntax). The thumbprint is the stable identifier
worth persisting — names can collide, e.g. after a renewal, which
:func:`identity_by_thumbprint` refuses on macOS where curl would pick blindly.

The user's chosen certificate is persisted as a small JSON file
(:func:`save_selected_identity` / :func:`load_selected_identity`) — a
thumbprint is an identifier, not a secret, so a plain config file is fine.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from ..exceptions import AnafConfigError

__all__ = [
    "DEFAULT_IDENTITY_PATH",
    "SelectedIdentity",
    "StoreIdentity",
    "discover_identities",
    "identity_by_thumbprint",
    "list_keychain_identities",
    "list_windows_identities",
    "load_selected_identity",
    "save_selected_identity",
]

#: Default location of the persisted certificate selection.
DEFAULT_IDENTITY_PATH = "~/.anafpy/spv-identity.json"

# `  1) C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D "MIHAI-ROBERT MALAI"`
_IDENTITY_LINE = re.compile(r"^\s*\d+\)\s+([0-9A-F]{40})\s+\"(.+)\"\s*$")

# sc_auth: `458BB1B794999991FED6B2CC44E0626389072B9D	MIHAI-ROBERT MALAI`
_SC_AUTH_LINE = re.compile(r"^([0-9A-F]{40})\s+(.+?)\s*$")

# Client Authentication EKU filter over Cert:\CurrentUser\My, emitting JSON.
# -InputObject @(...) forces a JSON *array* even for a single match (PS 5.1 has
# no -AsArray).
_WINDOWS_LIST_SCRIPT = """
$candidates = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object {
    $_.HasPrivateKey -and
    $_.NotAfter -gt (Get-Date) -and
    ($eku = $_.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' }) -and
    ($eku.EnhancedKeyUsages | Where-Object { $_.Value -eq '1.3.6.1.5.5.7.3.2' })
} | ForEach-Object {
    [pscustomobject]@{
        name = $_.GetNameInfo('SimpleName', $false)
        thumbprint = $_.Thumbprint
        issuer = $_.Issuer
        not_after = $_.NotAfter.ToString('yyyy-MM-dd')
    }
}
ConvertTo-Json -InputObject @($candidates)
"""


class StoreIdentity(BaseModel):
    """One usable TLS-client identity in a platform key store."""

    name: str
    sha1_thumbprint: str
    platform: Literal["darwin", "win32"]
    #: Filled on Windows; macOS's ``find-identity`` output does not carry it.
    issuer: str | None = None
    not_after: str | None = None
    #: macOS: the identity came from ``sc_auth`` (smartcard / CryptoTokenKit —
    #: USB token or cloud vToken) rather than a file-based keychain.
    token_backed: bool = False

    @property
    def bootstrap_identity(self) -> str:
        """The ``--cert`` selector for :class:`~anafpy.spv.bootstrap.CurlBootstrapper`:
        the Keychain name on macOS, the thumbprint on Windows."""
        return self.name if self.platform == "darwin" else self.sha1_thumbprint


class SelectedIdentity(BaseModel):
    """The persisted certificate choice (``spv_select_certificate`` / CLI)."""

    name: str
    sha1_thumbprint: str
    platform: Literal["darwin", "win32"]

    @property
    def bootstrap_identity(self) -> str:
        return self.name if self.platform == "darwin" else self.sha1_thumbprint


def discover_identities() -> list[StoreIdentity]:
    """Usable TLS-client identities in this platform's key store.

    Raises:
        AnafConfigError: unsupported platform, or the platform tool failed.
    """
    if sys.platform == "darwin":
        return list_keychain_identities()
    if sys.platform == "win32":
        return list_windows_identities()
    raise AnafConfigError(
        "SPV certificate discovery supports macOS (Keychain) and Windows "
        f"(CertStore); not {sys.platform!r}"
    )


# --- macOS ------------------------------------------------------------------------


def list_keychain_identities() -> list[StoreIdentity]:
    """Valid TLS-client identities on macOS: Keychain **and** smartcard/CTK.

    ``security find-identity`` only sees file-based keychains; the token-backed
    identities that actually hold qualified certificates come from ``sc_auth``.

    Raises:
        AnafConfigError: the ``security`` tool failed or is unavailable
            (``sc_auth`` failures are tolerated — no smartcard stack is fine).
    """
    stdout = _run_discovery_tool(
        ["/usr/bin/security", "find-identity", "-v", "-p", "ssl-client"]
    )
    identities = parse_find_identity_output(stdout)
    try:
        sc_stdout = _run_discovery_tool(["/usr/sbin/sc_auth", "identities"])
    except AnafConfigError:
        sc_stdout = ""  # no smartcard subsystem / no tokens — not an error
    seen = {identity.sha1_thumbprint for identity in identities}
    identities += [
        identity
        for identity in parse_sc_auth_output(sc_stdout)
        if identity.sha1_thumbprint not in seen
    ]
    return identities


def parse_find_identity_output(stdout: str) -> list[StoreIdentity]:
    """Parse ``security find-identity -v`` output (separated for testability)."""
    identities = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        if match := _IDENTITY_LINE.match(line):
            thumbprint, name = match.group(1), match.group(2)
            if thumbprint not in seen:  # the tool may list a keychain twice
                seen.add(thumbprint)
                identities.append(
                    StoreIdentity(
                        name=name, sha1_thumbprint=thumbprint, platform="darwin"
                    )
                )
    return identities


def parse_sc_auth_output(stdout: str) -> list[StoreIdentity]:
    """Parse ``sc_auth identities`` output (separated for testability).

    The output mixes headers (``SmartCard: ...``, ``Unpaired identities:``)
    with ``<40-hex-hash>\\t<name>`` identity lines; only the latter match.
    """
    identities = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        if match := _SC_AUTH_LINE.match(line.strip()):
            thumbprint, name = match.group(1), match.group(2)
            if thumbprint not in seen:
                seen.add(thumbprint)
                identities.append(
                    StoreIdentity(
                        name=name,
                        sha1_thumbprint=thumbprint,
                        platform="darwin",
                        token_backed=True,
                    )
                )
    return identities


# --- Windows ----------------------------------------------------------------------


def list_windows_identities() -> list[StoreIdentity]:
    """Valid client-auth identities in ``Cert:\\CurrentUser\\My``.

    Raises:
        AnafConfigError: PowerShell failed or emitted an unrecognisable shape.
    """
    stdout = _run_discovery_tool(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _WINDOWS_LIST_SCRIPT,
        ]
    )
    return parse_windows_identities(stdout)


def parse_windows_identities(json_text: str) -> list[StoreIdentity]:
    """Parse the discovery script's JSON output (separated for testability)."""
    try:
        data = json.loads(json_text or "[]")
    except ValueError as exc:
        raise AnafConfigError(
            f"unrecognised certificate listing from PowerShell: {json_text[:200]!r}"
        ) from exc
    if isinstance(data, dict):  # a single certificate may serialize unwrapped
        data = [data]
    identities = []
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        try:
            identities.append(
                StoreIdentity(
                    name=str(entry["name"]),
                    sha1_thumbprint=str(entry["thumbprint"]).upper(),
                    platform="win32",
                    issuer=str(entry["issuer"]) if entry.get("issuer") else None,
                    not_after=str(entry["not_after"])
                    if entry.get("not_after")
                    else None,
                )
            )
        except KeyError as exc:
            raise AnafConfigError(
                f"certificate listing entry missing {exc}: {entry!r}"
            ) from exc
    return identities


# --- shared -----------------------------------------------------------------------


def _run_discovery_tool(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=60, check=False
        )
    except OSError as exc:
        raise AnafConfigError(f"cannot run {command[0]}: {exc}") from exc
    if result.returncode != 0:
        raise AnafConfigError(
            f"{command[0]} failed: {result.stderr.strip() or result.stdout[:200]}"
        )
    return result.stdout


def identity_by_thumbprint(thumbprint: str) -> StoreIdentity:
    """Resolve a thumbprint to its identity in this platform's store.

    Raises:
        AnafConfigError: no identity with that thumbprint; or (macOS only) its
            name is shared by another identity — curl selects by name there, so
            an ambiguous name could silently pick the wrong certificate.
    """
    wanted = thumbprint.replace(":", "").replace(" ", "").upper()
    identities = discover_identities()
    matches = [i for i in identities if i.sha1_thumbprint == wanted]
    if not matches:
        raise AnafConfigError(
            f"no usable identity with thumbprint {wanted} — list the available "
            "ones and select again"
        )
    identity = matches[0]
    namesakes = [
        i
        for i in identities
        if i.platform == "darwin"
        and i.name == identity.name
        and i.sha1_thumbprint != wanted
    ]
    if namesakes:
        raise AnafConfigError(
            f"the Keychain holds {len(namesakes) + 1} identities named "
            f"{identity.name!r} (e.g. a renewed certificate next to the old "
            "one) — curl selects by name, so remove or rename the stale one "
            "in Keychain Access before using SPV"
        )
    return identity


def load_selected_identity(
    path: str | os.PathLike[str] = DEFAULT_IDENTITY_PATH,
) -> SelectedIdentity | None:
    """The persisted certificate selection, or ``None`` when none was made.

    Raises:
        AnafConfigError: the file exists but cannot be read or parsed.
    """
    file = Path(path).expanduser()
    if not file.exists():
        return None
    try:
        return SelectedIdentity.model_validate_json(file.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise AnafConfigError(
            f"unreadable SPV identity selection {file}: {exc} — delete it and "
            "select a certificate again"
        ) from exc


def save_selected_identity(
    identity: StoreIdentity | SelectedIdentity,
    path: str | os.PathLike[str] = DEFAULT_IDENTITY_PATH,
) -> SelectedIdentity:
    """Persist the certificate choice; returns what was saved."""
    selected = SelectedIdentity(
        name=identity.name,
        sha1_thumbprint=identity.sha1_thumbprint,
        platform=identity.platform,
    )
    file = Path(path).expanduser()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(selected.model_dump_json(indent=2), encoding="utf-8")
    return selected
