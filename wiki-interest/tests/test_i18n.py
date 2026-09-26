"""Locales, font selection and non-Latin reports. Run from the skill dir: .venv/bin/python -m unittest discover -s tests"""
import re
import string
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fonts  # noqa: E402
import i18n  # noqa: E402
import render  # noqa: E402
from test_report import make_run  # noqa: E402


def placeholders(s):
    return {name for _, name, _, _ in string.Formatter().parse(s) if name}


class Locales(unittest.TestCase):
    def test_all_languages_present(self):
        self.assertEqual(set(i18n.LANGS), {"en", "uk", "pl", "cs", "de", "es", "pt", "tr", "vi", "fr", "ja", "zh",
                                           "ar", "hi"})

    def test_same_keys_and_placeholders_as_english(self):
        en = i18n.TEXT["en"]
        for lang, texts in i18n.TEXT.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(texts), set(en))
                for key, value in texts.items():
                    self.assertEqual(placeholders(value), placeholders(en[key]), f"{lang}.{key}")

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(i18n.t("ko", "findings"), "Findings")
        self.assertEqual(i18n.chart_lang("ja"), "en")
        self.assertEqual(i18n.chart_lang("pl"), "pl")


class FontSelection(unittest.TestCase):
    def test_scripts(self):
        self.assertEqual(fonts.needed("Інтерес, Přerušovaný, Tiếng Anh"), [])
        self.assertEqual(fonts.needed("天文学", "zh"), ["zh"])
        self.assertEqual(fonts.needed("天文学", "ja"), ["ja"])
        self.assertEqual(fonts.needed("天文学への関心"), ["ja"])  # kana decides for Han characters
        self.assertEqual(fonts.needed("천문학"), ["ko"])
        self.assertEqual(fonts.needed("علم الفلك"), ["arabic"])
        self.assertEqual(fonts.needed("खगोल विज्ञान"), ["devanagari"])

    def test_shaped_scripts(self):
        self.assertTrue({"arabic", "hebrew", "devanagari"} <= fonts.SHAPED)
        self.assertNotIn("ja", fonts.SHAPED)


class NonLatinNumbers(unittest.TestCase):
    def check(self, line):
        doc = render.parse_findings(f"# T\n\n## Findings\n- {line}\n")
        return render.check_numbers(doc, make_run())

    def test_arabic_indic_and_fullwidth_digits(self):
        self.assertEqual(self.check("نمو ٥٠٪"), [])  # 50% is in the data
        self.assertEqual(len(self.check("نمو ٣٥٪")), 1)  # 35% is not
        self.assertEqual(self.check("成長率＋５０％"), [])
        self.assertEqual(len(self.check("成長率－３５％")), 1)

    def test_number_glued_to_cjk_text_is_checked(self):
        self.assertEqual(len(self.check("下降35%")), 1)


class NonLatinPdf(unittest.TestCase):
    """Needs the Noto fonts: downloaded on first run, skipped when offline."""

    def render(self, lang, findings):
        try:
            for key in fonts.needed(findings, lang):
                fonts.path(key)
        except fonts.FontError as e:
            self.skipTest(f"font not available offline: {e}")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.pdf"
            _, warnings = render.report(make_run(), render.parse_findings(findings), out, lang, "2026-09-26")
            self.assertEqual(warnings, [])
            self.assertEqual(len(re.findall(rb"/Type /Page\n", out.read_bytes())), 1)

    def test_japanese(self):
        self.render("ja", "# 天文学への関心\n質問：関心は高まっているか？\n\n## 結果\n- ukは+50%（信頼度：高）。\n")

    def test_arabic(self):
        self.render("ar", "# الاهتمام بعلم الفلك\nالسؤال: هل يزداد الاهتمام؟\n\n## النتائج\n- نمو ٥٠٪ في الأوكرانية.\n")


if __name__ == "__main__":
    unittest.main()
