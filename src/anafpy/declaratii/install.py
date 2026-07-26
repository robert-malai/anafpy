"""Managed DUKIntegrator provisioning from ANAF's update feed.

ANAF's ``versiuni.xml`` update feed is **self-sufficient** (established
2026-07-26): besides the per-form validator/PDF jars it lists the integrator
core (``zJars`` — ``DUKIntegrator.jar``), the shared lib jars (``sJars`` —
``DecValidation.jar``/``DecPdf.jar``/``Validator.jar``), the third-party jars
(``iJars`` — iText + BouncyCastle), and the ``config/`` files (``cFisiere``)
— exactly the inventory of a working dist. A dist is therefore assembled file
by file from the feed; the legacy ``dist_javaInclus20200203.zip`` is never
downloaded. The one exception is **D406T** (ANAF's no-fiscal-effect SAF-T test
form): its jars ship only inside the dedicated ``duk_SAFT`` distribution zip
(~91 MB), so it is fetched only when named explicitly.

Trust: the feed is plain XML with no signatures. Every download is pinned to
``static.anaf.ro`` over HTTPS (the feed's ``http://`` URLs are upgraded, any
other host is refused) and the manifest (:data:`MANIFEST_NAME` in the dist)
records each file's source URL, SHA-256, and version — so an install is
auditable, and :meth:`DukInstaller.install` is **convergent**: files that are
present and current are skipped, missing or outdated ones are (re)fetched, and
running it again with the same feed downloads nothing.

The managed dist lives at :data:`MANAGED_DUK_DIR` (``~/.anafpy/duk-dist``);
an explicit ``ANAFPY_DUK_DIR`` always wins over it (:func:`default_duk_dir`).
A pre-existing hand-assembled dist is simply **adopted**: installing over it
refreshes the feed-known files, writes the manifest, and leaves any extra
jars untouched.
"""

from __future__ import annotations

import hashlib
import tempfile
import urllib.parse
import zipfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import httpx
from parsel import Selector
from pydantic import BaseModel

from .._transport.base import raise_for_status
from ..exceptions import AnafConfigError, AnafResponseError, AnafTransportError
from .models import DukInstallReport

__all__ = [
    "MANAGED_DUK_DIR",
    "MANIFEST_NAME",
    "PREINSTALL_FORMS",
    "DukFeed",
    "DukInstaller",
    "FeedForm",
    "default_duk_dir",
    "fetch_feed",
    "parse_feed",
]

FEED_URL = "https://static.anaf.ro/static/10/Anaf/update5/versiuni.xml"

#: The dedicated SAF-T distribution — the only source of the D406T jars
#: (they are absent from the update feed; see the DUK reference §1).
SAFT_ZIP_URL = (
    "https://static.anaf.ro/static/10/Anaf/Informatii_R/duk_SAFT_20230216.zip"
)
_SAFT_FORM = "D406T"
_SAFT_TIMEOUT = 600.0  # ~91 MB on a slow line

#: The only host downloads are accepted from, always over HTTPS.
_ALLOWED_HOST = "static.anaf.ro"

MANAGED_DUK_DIR = Path("~/.anafpy/duk-dist")
MANIFEST_NAME = "anafpy-duk-manifest.json"

#: Installed by a bare ``install()``: the top two usage buckets of the
#: e-guvernare form inventory (docs/anaf-reference/declaratii/forms/README.md)
#: — the recurring SME compliance calendar plus the common event-driven forms.
PREINSTALL_FORMS = (
    "D100",
    "D101",
    "D112",
    "D205",
    "D212",
    "D300",
    "D301",
    "D390",
    "D394",
    "D406",
    "D700",
    "D710",
)


class FeedForm(BaseModel):
    """One per-form container of the update feed."""

    form: str
    validator_version: str
    """``versiuneJ`` — the validator jar's version."""
    validator_url: str
    """``JURL`` — the ``<form>Validator.jar`` download."""
    pdf_version: str | None = None
    pdf_url: str | None = None
    history_url: str | None = None
    """``DURL`` — the ``<form>IstoriaVersiunilor.txt`` version history."""


class DukFeed(BaseModel):
    """The parsed ``versiuni.xml``: integrator core files plus per-form jars."""

    core_version: str
    root_jars: list[str]
    """``zJars`` jar URLs — installed at the dist root (``DUKIntegrator.jar``)."""
    lib_jars: list[str]
    """``sJars`` + ``iJars`` URLs — the shared and third-party ``lib/`` jars."""
    config_files: list[str]
    """``cFisiere`` URLs — the ``config/`` folder content."""
    forms: dict[str, FeedForm]

    @property
    def validator_versions(self) -> dict[str, str]:
        """``{form: versiuneJ}`` — the staleness-table shape."""
        return {name: entry.validator_version for name, entry in self.forms.items()}


class InstalledFile(BaseModel):
    """Provenance of one manifest-tracked file in the managed dist."""

    url: str
    sha256: str
    size: int


class DukManifest(BaseModel):
    """The install record written next to the managed dist's files.

    ``files`` maps dist-relative POSIX paths (``lib/D300Validator.jar``) to
    their provenance; ``forms`` records each installed form's ``versiuneJ``.
    An unreadable or invalid manifest is treated as absent — the next install
    re-fetches and re-records everything (adoption).
    """

    created_at: datetime
    updated_at: datetime
    core_version: str = ""
    files: dict[str, InstalledFile] = {}
    forms: dict[str, str] = {}


def default_duk_dir() -> Path | None:
    """The managed dist when present — else ``None``.

    Callers resolve an explicit ``duk_dir`` / ``ANAFPY_DUK_DIR`` first and fall
    back here, so a user-managed dist always wins over the managed one.
    """
    directory = MANAGED_DUK_DIR.expanduser()
    return directory if (directory / "DUKIntegrator.jar").exists() else None


def parse_feed(text: str) -> DukFeed:
    """Parse ``versiuni.xml`` into a :class:`DukFeed`.

    Best-effort, like the rest of the feed handling: unusable content yields an
    empty feed (the staleness table then simply shows nothing, while the
    installer refuses to assemble from it with a clear error). The live shape
    (2026-07-26): one ``<integrator>`` element with ``iJars``/``sJars``/
    ``zJars``/``cFisiere`` lists, then per-form containers named after the form
    inside a ``<declaratii>`` wrapper — see the DUK reference §1.
    """
    if not text.strip():  # Selector rejects empty input with an exception
        return DukFeed(
            core_version="", root_jars=[], lib_jars=[], config_files=[], forms={}
        )
    selector = Selector(text=text, type="xml")
    integrator = selector.xpath("//integrator")
    forms: dict[str, FeedForm] = {}
    for entry in selector.xpath("//*[JURL and versiuneJ]"):
        form = str(entry.root.tag)
        jar = entry.xpath("JURL/text()").get("").strip()
        version = entry.xpath("versiuneJ/text()").get("").strip()
        if not (jar.endswith("Validator.jar") and version and form):
            continue
        forms.setdefault(
            form,
            FeedForm(
                form=form,
                validator_version=version,
                validator_url=jar,
                pdf_version=entry.xpath("versiuneP/text()").get("").strip() or None,
                pdf_url=entry.xpath("PURL/text()").get("").strip() or None,
                history_url=entry.xpath("DURL/text()").get("").strip() or None,
            ),
        )
    return DukFeed(
        core_version=integrator.xpath("versiune/text()").get("").strip(),
        root_jars=[
            url
            for url in integrator.xpath("zJars/jarURL/text()").getall()
            if url.strip().endswith(".jar")  # skip ajutor.chm, the GUI help file
        ],
        lib_jars=[
            *integrator.xpath("sJars/jarURL/text()").getall(),
            *integrator.xpath("iJars/jarURL/text()").getall(),
        ],
        config_files=integrator.xpath("cFisiere/fisierURL/text()").getall(),
        forms=forms,
    )


async def fetch_feed(http: httpx.AsyncClient | None = None) -> DukFeed:
    """Fetch and parse ANAF's DUK update feed.

    Raises:
        AnafTransportError: a network-level failure reaching the feed.
        AnafResponseError: the feed answered a non-success HTTP status.
    """
    owns_http = http is None
    client = http or httpx.AsyncClient(timeout=30.0)
    try:
        return parse_feed((await _fetch(client, FEED_URL)).decode("utf-8", "replace"))
    finally:
        if owns_http:
            await client.aclose()


class DukInstaller:
    """Assemble or refresh a DUKIntegrator dist from ANAF's update feed.

    Args:
        dist_dir: the target dist directory; defaults to the managed
            :data:`MANAGED_DUK_DIR`. An existing dist (managed or
            hand-assembled) is converged in place, never wiped.
        http: an injected ``httpx.AsyncClient`` (owned one otherwise).
        progress: called with one human-readable line per downloaded file —
            the CLI passes ``print``; ``None`` stays silent.
        timeout: per-request budget for feed/jar downloads (the SAF-T zip
            gets its own, longer budget).
    """

    def __init__(
        self,
        dist_dir: Path | None = None,
        *,
        http: httpx.AsyncClient | None = None,
        progress: Callable[[str], None] | None = None,
        timeout: float = 60.0,
    ) -> None:
        base = dist_dir if dist_dir is not None else MANAGED_DUK_DIR
        self.dist_dir = Path(base).expanduser().resolve()
        self._http = http
        self._progress = progress or (lambda _line: None)
        self.timeout = timeout

    async def install(self, forms: Sequence[str] = ()) -> DukInstallReport:
        """Converge the dist: core + config always, then the target forms.

        With *forms* named, exactly those are installed/refreshed (an unknown
        name raises). With none, the target set is :data:`PREINSTALL_FORMS`
        plus everything already installed (manifest **and** ``lib/`` scan, so
        a hand-assembled dist is refreshed wholesale) — except D406T, whose
        ~91 MB source zip is only ever fetched when the form is named.

        Raises:
            AnafConfigError: an explicitly named form is not in the feed.
            AnafTransportError: a network-level download failure.
            AnafResponseError: a non-success HTTP answer, a download URL
                pointing off ``static.anaf.ro``, or a feed with no core jars.
        """
        requested = [name.strip().upper() for name in forms if name.strip()]
        owns_http = self._http is None
        client = self._http or httpx.AsyncClient(timeout=self.timeout)
        try:
            feed = parse_feed(
                (await _fetch(client, FEED_URL)).decode("utf-8", "replace")
            )
            if not (feed.root_jars and feed.lib_jars):
                raise AnafResponseError(
                    "ANAF's update feed did not include the integrator core "
                    "jars — cannot assemble a dist from it",
                    status_code=200,
                )
            manifest = self._load_manifest()
            report = DukInstallReport(
                dist_dir=str(self.dist_dir), core_version=feed.core_version
            )
            core_changed = manifest.core_version != feed.core_version
            base_files = [
                *((url, "") for url in feed.root_jars),
                *((url, "lib") for url in feed.lib_jars),
                *((url, "config") for url in feed.config_files),
            ]
            for url, subdir in base_files:
                rel = _relative_name(url, subdir)
                if core_changed or not self._is_current(manifest, rel):
                    await self._fetch_into(client, manifest, url, rel, report)
            targets = requested or sorted(self._default_targets(manifest))
            for form in targets:
                await self._install_form(
                    client, manifest, feed, form, report, explicit=bool(requested)
                )
            manifest.core_version = feed.core_version
            self._save_manifest(manifest)
            return report
        finally:
            if owns_http:
                await client.aclose()

    # -- convergence internals ---------------------------------------------------------

    def _default_targets(self, manifest: DukManifest) -> set[str]:
        installed = {
            jar.name.removesuffix("Validator.jar")
            for jar in (self.dist_dir / "lib").glob("*Validator.jar")
        }
        return set(PREINSTALL_FORMS) | set(manifest.forms) | {f for f in installed if f}

    async def _install_form(
        self,
        client: httpx.AsyncClient,
        manifest: DukManifest,
        feed: DukFeed,
        form: str,
        report: DukInstallReport,
        *,
        explicit: bool,
    ) -> None:
        if form == _SAFT_FORM:
            if explicit:
                await self._install_saft(client, manifest, report)
            else:
                report.notes.append(
                    f"{_SAFT_FORM} is not in the update feed (its jars ship in "
                    f"the dedicated duk_SAFT distribution, ~91 MB) — refresh it "
                    f"by naming it explicitly"
                )
            return
        entry = feed.forms.get(form)
        if entry is None:
            message = f"form {form!r} is not in ANAF's update feed"
            if explicit:
                raise AnafConfigError(
                    f"{message} — check the spelling (declaratie_duk_status / "
                    "installed_forms list what exists)"
                )
            report.notes.append(f"{message}; left as installed")
            return
        downloads = [
            (url, _relative_name(url, "lib"))
            for url in (entry.validator_url, entry.pdf_url, entry.history_url)
            if url
        ]
        if manifest.forms.get(form) == entry.validator_version and all(
            self._is_current(manifest, rel) for _url, rel in downloads
        ):
            report.forms_current[form] = entry.validator_version
            return
        for url, rel in downloads:
            await self._fetch_into(client, manifest, url, rel, report)
        manifest.forms[form] = entry.validator_version
        report.forms_installed[form] = entry.validator_version

    async def _install_saft(
        self,
        client: httpx.AsyncClient,
        manifest: DukManifest,
        report: DukInstallReport,
    ) -> None:
        """Extract the D406T jars from the dedicated SAF-T distribution zip."""
        wanted = {
            f"{_SAFT_FORM}Validator.jar",
            f"{_SAFT_FORM}Pdf.jar",
            f"{_SAFT_FORM}IstoriaVersiunilor.txt",
        }
        jar_rels = [f"lib/{_SAFT_FORM}Validator.jar", f"lib/{_SAFT_FORM}Pdf.jar"]
        if _SAFT_FORM in manifest.forms and all(
            self._is_current(manifest, rel) for rel in jar_rels
        ):
            report.forms_current[_SAFT_FORM] = manifest.forms[_SAFT_FORM]
            return
        self._progress(f"downloading the SAF-T distribution ({SAFT_ZIP_URL}, ~91 MB) …")
        extracted: dict[str, bytes] = {}
        with tempfile.TemporaryDirectory(prefix="anafpy-duk-saft-") as tmp:
            archive = Path(tmp) / "duk_saft.zip"
            await _stream_to_file(client, SAFT_ZIP_URL, archive)
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.namelist():
                    if (name := PurePosixPath(member).name) in wanted:
                        extracted.setdefault(name, bundle.read(member))
        if f"{_SAFT_FORM}Validator.jar" not in extracted:
            raise AnafResponseError(
                f"the duk_SAFT distribution at {SAFT_ZIP_URL} contained no "
                f"{_SAFT_FORM}Validator.jar",
                status_code=200,
            )
        version = "unknown"
        if history := extracted.get(f"{_SAFT_FORM}IstoriaVersiunilor.txt"):
            for line in history.decode("utf-8", errors="replace").splitlines():
                if stripped := line.strip():
                    version = stripped
                    break
        for name, data in extracted.items():
            rel = f"lib/{name}"
            self._write(rel, data)
            manifest.files[rel] = InstalledFile(
                url=f"{SAFT_ZIP_URL}#{name}",
                sha256=hashlib.sha256(data).hexdigest(),
                size=len(data),
            )
            report.updated_files.append(rel)
            self._progress(f"{rel} ({_size(len(data))})")
        manifest.forms[_SAFT_FORM] = version
        report.forms_installed[_SAFT_FORM] = version

    async def _fetch_into(
        self,
        client: httpx.AsyncClient,
        manifest: DukManifest,
        url: str,
        rel: str,
        report: DukInstallReport,
    ) -> None:
        data = await _fetch(client, url)
        self._write(rel, data)
        manifest.files[rel] = InstalledFile(
            url=_download_url(url),
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
        )
        report.updated_files.append(rel)
        self._progress(f"{rel} ({_size(len(data))})")

    def _is_current(self, manifest: DukManifest, rel: str) -> bool:
        """The file exists and matches its recorded hash — integrity, not mtime."""
        if (recorded := manifest.files.get(rel)) is None:
            return False
        try:
            data = (self.dist_dir / rel).read_bytes()
        except OSError:
            return False
        return hashlib.sha256(data).hexdigest() == recorded.sha256

    def _write(self, rel: str, data: bytes) -> None:
        dest = self.dist_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".anafpy-part")
        partial.write_bytes(data)
        partial.replace(dest)

    @property
    def _manifest_path(self) -> Path:
        return self.dist_dir / MANIFEST_NAME

    def _load_manifest(self) -> DukManifest:
        try:
            return DukManifest.model_validate_json(self._manifest_path.read_bytes())
        except (OSError, ValueError):
            now = datetime.now(UTC)
            return DukManifest(created_at=now, updated_at=now)

    def _save_manifest(self, manifest: DukManifest) -> None:
        manifest.updated_at = datetime.now(UTC)
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )


def _download_url(url: str) -> str:
    """Upgrade a feed URL to HTTPS and refuse hosts other than ANAF's static CDN."""
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.hostname != _ALLOWED_HOST:
        raise AnafResponseError(
            f"refusing download from unexpected host: {url!r} — the update feed "
            f"should only reference {_ALLOWED_HOST}",
            status_code=200,
        )
    return urllib.parse.urlunsplit(
        ("https", parsed.netloc, parsed.path, parsed.query, "")
    )


def _relative_name(url: str, subdir: str) -> str:
    """The dist-relative destination for a feed URL (its basename in *subdir*)."""
    name = PurePosixPath(urllib.parse.urlsplit(url).path).name
    if not name or name in {".", ".."}:
        raise AnafResponseError(
            f"the update feed offered an unusable file URL: {url!r}",
            status_code=200,
        )
    return f"{subdir}/{name}" if subdir else name


def _size(count: int) -> str:
    if count >= 1024 * 1024:
        return f"{count / (1024 * 1024):.1f} MB"
    return f"{max(count // 1024, 1)} KB"


async def _fetch(client: httpx.AsyncClient, url: str) -> bytes:
    target = _download_url(url)
    try:
        response = await client.get(target)
    except httpx.HTTPError as exc:
        raise AnafTransportError(f"cannot download {target}: {exc}") from exc
    raise_for_status(response)
    return response.content


async def _stream_to_file(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    target = _download_url(url)
    try:
        async with client.stream("GET", target, timeout=_SAFT_TIMEOUT) as response:
            if response.status_code != 200:
                await response.aread()  # raise_for_status needs the body
                raise_for_status(response)
            with dest.open("wb") as sink:
                async for chunk in response.aiter_bytes():
                    sink.write(chunk)
    except httpx.HTTPError as exc:
        raise AnafTransportError(f"cannot download {target}: {exc}") from exc
