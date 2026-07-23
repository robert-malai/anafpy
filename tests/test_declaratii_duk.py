"""Tests for the DUKIntegrator wrapper — command construction, err parsing, feed.

Credential-free and DUK-free: the Java subprocess is faked by overriding
``_run`` so the tests assert on the exact positional command and drive the
err-file parser directly.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from anafpy.declaratii import DukIntegrator
from anafpy.declaratii.duk import _parse_err_file, _parse_versions_feed
from anafpy.exceptions import AnafConfigError, AnafResponseError, AnafTransportError


@pytest.fixture
def duk_dir(tmp_path: Path) -> Path:
    """A minimally-valid DUK install tree."""
    (tmp_path / "DUKIntegrator.jar").write_text("")
    (tmp_path / "lib").mkdir()
    return tmp_path


class FakeDuk(DukIntegrator):
    """A DukIntegrator whose ``_run`` writes a canned err file instead of Java."""

    def __init__(
        self,
        *args: object,
        err: str = "ok",
        stdout: bytes = b"stdout",
        stderr: bytes = b"",
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.err = err
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[list[str]] = []
        self.pdf_on_success = False

    async def _run(self, args: list[str]) -> tuple[int, bytes, bytes]:
        self.calls.append(args)
        Path(args[3]).write_text(self.err, encoding="utf-8")
        if self.pdf_on_success and self.err.strip() == "ok" and "-p" in args:
            Path(args[-1]).write_bytes(b"%PDF-1.7\n")
        return 0, self.stdout, self.stderr


# -- construction ------------------------------------------------------------------


def test_bad_duk_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(AnafConfigError, match="not a DUKIntegrator install"):
        DukIntegrator(tmp_path, java="java")


def test_missing_java_raises(duk_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANAFPY_DUK_JAVA", raising=False)
    monkeypatch.setattr("anafpy.declaratii.duk.shutil.which", lambda _: None)
    with pytest.raises(AnafConfigError, match="no Java runtime"):
        DukIntegrator(duk_dir)


def test_java_from_env(duk_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANAFPY_DUK_JAVA", "/opt/java/bin/java")
    duk = DukIntegrator(duk_dir)
    assert duk.java == "/opt/java/bin/java"


# -- command construction ----------------------------------------------------------


async def test_validate_command_shape(duk_dir: Path) -> None:
    duk = FakeDuk(duk_dir, java="java")
    result = await duk.validate("D300", b"<x/>", option=0)
    assert result.ok
    args = duk.calls[0]
    assert args[0] == "-v"
    assert args[1] == "D300"
    assert args[2].endswith(".xml")
    assert args[3].endswith(".txt")
    assert args[4] == "0"
    assert Path(args[2]).is_absolute()
    assert Path(args[3]).is_absolute()


async def test_render_command_shape(duk_dir: Path, tmp_path: Path) -> None:
    duk = FakeDuk(duk_dir, java="java")
    duk.pdf_on_success = True
    pdf = tmp_path / "out.pdf"
    result = await duk.render("D300", b"<x/>", pdf)
    assert result.ok
    args = duk.calls[0]
    assert args[0] == "-p"
    assert args[1] == "D300"
    assert args[5] == "0"  # zipFile: no attachment
    assert args[6] == str(pdf)
    assert pdf.read_bytes().startswith(b"%PDF")


async def test_render_resolves_relative_output_before_duk_cwd(
    duk_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    duk = FakeDuk(duk_dir, java="java")
    duk.pdf_on_success = True

    await duk.render("D300", b"<x/>", Path("relative.pdf"))

    assert duk.calls[0][-1] == str((tmp_path / "relative.pdf").resolve())


async def test_render_validation_failure_writes_no_pdf(
    duk_dir: Path, tmp_path: Path
) -> None:
    duk = FakeDuk(duk_dir, java="java", err="E: eroare regula: R25: ceva")
    duk.pdf_on_success = True
    pdf = tmp_path / "out.pdf"
    result = await duk.render("D300", b"<x/>", pdf)
    assert not result.ok
    assert not pdf.exists()
    assert result.findings[0].severity == "error"


# -- err-file parsing --------------------------------------------------------------


def test_parse_ok() -> None:
    result = _parse_err_file("ok\n")
    assert result.ok
    assert result.findings == []


def test_parse_single_error() -> None:
    text = "E: eroare regula: R25: campul X\n    detaliu suplimentar\n"
    result = _parse_err_file(text)
    assert not result.ok
    assert len(result.findings) == 1
    assert result.findings[0].severity == "error"
    assert "R25" in result.findings[0].message
    assert "detaliu suplimentar" in result.findings[0].message


def test_parse_saft_fatal_prefix() -> None:
    # The D406/D406T (SAF-T) validators emit F: structure findings.
    text = (
        "F: Header (1) sectiune Company (1)\n"
        " eroare structura: elementul 'Address' ar fi trebuit sa apara de "
        "minimum 1 ori, dar apare efectiv de 0 ori\n"
    )
    result = _parse_err_file(text)
    assert not result.ok
    assert result.findings[0].severity == "error"
    assert "Address" in result.findings[0].message


def test_parse_multi_finding() -> None:
    text = "E: eroare atribut: cui\nW: avertisment: pro_rata\n    valoare neobisnuita\n"
    result = _parse_err_file(text)
    assert not result.ok  # an error is present, warning notwithstanding
    assert [f.severity for f in result.findings] == ["error", "warning"]
    assert "pro_rata" in result.findings[1].message


def test_parse_warning_only_passes() -> None:
    # D700 (and the SAF-T W: notices) never write a bare "ok"; a run whose only
    # findings are warnings is a PASS, and the warnings still ride the result.
    text = (
        "A: validari globale\n"
        " atentionare regula: ATENTIONARE: Formularul urmeaza sa fie prelucrat "
        "la organul fiscal competent\n"
    )
    result = _parse_err_file(text)
    assert result.ok
    assert [f.severity for f in result.findings] == ["warning"]
    assert result.warnings == result.findings
    assert result.errors == []
    assert "organul fiscal competent" in result.warnings[0].message


def test_parse_w_prefix_warning_only_passes() -> None:
    result = _parse_err_file("W: avertisment: valoare neobisnuita\n")
    assert result.ok
    assert result.warnings and not result.errors


def test_parse_mixed_error_and_atentionare_fails_and_splits() -> None:
    # A real D300 shape: an E: control-sum error and an A: VAT-rate atentionare
    # must split into two findings, and the error makes the run fail.
    text = (
        "E: validari globale\n eroare regula: R26: totalPlata_A\n"
        "A: validari globale\n atentionare regula: R47: TVA marja\n"
    )
    result = _parse_err_file(text)
    assert not result.ok
    assert [f.severity for f in result.findings] == ["error", "warning"]
    assert result.errors and len(result.warnings) == 1


def test_parse_empty_err_file_is_failure() -> None:
    # A broken/mis-versioned dist leaves an empty err file — never a pass.
    assert not _parse_err_file("").ok
    assert not _parse_err_file("   \n").ok


async def test_empty_err_failure_carries_process_output_tail(duk_dir: Path) -> None:
    # The documented broken-dist modes leave an empty err file with the only
    # clue on stdout ("cod eroare=-5") — the result must carry it.
    duk = FakeDuk(duk_dir, java="java", err="", stdout=b"cod eroare=-5", stderr=b"boom")
    result = await duk.validate("D300", b"<x/>")
    assert not result.ok
    assert result.findings == []
    assert "[stdout] cod eroare=-5" in result.raw
    assert "[stderr] boom" in result.raw


async def test_empty_err_failure_process_tail_is_bounded(duk_dir: Path) -> None:
    duk = FakeDuk(duk_dir, java="java", err="", stdout=b"x" * 10_000)
    result = await duk.validate("D300", b"<x/>")
    assert not result.ok
    assert len(result.raw) < 2_100  # last ~2000 chars, plus the [stdout] label


async def test_parseable_failure_keeps_raw_as_the_err_file(duk_dir: Path) -> None:
    # With findings the err file explains itself — raw stays verbatim.
    err = "E: eroare regula: R25: campul X"
    duk = FakeDuk(duk_dir, java="java", err=err, stdout=b"cod eroare=-5")
    result = await duk.validate("D300", b"<x/>")
    assert not result.ok
    assert result.findings
    assert result.raw == err
    assert "[stdout]" not in result.raw


async def test_render_empty_err_failure_carries_process_output_tail(
    duk_dir: Path, tmp_path: Path
) -> None:
    duk = FakeDuk(duk_dir, java="java", err="", stdout=b"cod eroare=-5")
    result = await duk.render("D300", b"<x/>", tmp_path / "out.pdf")
    assert not result.ok
    assert "[stdout] cod eroare=-5" in result.raw


def test_parse_cp1250_bytes(tmp_path: Path) -> None:
    # A cp1250-encoded Romanian message decoded through _read_err.
    from anafpy.declaratii.duk import _read_err

    raw = "E: eroare: cîmp invalid".encode("cp1250")
    err_path = tmp_path / "cp1250.txt"
    err_path.write_bytes(raw)
    result = _parse_err_file(_read_err(err_path))
    assert not result.ok
    assert "invalid" in result.findings[0].message


# -- installed_forms ---------------------------------------------------------------


def test_installed_forms(duk_dir: Path) -> None:
    lib = duk_dir / "lib"
    (lib / "D300Validator.jar").write_text("")
    (lib / "D300IstoriaVersiunilor.txt").write_text("J12.0.1\n")
    (lib / "D112Validator.jar").write_text("")  # no history -> unknown
    duk = DukIntegrator(duk_dir, java="java")
    forms = duk.installed_forms()
    assert forms == {"D300": "J12.0.1", "D112": "unknown"}


# `IstoriaVersiunilor.txt` as ANAF actually ships it: a changelog in
# chronological order, so the CURRENT version is its last `J…` token. Reading
# the first line instead (as anafpy did until 2026-07-23) yields the 2011 test
# release for every form, which made every staleness comparison cry wolf.
_D300_HISTORY = """\
19-Oct-2011 publicat versiunea de test J1.0.0

29-Nov-2011
\t- publicat versiunea J2.0.0
11-Feb-2026
\t- publicat versiunea J12.0.1,  modificare validari rd 26
"""

# D100's newest entry is followed by a further detail line carrying no version,
# so "the last line" is as wrong as "the first line" — only the last token works.
_D100_HISTORY = """\
19-Oct-2011 publicat versiunea de test J1.0.0
14-Jul-2026
\t- publicat versiune J21.0.6
\t- modificare scadenta pt 131,132
"""


@pytest.mark.parametrize(
    ("history", "expected"),
    [(_D300_HISTORY, "J12.0.1"), (_D100_HISTORY, "J21.0.6")],
)
def test_installed_version_is_the_changelogs_last_token(
    duk_dir: Path, history: str, expected: str
) -> None:
    lib = duk_dir / "lib"
    (lib / "D300Validator.jar").write_text("")
    (lib / "D300IstoriaVersiunilor.txt").write_text(history)
    assert DukIntegrator(duk_dir, java="java").installed_forms() == {"D300": expected}


def test_installed_version_unknown_when_the_changelog_has_no_version(
    duk_dir: Path,
) -> None:
    lib = duk_dir / "lib"
    (lib / "D406TValidator.jar").write_text("")
    (lib / "D406TIstoriaVersiunilor.txt").write_text(
        "Istoria versiunilor pentru D406\n"
    )
    assert DukIntegrator(duk_dir, java="java").installed_forms() == {"D406T": "unknown"}


# -- feed_versions -----------------------------------------------------------------


_FEED_ENTRY = (
    "<{form}>"
    "<versiuneJ>{version}</versiuneJ>"
    "<versiuneP>P9.0.0</versiuneP>"
    "<JURL>http://static.anaf.ro/static/10/Anaf/update5/{form}/"
    "{form}Validator.jar</JURL>"
    "<PURL>http://static.anaf.ro/static/10/Anaf/update5/{form}/"
    "{form}Pdf.jar</PURL>"
    "</{form}>"
)


def _feed(*forms: tuple[str, str]) -> str:
    """A ``versiuni.xml`` body in the live per-form container shape."""
    entries = "".join(_FEED_ENTRY.format(form=f, version=v) for f, v in forms)
    return (
        "<versiuni><integrator><versiune>1.4.18.3.3</versiune>"
        "<sJars><jarURL>http://static.anaf.ro/static/10/Anaf/update5/ss8/"
        "Validator.jar</jarURL></sJars>"
        f"</integrator>{entries}</versiuni>"
    )


def test_parse_versions_feed() -> None:
    xml = _feed(("D300", "J12.0.1"), ("D112", "J5.0.0"))
    assert _parse_versions_feed(xml) == {"D300": "J12.0.1", "D112": "J5.0.0"}


def test_parse_versions_feed_garbage_is_empty() -> None:
    assert _parse_versions_feed("not xml <<<") == {}
    assert _parse_versions_feed("") == {}


@respx.mock
async def test_feed_versions_over_https(duk_dir: Path) -> None:
    xml = _feed(("D300", "J12.0.1"))
    respx.get("https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(200, text=xml)
    )
    duk = DukIntegrator(duk_dir, java="java")
    assert await duk.feed_versions() == {"D300": "J12.0.1"}


@respx.mock
async def test_feed_versions_http_status_raises_response_error(duk_dir: Path) -> None:
    # A received non-success answer is AnafResponseError (with the status code),
    # per the transport/response error split — not a bare AnafTransportError.
    respx.get("https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(503)
    )
    duk = DukIntegrator(duk_dir, java="java")
    with pytest.raises(AnafResponseError) as excinfo:
        await duk.feed_versions()
    assert excinfo.value.status_code == 503


@respx.mock
async def test_feed_versions_network_failure_raises_transport_error(
    duk_dir: Path,
) -> None:
    respx.get("https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        side_effect=httpx.ConnectError("boom")
    )
    duk = DukIntegrator(duk_dir, java="java")
    with pytest.raises(AnafTransportError) as excinfo:
        await duk.feed_versions()
    assert not isinstance(excinfo.value, AnafResponseError)


async def test_run_timeout_raises(
    duk_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duk = DukIntegrator(duk_dir, java="java", timeout=0.01)

    async def hang(*_a: object, **_k: object) -> tuple[int, bytes, bytes]:
        raise TimeoutError

    monkeypatch.setattr("anafpy.declaratii.duk.run_subprocess", hang)
    with pytest.raises(AnafConfigError, match="did not finish within"):
        await duk.validate("D300", b"<x/>")


async def test_run_oserror_is_config_error(duk_dir: Path) -> None:
    duk = DukIntegrator(duk_dir, java="/definitely/missing/java")
    with pytest.raises(AnafConfigError, match="ANAFPY_DUK_JAVA"):
        await duk.validate("D300", b"<x/>")
