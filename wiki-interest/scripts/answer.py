"""Check a draft chat answer against the run, the way `report` checks findings.md.

The PDF path is protected by code: a wrong number stops it, and the assumptions and limitations
blocks are written by the tool. The chat answer had no such gate - it rested on rules the model
may ignore, and the evals show it sometimes does. This module closes that gap.

Two kinds of output. Problems are things code can decide on its own in any language: a number
that is not in the data, a sign pointing the wrong way, a flag emoji standing in for a language
edition. Reminders are things code can only guess at, because the answer is written in the user's
language and in the model's own words; they are printed as a checklist, never as a blocker.
"""
import re

import render
from i18n import TEXT

# Two regional indicator letters make a flag. A flag turns a language edition into a country,
# which is exactly the claim the data cannot support.
FLAG_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")

# One stem per locale for each mandatory limitation. Prefixes, because the model inflects freely;
# word boundaries for alphabetic scripts, so "Poland" does not pass as the German word for country.
NOT_A_COUNTRY = re.compile(
    r"\bcountr|\bкраїн|\bkraj|\bzem[ěeií]|\bland\b|\bländer|\bpaís|\bpais\b|\bpays\b|\bülke|\bquốc gia"
    r"|\bnư[ơớ]c\b|国|بلد|دول|देश", re.IGNORECASE)
NOT_PAYING = re.compile(
    r"\bpay|\bплат|\bpłac|\bplatit|\bplac[eí]|\bzahl|\bpagar|\bpayer|\böde|\btrả tiền|\bchi trả"
    r"|支払|課金|付费|支付|الدفع|تدفع|भुगतान", re.IGNORECASE)

def _stem(word):
    """Cut the last two letters off, so an inflected form still matches: НИЗЬКА also covers НИЗЬКІЙ."""
    return word[:max(3, len(word) - 2)]


# Every locale's word for each level, plus the English one: models often keep "LOW" verbatim.
CONF_RE = {lvl: re.compile("|".join(sorted({rf"\b{re.escape(_stem(loc[lvl]))}" for loc in TEXT.values()}
                                           | {rf"\b{lvl}"})), re.IGNORECASE)
           for lvl in ("HIGH", "MEDIUM", "LOW")}

BOT_MONTHS = ("2025-03", "2025-08")  # the Wikimedia bot reclassification window


def review(text, run):
    """Returns (problems, reminders) for a draft answer. Problems must be fixed before replying."""
    problems = render.check_text(text, run)
    for flag in dict.fromkeys(FLAG_RE.findall(text)):
        problems.append(f"'{flag}' is a country flag: name the language edition instead")

    reminders = []
    missing = [r["code"] for r in run["rows"] if r["status"] != "ok"]
    if missing:
        reminders.append(f"{', '.join(missing)} returned no data: say interest there could not be measured, "
                         f"and do not answer for them with another language or another article")
    unstated = [lvl for lvl, rx in CONF_RE.items()
                if any(r["confidence"] == lvl for r in run["rows"]) and not rx.search(text)]
    if unstated:
        reminders.append(f"no word found for {', '.join(unstated)}: the data has editions at "
                         f"{'this level' if len(unstated) == 1 else 'these levels'} and each one needs its level "
                         f"and the reason for it")
    else:
        reminders.append("give the reason next to each confidence level, not the level alone")
    if not NOT_A_COUNTRY.search(text):
        reminders.append("limitation missing: a language edition is not a country")
    if not NOT_PAYING.search(text):
        reminders.append("limitation missing: views show curiosity, not willingness to pay")
    if run["months"][0] <= BOT_MONTHS[1] and BOT_MONTHS[0] <= run["months"][-1]:
        reminders.append("the period covers the 2025 bot reclassification: say so if you report a decline")
    reminders.append("no causes, competition, market size or revenue: pageviews do not show them")
    return problems, reminders
