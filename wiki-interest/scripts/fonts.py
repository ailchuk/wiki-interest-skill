"""Extra Noto fonts for scripts DejaVu Sans lacks (CJK, Arabic, Hebrew, Indic, Thai).

Downloaded on first use from pinned commits, checked by SHA-256, cached next to the API cache.
Latin, Cyrillic and Greek need nothing: DejaVu Sans (bundled with matplotlib) covers them.
"""
import hashlib
import urllib.request

from fontTools.ttLib import TTFont

import wikiapi

GOOGLE = "https://raw.githubusercontent.com/google/fonts/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/ofl"
NOTO = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/f145d86c53996717bc4c25d4602eb9294e43dccc/fonts"

# key: (file, url, sha256, variable-font weight or None)
FONTS = {
    "ja": ("NotoSansJP[wght].ttf", f"{GOOGLE}/notosansjp/NotoSansJP%5Bwght%5D.ttf",
           "c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f", 400),
    "zh": ("NotoSansSC[wght].ttf", f"{GOOGLE}/notosanssc/NotoSansSC%5Bwght%5D.ttf",
           "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da", 400),
    "ko": ("NotoSansKR[wght].ttf", f"{GOOGLE}/notosanskr/NotoSansKR%5Bwght%5D.ttf",
           "194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252", 400),
    "arabic": ("NotoSansArabic-Regular.ttf", f"{NOTO}/NotoSansArabic/hinted/ttf/NotoSansArabic-Regular.ttf",
               "bdff3e5659d67e67def05b33f749683b9376ae819d65d3dd62ac4640b3aaef48", None),
    "hebrew": ("NotoSansHebrew-Regular.ttf", f"{NOTO}/NotoSansHebrew/hinted/ttf/NotoSansHebrew-Regular.ttf",
               "cdefaf8efd47045f6820928eba84db5bed7557539328952b5f828315485e02ee", None),
    "devanagari": ("NotoSansDevanagari-Regular.ttf",
                   f"{NOTO}/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Regular.ttf",
                   "4e3c66638958c3e2ab5d37f47a8deb89fffeb7be9985c665a519bbc7ba762313", None),
    "bengali": ("NotoSansBengali-Regular.ttf", f"{NOTO}/NotoSansBengali/hinted/ttf/NotoSansBengali-Regular.ttf",
                "b55c62ee531e3214da6c0701daecea89a52ba42db7d8206b92e6b51f397a3193", None),
    "thai": ("NotoSansThai-Regular.ttf", f"{NOTO}/NotoSansThai/hinted/ttf/NotoSansThai-Regular.ttf",
             "61cf814eec46b294d6ea4401ac295d0cecd5207bd2331dcc5a15e7301d30ee44", None),
}

RANGES = [  # (first, last, key); "cjk" is resolved by language
    (0x0590, 0x05FF, "hebrew"), (0xFB1D, 0xFB4F, "hebrew"),
    (0x0600, 0x06FF, "arabic"), (0x0750, 0x077F, "arabic"), (0x08A0, 0x08FF, "arabic"),
    (0xFB50, 0xFDFF, "arabic"), (0xFE70, 0xFEFF, "arabic"),
    (0x0900, 0x097F, "devanagari"), (0xA8E0, 0xA8FF, "devanagari"),
    (0x0980, 0x09FF, "bengali"), (0x0E00, 0x0E7F, "thai"),
    (0x3040, 0x30FF, "ja"), (0x31F0, 0x31FF, "ja"),
    (0x1100, 0x11FF, "ko"), (0x3130, 0x318F, "ko"), (0xAC00, 0xD7AF, "ko"),
    (0x3000, 0x303F, "cjk"), (0x3400, 0x4DBF, "cjk"), (0x4E00, 0x9FFF, "cjk"),
    (0xF900, 0xFAFF, "cjk"), (0xFF00, 0xFFEF, "cjk"),
]
SHAPED = {"arabic", "hebrew", "devanagari", "bengali", "thai"}  # need HarfBuzz shaping / bidi
RTL = {"arabic", "hebrew"}


class FontError(RuntimeError):
    pass


def needed(text, lang="en"):
    """Font keys needed for `text`, in fallback order. Han characters use the report language's font."""
    keys = set()
    for ch in text:
        cp = ord(ch)
        for first, last, key in RANGES:
            if first <= cp <= last:
                keys.add(key)
                break
    if "cjk" in keys:
        keys.discard("cjk")
        keys.add(lang if lang in ("ja", "ko") else ("ja" if "ja" in keys else "zh"))
    order = [lang] + list(FONTS) if lang in FONTS else list(FONTS)
    return list(dict.fromkeys(k for k in order if k in keys))


def path(key):
    """Local path of a font, downloading and verifying it on first use."""
    file, url, sha, _ = FONTS[key]
    dest = wikiapi.CACHE_DIR / "fonts" / file
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": wikiapi.USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except OSError as e:
        raise FontError(f"could not download {file}: {e}") from e
    if hashlib.sha256(data).hexdigest() != sha:
        raise FontError(f"checksum mismatch for {file}; not used")
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def covers(key, text):
    """Characters of `text` that the font `key` can draw (for tests and warnings)."""
    with TTFont(path(key), lazy=True) as font:
        cmap = font.getBestCmap()
    return {ch for ch in text if ord(ch) in cmap}
