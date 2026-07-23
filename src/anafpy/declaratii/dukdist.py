"""Assemble and refresh a DUKIntegrator dist from ANAF's own update feed.

ANAF ships DUKIntegrator as a 27 MB zip built in 2020 (around a 32-bit JRE 6
nobody uses) and, separately, an update feed that carries the **current** build
of every one of its parts. Everything a working dist contains has a feed URL:
the core jar (``zJars``), the shared libraries (``iJars`` + ``sJars``), the
``config/`` files (``cFisiere``), and each form's validator/PDF/history triple.
So this module assembles a dist from the feed alone and never touches the zip
(proven 2026-07-23: a feed-only dist validated a D300 nil return clean and
rendered its PDF, at 5.2 MB).

Building from the feed is not merely smaller — it makes the two documented
ways a hand-assembled dist breaks **structurally impossible** rather than
repair steps (see the DUK reference §1):

* the 2020-era core cannot run the D406 validators
  (``NoClassDefFoundError: dec/DECTagStruct``, an empty err file, and a bare
  ``cod eroare=-5`` on stdout). Assembly starts from the feed's current core,
  so there is no stale core to update.
* a dist missing ``config/`` makes an updated core **exit silently**.
  ``config/`` is part of what gets fetched, so it cannot be missing. The zip's
  copy of ``config.properties`` also carries ``javaStartPrefix=..\\jre6\\...``
  — a hardcoded Windows path implicated in the silent-exit failure — which the
  feed's copy does not.

Two things the feed does not cover:

* **D406T**, the SAF-T test declaration used to verify portal filing, is not in
  the feed at all; its jars ship only inside a separate SAF-T distribution
  (:data:`OUT_OF_FEED_FORMS`). It stays fetchable so the filing-mechanism
  rediscovery path is reproducible, but it is never part of a routine install.
* **Integrity**. ANAF publishes no checksums and the feed's URLs are plain
  ``http``. Every download is therefore forced to ``https`` and pinned to
  ANAF's static host (:func:`secure_url`), and each ``.jar`` is checked for the
  zip magic before it lands — a 200-with-HTML error page must never be written
  into ``lib/`` as an executable.
"""

from __future__ import annotations

import asyncio
import io
import os
import zipfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .._transport.base import raise_for_status
from ..exceptions import AnafConfigError, AnafTransportError
from .duk import DukIntegrator, _form_version, fetch_feed, url_basename
from .models import DukFeed, DukInstallReport

__all__ = [
    "ALL_FORMS",
    "OUT_OF_FEED_FORMS",
    "apply_offline_mode",
    "install_dist",
    "secure_url",
    "smoke_test",
    "update_dist",
]

#: Pass this instead of a form name to select every form the feed lists. No
#: real form is named "all", so it cannot collide.
ALL_FORMS = "all"

# ANAF's static host — the only origin a jar may be fetched from.
_STATIC_HOST = "static.anaf.ro"

# Forms whose jars are absent from the update feed, mapped to the distribution
# zip that does carry them. D406T is ANAF's sanctioned no-fiscal-effect SAF-T
# test declaration — the vehicle for verifying the portal filing mechanism —
# and its jars have shipped only inside the dedicated SAF-T zip since 2023.
OUT_OF_FEED_FORMS = {
    "D406T": "https://static.anaf.ro/static/10/Anaf/Informatii_R/duk_SAFT_20230216.zip",
}

# How many downloads run at once. ANAF's rate-limit rule covers the lookup
# services, not this static host; four is brisk for `--forms all` (346 jars)
# without hammering anyone.
_MAX_CONCURRENT_DOWNLOADS = 4

# A deliberately invalid probe document. It carries no namespace, so **every**
# form's validator must reject it — which is exactly what makes it a liveness
# check that needs no per-form valid document: a working dist answers with
# findings naming the expected namespace, while a broken one leaves the empty
# err file (verified against D300, 2026-07-23).
_PROBE_XML = b'<?xml version="1.0" encoding="UTF-8"?>\n<anafpySmokeProbe/>\n'

# The leading bytes of any zip container, jars included.
_ZIP_MAGIC = b"PK\x03\x04"

Progress = Callable[[str], None]


def secure_url(url: str) -> str:
    """Force *url* to HTTPS and pin it to ANAF's static host.

    The feed lists its jar URLs as plain ``http://`` and ANAF publishes no
    checksums, so TLS is the only integrity available — and it is only worth
    anything if the origin is fixed too. An entry pointing anywhere else is
    refused rather than fetched.

    Raises:
        AnafConfigError: *url* is not an ANAF static-host URL.
    """
    parts = urlsplit(url)
    if parts.hostname != _STATIC_HOST or parts.scheme not in ("http", "https"):
        raise AnafConfigError(
            f"refusing to download {url!r}: the DUK update feed may only point "
            f"at https://{_STATIC_HOST}/"
        )
    return parts._replace(scheme="https").geturl()


async def _download(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    """Fetch *url* into *dest*, atomically and only if it looks like its type.

    The write goes to a sibling ``.part`` file and is renamed into place, so an
    interrupted download can never leave a truncated jar behind — that failure
    mode reads downstream as the same empty err file a broken dist produces,
    and is miserable to diagnose.

    Raises:
        AnafTransportError: the download failed, or answered something that is
            not the expected file type.
        AnafResponseError: a non-success HTTP status.
    """
    target = secure_url(url)
    try:
        response = await client.get(target, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise AnafTransportError(f"cannot download {target}: {exc}") from exc
    raise_for_status(response)
    body = response.content
    if dest.suffix == ".jar" and not body.startswith(_ZIP_MAGIC):
        raise AnafTransportError(
            f"{target} did not answer a jar ({len(body)} bytes, no zip magic) — "
            "ANAF likely served an error page; nothing was written"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(body)
    part.replace(dest)


async def _download_all(
    client: httpx.AsyncClient, jobs: Sequence[tuple[str, Path]]
) -> None:
    """Run *jobs* (``(url, dest)`` pairs) with bounded concurrency."""
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DOWNLOADS)

    async def one(url: str, dest: Path) -> None:
        async with semaphore:
            await _download(client, url, dest)

    await asyncio.gather(*(one(url, dest) for url, dest in jobs))


def apply_offline_mode(duk_dir: Path, *, enabled: bool = True) -> None:
    """Set (or clear) ``offLine=Y`` in the dist's ``config/config.properties``.

    DUK's startup update check uses hardcoded Windows paths and can make the
    app **exit silently** on a non-Windows host — exit 0, no err file, no PDF
    (DUK reference §1). ``offLine=Y`` disables that check. anafpy fetches
    updates itself, so the check earns nothing here even where it works, and
    disabling it makes a run deterministic. Verified harmless for both ``-v``
    and ``-p`` (2026-07-23: byte-identical PDF output).
    """
    config = duk_dir / "config" / "config.properties"
    if not config.exists():
        return
    lines = [
        line
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines()
        if not line.strip().lower().startswith("offline=")
    ]
    if enabled:
        lines.append("offLine=Y")
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def smoke_test(duk: DukIntegrator, form: str) -> tuple[bool, str]:
    """Prove the assembled dist can actually run *form*'s validator.

    Runs ``-v`` against :data:`_PROBE_XML`, a namespace-less document every
    validator must reject. A dist that works answers with findings (naming the
    namespace it expected); a broken or mis-versioned one leaves an empty err
    file and no parseable finding — the very signature
    :func:`~anafpy.declaratii.duk._parse_err_file` already distinguishes. This
    is what turns "the files were copied" into "this dist runs on your JVM",
    and it needs no valid document for the form.

    Returns:
        ``(alive, detail)`` — *detail* is DUK's own first finding, or the raw
        output that failed to parse.
    """
    result = await duk.validate(form, _PROBE_XML)
    if result.findings:
        return True, result.findings[0].message.splitlines()[0]
    return False, (
        result.raw.strip()
        or f"the {form} validator produced no output at all — the dist is broken"
    )


def _installed_versions(lib: Path) -> dict[str, str]:
    """``{form: version}`` already present in *lib* (empty for a fresh dir)."""
    if not lib.is_dir():
        return {}
    return {
        form: _form_version(lib, form)
        for jar in sorted(lib.glob("*Validator.jar"))
        if (form := jar.name.removesuffix("Validator.jar"))
    }


async def _install_out_of_feed(
    client: httpx.AsyncClient, form: str, lib: Path, progress: Progress | None
) -> None:
    """Install a form whose jars ship in a distribution zip, not the feed.

    Members are matched by **basename**, so nothing is extracted to a path the
    archive chose — a zip cannot write outside ``lib/``.
    """
    url = secure_url(OUT_OF_FEED_FORMS[form])
    if progress:
        progress(f"{form}: not in the feed — fetching {url_basename(url)}")
    try:
        response = await client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise AnafTransportError(f"cannot download {url}: {exc}") from exc
    raise_for_status(response)
    wanted = {f"{form}Validator.jar", f"{form}Pdf.jar"}
    found: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for member in archive.infolist():
                name = url_basename(member.filename)
                if name in wanted and not member.is_dir():
                    (lib / name).write_bytes(archive.read(member))
                    found.add(name)
    except zipfile.BadZipFile as exc:
        raise AnafTransportError(f"{url} is not a readable zip: {exc}") from exc
    if missing := wanted - found:
        raise AnafConfigError(
            f"{url} does not contain {', '.join(sorted(missing))} — ANAF may have "
            f"replaced the SAF-T distribution; {form} must be installed by hand"
        )


async def _sync(
    duk_dir: Path,
    wanted: Iterable[str],
    *,
    force: bool,
    offline: bool | None,
    http: httpx.AsyncClient | None,
    progress: Progress | None,
) -> DukInstallReport:
    """Fetch the core, then each wanted form, into *duk_dir*."""
    duk_dir = Path(duk_dir).expanduser().resolve()
    lib = duk_dir / "lib"
    owns_http = http is None
    client = http or httpx.AsyncClient(timeout=120.0)
    try:
        if progress:
            progress("reading ANAF's update feed…")
        feed = await fetch_feed(client)
        if not feed.root_jars:
            raise AnafConfigError(
                "ANAF's update feed carried no core jar — refusing to assemble "
                "an incomplete dist; retry later"
            )
        selected = {form.strip() for form in wanted if form.strip()}
        if any(form.lower() == ALL_FORMS for form in selected):
            # Every feed form — what a complete, redistribution-free dist needs.
            # The out-of-feed forms stay opt-in; `all` means "all of the feed".
            selected = {f for f in selected if f.lower() != ALL_FORMS} | set(feed.forms)
        wanted = selected
        unknown = sorted(
            form
            for form in wanted
            if form not in feed.forms and form not in OUT_OF_FEED_FORMS
        )
        if unknown:
            raise AnafConfigError(
                f"unknown form(s) {', '.join(unknown)} — the feed lists "
                f"{len(feed.forms)} forms; check the name against "
                "`anafpy declaratii duk forms`"
            )

        before = _installed_versions(lib)
        jobs = _core_jobs(feed, duk_dir)
        core_files = len(jobs)
        if progress:
            progress(f"core {feed.core_version}: {core_files} files")

        installed: dict[str, str] = {}
        updated: dict[str, str] = {}
        unchanged: list[str] = []
        out_of_feed: list[str] = []
        for form in sorted(set(wanted)):
            if form in OUT_OF_FEED_FORMS:
                # These carry no feed version to compare against, so presence is
                # the only signal — otherwise every `update` would re-fetch the
                # whole SAF-T zip for a form that never changes.
                if (lib / f"{form}Validator.jar").exists() and not force:
                    unchanged.append(form)
                    continue
                out_of_feed.append(form)
                installed[form] = "unversioned"
                continue
            entry = feed.forms[form]
            current = before.get(form)
            if current == entry.validator_version and not force:
                unchanged.append(form)
                continue
            if current is None:
                installed[form] = entry.validator_version
            else:
                updated[form] = f"{current} -> {entry.validator_version}"
            jobs.extend(
                (url, lib / url_basename(url))
                for url in (entry.validator_url, entry.pdf_url, entry.history_url)
                if url
            )

        await _download_all(client, jobs)
        for form in out_of_feed:
            lib.mkdir(parents=True, exist_ok=True)
            await _install_out_of_feed(client, form, lib, progress)

        offline_mode = os.name != "nt" if offline is None else offline
        apply_offline_mode(duk_dir, enabled=offline_mode)

        return DukInstallReport(
            duk_dir=str(duk_dir),
            core_version=feed.core_version,
            core_files=core_files,
            forms_installed=installed,
            forms_updated=updated,
            forms_unchanged=unchanged,
            offline_mode=offline_mode,
        )
    finally:
        if owns_http:
            await client.aclose()


def _core_jobs(feed: DukFeed, duk_dir: Path) -> list[tuple[str, Path]]:
    """The ``(url, dest)`` pairs for the core jar, libraries, and config."""
    lib, config = duk_dir / "lib", duk_dir / "config"
    return [
        *((url, duk_dir / url_basename(url)) for url in feed.root_jars),
        *((url, lib / url_basename(url)) for url in feed.lib_jars),
        *((url, config / url_basename(url)) for url in feed.config_files),
    ]


async def install_dist(
    duk_dir: Path,
    *,
    forms: Iterable[str] = (),
    offline: bool | None = None,
    http: httpx.AsyncClient | None = None,
    progress: Progress | None = None,
) -> DukInstallReport:
    """Assemble a complete DUKIntegrator dist at *duk_dir* from the feed.

    Idempotent: run against an existing dist it refreshes the core and adds any
    *forms* not already at the feed's version. With no *forms* it installs the
    core and ``config/`` only — a usable dist still needs at least one form's
    validator.

    Args:
        duk_dir: where the dist is assembled (created if absent).
        forms: form names to install, e.g. ``("D300", "D394")``.
        offline: whether to set ``offLine=Y``; defaults to True off Windows
            (see :func:`apply_offline_mode`).
        http: an injected client, otherwise one is owned for the call.
        progress: called with human-readable progress lines.

    Raises:
        AnafConfigError: an unknown form name, or a feed with no core jar.
        AnafTransportError: a download failed or answered the wrong file type.
    """
    return await _sync(
        duk_dir,
        forms,
        force=False,
        offline=offline,
        http=http,
        progress=progress,
    )


async def update_dist(
    duk_dir: Path,
    *,
    forms: Iterable[str] = (),
    force: bool = False,
    offline: bool | None = None,
    http: httpx.AsyncClient | None = None,
    progress: Progress | None = None,
) -> DukInstallReport:
    """Refresh *duk_dir*'s core and every installed form that the feed moved past.

    CLI-mode DUK never updates itself, so this is the counterpart to
    ``declaratie_duk_status``: what that tool reports stale, this brings
    current. Forms named in *forms* are added if absent, so an update doubles
    as "also give me D101".

    Args:
        duk_dir: an existing dist.
        forms: extra forms to add alongside the refresh.
        force: re-download even forms already at the feed's version.
        offline: see :func:`apply_offline_mode`.
        http: an injected client, otherwise one is owned for the call.
        progress: called with human-readable progress lines.

    Raises:
        AnafConfigError: *duk_dir* is not a dist, or an unknown form name.
        AnafTransportError: a download failed or answered the wrong file type.
    """
    duk_dir = Path(duk_dir).expanduser().resolve()
    if not (duk_dir / "DUKIntegrator.jar").exists():
        raise AnafConfigError(
            f"{duk_dir} is not a DUKIntegrator dist — run `anafpy declaratii duk "
            "install` first"
        )
    wanted = set(_installed_versions(duk_dir / "lib")) | set(forms)
    return await _sync(
        duk_dir,
        wanted,
        force=force,
        offline=offline,
        http=http,
        progress=progress,
    )
