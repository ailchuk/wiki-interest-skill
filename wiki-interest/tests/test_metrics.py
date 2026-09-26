"""Metric tests on synthetic series. Run from the skill dir: .venv/bin/python -m unittest discover -s tests"""
import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import metrics as M  # noqa: E402

MONTHS = M.month_list("2026-08", 24)
LAST_YEAR_START = date(2025, 9, 1)


def series(fn):
    """Daily dict from fn(day) over the 24 test months."""
    start, end = M.month_bounds(MONTHS[0])[0], M.month_bounds(MONTHS[-1])[1]
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return {d.strftime("%Y%m%d"): int(fn(d)) for d in days}


def wiki(fn=lambda m: 1_000_000):
    return {m: fn(m) for m in MONTHS}


def run(daily, wiki_monthly=None):
    m = M.analyze_series(daily, wiki_monthly or wiki(), MONTHS)
    level, reasons = M.confidence(m)
    return m, level, [code for code, _ in reasons]


class Months(unittest.TestCase):
    def test_last_complete_month(self):
        self.assertEqual(M.last_complete_month(date(2026, 9, 26)), "2026-08")
        self.assertEqual(M.last_complete_month(date(2026, 9, 1)), "2026-07")
        self.assertEqual(M.last_complete_month(date(2026, 1, 5)), "2025-12")

    def test_month_list(self):
        self.assertEqual(M.month_list("2026-02", 3), ["2025-12", "2026-01", "2026-02"])
        self.assertEqual(len(MONTHS), 24)
        self.assertEqual(MONTHS[0], "2024-09")

    def test_needs_24_months(self):
        with self.assertRaises(ValueError):
            M.analyze_series({}, wiki(), MONTHS[-12:])


class Growth(unittest.TestCase):
    def test_steady_growth_is_high(self):
        m, level, _ = run(series(lambda d: 150 if d >= LAST_YEAR_START else 100))
        self.assertAlmostEqual(m["growth"], 0.5, places=2)
        self.assertAlmostEqual(m["adj_growth"], 0.5, places=2)
        self.assertEqual(m["months_up"], 12)
        self.assertEqual(level, "HIGH")
        self.assertEqual(M.trend(m), "up")

    def test_seasonality_is_flat(self):
        m, _, _ = run(series(lambda d: 300 + 150 * math.sin(d.month / 12 * 2 * math.pi)))
        self.assertLess(abs(m["growth"]), 0.01)
        self.assertEqual(M.trend(m), "flat")

    def test_spike_driven_growth_is_low(self):
        m, level, codes = run(series(lambda d: 20000 if d == date(2026, 3, 10) else 200))
        self.assertGreater(m["growth"], 0.2)
        self.assertLess(abs(m["growth_clean"]), 0.01)
        self.assertEqual(m["top_spikes"][0]["date"], "2026-03-10")
        self.assertEqual(level, "LOW")
        self.assertIn("spike_driven", codes)

    def test_low_volume_is_low(self):
        _, level, codes = run(series(lambda d: 8 if d >= LAST_YEAR_START else 5))
        self.assertEqual(level, "LOW")
        self.assertIn("low_volume", codes)

    def test_user_thresholds_override_the_defaults(self):
        """A niche audience of 15/day: LOW by default, trusted once the user lowers the bar."""
        m = M.analyze_series(series(lambda d: 15 if d >= LAST_YEAR_START else 10), wiki(), MONTHS)
        self.assertEqual(M.confidence(m)[0], "LOW")
        self.assertEqual(M.confidence(m, low_views=10, high_views=12)[0], "HIGH")
        level, reasons = M.confidence(m, low_views=40, high_views=100)
        self.assertEqual(level, "LOW")
        self.assertEqual(dict(reasons)["low_volume"]["min"], 40)

    def test_article_created_mid_period_is_low(self):
        m, level, codes = run(series(lambda d: 300 if d >= date(2025, 3, 1) else 0))
        self.assertEqual(m["leading_zero_months"], 6)
        self.assertEqual(level, "LOW")
        self.assertIn("appeared", codes)

    def test_wiki_decline_is_adjusted(self):
        # Article flat, whole Wikipedia -20% -> share of attention grows 25%.
        m, level, codes = run(series(lambda d: 200), wiki(lambda mo: 800_000 if mo >= "2025-09" else 1_000_000))
        self.assertLess(abs(m["growth"]), 0.01)
        self.assertAlmostEqual(m["adj_growth"], 0.25, places=2)
        self.assertEqual(level, "MEDIUM")
        self.assertIn("disagree", codes)

    def test_year_by_year_with_36_months(self):
        months = M.month_list("2026-08", 36)
        start, end = M.month_bounds(months[0])[0], M.month_bounds(months[-1])[1]
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        # 100/day, then 200/day (year 2), then 200/day (year 3): +100% then flat.
        daily = {d.strftime("%Y%m%d"): (100 if d < date(2024, 9, 1) else 200) for d in days}
        m = M.analyze_series(daily, {mo: 1_000_000 for mo in months}, months)
        self.assertEqual([y["period"] for y in m["yearly"]], ["2024-09..2025-08", "2025-09..2026-08"])
        self.assertAlmostEqual(m["yearly"][0]["growth_clean"], 365 * 200 / (366 * 100) - 1, places=4)  # 2024 is a leap year
        self.assertAlmostEqual(m["yearly"][1]["growth_clean"], 0.0, places=2)
        self.assertAlmostEqual(m["growth"], m["yearly"][-1]["growth_clean"], places=2)

    def test_warmup_makes_metrics_independent_of_window(self):
        """Ten busy days at the start of the 24-month window must be cleaned the same either way."""
        months36, months24 = M.month_list("2026-08", 36), M.month_list("2026-08", 24)
        start = M.month_bounds(months36[0])[0] - timedelta(days=M.SPIKE_WARMUP)
        end = M.month_bounds(months36[-1])[1]
        busy = {M.month_bounds(months24[0])[0] + timedelta(days=i) for i in range(10)}
        daily = {d.strftime("%Y%m%d"): (700 if d in busy else 200)
                 for d in [start + timedelta(days=i) for i in range((end - start).days + 1)]}

        short = M.analyze_series(daily, wiki(), months24, M.SPIKE_WARMUP)
        long = M.analyze_series(daily, wiki(), months36, M.SPIKE_WARMUP)
        for key in ("growth_clean", "adj_growth"):
            self.assertAlmostEqual(short[key], long[key], places=6, msg=key)

        # Without the warm-up those days keep a truncated median window and inflate the baseline.
        self.assertNotAlmostEqual(M.analyze_series(daily, wiki(), months24)["growth_clean"],
                                  long["growth_clean"], places=6)

    def test_no_views_before_is_low(self):
        _, level, codes = run(series(lambda d: 300 if d >= LAST_YEAR_START else 0))
        self.assertEqual(level, "LOW")
        self.assertIn("appeared", codes)


class Ranking(unittest.TestCase):
    def rows(self):
        def row(lang, conf, adj, vpd):
            return {"lang": lang, "status": "ok", "confidence": conf,
                    "metrics": {"adj_growth": adj, "views_per_day": vpd}}
        return [row("tiny", "LOW", 0.8, 5), row("big", "MEDIUM", 0.1, 900), row("mid", "HIGH", 0.05, 300),
                {"lang": "none", "status": "missing"}]

    def test_default_puts_low_confidence_last(self):
        self.assertEqual([r["lang"] for r in M.rank(self.rows())], ["big", "mid", "tiny", "none"])

    def test_confident_decline_does_not_outrank_growth(self):
        rows = [{"lang": "down", "status": "ok", "confidence": "HIGH", "metrics": {"adj_growth": -0.10, "views_per_day": 300}},
                {"lang": "up", "status": "ok", "confidence": "MEDIUM", "metrics": {"adj_growth": 0.02, "views_per_day": 300}}]
        self.assertEqual([r["lang"] for r in M.rank(rows)], ["up", "down"])

    def test_sort_by_growth_and_volume(self):
        self.assertEqual([r["lang"] for r in M.rank(self.rows(), "growth")][:3], ["tiny", "big", "mid"])
        self.assertEqual([r["lang"] for r in M.rank(self.rows(), "volume")][:3], ["big", "mid", "tiny"])

    def test_missing_has_no_rank(self):
        self.assertIsNone(M.rank(self.rows())[-1]["rank"])


if __name__ == "__main__":
    unittest.main()
