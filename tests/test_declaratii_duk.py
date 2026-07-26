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
from anafpy.declaratii.duk import _parse_err_file
from anafpy.declaratii.install import parse_feed
from anafpy.exceptions import AnafConfigError, AnafResponseError, AnafTransportError


@pytest.fixture
def duk_dir(tmp_path: Path) -> Path:
    """A minimally-valid DUK install tree."""
    (tmp_path / "DUKIntegrator.jar").write_text("")
    (tmp_path / "lib").mkdir()
    return tmp_path


def _err_path(args: list[str]) -> Path:
    """The err-file positional: third after the ``-v``/``-p`` operation flag."""
    operation = "-v" if "-v" in args else "-p"
    return Path(args[args.index(operation) + 3])


class FakeDuk(DukIntegrator):
    """A DukIntegrator whose ``_run`` writes a canned err file instead of Java."""

    def __init__(
        self,
        *args: object,
        err: str = "ok",
        stdout: bytes = b"stdout",
        stderr: bytes = b"",
        validator_log: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.err = err
        self.stdout = stdout
        self.stderr = stderr
        self.validator_log = validator_log
        self.calls: list[list[str]] = []
        self.workdirs: list[Path] = []
        self.config_snapshots: list[bytes] = []
        self.pdf_on_success = False

    async def _run(self, args: list[str], *, workdir: Path) -> tuple[int, bytes, bytes]:
        self.calls.append(args)
        self.workdirs.append(workdir)
        # The per-run config dir is gone with the temp dir — snapshot it now.
        self.config_snapshots.append(
            (Path(args[1]) / "config.properties").read_bytes()
            if args[0] == "-c"
            else b""
        )
        _err_path(args).write_text(self.err, encoding="utf-8")
        if self.validator_log:
            (workdir / "validator.log").write_text(self.validator_log, encoding="utf-8")
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
    # -c must point at a DIRECTORY inside the run's temp dir (a file path
    # makes real DUK exit silently), ahead of the operation positionals.
    assert args[0] == "-c"
    assert Path(args[1]) == duk.workdirs[0] / "config"
    assert args[2] == "-v"
    assert args[3] == "D300"
    assert args[4].endswith(".xml")
    assert args[5].endswith(".txt")
    assert args[6] == "0"
    assert Path(args[4]).is_absolute()
    assert Path(args[5]).is_absolute()


async def test_config_dir_forces_offline_over_dist_settings(duk_dir: Path) -> None:
    # The dist's config rides along, its offLine line replaced — never doubled.
    (duk_dir / "config").mkdir()
    (duk_dir / "config" / "config.properties").write_bytes(
        b"proxy=auto\noffLine=N\nurlVersiuni=http://example.invalid\n"
    )
    duk = FakeDuk(duk_dir, java="java")
    await duk.validate("D300", b"<x/>")
    assert duk.config_snapshots[0] == (
        b"proxy=auto\nurlVersiuni=http://example.invalid\noffLine=Y\n"
    )


async def test_config_dir_without_dist_config_is_minimal(duk_dir: Path) -> None:
    duk = FakeDuk(duk_dir, java="java")
    await duk.validate("D300", b"<x/>")
    assert duk.config_snapshots[0] == b"offLine=Y\n"


async def test_render_command_shape(duk_dir: Path, tmp_path: Path) -> None:
    duk = FakeDuk(duk_dir, java="java")
    duk.pdf_on_success = True
    pdf = tmp_path / "out.pdf"
    result = await duk.render("D300", b"<x/>", pdf)
    assert result.ok
    args = duk.calls[0]
    assert args[2] == "-p"
    assert args[3] == "D300"
    assert args[7] == "0"  # zipFile: no attachment
    # DUK renders into the run's temp dir; the PDF is moved to the caller's
    # path only on success.
    assert Path(args[8]) == duk.workdirs[0] / "out.pdf"
    assert pdf.read_bytes().startswith(b"%PDF")


async def test_render_resolves_relative_output_against_caller_cwd(
    duk_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    duk = FakeDuk(duk_dir, java="java")
    duk.pdf_on_success = True

    result = await duk.render("D300", b"<x/>", Path("relative.pdf"))

    assert result.ok
    assert (tmp_path / "relative.pdf").read_bytes().startswith(b"%PDF")


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
    assert result.findings[0].rule == "R25"


def test_parse_rule_id_only_for_r_numbers() -> None:
    # "eroare atribut"/"eroare structura" details and the D700 ATENTIONARE
    # label carry no R-number — rule stays None, message stays verbatim.
    result = _parse_err_file(
        "E: eroare atribut: cui\n"
        "A: validari globale\n"
        " atentionare regula: ATENTIONARE: Formularul urmeaza sa fie prelucrat\n"
    )
    assert [f.rule for f in result.findings] == [None, None]


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


async def test_empty_err_failure_carries_validator_log_tail(duk_dir: Path) -> None:
    # The SAF-T validators crash-log into the working directory (the old-core
    # NoClassDefFoundError mode) — with the per-run cwd that file is ours to read.
    duk = FakeDuk(
        duk_dir,
        java="java",
        err="",
        stdout=b"",
        validator_log="java.lang.NoClassDefFoundError: dec/DECTagStruct",
    )
    result = await duk.validate("D406", b"<x/>")
    assert not result.ok
    assert "[validator.log] java.lang.NoClassDefFoundError" in result.raw


async def test_empty_err_failure_carries_input_log_tail(duk_dir: Path) -> None:
    # The SAF-T validators also write a verbose trace next to the input XML —
    # always the temp copy ``decl.xml``, so ``decl.xml.log`` in the run dir.
    class LogWritingDuk(FakeDuk):
        async def _run(
            self, args: list[str], *, workdir: Path
        ) -> tuple[int, bytes, bytes]:
            (workdir / "decl.xml.log").write_text(
                "SECTION DETECTED: Account", encoding="utf-8"
            )
            return await super()._run(args, workdir=workdir)

    duk = LogWritingDuk(duk_dir, java="java", err="", stdout=b"")
    result = await duk.validate("D406T", b"<x/>")
    assert not result.ok
    assert "[decl.xml.log] SECTION DETECTED: Account" in result.raw


async def test_jvm_command_pins_utf8_and_runs_from_workdir(
    duk_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded: dict[str, object] = {}

    async def record(
        argv: list[str], *, timeout: float, cwd: object = None, env: object = None
    ) -> tuple[int, bytes, bytes]:
        recorded["argv"] = list(argv)
        recorded["cwd"] = cwd
        _err_path(list(argv)).write_text("ok", encoding="utf-8")
        return 0, b"", b""

    monkeypatch.setattr("anafpy.declaratii.duk.run_subprocess", record)
    duk = DukIntegrator(duk_dir, java="java")
    result = await duk.validate("D300", b"<x/>")
    assert result.ok
    argv = recorded["argv"]
    assert isinstance(argv, list)
    assert argv[:3] == ["java", "-Dfile.encoding=UTF-8", "-jar"]
    # The run executes from the per-run temp dir, never the dist.
    assert recorded["cwd"] != duk.duk_dir
    assert _err_path(argv).parent == Path(str(recorded["cwd"]))


def test_explicit_jvm_args_replace_the_default(duk_dir: Path) -> None:
    duk = DukIntegrator(duk_dir, java="java", jvm_args=["-Xmx2g"])
    assert duk.jvm_args == ("-Xmx2g",)
    assert DukIntegrator(duk_dir, java="java").jvm_args == ("-Dfile.encoding=UTF-8",)


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


def test_parse_versions_view() -> None:
    # The staleness-table view over the full feed parse (its detailed tests
    # live in test_declaratii_install.py).
    xml = _feed(("D300", "J12.0.1"), ("D112", "J5.0.0"))
    assert parse_feed(xml).validator_versions == {"D300": "J12.0.1", "D112": "J5.0.0"}


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
