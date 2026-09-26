"""Report tests on a synthetic run (no network). Run from the skill dir: .venv/bin/python -m unittest discover -s tests"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import metrics as M  # noqa: E402
import render  # noqa: E402
from test_metrics import MONTHS, LAST_YEAR_START, series, wiki  # noqa: E402


def make_run():
    rows = []
    for code, fn in (("uk", lambda d: 150 if d >= LAST_YEAR_START else 100), ("pl", lambda d: 200)):
        m = M.analyze_series(series(fn), wiki(), MONTHS)
        m["wiki_monthly"] = wiki()
        level, reasons = M.confidence(m)
        rows.append({"code": code, "english": code, "project": f"{code}.wikipedia", "title": f"Article {code}",
                     "proxy": False, "status": "ok", "confidence": level, "reasons": reasons, "metrics": m,
                     "trend": M.trend(m)})
    rows.append({"code": "cs", "english": "Czech", "project": "cs.wikipedia", "title": None, "proxy": False,
                 "status": "missing", "confidence": None, "reasons": []})
    return {"created": "2026-09-26", "qid": "Q1", "label": "test", "langs": ["uk", "pl", "cs"], "months": MONTHS,
            "sort": "confidence", "command": "bash /x/scripts/wi analyze Q1 --langs uk,pl,cs", "rows": M.rank(rows)}


FINDINGS = """# Test title
Question: Is interest growing?

## Findings
- uk grows +50% (HIGH), 12/12 months above last year.
- pl is flat: 0% adjusted.

## Recommendation
Focus on uk.
"""


class Findings(unittest.TestCase):
    def test_parse(self):
        doc = render.parse_findings(FINDINGS)
        self.assertEqual(doc["title"], "Test title")
        self.assertEqual(doc["question"], "Is interest growing?")
        self.assertEqual([s["heading"] for s in doc["sections"]], ["Findings", "Recommendation"])

    def test_numbers_match(self):
        self.assertEqual(render.check_numbers(render.parse_findings(FINDINGS), make_run()), [])

    def test_wrong_percent_is_caught(self):
        bad = render.check_numbers(render.parse_findings(FINDINGS.replace("+50%", "+35%")), make_run())
        self.assertEqual(len(bad), 1)
        self.assertIn("35%", bad[0])

    def test_wrong_months_is_caught(self):
        bad = render.check_numbers(render.parse_findings(FINDINGS.replace("12/12", "7/12")), make_run())
        self.assertIn("'7/12' is not in the data", bad)

    def test_flipped_sign_is_caught(self):
        bad = render.check_numbers(render.parse_findings(FINDINGS.replace("+50%", "-50%")), make_run())
        self.assertEqual(len(bad), 1)
        self.assertIn("points the wrong way", bad[0])
        self.assertIn("+50%", bad[0])

    def test_unsigned_percent_matches_on_magnitude(self):
        # The direction lives in the words ("fell by 50%"), so an unsigned number is not a sign error.
        text = FINDINGS.replace("uk grows +50%", "uk fell by 50%")
        self.assertEqual(render.check_numbers(render.parse_findings(text), make_run()), [])

    def test_invented_count_is_caught(self):
        text = FINDINGS.replace("Focus on uk.", "Focus on uk: 1500 views per day is a big audience.")
        bad = render.check_numbers(render.parse_findings(text), make_run())
        self.assertEqual(bad, ["'1500' is not a number the tool printed"])

    def test_real_counts_and_dates_pass(self):
        text = FINDINGS.replace("Focus on uk.",
                                "uk has 150 views/day over 2024-09..2026-08, all 24 months, even in 2025.")
        self.assertEqual(render.check_numbers(render.parse_findings(text), make_run()), [])

    def test_question_is_not_checked(self):
        text = FINDINGS.replace("Is interest growing?", "Did it grow 99%?")
        self.assertEqual(render.check_numbers(render.parse_findings(text), make_run()), [])

    def test_markdown_written_by_model(self):
        # Real shapes from Haiku runs: bold question label, bold at bullet start, bold paragraph start.
        doc = render.parse_findings("# T\n**Питання:** Чи росте?\n\n## Результати\n- **Іспанська**: -10%\n"
                                    "**Пріоритет 1:** іспанська\n")
        self.assertEqual((doc["question_label"], doc["question"]), ("Питання", "Чи росте?"))
        bullet, para = doc["sections"][0]["lines"]
        self.assertEqual(render.BULLET_RE.sub("", bullet), "**Іспанська**: -10%")
        self.assertIsNone(render.BULLET_RE.match(para))
        self.assertEqual(render._md("**open only: text"), "open only: text")

    def test_unsupported_chars(self):
        self.assertEqual(render.unsupported_chars("Інтерес, Přerušovaný, Tiếng"), [])
        self.assertEqual(render.unsupported_chars("天文学"), ["天", "学", "文"])


class Assumptions(unittest.TestCase):
    def test_default_thresholds_are_not_mentioned(self):
        text = " ".join(render._assumptions(make_run(), "en"))
        self.assertNotIn("Confidence thresholds", text)

    def test_changed_thresholds_are_stated(self):
        run = dict(make_run(), thresholds={"low_views": 5.0, "high_views": 50.0})
        text = " ".join(render._assumptions(run, "en"))
        self.assertIn("under 5 views/day = LOW", text)
        self.assertIn("50+ views/day needed for HIGH", text)


class Pdf(unittest.TestCase):
    def test_one_page_in_both_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            for lang in ("uk", "en"):
                out = Path(tmp) / f"r_{lang}.pdf"
                render.report(make_run(), render.parse_findings(FINDINGS), out, lang, date.today().isoformat())
                self.assertEqual(out.read_bytes().count(b"/Type /Page\n"), 1)

    def test_too_long_findings_fail(self):
        long = FINDINGS + "\n".join(f"- bullet {i} " + "word " * 60 for i in range(25))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            render.report(make_run(), render.parse_findings(long), Path(tmp) / "r.pdf", "en", "2026-09-26")


if __name__ == "__main__":
    unittest.main()
