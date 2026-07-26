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

CLI contract facts baked in below (proven 2026-07-15 and 2026-07-26, Oracle
Java 26, macOS):

* positional args; success of ``-v`` writes literally ``ok`` to the err file
  and prints ``Validare fara erori fisier: <path>`` to stdout; problems write
  ``E:``/``W:``/``A:``-prefixed lines with indented detail — the D406/D406T
  (SAF-T) validators additionally emit ``F:`` (structure/fatal) lines.
  ``E:``/``F:`` are errors; ``W:`` (warning) and ``A:`` (atentionare, e.g. D700
  always emits one and never a bare ``ok``) are informational and do not fail
  the run. **Exit code is 0 either way** — judge by err-file content, never by
  the exit code.
* ``-p`` writes the official multi-page PDF with the XML as an embedded file.
* the ``zipFile`` positional is ``0`` for forms with no attachment (D300).
* ``-c`` expects the config **directory** — pointing it at the properties
  *file* (or a missing path) makes DUK exit silently (exit 0, no output, no
  err file). Every run here passes a per-run config dir derived from the
  dist's ``config/config.properties`` with ``offLine=Y`` forced, so the
  startup update check (hardcoded Windows paths — the documented silent-exit
  mode) can never fire.
* runs execute from the per-run temp dir, never ``dist/``: ``lib/`` resolves
  relative to the jar, and both cwd-relative output (``validator.log``, crash
  modes) and input-relative output (the SAF-T validators' verbose
  ``<xml>.log`` trace — the XML is always a temp copy) land in the run's own
  directory — concurrent runs share no writable state.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

import httpx
from parsel import Selector

from .._transport.base import raise_for_status
from .._transport.subprocess import run_subprocess
from ..exceptions import AnafConfigError, AnafTransportError
from .models import DukFinding, DukResult

__all__ = [
    "DukIntegrator",
    "fetch_feed_versions",
]

_DUK_DOWNLOAD_URL = (
    "https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip"
)
_VERSIONS_FEED_URL = "https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml"


# DUK err-file section prefixes mapped to a finding severity. ``E:`` (error) and
# ``F:`` (fatal/structure — the SAF-T validators) are blocking; ``W:`` (warning)
# and ``A:`` (atentionare — e.g. D700's "the form will be processed at the
# competent tax office" notice) are informational and do NOT fail validation on
# their own.
_SEVERITY_BY_PREFIX = {"E:": "error", "F:": "error", "W:": "warning", "A:": "warning"}

# How much of each captured diagnostic source a no-findings failure carries
# into ``DukResult.raw`` — enough for the documented one-line clues (``cod
# eroare=-5``), bounded so a chatty JVM cannot flood the result.
_PROCESS_TAIL_CHARS = 2000

# The official rule id inside a finding's detail line (``eroare regula: R25:
# nr_evid ...``). Only the unambiguous ``R<number>`` shape is extracted — other
# detail flavours (``eroare atribut:``, ``eroare structura:``, the D700
# ``ATENTIONARE`` label) carry no id.
_RULE_ID = re.compile(r"\bregula:\s*(R\d+)\b")


def _with_diagnostics(
    result: DukResult, stdout: bytes, stderr: bytes, workdir: Path
) -> DukResult:
    """Fold bounded run diagnostics into a no-findings failure's ``raw``.

    DUK's documented broken-dist failure modes (the old-core
    ``NoClassDefFoundError`` run whose stdout only says ``cod eroare=-5``, the
    missing-config silent exit) leave an empty/unparseable err file — the only
    clues live on stdout/stderr and in the log files the SAF-T validators drop
    into the run directory: ``validator.log`` (crash modes) and the verbose
    ``decl.xml.log`` trace written next to the input XML. Carry the tail of
    those sources so the ``ok=False, findings=[]`` outcome is self-explaining
    (the MCP layer surfaces ``raw`` exactly when there are no findings). Runs
    with parseable findings — and successes — pass through untouched.
    """
    if result.ok or result.findings:
        return result
    logs: dict[str, bytes] = {}
    for name in ("validator.log", "decl.xml.log"):
        with contextlib.suppress(OSError):
            logs[name] = (workdir / name).read_bytes()
    tails = [
        f"[{label}] {text[-_PROCESS_TAIL_CHARS:]}"
        for label, data in (
            ("stdout", stdout),
            ("stderr", stderr),
            *logs.items(),
        )
        if (text := data.decode("utf-8", errors="replace").strip())
    ]
    if not tails:
        return result
    err_part = [result.raw.rstrip()] if result.raw.strip() else []
    return result.model_copy(update={"raw": "\n".join(err_part + tails)})


def _parse_err_file(text: str) -> DukResult:
    """Parse a DUKIntegrator err file into a :class:`DukResult`.

    A literal ``ok`` is success. Otherwise each line opening with a known
    section prefix (:data:`_SEVERITY_BY_PREFIX`) starts a finding and the
    following indented lines attach to it. The run is ``ok`` when DUK produced
    findings but none are errors — a **warning-only** run passes (D700 always
    emits an ``A:`` atentionare and never a bare ``ok``, so a valid D700 would
    otherwise read as a failure). An ``E:``/``F:`` finding fails; so does
    unrecognized non-``ok`` output with no parseable finding (e.g. the empty
    err file a broken/mis-versioned dist leaves behind) — success is never
    inferred from output we do not understand.
    """
    if text.strip() == "ok":
        return DukResult(ok=True, findings=[], raw=text)

    findings: list[DukFinding] = []
    current: list[str] = []
    severity = ""

    def flush() -> None:
        if severity:
            message = "\n".join(current).strip()
            rule = match.group(1) if (match := _RULE_ID.search(message)) else None
            findings.append(DukFinding(severity=severity, message=message, rule=rule))

    for line in text.splitlines():
        if (mapped := _SEVERITY_BY_PREFIX.get(line[:2])) is not None:
            flush()
            severity = mapped
            current = [line[2:].strip()]
        elif severity and line.strip():
            current.append(line.strip())
    flush()
    has_error = any(finding.severity == "error" for finding in findings)
    return DukResult(ok=bool(findings) and not has_error, findings=findings, raw=text)


class DukIntegrator:
    """Async wrapper over ``java -jar DUKIntegrator.jar`` for validate and render.

    Args:
        duk_dir: the extracted ``dist/`` folder (must contain
            ``DUKIntegrator.jar`` and ``lib/``).
        java: the ``java`` binary; explicit arg > ``ANAFPY_DUK_JAVA`` >
            ``shutil.which("java")``. Resolution happens at construction; a
            missing java raises :class:`AnafConfigError`.
        timeout: per-run wall-clock budget for the Java subprocess (seconds).
        jvm_args: extra JVM flags placed before ``-jar``. The default pins
            ``-Dfile.encoding=UTF-8`` so the err file's encoding is
            deterministic on every platform (DUK otherwise writes it in the
            platform default — cp1250 on a Romanian Windows). Passing a value
            replaces the default; include the encoding pin yourself if you
            only mean to add flags (e.g. ``-Xmx`` for large SAF-T documents).

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
        jvm_args: Sequence[str] | None = None,
    ) -> None:
        self.duk_dir = Path(duk_dir).expanduser().resolve()
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
        self.jvm_args = (
            tuple(jvm_args) if jvm_args is not None else ("-Dfile.encoding=UTF-8",)
        )

    # -- public operations -------------------------------------------------------------

    async def validate(self, form: str, xml: bytes, *, option: int = 0) -> DukResult:
        """Validate *xml* for *form* (e.g. ``"D300"``) via ``-v``.

        Returns a :class:`DukResult`; ``ok=True`` means the validator wrote
        ``ok``. Findings are DUK's own messages, verbatim; a failure with no
        parseable findings carries a bounded stdout/stderr/``validator.log``
        tail in ``raw``.
        """
        with tempfile.TemporaryDirectory(prefix="anafpy-duk-") as tmp:
            workdir = Path(tmp).resolve()
            xml_path = workdir / "decl.xml"
            err_path = workdir / "err.txt"
            xml_path.write_bytes(xml)
            _, stdout, stderr = await self._run(
                [
                    *self._config_args(workdir),
                    "-v",
                    form,
                    str(xml_path),
                    str(err_path),
                    str(option),
                ],
                workdir=workdir,
            )
            return _with_diagnostics(
                _parse_err_file(_read_err(err_path)), stdout, stderr, workdir
            )

    async def render(
        self, form: str, xml: bytes, pdf_path: Path, *, option: int = 0
    ) -> DukResult:
        """Render the official PDF for *form* to *pdf_path* via ``-p``.

        DUK validates before rendering: on a validation failure it writes no PDF
        and the returned :class:`DukResult` carries the findings (``ok=False``).
        On success ``ok=True`` and *pdf_path* holds the multi-page PDF with the
        XML embedded (``/EmbeddedFiles``). DUK renders into the run's temp dir
        and the PDF is moved to *pdf_path* only on success, so a killed or
        failed run never leaves a partial file at the caller's path.
        """
        pdf_path = Path(pdf_path).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="anafpy-duk-") as tmp:
            workdir = Path(tmp).resolve()
            xml_path = workdir / "decl.xml"
            err_path = workdir / "err.txt"
            staging_pdf = workdir / "out.pdf"
            xml_path.write_bytes(xml)
            # -p <form> <xml> <err> <option> <zipFile=0> <pdf>
            _, stdout, stderr = await self._run(
                [
                    *self._config_args(workdir),
                    "-p",
                    form,
                    str(xml_path),
                    str(err_path),
                    str(option),
                    "0",
                    str(staging_pdf),
                ],
                workdir=workdir,
            )
            result = _with_diagnostics(
                _parse_err_file(_read_err(err_path)), stdout, stderr, workdir
            )
            if result.ok:
                _place_pdf(staging_pdf, pdf_path)
            return result

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
            _, _, stderr = await run_subprocess(
                [self.java, "-version"],
                timeout=15.0,
            )
        except (OSError, TimeoutError):
            return "unknown"
        # `java -version` writes to stderr.
        lines = stderr.decode("utf-8", errors="replace").splitlines()
        return lines[0].strip() if lines else "unknown"

    async def feed_versions(self) -> dict[str, str]:
        """Delegate to :func:`fetch_feed_versions` for caller convenience."""
        return await fetch_feed_versions()

    # -- execution ---------------------------------------------------------------------

    def _config_args(self, workdir: Path) -> list[str]:
        """Build ``-c <dir>`` pointing at a per-run config with ``offLine=Y``.

        DUK's ``-c`` expects the config *directory* — a file path (or a missing
        one) makes it exit silently — so the directory is always created here,
        inside the run's temp dir. Its ``config.properties`` carries the
        dist's own settings when readable, with any ``offLine`` line replaced
        by ``offLine=Y`` (the startup update check is the documented
        silent-exit mode on non-Windows hosts). Properties files predate
        UTF-8 defaults, so the merge stays at the byte level.
        """
        config_dir = workdir / "config"
        config_dir.mkdir()
        source = self.duk_dir / "config" / "config.properties"
        lines: list[bytes] = []
        with contextlib.suppress(OSError):
            lines = [
                line
                for line in source.read_bytes().splitlines()
                if not line.strip().startswith(b"offLine")
            ]
        lines.append(b"offLine=Y")
        (config_dir / "config.properties").write_bytes(b"\n".join(lines) + b"\n")
        return ["-c", str(config_dir)]

    async def _run(self, args: list[str], *, workdir: Path) -> tuple[int, bytes, bytes]:
        """Run ``java -jar DUKIntegrator.jar <args>``; returns (code, out, err).

        *workdir* — the run's temp dir — is the cwd, so cwd-relative outputs
        (``validator.log``) land there and concurrent runs share no writable
        state. The exit code is returned for diagnostics only — callers judge
        success by the err file, never by this.
        """
        command = [self.java, *self.jvm_args, "-jar", str(self.jar), *args]
        try:
            return await run_subprocess(
                command,
                timeout=self.timeout,
                cwd=workdir,
            )
        except TimeoutError:
            raise AnafConfigError(
                f"DUKIntegrator did not finish within {self.timeout:.0f}s "
                f"(command: {' '.join(args)}) — is the form's validator jar in "
                f"{self.lib}?"
            ) from None
        except OSError as exc:
            raise AnafConfigError(
                f"cannot run java at {self.java!r}: {exc}; check ANAFPY_DUK_JAVA"
            ) from exc


async def fetch_feed_versions(
    http: httpx.AsyncClient | None = None,
) -> dict[str, str]:
    """Fetch current per-form validator versions without requiring a DUK install.

    Raises:
        AnafTransportError: a network-level failure reaching the feed.
        AnafResponseError: the feed answered a non-success HTTP status.
    """
    owns_http = http is None
    client = http or httpx.AsyncClient(timeout=30.0)
    try:
        try:
            response = await client.get(_VERSIONS_FEED_URL)
        except httpx.HTTPError as exc:
            raise AnafTransportError(
                f"cannot fetch the DUK update feed {_VERSIONS_FEED_URL}: {exc}"
            ) from exc
        raise_for_status(response)
        return _parse_versions_feed(response.text)
    finally:
        if owns_http:
            await client.aclose()


def _default_java() -> str | None:
    """``ANAFPY_DUK_JAVA`` if set, else ``java`` on PATH, else ``None``."""
    if override := os.environ.get("ANAFPY_DUK_JAVA"):
        return override
    return shutil.which("java")


def _place_pdf(staging: Path, target: Path) -> None:
    """Move a successfully-rendered PDF from the run's temp dir to *target*.

    A rename for the atomic same-volume case; a temp dir on another volume
    falls back to a plain copy (the temp dir's removal cleans up the staging
    file). A PDF that cannot be placed after DUK reported success is a local
    filesystem problem, not a validation outcome.

    Raises:
        AnafConfigError: the rendered PDF could not be written at *target*.
    """
    try:
        try:
            staging.replace(target)
        except OSError:
            shutil.copyfile(staging, target)
    except OSError as exc:
        raise AnafConfigError(
            f"DUK rendered the PDF but it could not be placed at {target}: {exc}"
        ) from exc


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
