"""Opt-in live smoke for SPV (``ANAFPY_LIVE=1``) — read-only, production.

SPV has no TEST environment, but ``listaMesaje`` is a pure read, within the
repo's live-testing boundaries. The suite needs an **existing session** in the
default store (``~/.anafpy/spv-session.json``) — establishing one is
interactive (certificate + 2FA), e.g.::

    uv run python -c "
    import asyncio
    from anafpy.spv import CurlBootstrapper, FileSessionStore, SpvClient
    async def main() -> None:
        async with SpvClient(
            session_store=FileSessionStore(),
            bootstrapper=CurlBootstrapper('<your Keychain identity name>'),
        ) as client:
            await client.login()
    asyncio.run(main())
    "

Without ``ANAFPY_LIVE=1`` or without a stored session, everything skips.
"""

from __future__ import annotations

import os

import pytest

from anafpy.spv import FileSessionStore, SpvClient

pytestmark = pytest.mark.live

_live = os.environ.get("ANAFPY_LIVE") == "1"


def _store_or_skip() -> FileSessionStore:
    if not _live:
        pytest.skip("live tests disabled (set ANAFPY_LIVE=1)")
    store = FileSessionStore()
    if store.load() is None:
        pytest.skip(
            "no SPV session in ~/.anafpy/spv-session.json — log in first "
            "(interactive: certificate + 2FA)"
        )
    return store


async def test_lista_mesaje_shape_live() -> None:
    """Re-confirms the wire shape documented in docs/anaf-reference/spv/api.md §2."""
    async with SpvClient(session_store=_store_or_skip()) as client:
        listing = await client.list_messages(5)
    # Either the no-results note or a populated listing with identity fields.
    if listing.note is not None:
        assert listing.messages == []
    else:
        assert listing.cnp
        assert listing.authorized_cuis
        assert listing.certificate_serial
        for message in listing.messages:
            assert message.id
            assert message.kind
            assert message.created_at.tzinfo is not None
