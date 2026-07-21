"""Tests for the ``anafpy`` CLI (login/status/logout; loopback-only network)."""

from __future__ import annotations

import datetime
import json
import socket
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from anafpy.auth import FileTokenStore, KeyringTokenStore, TokenSet
from anafpy.auth.oauth import TOKEN_URL
from anafpy.cli.main import main
from conftest import FakeKeyring


def _file_args(store: Path) -> list[str]:
    return ["--store-backend", "file", "--store", str(store)]


def test_status_not_authenticated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["auth", "status", *_file_args(tmp_path / "tokens.json")]) == 1
    assert "not authenticated" in capsys.readouterr().out


def test_status_reports_token_validity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    # Non-JWT tokens: expiry falls back to the documented 90/365-day TTLs.
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", *_file_args(store)]) == 0
    out = capsys.readouterr().out
    assert "authenticated" in out
    assert "~90 days left" in out
    assert "~365 days left" in out


def test_store_env_is_read_at_parse_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # ANAFPY_TOKEN_STORE / ANAFPY_TOKEN_STORE_BACKEND must be honoured even when
    # set after module import, so wrappers and tests can configure them.
    store = tmp_path / "tokens.json"
    FileTokenStore(store).save(TokenSet(access_token="a", refresh_token="r"))
    monkeypatch.setenv("ANAFPY_TOKEN_STORE", str(store))
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "file")
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_status_ignores_stored_expiry_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Expiries are computed from the tokens, so stale `*_expires_at` keys in an
    # older store must be ignored, not trusted.
    store = tmp_path / "tokens.json"
    store.write_text(
        json.dumps(
            {
                "access_token": "a",
                "refresh_token": "r",
                "obtained_at": time.time(),
                "access_expires_at": time.time() - 86400,  # stale: claims expired
                "refresh_expires_at": time.time() - 86400,
            }
        ),
        encoding="utf-8",
    )
    assert main(["auth", "status", *_file_args(store)]) == 0
    assert "~90 days left" in capsys.readouterr().out


def test_status_corrupt_store_is_a_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "status", *_file_args(store)]) == 1
    assert "token store" in capsys.readouterr().err


def test_keyring_is_the_default_backend(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # No flags, no env: tokens come from the (fake, autouse) OS credential store.
    monkeypatch.delenv("ANAFPY_TOKEN_STORE_BACKEND", raising=False)
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_status_reads_the_keyring_backend(
    fake_keyring: FakeKeyring, capsys: pytest.CaptureFixture[str]
) -> None:
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status", "--store-backend", "keyring"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_status_env_selects_the_keyring_backend(
    fake_keyring: FakeKeyring,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "keyring")
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "status"]) == 0
    assert "authenticated" in capsys.readouterr().out


def test_unknown_store_backend_from_env_is_a_cli_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The backend is deliberately a plain str (no Literal): a bad env value must
    # travel the AnafConfigError path, not exit via a cyclopts parse error.
    monkeypatch.setenv("ANAFPY_TOKEN_STORE_BACKEND", "vault")
    assert main(["auth", "status"]) == 1
    assert "backend" in capsys.readouterr().err


# --- auth logout ------------------------------------------------------------------


def _saved_store(tmp_path: Path) -> Path:
    path = tmp_path / "tokens.json"
    FileTokenStore(path).save(TokenSet(access_token="acc", refresh_token="ref"))
    return path


def test_logout_not_authenticated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["auth", "logout", *_file_args(tmp_path / "tokens.json")]) == 0
    assert "nothing to remove" in capsys.readouterr().out


def test_logout_clears_the_store_without_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Logout is purely local (ANAF's /revoke is not reachable headlessly —
    # live-probed 2026-07-05): no respx mock is active, so any HTTP attempt
    # would hit the real network and fail loudly.
    store = _saved_store(tmp_path)
    assert main(["auth", "logout", *_file_args(store)]) == 0
    assert not store.exists()
    assert "Logged out" in capsys.readouterr().out


def test_logout_corrupt_store_is_still_cleared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Logout must be able to get rid of a store that status/login cannot even read.
    store = tmp_path / "tokens.json"
    store.write_text("{not json", encoding="utf-8")
    assert main(["auth", "logout", *_file_args(store)]) == 0
    assert not store.exists()
    assert "unreadable" in capsys.readouterr().err


def test_logout_clears_the_keyring_backend(
    fake_keyring: FakeKeyring, capsys: pytest.CaptureFixture[str]
) -> None:
    KeyringTokenStore().save(TokenSet(access_token="a", refresh_token="r"))
    assert main(["auth", "logout", "--store-backend", "keyring"]) == 0
    assert fake_keyring.entries == {}
    assert "Logged out" in capsys.readouterr().out


# --- spv ------------------------------------------------------------------------------


def _spv_args(tmp_path: Path) -> list[str]:
    return [
        "--session",
        str(tmp_path / "spv-session.json"),
        "--identity-file",
        str(tmp_path / "spv-identity.json"),
    ]


def test_spv_status_without_session(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["spv", "status", *_spv_args(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "anafpy spv login" in out


def test_spv_logout_clears_the_session_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from datetime import UTC, datetime

    from anafpy.spv import FileSessionStore, SpvSession

    store = FileSessionStore(tmp_path / "spv-session.json")
    store.save(
        SpvSession(cookies={"MRHSession": "x"}, established_at=datetime.now(tz=UTC))
    )
    assert main(["spv", "logout", *_spv_args(tmp_path)]) == 0
    assert store.load() is None
    assert "removed" in capsys.readouterr().out


def test_spv_select_and_certs_roundtrip(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from anafpy.spv import StoreIdentity

    identity = StoreIdentity(
        name="MIHAI-ROBERT MALAI",
        sha1_thumbprint="C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D",
        platform="darwin",
    )
    monkeypatch.setattr("anafpy.spv.certs.discover_identities", lambda: [identity])
    monkeypatch.setattr("anafpy.cli.main.discover_identities", lambda: [identity])
    assert main(["spv", "select", identity.sha1_thumbprint, *_spv_args(tmp_path)]) == 0
    assert "Selected" in capsys.readouterr().out
    assert main(["spv", "certs", *_spv_args(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "(selected)" in out


def test_spv_login_without_identity_or_selection_is_actionable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("anafpy.cli.main.discover_identities", lambda: [])
    assert main(["spv", "login", *_spv_args(tmp_path)]) == 1
    assert "anafpy spv certs" in capsys.readouterr().err


@respx.mock
def test_spv_login_reports_success_even_when_the_probe_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Observed live 2026-07-13: the identity probe can raise right after a good
    # login. The session is established and saved — the CLI must say so (exit
    # 0), not make the user re-fire their 2FA.
    from datetime import UTC, datetime

    from anafpy.spv import FileSessionStore, SpvSession, StoreIdentity

    identity = StoreIdentity(
        name="MIHAI-ROBERT MALAI",
        sha1_thumbprint="C5E18AB56B0AC30A05BE8D526610F17BB2EF9E7D",
        platform="darwin",
    )
    monkeypatch.setattr("anafpy.cli.main.discover_identities", lambda: [identity])

    class FakeBootstrapper:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def bootstrap(self) -> SpvSession:
            return SpvSession(
                cookies={"MRHSession": "fresh"},
                established_at=datetime.now(tz=UTC),
            )

    monkeypatch.setattr("anafpy.cli.main.CurlBootstrapper", FakeBootstrapper)
    respx.get("https://webserviced.anaf.ro/SPVWS2/rest/listaMesaje").respond(500)
    assert main(["spv", "login", *_spv_args(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "SPV session established" in out
    assert "identity probe failed" in out
    saved = FileSessionStore(tmp_path / "spv-session.json").load()
    assert saved is not None
    assert saved.cookies == {"MRHSession": "fresh"}


# --- declaratii -------------------------------------------------------------------


def _duk_dir(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "lib").mkdir(parents=True)
    (dist / "DUKIntegrator.jar").write_text("")
    return dist


def _fake_duk_run(err: str) -> Any:
    async def run(self: object, args: list[str]) -> tuple[int, bytes, bytes]:
        Path(args[3]).write_text(err, encoding="utf-8")
        # Like real DUK, a clean OR warning-only run still renders the PDF.
        has_error = any(line.startswith(("E:", "F:")) for line in err.splitlines())
        if "-p" in args and not has_error:
            Path(args[-1]).write_bytes(b"%PDF-1.7\n")
        return 0, b"", b""

    return run


def test_declaratii_validate_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("ok"))
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    code = main(
        [
            "declaratii",
            "validate",
            "D300",
            str(xml),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_declaratii_validate_reports_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("E: eroare: R25 lipseste"))
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    code = main(
        [
            "declaratii",
            "validate",
            "D300",
            str(xml),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 1
    assert "R25" in capsys.readouterr().out


def test_declaratii_render_writes_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("ok"))
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    out = tmp_path / "d300.pdf"
    code = main(
        [
            "declaratii",
            "render",
            "D300",
            str(xml),
            "-o",
            str(out),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    assert out.read_bytes().startswith(b"%PDF")


def test_declaratii_validate_prints_warnings_on_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A warning-only run passes but must still surface DUK's notices."""
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(
        DukIntegrator,
        "_run",
        _fake_duk_run("A: formularul se prelucreaza la organul fiscal competent"),
    )
    xml = tmp_path / "d700.xml"
    xml.write_text("<x/>")
    code = main(
        [
            "declaratii",
            "validate",
            "D700",
            str(xml),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "WARNING: formularul se prelucreaza" in out
    assert "valid" in out


def test_declaratii_render_prints_warnings_on_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("A: atentionare"))
    xml = tmp_path / "d700.xml"
    xml.write_text("<x/>")
    out = tmp_path / "d700.pdf"
    code = main(
        [
            "declaratii",
            "render",
            "D700",
            str(xml),
            "-o",
            str(out),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    assert out.read_bytes().startswith(b"%PDF")
    captured = capsys.readouterr().out
    assert "WARNING: atentionare" in captured
    assert "Rendered" in captured


def test_declaratii_validate_missing_xml_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bad path exits via the `error: ...` convention, not a traceback."""
    code = main(
        [
            "declaratii",
            "validate",
            "D300",
            str(tmp_path / "nope.xml"),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert err.startswith("error: cannot read declaration XML")
    assert "nope.xml" in err


def test_declaratii_validate_without_duk_dir_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ANAFPY_DUK_DIR", raising=False)
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    assert main(["declaratii", "validate", "D300", str(xml)]) == 1
    assert "ANAFPY_DUK_DIR" in capsys.readouterr().err


def test_declaratii_status_prints_unclassified_wire_wording(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii import DeclarationStatusClient
    from anafpy.declaratii.models import (
        DeclarationDocument,
        DeclarationState,
        DeclarationStatusList,
    )

    async def status(
        _self: DeclarationStatusClient,
        _index: int | str,
        _cui: int | str,
        *,
        filed_at_counter: bool = False,
    ) -> DeclarationStatusList:
        assert filed_at_counter is False
        return DeclarationStatusList(
            found=True,
            cui="99999909",
            documents=[
                DeclarationDocument(
                    index="1100000001",
                    form="D300",
                    state=DeclarationState.UNKNOWN,
                    state_text="Document în verificare manuală",
                    registration="INTERNT-1100000001-2026",
                    upload_date=datetime.date(2026, 7, 17),
                    receipt_available=False,
                )
            ],
        )

    monkeypatch.setattr(DeclarationStatusClient, "check_status", status)
    assert main(["declaratii", "status", "1100000001", "99999909"]) == 0
    output = capsys.readouterr().out
    assert "Document în verificare manuală" in output
    assert " unknown " not in output


def test_declaratii_status_ghiseu_marks_the_queried_registration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --ghiseu the queried-row marker matches the registration number.

    The query key is the counter registration number — the internet upload
    index in the Index column can never equal it.
    """
    from anafpy.declaratii import DeclarationStatusClient
    from anafpy.declaratii.models import (
        DeclarationDocument,
        DeclarationState,
        DeclarationStatusList,
    )

    def row(index: str, registration: str) -> DeclarationDocument:
        return DeclarationDocument(
            index=index,
            form="D300",
            state=DeclarationState.VALID,
            state_text="Documentul este valid",
            registration=registration,
            upload_date=datetime.date(2026, 7, 16),
            receipt_available=True,
        )

    async def status(
        _self: DeclarationStatusClient,
        _index: int | str,
        _cui: int | str,
        *,
        filed_at_counter: bool = False,
    ) -> DeclarationStatusList:
        assert filed_at_counter is True
        return DeclarationStatusList(
            found=True,
            cui="99999909",
            documents=[
                row("1100000001", "INTERNT-1100000001-2026 din 10.07.2026"),
                row("1100000002", "REG-555/2026 din 16.07.2026"),
            ],
        )

    monkeypatch.setattr(DeclarationStatusClient, "check_status", status)
    assert main(["declaratii", "status", "REG-555/2026", "99999909", "--ghiseu"]) == 0
    lines = capsys.readouterr().out.splitlines()
    marked = [line for line in lines if line.endswith("←")]
    assert len(marked) == 1
    assert "1100000002" in marked[0]


def test_declaratii_render_notes_replaced_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Overwrite-by-default stands, but replacing a file is never silent."""
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("ok"))
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    out = tmp_path / "d300.pdf"
    out.write_bytes(b"an earlier render")
    code = main(
        [
            "declaratii",
            "render",
            "D300",
            str(xml),
            "-o",
            str(out),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert f"replaced existing {out}" in output
    assert "Rendered" in output
    assert out.read_bytes().startswith(b"%PDF")


def test_declaratii_render_fresh_file_prints_no_replacement_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii.duk import DukIntegrator

    monkeypatch.setattr(DukIntegrator, "_run", _fake_duk_run("ok"))
    xml = tmp_path / "d300.xml"
    xml.write_text("<x/>")
    out = tmp_path / "fresh.pdf"
    code = main(
        [
            "declaratii",
            "render",
            "D300",
            str(xml),
            "-o",
            str(out),
            "--duk-dir",
            str(_duk_dir(tmp_path)),
            "--java",
            "java",
        ]
    )
    assert code == 0
    assert "replaced existing" not in capsys.readouterr().out


def test_declaratii_recipisa_notes_replaced_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from anafpy.declaratii import DeclarationStatusClient

    async def download(_self: DeclarationStatusClient, _index: int | str) -> bytes:
        return b"%PDF-1.7 recipisa"

    monkeypatch.setattr(DeclarationStatusClient, "download_receipt", download)
    out = tmp_path / "recipisa.pdf"
    out.write_bytes(b"old receipt")
    assert main(["declaratii", "recipisa", "1100000001", "-o", str(out)]) == 0
    output = capsys.readouterr().out
    assert f"replaced existing {out}" in output
    assert out.read_bytes() == b"%PDF-1.7 recipisa"


# --- auth login (callback capture modes) ----------------------------------------------


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _login_args(tmp_path: Path, redirect_uri: str) -> list[str]:
    return [
        "auth",
        "login",
        "--client-id",
        "CID",
        "--client-secret",
        "SECRET",
        "--redirect-uri",
        redirect_uri,
        *_file_args(tmp_path / "tokens.json"),
    ]


def test_login_flag_conflicts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _login_args(tmp_path, "https://localhost:9002/callback")
    assert main([*base, "--paste", "--tls-cert", "cert.pem"]) == 2
    assert main([*base, "--paste", "--no-tls"]) == 2
    assert main([*base, "--no-tls", "--tls-cert", "cert.pem"]) == 2
    assert main([*base, "--tls-key", "key.pem"]) == 2
    err = capsys.readouterr().err
    assert "--paste runs no listener" in err
    assert "--no-tls and --tls-cert are mutually exclusive" in err
    assert "--tls-key requires --tls-cert" in err


def test_login_default_serves_ephemeral_tls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # No flags, https:// redirect: the listener must come up with the generated
    # self-signed certificate, capture the state-bound code from the "browser",
    # and complete the exchange — the full default login path.
    port = _free_port()
    redirect_uri = f"https://127.0.0.1:{port}/callback"

    def fake_browser(url: str) -> bool:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        state = query["state"][0]

        def hit() -> None:
            for _ in range(50):
                try:
                    httpx.get(
                        f"{redirect_uri}?code=cli-code&state={state}", verify=False
                    )
                    return
                except httpx.TransportError:  # listener not up yet
                    time.sleep(0.05)

        threading.Thread(target=hit, daemon=True).start()
        return True

    monkeypatch.setattr("anafpy.cli.main.webbrowser.open", fake_browser)
    with respx.mock(assert_all_called=True) as router:
        router.route(host="127.0.0.1").pass_through()
        token_route = router.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "acc",
                    "refresh_token": "ref",
                    "token_type": "Bearer",
                },
            )
        )
        assert main(_login_args(tmp_path, redirect_uri)) == 0
    assert "self-signed certificate" in capsys.readouterr().out
    assert "code=cli-code" in token_route.calls.last.request.content.decode()
    tokens = FileTokenStore(tmp_path / "tokens.json").load()
    assert tokens is not None
    assert tokens.access_token == "acc"
