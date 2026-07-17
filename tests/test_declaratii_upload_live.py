"""Live D406T pipeline: validate → render → sign → **file on the real portal**.

D406T is ANAF's **sanctioned no-effect test filing**: the SAF-T voluntary
testing programme accepts it on the production "Depunere declarații" portal
with no legal or fiscal effect (data excluded from risk analyses and deleted
after the verification report) — see the portal-upload reference §5. That makes
this the one live test allowed to file against **production**: it exists to
capture the portal's successful-upload response (deliberately unobserved so
far, reference §4), to prove the pyHanko CMS signature is accepted, and to
check whether StareD112 tracks a D406T upload index.

Gating mirrors the signing test's: the full filing leg needs macOS, a DUK
install with the **D406T** jars (``ANAFPY_DUK_DIR``; the T jars ship in ANAF's
``duk_SAFT`` distribution, not the ``versiuni.xml`` feed), a selected Keychain
identity, and **fires the certificate 2FA twice** (sign + portal login), so it
hides behind its own opt-in:

    ANAFPY_LIVE=1 ANAFPY_LIVE_FILE_D406T=1 uv run pytest -q -m live \\
        tests/test_declaratii_upload_live.py -s

The validate/render leg runs under plain ``ANAFPY_LIVE=1`` (local subprocess,
nothing filed, no 2FA).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from anafpy.declaratii import DukIntegrator

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ANAFPY_LIVE") != "1",
        reason="live ANAF tests are opt-in (set ANAFPY_LIVE=1)",
    ),
]

_FIXTURE = Path(__file__).parent / "fixtures" / "declaratii" / "d406t-minimal.xml"


def _d406t_xml() -> bytes:
    """The minimal valid D406T, with the filer CUI from the environment.

    The committed fixture carries a synthetic filer CUI (``RO88888808``), so
    ``ANAFPY_CIF`` is required: the substituted value makes the filing belong
    to the certificate holder's company (StareD112 keys on the (index, CUI)
    pair).
    """
    cif = os.environ.get("ANAFPY_CIF")
    if not cif:
        pytest.skip("set ANAFPY_CIF to the certificate holder's CUI")
    return _FIXTURE.read_bytes().replace(b"RO88888808", b"RO" + cif.encode())


def _duk() -> DukIntegrator:
    duk_dir = os.environ.get("ANAFPY_DUK_DIR")
    if not duk_dir:
        pytest.skip("set ANAFPY_DUK_DIR to a DUKIntegrator dist/ folder")
    duk = DukIntegrator(Path(duk_dir))
    if "D406T" not in duk.installed_forms():
        pytest.skip(
            "the DUK install has no D406T module — drop D406TValidator.jar and "
            "D406TPdf.jar from ANAF's duk_SAFT distribution into its lib/ "
            "(see the DUK reference)"
        )
    return duk


async def test_live_validate_and_render_d406t(tmp_path: Path) -> None:
    duk = _duk()
    result = await duk.validate("D406T", _d406t_xml())
    assert result.ok, result.raw
    pdf = tmp_path / "d406t.pdf"
    render = await duk.render("D406T", _d406t_xml(), pdf)
    assert render.ok, render.raw
    assert pdf.exists() and pdf.read_bytes().startswith(b"%PDF")


@pytest.mark.skipif(
    os.environ.get("ANAFPY_LIVE_FILE_D406T") != "1",
    reason="files a D406T on the PRODUCTION portal and fires the certificate "
    "2FA twice — set ANAFPY_LIVE_FILE_D406T=1 to run it",
)
async def test_live_file_d406t_on_portal(tmp_path: Path) -> None:
    if sys.platform != "darwin":
        pytest.skip("signing and the portal bootstrap are macOS-only for now")
    from anafpy.declaratii import (
        DeclarationStatusClient,
        DeclarationUploadClient,
        KeychainRawSigner,
        PortalCurlBootstrapper,
        pdfsign,
    )
    from anafpy.declaratii.signing import resolve_signing_label

    duk = _duk()
    xml = _d406t_xml()
    assert (await duk.validate("D406T", xml)).ok

    pdf_path = tmp_path / "d406t.pdf"
    assert (await duk.render("D406T", xml, pdf_path)).ok, "DUK render failed"

    # 2FA #1: the qualified signature.
    identity = resolve_signing_label()
    signed = await pdfsign.sign_pdf(pdf_path.read_bytes(), KeychainRawSigner(identity))
    assert signed.pdf.startswith(b"%PDF")
    (tmp_path / "d406t-semnat.pdf").write_bytes(signed.pdf)

    # 2FA #2: the portal certificate login, then the one multipart POST.
    async with DeclarationUploadClient(
        bootstrapper=PortalCurlBootstrapper(identity)
    ) as client:
        await client.login()
        result = await client.upload(signed.pdf, filename="d406t.pdf")
        await client.logout()

    print(f"\naccepted={result.accepted} index={result.upload_index}")
    assert result.accepted is not False, (
        f"the portal REJECTED the upload: {result.reason!r} — if the reason "
        "points at the signature, the pyHanko CMS shape is the suspect"
    )

    # Persist the raw response — the point of this filing is to observe the
    # success page (reference §4); only AFTER the outcome assertions pass, so a
    # rejected/unexpected re-run never clobbers the committed success capture.
    capture = (
        Path(__file__).parent.parent
        / "docs/anaf-reference/_sources/decl-portal/upload-response-d406t.html"
    )
    capture.write_text(result.html, encoding="utf-8")
    print(f"portal response captured to {capture}")

    if result.upload_index and (cif := os.environ.get("ANAFPY_CIF")):
        async with DeclarationStatusClient() as status:
            listing = await status.check_status(result.upload_index, cif)
        print(f"StareD112: found={listing.found}")
        if listing.found and (doc := listing.document(result.upload_index)):
            print(f"StareD112 state: {doc.state_text!r} (form {doc.form!r})")
