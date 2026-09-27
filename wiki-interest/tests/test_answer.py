"""Tests for the chat-answer check. Run from the skill dir: .venv/bin/python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import answer  # noqa: E402
from test_report import make_run  # noqa: E402


TEMPLATE = """Ukrainian-language Wikipedia is the one to start with.
- Ukrainian-language Wikipedia: {uk_pct:+d}% adjusted, confidence {uk_conf} ({uk_vpd:.0f} views/day, \
{uk_up}/12 months above the year before).
- Polish-language Wikipedia: {pl_pct:+d}% adjusted, confidence {pl_conf} ({pl_vpd:.0f} views/day).
- Czech: no article, so interest there cannot be measured.
Next, check whether the rise holds into 2026.
A language edition is not a country, and views show curiosity, not willingness to pay.
"""


def draft(run):
    """The answer a well-behaved agent would write for this run: every number taken from it."""
    ok = {r["code"]: r for r in run["rows"] if r["status"] == "ok"}
    return TEMPLATE.format(**{f"{c}_{k}": v for c, r in ok.items() for k, v in
                              (("pct", round(r["metrics"]["adj_growth"] * 100)), ("conf", r["confidence"]),
                               ("vpd", r["metrics"]["views_per_day"]), ("up", r["metrics"]["months_up"]))})


class Problems(unittest.TestCase):
    def test_a_correct_answer_passes(self):
        run = make_run()
        problems, _ = answer.review(draft(run), run)
        self.assertEqual(problems, [])

    def test_invented_number_is_caught(self):
        run = make_run()
        problems, _ = answer.review(draft(run) + "That is 4200 readers a day.", run)
        self.assertEqual(problems, ["'4200' is not a number the tool printed"])

    def test_flag_emoji_is_caught(self):
        run = make_run()
        problems, _ = answer.review(draft(run) + "\U0001F1FA\U0001F1E6 is the priority.", run)
        self.assertEqual(len(problems), 1)
        self.assertIn("country flag", problems[0])


class Reminders(unittest.TestCase):
    def reminders(self, text):
        run = make_run()
        return " | ".join(answer.review(text, run)[1])

    def test_missing_limitations_are_named(self):
        text = self.reminders("Ukrainian grows, Polish is flat.")
        self.assertIn("not a country", text)
        self.assertIn("willingness to pay", text)

    def test_limitations_in_another_language_count(self):
        text = self.reminders("Мовний розділ - це не країна, і перегляди показують цікавість, "
                              "а не готовність платити.")
        self.assertNotIn("limitation missing", text)

    def test_language_without_data_is_named(self):
        self.assertIn("cs returned no data", self.reminders("Ukrainian first."))

    def test_missing_confidence_word_is_named(self):
        run = make_run()
        levels = {r["confidence"] for r in run["rows"] if r["status"] == "ok"}
        text = self.reminders("Ukrainian first.")
        for level in levels:
            self.assertIn(level, text)

    def test_stated_confidence_leaves_only_the_reason_reminder(self):
        run = make_run()
        text = self.reminders(draft(run))
        self.assertNotIn("no word found", text)
        self.assertIn("reason next to each confidence level", text)

    def test_an_inflected_confidence_word_counts(self):
        # A Haiku run wrote "НИЗЬКІЙ" where the locale has "НИЗЬКА" and was told the level was missing.
        run = make_run()
        text = "\n".join(f"{r['code']}: довіра {'ВИСОКІЙ' if r['confidence'] == 'HIGH' else 'СЕРЕДНІЙ'}"
                         for r in run["rows"] if r["status"] == "ok")
        self.assertNotIn("no word found", " | ".join(answer.review(text, run)[1]))

    def test_causes_are_always_flagged(self):
        self.assertIn("no causes", self.reminders(draft(make_run())))


if __name__ == "__main__":
    unittest.main()
