"""Tests for assembling a DUKIntegrator dist from ANAF's update feed.

Network-free: the feed and every download are respx-mocked, and the "jars" are
real (tiny) zip containers so the magic-byte guard sees what it would see live.
No Java is involved — assembly is pure fetch-and-place.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx
import pytest
import respx

from anafpy.declaratii.dukdist import (
    OUT_OF_FEED_FORMS,
    apply_offline_mode,
    install_dist,
    secure_url,
    update_dist,
)
from anafpy.exceptions import AnafConfigError, AnafResponseError, AnafTransportError

_BASE = "https://static.anaf.ro/static/10/Anaf/update5"
_FEED_URL = f"{_BASE}/versiuni.xml"


def _jar(name: str = "x.class") -> bytes:
    """A real (tiny) zip container — what the magic-byte guard expects of a jar."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, "")
    return buffer.getvalue()


def _feed(*forms: tuple[str, str]) -> str:
    """A ``versiuni.xml`` in the live shape: core + config + per-form entries."""
    entries = "".join(
        f"<{form}><versiuneJ>{version}</versiuneJ><versiuneP>P1.0.0</versiuneP>"
        f"<JURL>http://static.anaf.ro/static/10/Anaf/update5/{form}_1/"
        f"{form}Validator.jar</JURL>"
        f"<PURL>http://static.anaf.ro/static/10/Anaf/update5/{form}_1/"
        f"{form}Pdf.jar</PURL>"
        f"<DURL>http://static.anaf.ro/static/10/Anaf/update5/{form}_1/"
        f"{form}IstoriaVersiunilor.txt</DURL></{form}>"
        for form, version in forms
    )
    return (
        "<versiuni><integrator><versiune>1.4.18.3.3</versiune>"
        f"<iJars><jarURL>http://static.anaf.ro/static/10/Anaf/update5/ii/iText.jar"
        "</jarURL></iJars>"
        f"<sJars><jarURL>http://static.anaf.ro/static/10/Anaf/update5/ss8/"
        "DecValidation.jar</jarURL></sJars>"
        f"<zJars><jarURL>http://static.anaf.ro/static/10/Anaf/update5/zz9/"
        "DUKIntegrator.jar</jarURL>"
        f"<jarURL>http://static.anaf.ro/static/10/Anaf/update5/zz9/ajutor.chm</jarURL>"
        "</zJars>"
        f"<dJars><jarURL>http://static.anaf.ro/static/10/Anaf/update5/dd5/Download.jar"
        "</jarURL></dJars>"
        f"<cFisiere><fisierURL>http://static.anaf.ro/static/10/Anaf/update5/cc2/"
        "config.properties</fisierURL></cFisiere>"
        f"</integrator>{entries}</versiuni>"
    )


def _mock_feed(*forms: tuple[str, str]) -> None:
    """Route the feed and every file it points at."""
    respx.get(_FEED_URL).mock(return_value=httpx.Response(200, text=_feed(*forms)))
    respx.get(f"{_BASE}/zz9/DUKIntegrator.jar").mock(
        return_value=httpx.Response(200, content=_jar())
    )
    respx.get(f"{_BASE}/ii/iText.jar").mock(
        return_value=httpx.Response(200, content=_jar())
    )
    respx.get(f"{_BASE}/ss8/DecValidation.jar").mock(
        return_value=httpx.Response(200, content=_jar())
    )
    respx.get(f"{_BASE}/cc2/config.properties").mock(
        return_value=httpx.Response(200, text="proxy=auto\n")
    )
    for form, version in forms:
        respx.get(f"{_BASE}/{form}_1/{form}Validator.jar").mock(
            return_value=httpx.Response(200, content=_jar())
        )
        respx.get(f"{_BASE}/{form}_1/{form}Pdf.jar").mock(
            return_value=httpx.Response(200, content=_jar())
        )
        respx.get(f"{_BASE}/{form}_1/{form}IstoriaVersiunilor.txt").mock(
            return_value=httpx.Response(
                200,
                text=f"19-Oct-2011 publicat versiunea de test J1.0.0\n"
                f"11-Feb-2026\n\t- publicat versiunea {version}, modificare\n",
            )
        )


# -- secure_url --------------------------------------------------------------------


def test_secure_url_upgrades_http() -> None:
    # The feed lists plain http; TLS is the only integrity ANAF offers (no
    # checksums), so every fetch is forced onto it.
    assert (
        secure_url("http://static.anaf.ro/a/b.jar") == "https://static.anaf.ro/a/b.jar"
    )


def test_secure_url_refuses_foreign_host() -> None:
    with pytest.raises(AnafConfigError, match="refusing to download"):
        secure_url("https://evil.example.com/x.jar")


def test_secure_url_refuses_non_http_scheme() -> None:
    with pytest.raises(AnafConfigError, match="refusing to download"):
        secure_url("file:///etc/passwd")


# -- install_dist ------------------------------------------------------------------


@respx.mock
async def test_install_assembles_the_whole_dist(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    report = await install_dist(tmp_path / "dist", forms=["D300"])

    dist = tmp_path / "dist"
    # The core jar lands at the root, libraries and form jars in lib/, and
    # config/ is fetched too — its absence is what makes DUK exit silently.
    assert (dist / "DUKIntegrator.jar").exists()
    assert (dist / "lib" / "iText.jar").exists()
    assert (dist / "lib" / "DecValidation.jar").exists()
    assert (dist / "lib" / "D300Validator.jar").exists()
    assert (dist / "lib" / "D300Pdf.jar").exists()
    assert (dist / "lib" / "D300IstoriaVersiunilor.txt").exists()
    assert (dist / "config" / "config.properties").exists()
    assert report.core_version == "1.4.18.3.3"
    assert report.forms_installed == {"D300": "J12.0.1"}


@respx.mock
async def test_install_skips_the_gui_only_members(tmp_path: Path) -> None:
    # A headless dist has no use for the Windows help file or the GUI updater,
    # and fetching them would only be routed-request noise.
    _mock_feed(("D300", "J12.0.1"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    assert not (tmp_path / "dist" / "ajutor.chm").exists()
    assert not (tmp_path / "dist" / "Download.jar").exists()


@respx.mock
async def test_install_leaves_no_part_files(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    assert list((tmp_path / "dist").rglob("*.part")) == []


@respx.mock
async def test_install_sets_offline_mode(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    report = await install_dist(tmp_path / "dist", forms=["D300"], offline=True)
    config = (tmp_path / "dist" / "config" / "config.properties").read_text()
    assert "offLine=Y" in config
    assert report.offline_mode is True


@respx.mock
async def test_install_can_opt_out_of_offline_mode(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    report = await install_dist(tmp_path / "dist", forms=["D300"], offline=False)
    config = (tmp_path / "dist" / "config" / "config.properties").read_text()
    assert "offLine" not in config
    assert report.offline_mode is False


@respx.mock
async def test_install_unknown_form_raises(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    with pytest.raises(AnafConfigError, match="unknown form"):
        await install_dist(tmp_path / "dist", forms=["D999"])


@respx.mock
async def test_install_all_selects_every_feed_form(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"), ("D394", "J8.0.2"))
    report = await install_dist(tmp_path / "dist", forms=["all"])
    assert set(report.forms_installed) == {"D300", "D394"}


@respx.mock
async def test_install_refuses_a_feed_without_a_core_jar(tmp_path: Path) -> None:
    # Half a dist is worse than none: it would fail later, opaquely.
    respx.get(_FEED_URL).mock(
        return_value=httpx.Response(200, text="<versiuni><integrator/></versiuni>")
    )
    with pytest.raises(AnafConfigError, match="no core jar"):
        await install_dist(tmp_path / "dist")


# -- integrity ---------------------------------------------------------------------


@respx.mock
async def test_html_error_page_is_never_written_as_a_jar(tmp_path: Path) -> None:
    # ANAF answering 200-with-HTML must not land an "executable" in lib/ that
    # then fails as the same empty err file a broken dist produces.
    _mock_feed(("D300", "J12.0.1"))
    respx.get(f"{_BASE}/D300_1/D300Validator.jar").mock(
        return_value=httpx.Response(200, text="<html>Not found</html>")
    )
    with pytest.raises(AnafTransportError, match="did not answer a jar"):
        await install_dist(tmp_path / "dist", forms=["D300"])
    assert not (tmp_path / "dist" / "lib" / "D300Validator.jar").exists()


@respx.mock
async def test_download_failure_surfaces_as_transport_error(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    respx.get(f"{_BASE}/D300_1/D300Pdf.jar").mock(
        side_effect=httpx.ConnectError("boom")
    )
    with pytest.raises(AnafTransportError):
        await install_dist(tmp_path / "dist", forms=["D300"])


@respx.mock
async def test_download_status_error_surfaces_as_response_error(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    respx.get(f"{_BASE}/D300_1/D300Validator.jar").mock(
        return_value=httpx.Response(503)
    )
    with pytest.raises(AnafResponseError) as excinfo:
        await install_dist(tmp_path / "dist", forms=["D300"])
    assert excinfo.value.status_code == 503


# -- staleness / update ------------------------------------------------------------


@respx.mock
async def test_reinstall_skips_a_form_already_current(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    report = await install_dist(tmp_path / "dist", forms=["D300"])
    assert report.forms_unchanged == ["D300"]
    assert report.forms_installed == {}


@respx.mock
async def test_force_redownloads_a_current_form(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    report = await update_dist(tmp_path / "dist", force=True)
    assert report.forms_unchanged == []
    assert "D300" in report.forms_updated or "D300" in report.forms_installed


@respx.mock
async def test_update_reports_the_version_transition(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.0"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    respx.reset()
    _mock_feed(("D300", "J12.0.1"))
    report = await update_dist(tmp_path / "dist")
    assert report.forms_updated == {"D300": "J12.0.0 -> J12.0.1"}


@respx.mock
async def test_update_adds_a_named_form(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"), ("D394", "J8.0.2"))
    await install_dist(tmp_path / "dist", forms=["D300"])
    report = await update_dist(tmp_path / "dist", forms=["D394"])
    assert report.forms_installed == {"D394": "J8.0.2"}
    assert report.forms_unchanged == ["D300"]


async def test_update_refuses_a_directory_that_is_not_a_dist(tmp_path: Path) -> None:
    with pytest.raises(AnafConfigError, match="is not a DUKIntegrator dist"):
        await update_dist(tmp_path / "nowhere")


# -- out-of-feed forms (D406T) -----------------------------------------------------


def _saft_zip(*names: str) -> bytes:
    """A stand-in for ANAF's SAF-T distribution zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "jar-bytes")
    return buffer.getvalue()


@respx.mock
async def test_out_of_feed_form_comes_from_the_saft_zip(tmp_path: Path) -> None:
    # D406T is absent from the feed entirely; its jars ship only in the SAF-T
    # distribution. It stays fetchable so the portal-filing rediscovery path
    # is reproducible.
    _mock_feed(("D300", "J12.0.1"))
    respx.get(OUT_OF_FEED_FORMS["D406T"]).mock(
        return_value=httpx.Response(
            200,
            content=_saft_zip(
                "duk_SAFT/dist/lib/D406TValidator.jar",
                "duk_SAFT/dist/lib/D406TPdf.jar",
                "duk_SAFT/readme.txt",
            ),
        )
    )
    report = await install_dist(tmp_path / "dist", forms=["D406T"])
    lib = tmp_path / "dist" / "lib"
    # Members are matched by basename, so the archive cannot choose its own
    # destination path.
    assert (lib / "D406TValidator.jar").exists()
    assert (lib / "D406TPdf.jar").exists()
    assert not (lib / "readme.txt").exists()
    assert report.forms_installed == {"D406T": "unversioned"}


@respx.mock
async def test_out_of_feed_form_is_not_refetched_once_present(tmp_path: Path) -> None:
    # D406T has no feed version to compare against, so presence is the only
    # signal — without it every `update` would re-pull the whole SAF-T zip.
    _mock_feed(("D300", "J12.0.1"))
    route = respx.get(OUT_OF_FEED_FORMS["D406T"]).mock(
        return_value=httpx.Response(
            200, content=_saft_zip("lib/D406TValidator.jar", "lib/D406TPdf.jar")
        )
    )
    await install_dist(tmp_path / "dist", forms=["D406T"])
    report = await update_dist(tmp_path / "dist")
    assert route.call_count == 1
    assert "D406T" in report.forms_unchanged


@respx.mock
async def test_out_of_feed_zip_missing_the_jars_raises(tmp_path: Path) -> None:
    _mock_feed(("D300", "J12.0.1"))
    respx.get(OUT_OF_FEED_FORMS["D406T"]).mock(
        return_value=httpx.Response(200, content=_saft_zip("duk_SAFT/readme.txt"))
    )
    with pytest.raises(AnafConfigError, match="does not contain"):
        await install_dist(tmp_path / "dist", forms=["D406T"])


# -- apply_offline_mode ------------------------------------------------------------


def test_apply_offline_mode_replaces_an_existing_key(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.properties").write_text("proxy=auto\noffLine=N\n")
    apply_offline_mode(tmp_path, enabled=True)
    text = (config_dir / "config.properties").read_text()
    assert text.count("offLine") == 1
    assert "offLine=Y" in text
    assert "proxy=auto" in text


def test_apply_offline_mode_without_a_config_is_a_no_op(tmp_path: Path) -> None:
    apply_offline_mode(tmp_path, enabled=True)  # must not raise
