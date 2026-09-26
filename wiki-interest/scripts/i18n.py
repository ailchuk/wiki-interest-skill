"""Fixed texts for charts and PDF reports (scripts/locales/<lang>.json) and confidence reasons (English, for the agent).

Languages without a locale file get English labels. Charts use English labels for scripts that
matplotlib cannot lay out well (Arabic, Devanagari, CJK); the PDF itself supports them via fonts.py.
"""
import json
from pathlib import Path

LOCALES = Path(__file__).resolve().parent / "locales"
TEXT = {p.stem: json.loads(p.read_text("utf-8")) for p in sorted(LOCALES.glob("*.json"))}
LANGS = tuple(TEXT)
CHART_LANGS = ("en", "uk", "pl", "cs", "de", "es", "pt", "tr", "vi", "fr")  # DejaVu Sans covers these
RTL_LANGS = ("ar",)

REASONS = {
    "low_volume": "low volume: {vpd:.1f} views/day (under {min} = LOW)",
    "appeared": "no views in the first {months} month(s): article created or renamed during the period",
    "no_baseline": "no views in the previous 12 months: growth undefined",
    "spike_driven": "growth comes from spike days: {growth} raw vs {clean} without spikes",
    "volume_ok": "solid volume: {vpd:.0f} views/day",
    "moderate_volume": "moderate volume: {vpd:.0f} views/day (HIGH needs {min}+)",
    "steady_up": "{n}/12 months above the same month a year earlier",
    "steady_down": "{n}/12 months below the same month a year earlier",
    "steady_flat": "without spikes the change is within +-5%",
    "unsteady_up": "only {n}/12 months above the same month a year earlier (HIGH needs {need})",
    "unsteady_down": "only {n}/12 months below the same month a year earlier (HIGH needs {need})",
    "agree": "same direction after adjusting for total Wikipedia traffic",
    "disagree": "trend differs after adjusting for total Wikipedia traffic: {clean} without spikes, {adj} adjusted, "
                "whole Wikipedia {wiki}",
}


def lang_or_en(lang):
    return lang if lang in LANGS else "en"


def chart_lang(lang):
    return lang if lang in CHART_LANGS else "en"


def t(lang, key, **kw):
    s = TEXT[lang_or_en(lang)][key]
    return s.format(**kw) if kw else s


def pct(x):
    """0.123 -> '+12%'; None -> 'n/a'. Integers only, so reports and checks agree."""
    if x is None:
        return "n/a"
    v = round(x * 100)
    return "0%" if v == 0 else f"{v:+d}%"


def reason(code, params):
    p = dict(params)
    for k in ("growth", "clean", "adj", "wiki"):
        if k in p:
            p[k] = pct(p[k])
    if code in ("steady", "unsteady"):
        code = f"{code}_{ {1: 'up', -1: 'down', 0: 'flat'}[p['dir']] }"
    return REASONS[code].format(**p)
