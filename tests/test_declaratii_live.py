"""Opt-in live smoke for the declaration pipeline (skipped by default).

Runs the real DUKIntegrator ``-v`` + ``-p`` on the validated nil D300 fixture
(Appendix C of the plan) — needs a local DUK install:

    ANAFPY_LIVE=1 ANAFPY_DUK_DIR=/path/to/dist uv run pytest -m live \\
        tests/test_declaratii_live.py

The signing leg additionally requires ``ANAFPY_LIVE_SIGN=1`` (it fires a REAL
certificate 2FA approval, so it must never ride along with a normal live run)
and macOS. Filing is out of scope — nothing is sent to ANAF here.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from anafpy.declaratii import DukIntegrator

pytestmark = pytest.mark.live

# The validated nil D300 (06/2026, XSD v12) — `Validare fara erori` 2026-07-15.
_D300_NIL = b"""<?xml version="1.0" encoding="UTF-8"?>
<declaratie300 xmlns="mfp:anaf:dgti:d300:declaratie:v12"
  luna="6" an="2026" depusReprezentant="0" bifa_interne="1" temei="0"
  nume_declar="Popescu" prenume_declar="Ion" functie_declar="Administrator"
  cui="12345674" den="TEST SPIKE SRL" adresa="Str. Exemplu nr. 1, Bucuresti"
  banca="-" cont="-" caen="6201" tip_decont="L" pro_rata="100.0"
  bifa_cereale="N" bifa_mob="N" bifa_disp="N" bifa_cons="N"
  solicit_ramb="N" nr_evid="10301010626250726000042" totalPlata_A="0"/>
"""


def _duk() -> DukIntegrator:
    duk_dir = os.environ.get("ANAFPY_DUK_DIR")
    if not duk_dir:
        pytest.skip("set ANAFPY_DUK_DIR to a DUKIntegrator dist/ folder")
    return DukIntegrator(Path(duk_dir))


async def test_live_validate_nil_d300() -> None:
    result = await _duk().validate("D300", _D300_NIL)
    assert result.ok, result.raw


async def test_live_render_nil_d300(tmp_path: Path) -> None:
    pdf = tmp_path / "d300.pdf"
    result = await _duk().render("D300", _D300_NIL, pdf)
    assert result.ok, result.raw
    assert pdf.exists() and pdf.read_bytes().startswith(b"%PDF")


# Real production index/CUI pair (the maintainer's own F4109 filings) — StareD112
# is public, no-auth, read-only, so a prod query is within the live-testing
# boundaries. Re-confirms the wire shapes captured 2026-07-16.
_STARE_INDEX = "1100000001"
_STARE_CUI = "99999909"


async def test_live_stared112_status_and_recipisa(tmp_path: Path) -> None:
    from anafpy.declaratii import DeclarationStatusClient

    async with DeclarationStatusClient() as client:
        result = await client.check_status(_STARE_INDEX, _STARE_CUI)
        assert result.found, result.message
        queried = result.document(_STARE_INDEX)
        assert queried is not None
        assert queried.form
        assert queried.upload_date is not None
        if queried.receipt_available:
            pdf = await client.download_receipt(_STARE_INDEX)
            assert pdf is not None and pdf.startswith(b"%PDF")
        # The not-found business outcome (bogus pair) must be returned, not raised.
        missing = await client.check_status("9999999999", "9999999999")
        assert missing.found is False


@pytest.mark.skipif(
    os.environ.get("ANAFPY_LIVE_SIGN") != "1",
    reason="signing fires a real 2FA — set ANAFPY_LIVE_SIGN=1 to run it",
)
async def test_live_sign_nil_d300(tmp_path: Path) -> None:
    import sys

    if sys.platform != "darwin":
        pytest.skip("signing is macOS-only in this release")
    from anafpy.declaratii import pdfsign
    from anafpy.declaratii.signing import KeychainRawSigner, resolve_signing_label

    pdf = tmp_path / "d300.pdf"
    assert (await _duk().render("D300", _D300_NIL, pdf)).ok
    signer = KeychainRawSigner(resolve_signing_label())
    result = await pdfsign.sign_pdf(pdf.read_bytes(), signer)
    assert result.pdf.startswith(b"%PDF")
    (tmp_path / "d300-semnat.pdf").write_bytes(result.pdf)
