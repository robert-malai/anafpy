"""Tests for certificate discovery parsing and the persisted selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from anafpy.exceptions import AnafConfigError
from anafpy.spv import (
    StoreIdentity,
    load_selected_identity,
    save_selected_identity,
)
from anafpy.spv.certs import parse_windows_identities

WINDOWS_JSON = """
[
  {
    "name": "MIHAI-ROBERT MALAI",
    "thumbprint": "c5e18ab56b0ac30a05be8d526610f17bb2ef9e7d",
    "issuer": "CN=certSIGN Qualified 2023 RSA CA, O=CERTSIGN SA, C=RO",
    "not_after": "2029-06-26"
  }
]
"""


# --- Windows listing parsing --------------------------------------------------------


def test_windows_listing_parses_and_uppercases_the_thumbprint() -> None:
    (identity,) = parse_windows_identities(WINDOWS_JSON)
    assert identity.platform == "win32"
    assert identity.sha1_thumbprint == "C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D"
    assert identity.bootstrap_identity == identity.sha1_thumbprint
    assert identity.issuer is not None and "certSIGN" in identity.issuer


def test_windows_listing_accepts_a_single_unwrapped_object() -> None:
    single = WINDOWS_JSON.strip().removeprefix("[").removesuffix("]")
    (identity,) = parse_windows_identities(single)
    assert identity.name == "MIHAI-ROBERT MALAI"


def test_windows_listing_empty_output_is_no_identities() -> None:
    assert parse_windows_identities("") == []
    assert parse_windows_identities("[]") == []


def test_windows_listing_junk_is_a_config_error() -> None:
    with pytest.raises(AnafConfigError, match="unrecognised certificate listing"):
        parse_windows_identities("PowerShell exploded")


def test_windows_listing_missing_key_is_explicit() -> None:
    with pytest.raises(AnafConfigError, match="missing"):
        parse_windows_identities('[{"name": "x"}]')


# --- identity selection persistence ---------------------------------------------------


def test_selection_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "spv-identity.json"
    assert load_selected_identity(path) is None
    identity = StoreIdentity(
        name="MIHAI-ROBERT MALAI",
        sha1_thumbprint="C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D",
        platform="darwin",
    )
    saved = save_selected_identity(identity, path)
    assert saved.bootstrap_identity == "MIHAI-ROBERT MALAI"  # macOS: curl by name
    loaded = load_selected_identity(path)
    assert loaded is not None
    assert loaded.sha1_thumbprint == identity.sha1_thumbprint


def test_selection_corrupt_file_is_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "spv-identity.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AnafConfigError, match="unreadable SPV identity selection"):
        load_selected_identity(path)


def test_bootstrap_identity_is_thumbprint_on_windows() -> None:
    identity = StoreIdentity(name="X", sha1_thumbprint="AB" * 20, platform="win32")
    assert identity.bootstrap_identity == "AB" * 20


# --- macOS listing parsing -----------------------------------------------------------


def test_find_identity_output_parses_and_dedupes() -> None:
    from anafpy.spv.certs import parse_find_identity_output

    out = (
        '  1) BB93F47DDCC6A6536F4CDF8F31B27596B335E219 "127.0.0.1"\n'
        '  2) BB93F47DDCC6A6536F4CDF8F31B27596B335E219 "127.0.0.1"\n'
        "     2 valid identities found\n"
    )
    identities = parse_find_identity_output(out)
    assert len(identities) == 1
    assert identities[0].token_backed is False


def test_sc_auth_output_yields_token_backed_identities() -> None:
    from anafpy.spv.certs import parse_sc_auth_output

    out = (
        "SmartCard: ro.certsign.vtoken.ctke:ADDADECADECAFEFEEDABEEFEDBADBABE\n"
        "Unpaired identities:\n"
        "458BB1B794999991FED6B2CC44E0626389072B9D\tMIHAI-ROBERT MALAI\n"
    )
    (identity,) = parse_sc_auth_output(out)
    assert identity.name == "MIHAI-ROBERT MALAI"
    assert identity.token_backed is True
    assert identity.bootstrap_identity == "MIHAI-ROBERT MALAI"  # curl by name


def test_sc_auth_output_empty_or_headers_only() -> None:
    from anafpy.spv.certs import parse_sc_auth_output

    assert parse_sc_auth_output("") == []
    assert parse_sc_auth_output("SmartCard: x\nUnpaired identities:\n") == []
