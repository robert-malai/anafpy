"""Headless wrapper around ANAF's DUKIntegrator ("mode B").

DUKIntegrator is ANAF's Java desktop tool for declaration validation, official
PDF rendering, and signing. Its per-form validator jars ARE ANAF's validation
code — we run them, we never re-implement the rules (:mod:`nr_evid` is
composition, not validation). This wrapper drives the CLI contract headlessly
for the two operations M1 needs: ``-v`` (validate) and ``-p`` (render the
official PDF with the XML embedded). Signing (``-s``) is not used here — on
macOS the certificate lives behind a CryptoTokenKit extension with no PKCS#11
dylib, so DUK's signing path cannot reach it; :mod:`signing` + :mod:`pdfsign`
handle the qualified signature instead.

The distribution is the user's to install (like the OAuth app and the
certificate): point at the extracted ``dist/`` folder via ``duk_dir`` /
``ANAFPY_DUK_DIR``. Grab it from
``https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip``
(ignore the bundled 32-bit JRE 6 — a modern JVM runs ``-v``/``-p`` fine) and
drop the per-form validator jars from the update feed into ``dist/lib/``.

CLI contract facts baked in below (proven 2026-07-15, Oracle Java 26, macOS):

* positional args; success of ``-v`` writes literally ``ok`` to the err file
  and prints ``Validare fara erori fisier: <path>`` to stdout; failure writes
  ``E:``/``W:``-prefixed lines with indented detail — the D406/D406T (SAF-T)
  validators additionally emit ``F:`` (structure/fatal) lines. **Exit code is
  0 either way** — judge by err-file content, never by the exit code.
* ``-p`` writes the official multi-page PDF with the XML as an embedded file.
* the ``zipFile`` positional is ``0`` for forms with no attachment (D300).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import httpx
from parsel import Selector
from pydantic import BaseModel

from ..exceptions import AnafConfigError, AnafTransportError

__all__ = ["DukFinding", "DukIntegrator", "DukResult"]

_DUK_DOWNLOAD_URL = (
    "https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip"
)
_VERSIONS_FEED_URL = "http://static.anaf.ro/static/10/Anaf/update5/versiuni.xml"


class DukFinding(BaseModel):
    """One validator finding — an ``E:``/``F:`` (error) or ``W:`` (warning) line.

    ``F:`` is the SAF-T validators' structure/fatal prefix (D406/D406T); it maps
    to ``severity="error"`` like ``E:``.
    """

    severity: str  # "error" | "warning"
    message: str  # the header line plus its indented detail lines, joined


class DukResult(BaseModel):
    """Outcome of a ``-v`` / ``-p`` run.

    ``ok`` is the err file's verdict (``ok`` text on success), not the exit
    code. ``raw`` is the full err-file text for debugging.
    """

    ok: bool
    findings: list[DukFinding]
    raw: str


def _parse_err_file(text: str) -> DukResult:
    """Parse a DUKIntegrator err file into a :class:`DukResult`.

    ``ok`` (exact, stripped) means success. Otherwise every line starting
    ``E:``/``F:``/``W:`` opens a finding; following indented lines attach to it.
    """
    if text.strip() == "ok":
        return DukResult(ok=True, findings=[], raw=text)

    findings: list[DukFinding] = []
    current: list[str] = []
    severity = ""

    def flush() -> None:
        if severity:
            findings.append(
                DukFinding(severity=severity, message="\n".join(current).strip())
            )

    for line in text.splitlines():
        if line.startswith(("E:", "F:", "W:")):
            flush()
            severity = "warning" if line.startswith("W:") else "error"
            current = [line[2:].strip()]
        elif severity and line.strip():
            current.append(line.strip())
    flush()
    # A non-"ok" err file with no parseable finding still means failure; keep the
    # raw text so the caller can see what DUK actually wrote.
    return DukResult(ok=False, findings=findings, raw=text)


class DukIntegrator:
    """Async wrapper over ``java -jar DUKIntegrator.jar`` for validate and render.

    Args:
        duk_dir: the extracted ``dist/`` folder (must contain
            ``DUKIntegrator.jar`` and ``lib/``).
        java: the ``java`` binary; explicit arg > ``ANAFPY_DUK_JAVA`` >
            ``shutil.which("java")``. Resolution happens at construction; a
            missing java raises :class:`AnafConfigError`.
        timeout: per-run wall-clock budget for the Java subprocess (seconds).

    Raises:
        AnafConfigError: ``duk_dir`` is not a valid DUK install, or no ``java``
            could be found.
    """

    def __init__(
        self,
        duk_dir: Path,
        *,
        java: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.duk_dir = Path(duk_dir).expanduser()
        self.jar = self.duk_dir / "DUKIntegrator.jar"
        self.lib = self.duk_dir / "lib"
        if not self.jar.exists() or not self.lib.is_dir():
            raise AnafConfigError(
                f"{self.duk_dir} is not a DUKIntegrator install "
                "(expected DUKIntegrator.jar and lib/). Download and extract "
                f"{_DUK_DOWNLOAD_URL} and point ANAFPY_DUK_DIR at its dist/ folder."
            )
        resolved = java or _default_java()
        if not resolved:
            raise AnafConfigError(
                "no Java runtime found — install a JRE/JDK (Java 8+) and set "
                "ANAFPY_DUK_JAVA, or put `java` on PATH"
            )
        self.java = resolved
        self.timeout = timeout

    # -- public operations -------------------------------------------------------------

    async def validate(self, form: str, xml: bytes, *, option: int = 0) -> DukResult:
        """Validate *xml* for *form* (e.g. ``"D300"``) via ``-v``.

        Returns a :class:`DukResult`; ``ok=True`` means the validator wrote
        ``ok``. Findings are DUK's own messages, verbatim.
        """
        with tempfile.TemporaryDirectory(prefix="anafpy-duk-") as tmp:
            xml_path = Path(tmp) / "decl.xml"
            err_path = Path(tmp) / "err.txt"
            xml_path.write_bytes(xml)
            await self._run(["-v", form, str(xml_path), str(err_path), str(option)])
            return _parse_err_file(_read_err(err_path))

    async def render(
        self, form: str, xml: bytes, pdf_path: Path, *, option: int = 0
    ) -> DukResult:
        """Render the official PDF for *form* to *pdf_path* via ``-p``.

        DUK validates before rendering: on a validation failure it writes no PDF
        and the returned :class:`DukResult` carries the findings (``ok=False``).
        On success ``ok=True`` and *pdf_path* holds the multi-page PDF with the
        XML embedded (``/EmbeddedFiles``).
        """
        pdf_path = Path(pdf_path).expanduser()
        with tempfile.TemporaryDirectory(prefix="anafpy-duk-") as tmp:
            xml_path = Path(tmp) / "decl.xml"
            err_path = Path(tmp) / "err.txt"
            xml_path.write_bytes(xml)
            # -p <form> <xml> <err> <option> <zipFile=0> <pdf>
            await self._run(
                [
                    "-p",
                    form,
                    str(xml_path),
                    str(err_path),
                    str(option),
                    "0",
                    str(pdf_path),
                ]
            )
            return _parse_err_file(_read_err(err_path))

    def installed_forms(self) -> dict[str, str]:
        """Installed per-form validators as ``{form: version}``.

        Scans ``lib/*Validator.jar``; the version comes from a sibling
        ``<form>IstoriaVersiunilor.txt`` when present, else ``"unknown"``. Cheap
        and non-fatal — a form with no readable version still appears.
        """
        forms: dict[str, str] = {}
        for jar in sorted(self.lib.glob("*Validator.jar")):
            form = jar.name.removesuffix("Validator.jar")
            if not form:
                continue
            forms[form] = _form_version(self.lib, form)
        return forms

    async def java_version(self) -> str:
        """The configured Java's version string (its ``java -version`` first line).

        Best-effort — returns ``"unknown"`` if java cannot be run.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                self.java,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
        except (OSError, TimeoutError):
            return "unknown"
        # `java -version` writes to stderr.
        lines = stderr.decode("utf-8", errors="replace").splitlines()
        return lines[0].strip() if lines else "unknown"

    async def feed_versions(self) -> dict[str, str]:
        """Current per-form validator versions from ANAF's update feed.

        Reads ``versiuni.xml`` and returns ``{form: version}`` for entries that
        look like ``<form>Validator.jar``. Best-effort — used only to surface
        staleness.

        Raises:
            AnafTransportError: the feed could not be fetched or parsed.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(_VERSIONS_FEED_URL)
                response.raise_for_status()
                return _parse_versions_feed(response.text)
        except httpx.HTTPError as exc:
            raise AnafTransportError(
                f"cannot fetch the DUK update feed {_VERSIONS_FEED_URL}: {exc}"
            ) from exc

    # -- execution ---------------------------------------------------------------------

    async def _run(self, args: list[str]) -> tuple[int, bytes, bytes]:
        """Run ``java -jar DUKIntegrator.jar <args>``; returns (code, out, err).

        The exit code is returned for diagnostics only — callers judge success
        by the err file, never by this.
        """
        command = [self.java, "-jar", str(self.jar), *args]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.duk_dir),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise AnafConfigError(
                f"DUKIntegrator did not finish within {self.timeout:.0f}s "
                f"(command: {' '.join(args)}) — is the form's validator jar in "
                f"{self.lib}?"
            ) from None
        return process.returncode or 0, stdout, stderr


def _default_java() -> str | None:
    """``ANAFPY_DUK_JAVA`` if set, else ``java`` on PATH, else ``None``."""
    if override := os.environ.get("ANAFPY_DUK_JAVA"):
        return override
    return shutil.which("java")


def _read_err(err_path: Path) -> str:
    """Read a DUK err file, tolerating the platform's default encoding.

    DUK writes the err file in the platform default (UTF-8 on modern macOS/Linux,
    cp1250 on a Romanian Windows). Try UTF-8, fall back to cp1250, and never
    raise on undecodable bytes.
    """
    if not err_path.exists():
        return ""
    data = err_path.read_bytes()
    for encoding in ("utf-8", "cp1250"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _form_version(lib: Path, form: str) -> str:
    history = lib / f"{form}IstoriaVersiunilor.txt"
    if history.exists():
        for line in history.read_text(encoding="utf-8", errors="replace").splitlines():
            if stripped := line.strip():
                return stripped
    return "unknown"


def _parse_versions_feed(text: str) -> dict[str, str]:
    """Extract ``{form: version}`` from ANAF's ``versiuni.xml`` feed.

    The feed holds one container per form (``<D300>``, ``<D112>``, ...) whose
    ``JURL`` child points at the ``<form>Validator.jar`` and whose ``versiuneJ``
    child is that jar's current version — the same ``J…`` string the installed
    ``<form>IstoriaVersiunilor.txt`` leads with (live shape, 2026-07-17; see the
    DUK reference §1). Unparseable content yields an empty mapping (best-effort
    — parsel's recovering XML mode simply matches nothing).
    """
    versions: dict[str, str] = {}
    if not text.strip():  # Selector rejects empty input with an exception
        return versions
    for entry in Selector(text=text, type="xml").xpath("//*[JURL and versiuneJ]"):
        jar = entry.xpath("JURL/text()").get("")
        version = entry.xpath("versiuneJ/text()").get("")
        if jar.endswith("Validator.jar") and version:
            form = Path(jar).name.removesuffix("Validator.jar")
            if form:
                versions.setdefault(form, version)
    return versions
