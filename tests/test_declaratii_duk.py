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
from anafpy.exceptions import AnafConfigError, AnafTransportError


@pytest.fixture
def duk_dir(tmp_path: Path) -> Path:
    """A minimally-valid DUK install tree."""
    (tmp_path / "DUKIntegrator.jar").write_text("")
    (tmp_path / "lib").mkdir()
    return tmp_path


class FakeDuk(DukIntegrator):
    """A DukIntegrator whose ``_run`` writes a canned err file instead of Java."""

    def __init__(self, *args: object, err: str = "ok", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.err = err
        self.calls: list[list[str]] = []
        self.pdf_on_success = False

    async def _run(self, args: list[str]) -> tuple[int, bytes, bytes]:
        self.calls.append(args)
        Path(args[3]).write_text(self.err, encoding="utf-8")
        if self.pdf_on_success and self.err.strip() == "ok" and "-p" in args:
            Path(args[-1]).write_bytes(b"%PDF-1.7\n")
        return 0, b"stdout", b""


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
    assert [f.severity for f in result.findings] == ["error", "warning"]
    assert "pro_rata" in result.findings[1].message


def test_parse_cp1250_bytes() -> None:
    # A cp1250-encoded Romanian message decoded through _read_err.
    from anafpy.declaratii.duk import _read_err

    raw = "E: eroare: cîmp invalid".encode("cp1250")
    err_path = Path("/tmp/anafpy-cp1250-test.txt")
    err_path.write_bytes(raw)
    try:
        result = _parse_err_file(_read_err(err_path))
        assert not result.ok
        assert "invalid" in result.findings[0].message
    finally:
        err_path.unlink(missing_ok=True)


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


def test_parse_versions_feed() -> None:
    xml = _feed(("D300", "J12.0.1"), ("D112", "J5.0.0"))
    assert _parse_versions_feed(xml) == {"D300": "J12.0.1", "D112": "J5.0.0"}


def test_parse_versions_feed_garbage_is_empty() -> None:
    assert _parse_versions_feed("not xml <<<") == {}
    assert _parse_versions_feed("") == {}


@respx.mock
async def test_feed_versions_over_http(duk_dir: Path) -> None:
    xml = _feed(("D300", "J12.0.1"))
    respx.get("http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(200, text=xml)
    )
    duk = DukIntegrator(duk_dir, java="java")
    assert await duk.feed_versions() == {"D300": "J12.0.1"}


@respx.mock
async def test_feed_versions_http_error_raises(duk_dir: Path) -> None:
    respx.get("http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml").mock(
        return_value=httpx.Response(503)
    )
    duk = DukIntegrator(duk_dir, java="java")
    with pytest.raises(AnafTransportError):
        await duk.feed_versions()


async def test_run_timeout_raises(
    duk_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duk = DukIntegrator(duk_dir, java="java", timeout=0.01)

    async def hang(*_a: object, **_k: object) -> object:
        import asyncio

        class _Proc:
            returncode = None

            async def communicate(self) -> tuple[bytes, bytes]:
                await asyncio.sleep(1)
                return b"", b""

            def kill(self) -> None: ...
            async def wait(self) -> None: ...

        return _Proc()

    monkeypatch.setattr("anafpy.declaratii.duk.asyncio.create_subprocess_exec", hang)
    with pytest.raises(AnafConfigError, match="did not finish within"):
        await duk.validate("D300", b"<x/>")
