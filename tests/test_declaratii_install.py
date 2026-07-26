"""Tests for the managed DUKIntegrator installer — feed parse, convergence, D406T.

Credential-free: every download is respx-mocked, dists are assembled in tmp
dirs. The live one-form install smoke lives in ``test_declaratii_live.py``.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
import respx

from anafpy.declaratii.install import (
    FEED_URL,
    MANIFEST_NAME,
    SAFT_ZIP_URL,
    DukInstaller,
    _download_url,
    default_duk_dir,
    parse_feed,
)
from anafpy.exceptions import AnafConfigError, AnafResponseError

_BASE = "http://static.anaf.ro/static/10/Anaf/update5"

_FORM_ENTRY = """<{form}>
  <versiuneJ>{version}</versiuneJ>
  <versiuneP>P1.0.0</versiuneP>
  <JURL>{base}/{form}_1/{form}Validator.jar</JURL>
  <PURL>{base}/{form}_1/{form}Pdf.jar</PURL>
  <DURL>{base}/{form}_1/{form}IstoriaVersiunilor.txt</DURL>
</{form}>"""


def _feed_xml(*forms: tuple[str, str], core: str = "1.4.18.3.3") -> str:
    """A ``versiuni.xml`` body in the live shape (integrator + declaratii)."""
    entries = "".join(
        _FORM_ENTRY.format(form=form, version=version, base=_BASE)
        for form, version in forms
    )
    return f"""<versiuni>
      <integrator>
        <versiune>{core}</versiune>
        <iJars><jarURL>{_BASE}/ii/iText-5.0.4.jar</jarURL></iJars>
        <sJars><jarURL>{_BASE}/ss8/DecValidation.jar</jarURL></sJars>
        <zJars>
          <jarURL>{_BASE}/zz9/DUKIntegrator.jar</jarURL>
          <jarURL>{_BASE}/zz9/ajutor.chm</jarURL>
        </zJars>
        <dJars><jarURL>{_BASE}/dd5/Download.jar</jarURL></dJars>
        <cFisiere><fisierURL>{_BASE}/cc2/config.properties</fisierURL></cFisiere>
      </integrator>
      <declaratii>{entries}</declaratii>
    </versiuni>"""


def _mock_downloads(*forms: str, core: str = "1.4.18.3.3") -> None:
    """Register the feed and every file a *forms* install needs (https URLs)."""
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(
            200, text=_feed_xml(*((form, "J1.0.0") for form in forms), core=core)
        )
    )
    https = _BASE.replace("http://", "https://")
    for name in (
        "ii/iText-5.0.4.jar",
        "ss8/DecValidation.jar",
        "zz9/DUKIntegrator.jar",
    ):
        respx.get(f"{https}/{name}").mock(
            return_value=httpx.Response(200, content=name.encode())
        )
    respx.get(f"{https}/cc2/config.properties").mock(
        return_value=httpx.Response(200, content=b"proxy=auto\n")
    )
    for form in forms:
        for suffix in ("Validator.jar", "Pdf.jar", "IstoriaVersiunilor.txt"):
            respx.get(f"{https}/{form}_1/{form}{suffix}").mock(
                return_value=httpx.Response(200, content=f"{form}{suffix}".encode())
            )


# -- feed parsing ------------------------------------------------------------------


def test_parse_feed_full_shape() -> None:
    feed = parse_feed(_feed_xml(("D300", "J12.0.1"), ("D112", "J26.0.3")))
    assert feed.core_version == "1.4.18.3.3"
    # zJars keeps only jars (the .chm help file is skipped); dJars is ignored.
    assert feed.root_jars == [f"{_BASE}/zz9/DUKIntegrator.jar"]
    assert [Path(url).name for url in feed.lib_jars] == [
        "DecValidation.jar",
        "iText-5.0.4.jar",
    ]
    assert feed.config_files == [f"{_BASE}/cc2/config.properties"]
    assert set(feed.forms) == {"D300", "D112"}
    entry = feed.forms["D300"]
    assert entry.validator_version == "J12.0.1"
    assert entry.validator_url.endswith("D300Validator.jar")
    assert entry.pdf_url and entry.pdf_url.endswith("D300Pdf.jar")
    assert entry.history_url and entry.history_url.endswith("IstoriaVersiunilor.txt")
    assert feed.validator_versions == {"D300": "J12.0.1", "D112": "J26.0.3"}


def test_parse_feed_garbage_is_empty() -> None:
    for text in ("", "   ", "not xml <<<"):
        feed = parse_feed(text)
        assert feed.forms == {}
        assert feed.root_jars == []


def test_download_url_upgrades_and_pins_host() -> None:
    assert (
        _download_url("http://static.anaf.ro/static/x/y.jar")
        == "https://static.anaf.ro/static/x/y.jar"
    )
    with pytest.raises(AnafResponseError, match="unexpected host"):
        _download_url("https://evil.example/y.jar")


def test_default_duk_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    managed = tmp_path / "managed"
    monkeypatch.setattr("anafpy.declaratii.install.MANAGED_DUK_DIR", managed)
    assert default_duk_dir() is None
    managed.mkdir()
    (managed / "DUKIntegrator.jar").write_text("")
    assert default_duk_dir() == managed


# -- install / convergence ---------------------------------------------------------


@respx.mock
async def test_install_assembles_dist_from_feed(tmp_path: Path) -> None:
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    report = await DukInstaller(dist).install(["D300"])

    assert (dist / "DUKIntegrator.jar").read_bytes() == b"zz9/DUKIntegrator.jar"
    assert (dist / "lib" / "DecValidation.jar").exists()
    assert (dist / "lib" / "iText-5.0.4.jar").exists()
    assert (dist / "config" / "config.properties").read_bytes() == b"proxy=auto\n"
    assert not (dist / "ajutor.chm").exists()
    assert (dist / "lib" / "D300Validator.jar").read_bytes() == b"D300Validator.jar"
    assert (dist / "lib" / "D300Pdf.jar").exists()
    assert (dist / "lib" / "D300IstoriaVersiunilor.txt").exists()

    manifest = json.loads((dist / MANIFEST_NAME).read_text())
    assert manifest["core_version"] == "1.4.18.3.3"
    assert manifest["forms"] == {"D300": "J1.0.0"}
    recorded = manifest["files"]["lib/D300Validator.jar"]
    assert recorded["url"].startswith("https://static.anaf.ro/")
    assert recorded["sha256"] == hashlib.sha256(b"D300Validator.jar").hexdigest()

    assert report.forms_installed == {"D300": "J1.0.0"}
    assert "lib/D300Validator.jar" in report.updated_files


@respx.mock
async def test_install_is_convergent(tmp_path: Path) -> None:
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    await DukInstaller(dist).install(["D300"])
    report = await DukInstaller(dist).install(["D300"])
    assert report.updated_files == []
    assert report.forms_installed == {}
    assert report.forms_current == {"D300": "J1.0.0"}


@respx.mock
async def test_install_refreshes_on_version_bump(tmp_path: Path) -> None:
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    await DukInstaller(dist).install(["D300"])
    # ANAF publishes a new validator: same URLs, bumped versiuneJ.
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(200, text=_feed_xml(("D300", "J2.0.0")))
    )
    report = await DukInstaller(dist).install(["D300"])
    assert report.forms_installed == {"D300": "J2.0.0"}
    manifest = json.loads((dist / MANIFEST_NAME).read_text())
    assert manifest["forms"] == {"D300": "J2.0.0"}


@respx.mock
async def test_install_repairs_a_corrupted_file(tmp_path: Path) -> None:
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    await DukInstaller(dist).install(["D300"])
    (dist / "lib" / "D300Validator.jar").write_bytes(b"bit rot")
    report = await DukInstaller(dist).install(["D300"])
    assert report.forms_installed == {"D300": "J1.0.0"}
    assert (dist / "lib" / "D300Validator.jar").read_bytes() == b"D300Validator.jar"


@respx.mock
async def test_bare_install_adopts_and_converges_existing_lib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A hand-assembled dist (no manifest) is refreshed wholesale: the lib scan
    # brings its forms into the target set alongside the preinstall defaults.
    monkeypatch.setattr("anafpy.declaratii.install.PREINSTALL_FORMS", ("D300",))
    _mock_downloads("D300", "D112")
    dist = tmp_path / "dist"
    (dist / "lib").mkdir(parents=True)
    (dist / "lib" / "D112Validator.jar").write_bytes(b"stale hand-installed jar")
    report = await DukInstaller(dist).install()
    assert set(report.forms_installed) == {"D300", "D112"}
    assert (dist / "lib" / "D112Validator.jar").read_bytes() == b"D112Validator.jar"


@respx.mock
async def test_bare_install_notes_unknown_installed_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("anafpy.declaratii.install.PREINSTALL_FORMS", ("D300",))
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    (dist / "lib").mkdir(parents=True)
    (dist / "lib" / "X999Validator.jar").write_bytes(b"who knows")
    report = await DukInstaller(dist).install()
    assert report.forms_installed == {"D300": "J1.0.0"}
    assert any("X999" in note for note in report.notes)


@respx.mock
async def test_explicit_unknown_form_raises(tmp_path: Path) -> None:
    _mock_downloads("D300")
    with pytest.raises(AnafConfigError, match="D999"):
        await DukInstaller(tmp_path / "dist").install(["D999"])


@respx.mock
async def test_empty_feed_refuses_to_assemble(tmp_path: Path) -> None:
    respx.get(FEED_URL).mock(return_value=httpx.Response(200, text="not xml <<<"))
    with pytest.raises(AnafResponseError, match="core jars"):
        await DukInstaller(tmp_path / "dist").install(["D300"])


# -- D406T (the duk_SAFT special case) ---------------------------------------------


def _saft_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("dist/lib/D406TValidator.jar", b"t-validator")
        bundle.writestr("dist/lib/D406TPdf.jar", b"t-pdf")
        bundle.writestr("dist/lib/D406TIstoriaVersiunilor.txt", "J2.0.6\nolder\n")
        bundle.writestr("dist/Instructiuni.txt", "ignored")
    return buffer.getvalue()


@respx.mock
async def test_explicit_d406t_extracts_from_saft_zip(tmp_path: Path) -> None:
    _mock_downloads()
    respx.get(SAFT_ZIP_URL).mock(return_value=httpx.Response(200, content=_saft_zip()))
    dist = tmp_path / "dist"
    report = await DukInstaller(dist).install(["D406T"])
    assert (dist / "lib" / "D406TValidator.jar").read_bytes() == b"t-validator"
    assert (dist / "lib" / "D406TPdf.jar").read_bytes() == b"t-pdf"
    assert not (dist / "Instructiuni.txt").exists()
    assert report.forms_installed == {"D406T": "J2.0.6"}
    manifest = json.loads((dist / MANIFEST_NAME).read_text())
    assert manifest["forms"]["D406T"] == "J2.0.6"
    assert manifest["files"]["lib/D406TValidator.jar"]["url"].endswith(
        "#D406TValidator.jar"
    )
    # A second explicit run is convergent — the ~91 MB zip is not re-fetched
    # (respx would raise on an unexpected second request if it were counted;
    # assert via the report instead since the route stays registered).
    second = await DukInstaller(dist).install(["D406T"])
    assert second.forms_installed == {}
    assert second.forms_current == {"D406T": "J2.0.6"}


@respx.mock
async def test_bare_install_never_downloads_the_saft_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The SAFT zip route is deliberately NOT mocked: touching it would fail.
    monkeypatch.setattr("anafpy.declaratii.install.PREINSTALL_FORMS", ("D300",))
    _mock_downloads("D300")
    dist = tmp_path / "dist"
    (dist / "lib").mkdir(parents=True)
    (dist / "lib" / "D406TValidator.jar").write_bytes(b"hand-installed")
    report = await DukInstaller(dist).install()
    assert any("D406T" in note for note in report.notes)
    assert (dist / "lib" / "D406TValidator.jar").read_bytes() == b"hand-installed"
