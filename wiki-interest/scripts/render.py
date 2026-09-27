"""Charts (matplotlib), findings check and the one-page PDF report (fpdf2)."""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from fpdf import FPDF  # noqa: E402
from fpdf.fonts import FontFace  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import fonts  # noqa: E402
import metrics  # noqa: E402
from i18n import RTL_LANGS, chart_lang, pct, t  # noqa: E402

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
DEJAVU = {"": "DejaVuSans.ttf", "B": "DejaVuSans-Bold.ttf", "I": "DejaVuSans-Oblique.ttf",
         "BI": "DejaVuSans-BoldOblique.ttf"}

# Validated light palette (dataviz skill): languages keep their color in the order the user listed them.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ORDINAL = ["#86b6ef", "#2a78d6", "#104281"]  # raw -> without spikes -> adjusted
SURFACE, INK, INK2, GRID, BAND = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#f0efec"
MAX_SERIES = len(SERIES)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7.5,
    "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def colors(run):
    return {code: SERIES[i % MAX_SERIES] for i, code in enumerate(run["langs"])}


def charted(run):
    """Rows that can be charted, capped at the palette size (the rest stay in the table)."""
    return [r for r in run["rows"] if r["status"] == "ok"][:MAX_SERIES]


def trend_chart(run, path, lang="en"):
    months, col = run["months"], colors(run)
    n = len(months)
    fig, ax = plt.subplots(figsize=(5.6, 3.1), dpi=200)
    ax.axvspan(n - 12 - 0.5, n - 0.5, color=BAND, zorder=0, lw=0)
    ax.text(n - 12 - 0.2, 0.97, t(lang, "last12"), transform=ax.get_xaxis_transform(), va="top", color=INK2, fontsize=6.5)
    ax.axhline(100, color=INK2, lw=0.8, ls=(0, (3, 3)), zorder=1)
    rows = charted(run)
    ends = []
    for r in rows:
        vals = [r["metrics"]["monthly"][m] for m in months]
        base = sum(vals[-24:-12]) / 12
        if not base:
            continue
        idx = [v / base * 100 for v in vals]
        c = col[r["code"]]
        ax.plot(range(n), idx, color=c, lw=1.6, solid_capstyle="round", label=r["code"], zorder=3)
        ax.plot([n - 1], [idx[-1]], "o", color=c, ms=4, mec=SURFACE, mew=1, zorder=4)
        ends.append([idx[-1], r["code"]])
    # Direct labels at line ends, nudged apart so they never overlap.
    lo, hi = ax.get_ylim()
    gap = (hi - lo) * 0.05
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
    for y, code in ends:
        ax.text(n - 0.4, y, code, va="center", color=INK, fontsize=7)
    step = 3 if n <= 36 else 6
    ax.set_xticks(range(0, n, step), [months[i] for i in range(0, n, step)], rotation=0)
    ax.set_xlim(-0.5, n + 1.5)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_title(t(lang, "trend_title"), loc="left", fontsize=8.5, color=INK)
    if len(rows) >= 2:
        ax.legend(frameon=False, fontsize=7, ncol=min(4, len(rows)), loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def growth_chart(run, path, lang="en"):
    rows = charted(run)
    keys = ("growth", "growth_clean", "adj_growth")
    height = 1.1 + 0.45 * max(len(rows), 1)
    fig, ax = plt.subplots(figsize=(5.6, height), dpi=200)
    for i, r in enumerate(rows):
        for j, key in enumerate(keys):
            v = r["metrics"][key]
            if v is None:
                continue
            y = i + (j - 1) * 0.27
            ax.barh(y, v * 100, height=0.24, color=ORDINAL[j], label=t(lang, key) if i == 0 else None, zorder=3)
            if key == "adj_growth":
                ax.annotate(f"{round(v * 100):+d}%", xy=(v * 100, y), xytext=(3 if v >= 0 else -3, 0),
                            textcoords="offset points", va="center", ha="left" if v >= 0 else "right",
                            color=INK, fontsize=6.5)
    ax.set_yticks(range(len(rows)), [f"{r['code']}  {t(lang, r['confidence'])}" for r in rows])
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8, zorder=2)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:+.0f}%" if x else "0%"))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    lo, hi = ax.get_xlim()
    pad = (hi - lo) * 0.08
    ax.set_xlim(min(lo, 0) - pad, max(hi, 0) + pad)
    ax.set_title(t(lang, "growth_title"), loc="left", fontsize=8.5, color=INK)
    fig.tight_layout(rect=(0, 0.28 / height, 1, 1))
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, fontsize=6.5, ncol=3, loc="lower left",
               bbox_to_anchor=(0.01, 0.0))
    fig.savefig(path)
    plt.close(fig)


def charts(run, out_dir, lang="en"):
    out_dir = Path(out_dir)
    paths = {"trend": out_dir / "trend.png", "growth": out_dir / "growth.png"}
    trend_chart(run, paths["trend"], lang)
    growth_chart(run, paths["growth"], lang)
    return paths


# --- findings.md -----------------------------------------------------------------

BULLET_RE = re.compile(r"^(?:[-*•]|\d+[.)])\s+")
QUESTION_RE = re.compile(r"^([^\W\d_][\w .-]{0,24}?)\s*:\s*(.+)$")


def parse_findings(text):
    """'# Title', optional 'Question: ...' line, then '## Section' blocks -> dict."""
    doc = {"title": "", "question_label": "", "question": "", "sections": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and not doc["title"]:
            doc["title"] = line[2:].strip()
        elif line.startswith("## "):
            doc["sections"].append({"heading": line[3:].strip(), "lines": []})
        elif not doc["sections"] and not doc["question"] and QUESTION_RE.match(re.sub(r"[*_`]", "", line)):
            m = QUESTION_RE.match(re.sub(r"[*_`]", "", line))
            doc["question_label"], doc["question"] = m.group(1).strip(), m.group(2).strip()
        else:
            if not doc["sections"]:
                doc["sections"].append({"heading": "", "lines": []})
            doc["sections"][-1]["lines"].append(line)
    return doc


def _md(line):
    """Safe inline markdown for fpdf2: drop '**' when unbalanced so bold cannot leak."""
    return line.replace("**", "") if line.count("**") % 2 else line


PCT_RE = re.compile(r"(?<![\d.,])([+-]?\s?\d+(?:[.,]\d+)?)\s?%")
# Arabic-Indic, Persian and full-width digits/percent signs, unicode minus -> ASCII, so every number gets checked.
NORMALIZE = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹０１２３４５６７８９٪％٫−–－", "0123456789" * 3 + "%%.---")
MONTHS_RE = re.compile(r"(?<!\d)(\d{1,2})\s?/\s?12(?!\d)")
DATE_RE = re.compile(r"\d{4}-\d{2}(?:-\d{2})?")
NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[ ,'\u00a0\u202f]\d{3})+|\d+(?:[.,]\d+)?)(?![\w.,])")
GROUPED_RE = re.compile(r"\d{1,3}(?:[ ,]\d{3})+")
MIN_CHECKED = 10  # below this a number is almost always a count of languages or bullets, not data


def _number(token):
    token = token.replace("\u00a0", " ").replace("\u202f", " ").replace("'", "")
    if GROUPED_RE.fullmatch(token):
        return float(token.replace(" ", "").replace(",", ""))
    return float(token.replace(",", "."))


def _percents(run):
    """Signed rounded percentages the data supports."""
    out = set()
    for r in run["rows"]:
        if r["status"] != "ok":
            continue
        m = r["metrics"]
        out |= {round(m[k] * 100) for k in ("growth", "growth_clean", "adj_growth", "wiki_growth")
                if m[k] is not None}
        out |= {round(y[k] * 100) for y in m.get("yearly", [])
                for k in ("growth_clean", "adj_growth") if y[k] is not None}
    return out


def _counts(run):
    """Plain numbers the tool prints: views/day, spike days, month counts and years of the period."""
    out = {12.0, float(len(run["months"]))}
    out |= {float(m[:4]) for m in run["months"]}
    # Thresholds are printed next to every confidence reason, so quoting them is not an invention.
    out |= {float(v) for v in run.get("thresholds", DEFAULT_THRESHOLDS).values()}
    for r in run["rows"]:
        if r["status"] != "ok":
            continue
        m = r["metrics"]
        out |= {m["views_per_day"], float(m["months_up"]), float(m["months_down"])}
        out |= {float(s["views"]) for s in m["top_spikes"]} | {float(s["times"]) for s in m["top_spikes"]}
        out |= {a["views_per_day"] for a in r.get("articles", []) if a.get("views_per_day") is not None}
    return out


def check_numbers(doc, run):
    """Check the findings sections of a parsed document; the `Question:` line is not checked."""
    return check_text("\n".join(line for s in doc["sections"] for line in s["lines"]), run)


def check_text(text, run):
    """Every number in the text must come from the data. Returns mismatch messages.

    Percentages written with an explicit sign must also match its direction; without a sign the
    direction lives in the words around it ("fell by 34%"), so only the magnitude is compared.
    """
    pcts, counts = _percents(run), _counts(run)
    months = {r["metrics"][k] for r in run["rows"] if r["status"] == "ok" for k in ("months_up", "months_down")}
    text = text.translate(NORMALIZE)
    bad = []
    for m in PCT_RE.finditer(text):
        raw = m.group(1).replace(" ", "")
        v, shown = _number(raw.lstrip("+-")), m.group(0).strip()
        if raw[0] in "+-":
            v = -v if raw[0] == "-" else v
            if not any(abs(v - a) <= 1 for a in pcts):
                flipped = [a for a in pcts if abs(-v - a) <= 1]
                bad.append(f"'{shown}' points the wrong way: the data says {flipped[0]:+d}%" if flipped
                           else f"'{shown}' is not in the data")
        elif not any(abs(v - abs(a)) <= 1 for a in pcts):
            bad.append(f"'{shown}' is not in the data")
    for m in MONTHS_RE.finditer(text):
        if int(m.group(1)) not in months:
            bad.append(f"'{m.group(0)}' is not in the data")
    plain = MONTHS_RE.sub(" ", PCT_RE.sub(" ", DATE_RE.sub(" ", text)))
    for m in NUM_RE.finditer(plain):
        v = _number(m.group(1))
        if v >= MIN_CHECKED and not any(abs(v - a) <= max(1.0, 0.1 * a) for a in counts):
            bad.append(f"'{m.group(1)}' is not a number the tool printed")
    return bad


def allowed_values(run):
    out = []
    for r in run["rows"]:
        if r["status"] == "ok":
            m = r["metrics"]
            years = "".join(f"; {y['period']}: w/o spikes {pct(y['growth_clean'])}, adjusted {pct(y['adj_growth'])}"
                            for y in m.get("yearly", [])[:-1])
            spikes = "".join(f"; spike {s['date']}: {s['views']} views, {s['times']}x normal"
                             for s in m["top_spikes"])
            if len(r.get("articles", [])) > 1:
                spikes += "; basket " + " + ".join(f"{a['title']} {a['views_per_day']:g}/day" for a in r["articles"])
            out.append(f"{r['code']}: growth {pct(m['growth'])}, w/o spikes {pct(m['growth_clean'])}, "
                       f"adjusted {pct(m['adj_growth'])}, whole wiki {pct(m['wiki_growth'])}, "
                       f"views/day {m['views_per_day']:.1f}, "
                       f"months up {m['months_up']}/12, down {m['months_down']}/12{years}{spikes}")
    return out


def unsupported_chars(text):
    with TTFont(FONT_DIR / DEJAVU[""], lazy=True) as font:
        cmap = font.getBestCmap()
    return sorted({ch for ch in text if ch.strip() and ord(ch) not in cmap})


# --- PDF -------------------------------------------------------------------------

GREY = (82, 81, 78)
PAGE_W = 186  # A4 minus 12 mm margins


DEFAULT_THRESHOLDS = {"low_views": metrics.LOW_VOLUME, "high_views": metrics.HIGH_VOLUME}


def _assumptions(run, lang):
    rows = run["rows"]
    arts = "; ".join(f"{r['code']}: {r['title']}" + (" (proxy)" if r["proxy"] else "") for r in rows if r["title"])
    first = (t(lang, "a_topic", qid=run["qid"], articles=arts) if run["qid"]
             else t(lang, "a_articles", articles=arts))
    out = [first, t(lang, "a_period", start=run["months"][0], end=run["months"][-1]),
           t(lang, "a_filters"), t(lang, "a_spikes"), t(lang, "a_adjusted")]
    if len(run.get("topics") or {}) > 1:
        out.append(t(lang, "a_basket", n=len(run["topics"]), topics=", ".join(run["topics"].values())))
        # Without this the reader would compare a two-article total with a one-article total.
        short = ", ".join(r["code"] for r in rows if r["status"] == "ok" and r.get("absent"))
        if short:
            out.append(t(lang, "a_partial", langs=short))
    # A changed threshold must be stated, or the report would misdescribe how confidence was set.
    th = run.get("thresholds", DEFAULT_THRESHOLDS)
    if th != DEFAULT_THRESHOLDS:
        out.append(t(lang, "a_thresholds", low=f"{th['low_views']:g}", high=f"{th['high_views']:g}",
                     dlow=f"{DEFAULT_THRESHOLDS['low_views']:g}", dhigh=f"{DEFAULT_THRESHOLDS['high_views']:g}"))
    return out


def _limitations(run, lang):
    rows = run["rows"]

    def codes(pred):
        return ", ".join(r["code"] for r in rows if pred(r))

    out = [t(lang, "l_interest"), t(lang, "l_country"), t(lang, "l_proxy")]
    ok = [r for r in rows if r["status"] == "ok"]
    checks = [
        ("l_missing", lambda r: r["status"] != "ok"),
        ("l_low", lambda r: r in ok and any(c == "low_volume" for c, _ in r["reasons"])),
        ("l_spikes", lambda r: r in ok and any(c == "spike_driven" for c, _ in r["reasons"])),
        ("l_appeared", lambda r: r in ok and any(c == "appeared" for c, _ in r["reasons"])),
    ]
    for key, pred in checks:
        if codes(pred):
            out.append(t(lang, key, langs=codes(pred)))
    if run["months"][0] <= "2025-08":
        out.append(t(lang, "l_bots"))
    return out


def _table_rows(run, lang):
    head = [t(lang, k) for k in ("lang", "article", "vpd", "raw", "clean", "adj", "steady", "conf")]
    body = []
    for r in run["rows"]:
        if r["status"] != "ok":
            body.append([r["code"], t(lang, "missing" if r["status"] == "missing" else "no_views")] + ["-"] * 6)
            continue
        m = r["metrics"]
        vpd = f"{m['views_per_day']:.1f}" if m["views_per_day"] < 10 else f"{m['views_per_day']:,.0f}"
        arts = r.get("articles") or []
        # A whole basket never fits the column; the assumptions block lists it in full.
        title = f"{arts[0]['title']} +{len(arts) - 1}" if len(arts) > 1 else r["title"]
        body.append([r["code"], title + (" *" if r["proxy"] else ""), vpd, pct(m["growth"]),
                     pct(m["growth_clean"]), pct(m["adj_growth"]), f"{m['months_up']}/12", t(lang, r["confidence"])])
    return head, body


HEADINGS = {"findings": "findings", "recommendation": "recommendation", "recommendations": "recommendation",
            "next steps": "next_steps"}


def _heading(h, lang):
    """Template headings (Findings, Recommendation, Next steps) follow the report language."""
    key = HEADINGS.get(h.strip().lower())
    return t(lang, key) if key else h


def _build(run, doc, charts_paths, lang, s, created, extra):
    """extra: [(font key, path)] fallback fonts for scripts DejaVu lacks."""
    pdf = FPDF(format="A4")
    pdf.set_margins(12, 10, 12)
    pdf.set_auto_page_break(True, 8)
    for style, file in DEJAVU.items():
        pdf.add_font("DejaVu", style, str(FONT_DIR / file))
    for key, path in extra:
        weight = fonts.FONTS[key][3]
        pdf.add_font(key, "", str(path), variations={"wght": weight} if weight else None)
    if extra:
        pdf.set_fallback_fonts([key for key, _ in extra], exact_match=False)
    if any(key in fonts.SHAPED for key, _ in extra):
        pdf.set_text_shaping(True)
    align = "R" if lang in RTL_LANGS else "L"
    pdf.add_page()

    def text(size, body, style="", color=(0, 0, 0), h=None, md=False):
        pdf.set_font("DejaVu", style, size * s)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, h or size * s * 0.48, body, markdown=md, align=align, new_x="LMARGIN", new_y="NEXT")

    def bullets(items, size, color=(0, 0, 0)):
        pdf.set_font("DejaVu", "", size * s)
        pdf.set_text_color(*color)
        for item in items:
            body = _md(BULLET_RE.sub("", item))
            if align == "R":  # right-to-left: the bullet goes to the right edge together with the text
                pdf.multi_cell(0, size * s * 0.47, "• " + body, markdown=True, align="R", new_x="LMARGIN", new_y="NEXT")
                continue
            pdf.set_x(14)
            pdf.cell(3, size * s * 0.47, "•")
            pdf.multi_cell(PAGE_W - 5, size * s * 0.47, body, markdown=True, align="L",
                           new_x="LMARGIN", new_y="NEXT")

    text(15, doc["title"] or run["label"], "B", h=15 * s * 0.5)
    if doc["question"]:
        label = doc["question_label"]
        if label.lower() in ("question", "питання"):
            label = t(lang, "question")
        text(8.5, f"{label}: {doc['question']}", color=GREY)
    pdf.ln(1.5 * s)
    for sec in doc["sections"]:
        if sec["heading"]:
            text(10.5, _heading(sec["heading"], lang), "B")
        for line in sec["lines"]:
            if BULLET_RE.match(line):
                bullets([line], 9)
            else:
                text(9, _md(line), md=True)
        pdf.ln(1.2 * s)

    w = (PAGE_W - 4) / 2
    y = pdf.get_y() + 1
    heights = []
    for i, key in enumerate(("trend", "growth")):
        img = pdf.image(str(charts_paths[key]), x=12 + i * (w + 4), y=y, w=w)
        heights.append(img.rendered_height)
    pdf.set_y(y + max(heights) + 2)

    head, body = _table_rows(run, lang)
    pdf.set_font("DejaVu", "", 7 * s)
    pdf.set_text_color(0, 0, 0)
    with pdf.table(col_widths=(8, 44, 21, 18, 19, 19, 16, 20), line_height=4.2 * s, padding=0.6,
                   text_align=("LEFT", "LEFT") + ("RIGHT",) * 6, borders_layout="HORIZONTAL_LINES",
                   headings_style=FontFace(emphasis="BOLD", fill_color=(240, 239, 236))) as table:
        for row in [head] + body:
            cells = table.row()
            for v in row:
                cells.cell(v)
    pdf.ln(2 * s)

    text(8, t(lang, "assumptions"), "B")
    bullets(_assumptions(run, lang), 6.8, GREY)
    pdf.ln(0.8 * s)
    text(8, t(lang, "limitations"), "B")
    bullets(_limitations(run, lang), 6.8, GREY)
    pdf.ln(1.2 * s)
    cmd = run["command"].split("/scripts/wi", 1)[-1]
    text(6.5, t(lang, "generated", date=created), color=GREY)
    text(6.5, f"{t(lang, 'reproduce')}: bash wiki-interest/scripts/wi{cmd}", color=GREY)
    return pdf


SCALES = (1.0, 0.94, 0.88, 0.82, 0.76)


def _all_text(run, doc, lang):
    head, body = _table_rows(run, lang)
    parts = [doc["title"], doc["question_label"], doc["question"]]
    parts += [x for sec in doc["sections"] for x in [sec["heading"]] + sec["lines"]]
    parts += _assumptions(run, lang) + _limitations(run, lang) + [c for row in [head] + body for c in row]
    parts += [t(lang, k) for k in ("findings", "recommendation", "next_steps", "assumptions", "limitations",
                                   "question", "generated", "reproduce")]
    return "\n".join(p for p in parts if p)


def prepare_fonts(text, lang):
    """Download fallback fonts the text needs. Returns ([(key, path)], warnings)."""
    extra, warnings = [], []
    for key in fonts.needed(text, lang):
        try:
            extra.append((key, fonts.path(key)))
        except fonts.FontError as e:
            warnings.append(f"font for {key} unavailable ({e}); those characters will be blank")
    left = set(unsupported_chars(text))
    for key, _ in extra:
        left -= fonts.covers(key, "".join(left))
    if left:
        warnings.append(f"no font draws {''.join(sorted(left)[:20])}; those characters will be blank")
    return extra, warnings


def report(run, doc, out_pdf, lang, created):
    """Render the one-page PDF. Returns (scale used, font warnings); raises ValueError if it cannot fit one page."""
    out_pdf = Path(out_pdf)
    chart_dir = out_pdf.parent / f"charts_{lang}"
    chart_dir.mkdir(parents=True, exist_ok=True)
    paths = charts(run, chart_dir, chart_lang(lang))
    extra, warnings = prepare_fonts(_all_text(run, doc, lang), lang)
    for s in SCALES:
        pdf = _build(run, doc, paths, lang, s, created, extra)
        if pdf.pages_count == 1:
            pdf.output(str(out_pdf))
            return s, warnings
    raise ValueError("findings do not fit on one page even at 76% text size: keep 3-5 short bullets and a "
                     "2-3 sentence recommendation")
