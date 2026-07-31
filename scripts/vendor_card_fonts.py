"""Re-vendor the OFL fonts the UIT card renderer embeds.

Run only when refreshing the fonts (they are committed, like the XSDs):

    uv run python scripts/vendor_card_fonts.py

Downloads Noto Sans (regular + bold) and Noto Sans Mono (bold) from the
upstream ``notofonts`` release trees and writes subsetted copies into
``src/anafpy/etransport/_fonts/``.

Why subset: the full faces are ~600 kB each, and a wheel's contents are not
conditional on extras — every ``pip install anafpy`` would carry 1.8 MB for a
feature most users never enable. Restricting the glyph set to Latin (including
the comma-below diacritics Romanian needs), Greek, Cyrillic, punctuation and
currency brings the three files to ~340 kB together while still covering the
partner and carrier names an e-Transport filing can carry across the region.

Why these faces: fpdf2's built-in core fonts are Latin-1 only, so ``ș``/``ț``
are unrepresentable in them; the card is a Romanian document and must render
its own labels. Bundling rather than discovering a system font keeps the output
byte-identical across macOS, Windows and Linux, and keeps the renderer from
failing at run time on a machine with no suitable face installed.
"""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

from fontTools import subset

DEST = Path(__file__).resolve().parent.parent / "src/anafpy/etransport/_fonts"
BASE = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts"
LICENSE_URL = (
    "https://raw.githubusercontent.com/notofonts/latin-greek-cyrillic/main/OFL.txt"
)

FACES = {
    "NotoSans-Regular.ttf": f"{BASE}/NotoSans/hinted/ttf/NotoSans-Regular.ttf",
    "NotoSans-Bold.ttf": f"{BASE}/NotoSans/hinted/ttf/NotoSans-Bold.ttf",
    "NotoSansMono-Bold.ttf": f"{BASE}/NotoSansMono/hinted/ttf/NotoSansMono-Bold.ttf",
}

# Latin + Latin Extended-A/B (U+0218-021B are Romania's comma-below letters),
# IPA, Greek, Cyrillic, Latin Extended Additional, general punctuation (the em
# dash and the Romanian quote marks), currency, and arrows. Note Noto Sans has
# no U+2192 arrow of its own, so the renderer never emits one.
UNICODES = ",".join(
    (
        "U+0000-024F",
        "U+0250-02AF",
        "U+0370-03FF",
        "U+0400-04FF",
        "U+1E00-1EFF",
        "U+2000-206F",
        "U+20A0-20BF",
        "U+2190-21FF",
        "U+FEFF",
    )
)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    staging = DEST / "_download"
    staging.mkdir(exist_ok=True)
    try:
        for name, url in FACES.items():
            raw = staging / name
            with urllib.request.urlopen(url) as response:
                raw.write_bytes(response.read())
            subset.main(
                [
                    str(raw),
                    f"--unicodes={UNICODES}",
                    f"--output-file={DEST / name}",
                    "--layout-features=kern,liga",
                    "--no-hinting",
                    "--desubroutinize",
                ]
            )
            print(
                f"{name}: {raw.stat().st_size // 1024}K -> "
                f"{(DEST / name).stat().st_size // 1024}K"
            )
        with urllib.request.urlopen(LICENSE_URL) as response:
            (DEST / "OFL.txt").write_bytes(response.read())
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
