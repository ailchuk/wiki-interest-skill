"""wiki-interest CLI. Run through the wrapper: bash <skill-dir>/scripts/wi <command> ...
Without bash: python <skill-dir>/scripts/wi.py <command> ... (bootstrap.py sets up the same .venv)."""
import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import date, timedelta
from pathlib import Path

if __name__ == "__main__":
    import bootstrap  # stdlib only
    if Path(sys.prefix).resolve() != bootstrap.venv_path().resolve():  # outside the skill's venv, e.g. no bash
        bootstrap.run()

import answer
import metrics
import render
import wikiapi
from i18n import LANGS, chart_lang, lang_or_en, pct, reason

SKILL_DIR = Path(__file__).resolve().parent.parent
# Commands printed for the agent use the entry it started with (bash wrapper, or python without bash).
# Forward slashes and quotes: printed commands are pasted into bash, where a Windows "\" would be eaten.
WI = os.environ.get("WI_CMD") or f'bash "{SKILL_DIR.as_posix()}/scripts/wi"'
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Exit codes tell the agent what kind of fix is needed (1 = environment, from scripts/wi).
EXIT_USAGE, EXIT_FINDINGS, EXIT_NETWORK = 2, 3, 4
DEFAULT_THRESHOLDS = {"low_views": metrics.LOW_VOLUME, "high_views": metrics.HIGH_VOLUME}
MAX_BASKET = 5  # articles per language in one run; more makes the table and the PDF unreadable
# Largest editions by readership, in order. Used only to name where a missing topic can still be
# read; the pageview API gives no size ranking, so this list is a rough guide, not data.
BIG_WIKIS = ("en", "de", "fr", "es", "ru", "ja", "zh", "pt", "it", "pl", "nl", "ar", "tr", "id")


class UsageError(Exception):
    """Wrong input from the agent. The message always says how to fix it."""


def cmd_find(args):
    wikis = wikiapi.wikipedias()
    langs = wikiapi.resolve_langs(args.langs) if args.langs else []
    if args.qid:
        candidates = [{"qid": q.strip().upper()} for q in args.qid.split(",")]
    else:
        candidates = wikiapi.search_entities(args.topic, args.query_lang, args.limit)
        if len(candidates) < args.limit and args.query_lang != "en":
            seen = {c["qid"] for c in candidates}
            candidates += [c for c in wikiapi.search_entities(args.topic, "en", args.limit) if c["qid"] not in seen]
        candidates = candidates[:args.limit]
    if not candidates:
        print(f'No Wikidata item found for "{args.topic}" (searched in {args.query_lang} and en).')
        print("Wikidata holds concepts, not phrases: try the English name, or a shorter one. A broad intent is "
              'several concepts, so search for each on its own ("English language", then "IELTS") and analyze '
              "them together as --qid Q1,Q2.")
        return EXIT_USAGE

    label_langs = [args.query_lang] + [w["code"] for w in langs]
    ents = wikiapi.entities([c["qid"] for c in candidates], label_langs)
    wiki_dbnames = {w["dbname"] for w in wikis.values()}

    print(f'## Wikidata candidates for "{args.topic or args.qid}"')
    for i, c in enumerate(candidates, 1):
        ent = ents.get(c["qid"])
        if not ent:
            print(f"{i}. {c['qid']} - not found on Wikidata")
            continue
        label = _pick(ent["labels"], args.query_lang) or c.get("label", "")
        desc = _pick(ent["descriptions"], args.query_lang) or c.get("description", "")
        n = sum(1 for db in ent["sitelinks"] if db in wiki_dbnames)
        print(f"{i}. {c['qid']} | {label} | {desc} | articles in {n} Wikipedias")

    if not langs:
        print(f"\nNext: add --langs <codes> to see article titles per language.")
        return 0

    # Items given by hand are a basket to measure together; items from a search are rival readings of the topic.
    basket = [c["qid"] for c in (candidates if args.qid else candidates[:1]) if c["qid"] in ents]
    if not basket:
        print("None of those items exist on Wikidata.")
        return EXIT_USAGE

    print(f"\n## Articles for " + (" + ".join(basket) if len(basket) > 1 else f"{basket[0]} (candidate 1)"))
    print("| lang | " + " | ".join(_pick(ents[q]["labels"], args.query_lang) or q for q in basket) + " |")
    print("|---" * (len(basket) + 1) + "|")
    missing, partial = [], []
    for w in langs:
        found = {q: ents[q]["sitelinks"].get(w["dbname"]) for q in basket}
        gaps = [q for q, title in found.items() if not title]
        cells = []
        for q in basket:
            if found[q]:
                cells.append(found[q])
                continue
            # Suggesting a replacement only makes sense when the language has nothing at all.
            query = ents[q]["labels"].get(w["code"]) or ents[q]["labels"].get("en") or args.topic or ""
            similar = wikiapi.search_wiki(w["project"], query) if query and len(gaps) == len(basket) else []
            cells.append("MISSING" + (f" - similar: {'; '.join(similar)}" if similar else ""))
        print(f"| {w['code']} | " + " | ".join(cells) + " |")
        if len(gaps) == len(basket):
            missing.append(w["code"])
        elif gaps:
            partial.append(w["code"])

    codes = ",".join(w["code"] for w in langs)
    print(f"\nNext: {WI} analyze {','.join(basket)} --langs {codes}")
    if len(basket) == 1:
        print(f"Is this one article the whole topic the user means? A broad intent is not: 'learning English' is the "
              f"language plus the exams people study for. If so, run find for the other concept, then analyze both "
              f"as one basket: {WI} analyze {basket[0]},<second QID> --langs {codes}")
    if missing:
        print(f"MISSING languages ({','.join(missing)}) are reported as 'no article': interest there cannot be measured. "
              "Do not replace them with a broader topic (e.g. 'fasting' for 'intermittent fasting'). Only if a similar "
              f'article is the SAME concept: add --article {missing[0]}:"Exact Title" and call it a proxy.')
        asked = {w["code"] for w in langs}
        have = {db for q in basket for db in ents[q]["sitelinks"]} & wiki_dbnames
        elsewhere = [c for c in BIG_WIKIS
                     if c not in asked and (wikis.get(c) or {}).get("dbname") in have][:5]
        print(f"The gap is an answer in itself, so say it: the topic has articles in {len(have)} Wikipedias"
              + (f", among the largest {', '.join(elsewhere)}" if elsewhere else "")
              + f". No article in {','.join(missing)} means the topic is niche there or not written up yet, not "
              f"that nobody is interested: those readers may be using another language for it. Which one is not in "
              f"this data - the list above is where articles exist, not what those readers read. Name an edition "
              f"only as something to check, never as a statement about who reads what.")
        print(f"Run the Next: command as printed: {','.join(missing)} stays in --langs and shows as MISSING. Do not "
              f"swap in or add another edition the user did not ask for.")
        if elsewhere:
            print(f"Only if the user explicitly asks for a wider signal: analyze {elsewhere[0]} in a separate run, "
                  f"call its readers a global audience, not the {missing[0]} one, and never present those numbers "
                  f"as interest in {missing[0]}.")
    if partial:
        print(f"{','.join(partial)} have only part of the basket, so fewer articles are counted there. `analyze` says "
              "which one is missing; report it before comparing that language with the others.")
    if len(candidates) > 1 and not args.qid:
        print("The candidates above are rival readings of the same words, not parts of one topic: if candidate 1 is "
              "the wrong concept, rerun find with --qid <QID> of the right one.")
    return 0


def _pick(values, lang):
    return values.get(lang) or values.get("en") or next(iter(values.values()), "")


def cmd_analyze(args):
    if args.months < 24:
        raise UsageError("--months must be >= 24 (growth compares the last 12 months with the previous 12).")
    if not 0 < args.low_views < args.high_views:
        raise UsageError(f"--low-views must be above 0 and below --high-views, "
                         f"got {args.low_views:g} and {args.high_views:g}.")
    overrides = {}
    for item in args.article or []:
        code, sep, title = item.partition(":")
        if not sep or not title.strip():
            raise UsageError(f'--article must look like pl:"Exact Title", got {item!r}')
        overrides.setdefault(code.strip().lower(), []).append(title.strip())
    qids = list(dict.fromkeys(q.strip().upper() for q in args.qid.split(","))) if args.qid else []
    if not qids and not overrides:
        raise UsageError("give a Wikidata QID (from `find`) or --article lang:Title.")
    if len(qids) > MAX_BASKET:
        raise UsageError(f"--qid takes at most {MAX_BASKET} Wikidata items, got {len(qids)}. A bigger basket makes "
                         f"the report unreadable; analyze the rest separately.")

    lang_spec = ",".join(filter(None, [args.langs or ""] + list(overrides)))
    wikis = wikiapi.resolve_langs(lang_spec)
    end = args.end or metrics.last_complete_month(date.today())
    if not MONTH_RE.match(end):
        raise UsageError(f"--end must be a month as YYYY-MM (e.g. 2026-08), got {end!r}.")
    months = metrics.month_list(end, args.months)
    dropped = [m for m in months if m < metrics.DATA_START]
    if dropped:
        months = months[len(dropped):]
        if len(months) < 24:
            raise UsageError(f"Wikimedia pageviews start in {metrics.DATA_START}, which leaves only "
                             f"{len(months)} months before {end}. Growth needs 24.")
        print(f"NOTE: Wikimedia pageviews start in {metrics.DATA_START}, so {len(dropped)} earlier month(s) were "
              f"dropped. Period is {months[0]}..{months[-1]} ({len(months)} months), not the {args.months} asked for.")
    start_day, end_day = metrics.month_bounds(months[0])[0], metrics.month_bounds(months[-1])[1]
    # Extra days before the period so spike detection sees a full window on its first days.
    warm_start = max(start_day - timedelta(days=metrics.SPIKE_WARMUP), metrics.month_bounds(metrics.DATA_START)[0])
    warmup = (start_day - warm_start).days

    ents = wikiapi.entities(qids, [w["code"] for w in wikis]) if qids else {}
    unknown = [q for q in qids if q not in ents]
    if unknown:
        raise UsageError(f"{', '.join(unknown)} not found on Wikidata. Run find first.")
    topics = {q: _pick(ents[q]["labels"], "en") or q for q in qids}
    label = " + ".join(topics.values()) if topics else "custom articles"

    rows = []
    last12 = months[-12:]
    for w in wikis:
        # Several items = a topic basket: the language's views are the sum of its articles. An override
        # replaces that language's whole basket, because which item it stands for cannot be guessed.
        titles = overrides.get(w["code"])
        arts = [{"qid": None, "title": t, "proxy": True} for t in titles] if titles else \
               [{"qid": q, "title": ents[q]["sitelinks"][w["dbname"]], "proxy": False}
                for q in qids if w["dbname"] in ents[q]["sitelinks"]]
        row = {"code": w["code"], "english": w["english"], "project": w["project"],
               "title": " + ".join(a["title"] for a in arts) or None, "articles": arts,
               "absent": [] if titles else [topics[q] for q in qids if w["dbname"] not in ents[q]["sitelinks"]],
               "proxy": bool(titles), "status": "ok", "confidence": None, "reasons": [], "rank": None}
        rows.append(row)
        if not arts:
            row["status"] = "missing"
            continue
        daily = {}
        for a in arts:
            one = wikiapi.article_daily(w["project"], a["title"], warm_start, end_day)
            a["views_per_day"] = round(metrics.views_per_day(one, last12), 1)
            for day, views in one.items():
                daily[day] = daily.get(day, 0) + views
        if not sum(daily.values()):
            row["status"] = "no_views"
            continue
        wiki_monthly = wikiapi.project_monthly(w["project"], start_day, end_day)
        m = metrics.analyze_series(daily, wiki_monthly, months, warmup)
        m["wiki_monthly"] = wiki_monthly
        row["metrics"] = m
        row["confidence"], row["reasons"] = metrics.confidence(m, args.low_views, args.high_views)
        row["trend"] = metrics.trend(m)
    rows = metrics.rank(rows, args.sort)

    cmd = [WI, "analyze"] + ([",".join(qids)] if qids else []) + ["--langs", ",".join(w["code"] for w in wikis),
                                                                  "--months", str(len(months)), "--end", end]
    cmd += [f"--article={shlex.quote(f'{c}:{t}')}" for c, ts in overrides.items() for t in ts]
    if args.sort != "confidence":
        cmd += ["--sort", args.sort]
    thresholds = {"low_views": args.low_views, "high_views": args.high_views}
    custom = {k: v for k, v in thresholds.items() if v != DEFAULT_THRESHOLDS[k]}
    for key, value in custom.items():
        cmd += [f"--{key.replace('_', '-')}", f"{value:g}"]
    run = {
        "created": date.today().isoformat(), "qid": ",".join(qids) or None, "topics": topics, "label": label,
        "langs": [w["code"] for w in wikis], "months": months, "sort": args.sort,
        "thresholds": thresholds, "command": " ".join(cmd), "rows": rows,
    }

    # Runs that differ only by article overrides or thresholds must not overwrite each other.
    variant = dict(overrides, **{f"threshold_{k}": v for k, v in custom.items()})
    slug = f"{'-'.join(qids) or 'articles'}_{'-'.join(run['langs'])}_{months[0]}_{months[-1]}"
    if variant:
        slug += "_" + hashlib.sha1(json.dumps(variant, sort_keys=True).encode()).hexdigest()[:6]
    out = Path(args.out) / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), "utf-8")
    _write_monthly_csv(run, out / "monthly.csv")
    render.charts(run, out, "en")
    summary = _summary(run, out)
    (out / "summary.md").write_text(summary, "utf-8")
    print(summary)
    return 0


def load_run(run_dir):
    mfile = Path(run_dir) / "metrics.json"
    if not mfile.exists():
        raise UsageError(f"{mfile} not found. Pass the run folder printed by `analyze`.")
    return json.loads(mfile.read_text("utf-8"))


def cmd_check(args):
    run = load_run(args.run_dir)
    path = Path(args.answer)
    if not path.exists():
        raise UsageError(f"{path} not found. Save the draft answer to that file, then check it.")
    text = path.read_text("utf-8")
    problems, reminders = answer.review(text, run)
    if problems:
        print("ANSWER DOES NOT MATCH THE DATA - fix these before replying:")
        print("\n".join(f"- {p}" for p in problems))
        print("Values in the data:")
        print("\n".join(f"- {v}" for v in render.allowed_values(run)))
    else:
        print("ANSWER CHECKED: every number and sign in it comes from the data.")
    print("Not checkable by code, so read the answer once against this list:")
    print("\n".join(f"- {r}" for r in reminders))
    if problems and not args.force:
        print("Rewrite the answer and run check again. Use --force only for numbers that are not metrics "
              "(e.g. the user's own targets).")
        return EXIT_FINDINGS
    # Without this the model tends to re-check an answer that already passed, then reply with an
    # unchecked summary of it - which is the one text the user actually reads.
    print("Done: this answer passed. Two things are left.")
    print("1. Did the user ask for a report, a PDF or something to share? Then run `report` now and give them the "
          "file path. Your chat message is not the report.")
    print(f"2. Send the text of {path} as your reply, word for word: do not shorten it, do not restyle it, and do "
          f"not run check again. A summary you write instead of it is not checked by anything.")
    return 0


def cmd_report(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    ftext = Path(args.findings).read_text("utf-8")
    doc = render.parse_findings(ftext)
    if not doc["sections"]:
        raise UsageError("findings.md has no sections. Use the template in SKILL.md.")

    bad = render.check_numbers(doc, run)
    if bad and not args.force:
        print("NUMBERS DO NOT MATCH THE DATA - PDF not created.")
        print("\n".join(f"- {b}" for b in bad))
        print("Values in the data:")
        print("\n".join(f"- {v}" for v in render.allowed_values(run)))
        print("Fix findings.md and run report again. Use --force only for numbers that are not metrics "
              "(e.g. the user's own targets).")
        return EXIT_FINDINGS
    lang = lang_or_en(args.lang)
    out = Path(args.out) if args.out else run_dir / f"report_{lang}.pdf"
    try:
        scale, warnings = render.report(run, doc, out, lang, date.today().isoformat())
    except ValueError as e:
        print(f"PDF not created: {e}")
        return EXIT_FINDINGS
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"PDF: {out.resolve()} (1 page, labels: {lang}, text size {round(scale * 100)}%)")
    print(f"Charts: {out.parent.resolve() / f'charts_{lang}'} (labels: {chart_lang(lang)})")
    print("Numbers check: skipped (--force)." if args.force else
          "Numbers check: every percentage, N/12 and plain number in findings matches the data, signs included.")
    return 0


def _write_monthly_csv(run, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "lang", "article", "views", "views_without_spikes", "wikipedia_views"])
        for r in run["rows"]:
            if r["status"] != "ok":
                continue
            m = r["metrics"]
            for mon in run["months"]:
                w.writerow([mon, r["code"], r["title"], m["monthly"][mon], m["monthly_clean"][mon],
                            m["wiki_monthly"].get(mon, "")])


def _year_change(prev, last):
    """Label for how adjusted growth changed between the last two years (5-point threshold)."""
    if prev is None or last is None:
        return "no comparison"
    if last - prev > metrics.FLAT:
        return "improving" + (" (still declining)" if last < -metrics.FLAT else "")
    if last - prev < -metrics.FLAT:
        return "worsening"
    return "about the same"


def _vpd(x):
    return f"{x:.1f}" if x < 10 else f"{x:,.0f}"


def _summary(run, out):
    months = run["months"]
    by = {"confidence": "adjusted growth, LOW confidence last", "growth": "adjusted growth",
          "volume": "views/day"}[run["sort"]]
    lines = [
        f"# Wikipedia interest: {run['label']}" + (f" ({run['qid']})" if run["qid"] else ""),
        f"Period {months[0]}..{months[-1]} ({len(months)} complete months). Human views, all platforms. "
        "Growth = last 12 months vs previous 12.",
        "",
        "| # | edition | article | views/day | growth | w/o spikes | adjusted | months up | trend | confidence |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in run["rows"]:
        if r["status"] != "ok":
            status = "MISSING (no article)" if r["status"] == "missing" else "NO VIEWS"
            lines.append(f"| - | {r['english']} ({r['code']}) | {r['title'] or '-'} | - | - | - | - | - | - | {status} |")
            continue
        m = r["metrics"]
        title = r["title"] + (" (proxy)" if r["proxy"] else "")
        lines.append(f"| {r['rank']} | {r['english']} ({r['code']}) | {title} | {_vpd(m['views_per_day'])} | {pct(m['growth'])} | "
                     f"{pct(m['growth_clean'])} | {pct(m['adj_growth'])} | {m['months_up']}/12 | {r['trend']} | "
                     f"{r['confidence']} |")
    lines += [
        "",
        f"Adjusted = change in the article's share of all views of that Wikipedia (removes the overall traffic "
        f"trend). Ranked by {by}.",
    ]
    if len(run.get("topics") or {}) > 1:
        lines += ["", "## Topic basket (a language's views are the sum of its articles)"]
        for r in run["rows"]:
            parts = " + ".join(f"{a['title']} ({_vpd(a['views_per_day'])}/day)" for a in r["articles"])
            gap = (f" - no article for {', '.join(r['absent'])}, so fewer articles are counted here than elsewhere"
                   if r["absent"] else "")
            lines.append(f"- {r['code']}: {parts or 'nothing from this basket'}{gap}")
    lines += ["", "## Why this confidence"]
    th = run.get("thresholds", DEFAULT_THRESHOLDS)
    if th != DEFAULT_THRESHOLDS:
        lines.append(f"Thresholds set by the user, not the defaults ({DEFAULT_THRESHOLDS['low_views']:g}/"
                     f"{DEFAULT_THRESHOLDS['high_views']:g}): under {th['low_views']:g} views/day = LOW, "
                     f"{th['high_views']:g}+ needed for HIGH. Say so when you report confidence.")
    else:
        lines.append(f"Default thresholds: under {th['low_views']:g} views/day = LOW, {th['high_views']:g}+ needed "
                     f"for HIGH. If the user said what audience size matters to them, rerun with --low-views N "
                     f"--high-views N so confidence answers their question and not the default one.")
    for r in run["rows"]:
        if r["status"] == "missing":
            what = f" for {', '.join(r['absent'])}" if r["absent"] else ""
            lines.append(f"- {r['code']}: no article in {r['english']} Wikipedia{what}. Interest there cannot be "
                         f"measured; `find` lists similar articles.")
        elif r["status"] == "no_views":
            lines.append(f"- {r['code']}: article '{r['title']}' had no views in the period (wrong title?).")
        else:
            lines.append(f"- {r['code']} {r['confidence']}: " + "; ".join(reason(c, p) for c, p in r["reasons"]))
    ok = [r for r in run["rows"] if r["status"] == "ok"]
    if ok and len(ok[0]["metrics"]["yearly"]) >= 2:
        lines += ["", "## Year by year (w/o spikes / adjusted), each 12 months vs the 12 before",
                  "The main table always compares the last 12 months with the previous 12; longer --months adds "
                  "these earlier years. Use them for multi-year questions."]
        for r in ok:
            ys = r["metrics"]["yearly"]
            steps = "; ".join(f"{y['period']}: {pct(y['growth_clean'])} / {pct(y['adj_growth'])}" for y in ys)
            lines.append(f"- {r['code']}: {steps} -> {_year_change(ys[-2]['adj_growth'], ys[-1]['adj_growth'])}")
    spikes = [(r["code"], s) for r in run["rows"] if r["status"] == "ok" for s in r["metrics"]["top_spikes"]]
    if spikes:
        lines += ["", "## Top spike days"]
        lines += [f"- {c}: {s['date']} - {s['views']:,} views, {s['times']}x normal" for c, s in spikes]
    wiki = [f"{r['code']} {pct(r['metrics']['wiki_growth'])}" for r in run["rows"] if r["status"] == "ok"]
    if wiki:
        lines += ["", "Whole-Wikipedia human views, last 12 vs previous 12 months: " + ", ".join(wiki) + "."]
    must = ["State confidence and its reason for every trend: HIGH = reliable, MEDIUM = plausible but unconfirmed "
            "(never call it reliable), LOW = not confirmed.",
            "End with limitations: a language edition is not a country; views show curiosity, not willingness to pay.",
            "Claim only what views show: nothing about competition, market readiness, money or causes of a trend."]
    if months[0] <= "2025-08":
        must.append("Mention: Wikimedia reclassified bot traffic for 2025-03..2025-08, so part of a decline across 2025 "
                    "can be a counting change (the 'adjusted' column is the safer signal).")
    if any(r["status"] == "missing" for r in run["rows"]):
        must.append("Languages without an article cannot be measured. Do not replace them with a broader or different "
                    "topic and do not compare such a substitute with the other languages.")
    if any(r["status"] == "ok" and r["absent"] for r in run["rows"]):
        must.append("A language missing part of the basket has fewer articles counted, so its total is smaller for "
                    "that reason alone: name the missing article before you rank or compare that language.")
    lines += ["", "## Answer rules"] + [f"- {m}" for m in must]
    lines += [
        "",
        "## Answer template (user's language)",
        "1. Direct answer in one sentence.",
        "2. One line per language edition, in rank order: '<Language>-language Wikipedia' (never a country name or flag), "
        "adjusted growth, confidence + reason. Numbers only from the table above; no sums or new numbers. "
        "views/day are page views, not people: write 'views', never 'users' or 'visitors'.",
        "3. What to research next and what to verify there. Name only things this data can point at: a language "
        "edition, a period, an article. Never a cause, a market or a competitor - 'the Vietnamese web is growing', "
        "'the market is saturated', 'other platforms are replacing Wikipedia' are inventions, not findings.",
        "4. Limitations, translated: 'A language edition is not a country; views show curiosity, not willingness "
        "to pay.'" + (" Add the bot reclassification note." if months[0] <= "2025-08" else ""),
    ]
    lines += [
        "",
        f"Files: {out.as_posix()}/ (metrics.json, monthly.csv, trend.png, growth.png)",
        f"Before you send the answer, save the draft to answer.md and run: {WI} check {shlex.quote(out.as_posix())} --answer answer.md",
        f"Rerun or change one parameter: {run['command']}",
        f"Report: write findings.md (template in SKILL.md), then: {WI} report {shlex.quote(out.as_posix())} --findings findings.md "
        f"--lang <user's language: {' '.join(LANGS)}; others: en>",
    ]
    return "\n".join(lines) + "\n"


def build_parser():
    p = argparse.ArgumentParser(prog="wi", description="Wikipedia interest research: find, analyze, report.")
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("find", help="Find the Wikidata item for a topic and its article in each language.")
    f.add_argument("topic", nargs="?", default="", help="Topic in any language, e.g. 'астрономія'.")
    f.add_argument("--langs", help="Wikipedia language codes or names, comma-separated: pl,cs,uk")
    f.add_argument("--query-lang", default="en", help="Language code the topic is written in (default: en).")
    f.add_argument("--qid", help="Skip search, show articles for this Wikidata item (e.g. Q333).")
    f.add_argument("--limit", type=int, default=3, help="Number of candidates (default 3).")
    f.set_defaults(func=cmd_find)

    a = sub.add_parser("analyze", help="Fetch pageviews, compute metrics, rank languages, draw charts.")
    a.add_argument("qid", nargs="?", metavar="QID[,QID...]",
                   help="Wikidata item from `find`, e.g. Q1666254. Several comma-separated items form one topic "
                        f"basket (max {MAX_BASKET}): each language's views are the sum of its articles, which is how "
                        "to measure a broad intent such as Q1860,Q212262 for learning English.")
    a.add_argument("--langs", help="Wikipedia language codes, comma-separated: pl,cs")
    a.add_argument("--article", action="append", metavar='LANG:"Title"',
                   help='Use this article for a language (proxy or no QID). Repeatable: --article pl:"Głodówka '
                        'lecznicza". Repeating one language replaces that language\'s whole basket.')
    a.add_argument("--months", type=int, default=24, help="Months to analyze, >= 24 (default 24).")
    a.add_argument("--end", help="Last month YYYY-MM (default: last complete month).")
    a.add_argument("--sort", default="confidence", choices=metrics.SORTS,
                   help="Ranking: confidence (default), growth (adjusted), volume (views/day).")
    a.add_argument("--low-views", type=float, default=metrics.LOW_VOLUME, metavar="N",
                   help=f"Views/day below which a trend is LOW, i.e. the smallest audience worth trusting "
                        f"(default {metrics.LOW_VOLUME}). Raise it to rank small editions last.")
    a.add_argument("--high-views", type=float, default=metrics.HIGH_VOLUME, metavar="N",
                   help=f"Views/day needed before a trend can be HIGH (default {metrics.HIGH_VOLUME}).")
    a.add_argument("--out", default="wiki-research", help="Output folder (default ./wiki-research).")
    a.set_defaults(func=cmd_analyze)

    c = sub.add_parser("check", help="Check a draft chat answer against the data before sending it.")
    c.add_argument("run_dir", help="Run folder printed by analyze (contains metrics.json).")
    c.add_argument("--answer", required=True, metavar="FILE", help="File holding the draft answer, in any language.")
    c.add_argument("--force", action="store_true", help="Print the problems but exit 0.")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("report", help="One-page PDF from an analyze run and the agent's findings.md.")
    r.add_argument("run_dir", help="Run folder printed by analyze (contains metrics.json).")
    r.add_argument("--findings", required=True, help="Markdown with title, Question:, ## sections (see SKILL.md).")
    r.add_argument("--lang", default="en", help="Language of fixed labels, e.g. uk, pl, ja, ar (unknown -> en).")
    r.add_argument("--out", help="PDF path (default: <run_dir>/report_<lang>.pdf).")
    r.add_argument("--force", action="store_true", help="Skip the numbers check.")
    r.set_defaults(func=cmd_report)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "find" and not (args.topic or args.qid):
        print("ERROR: give a topic or --qid.", file=sys.stderr)
        return EXIT_USAGE
    # A traceback is the worst output for a small model: it says nothing about what to do next.
    try:
        return args.func(args)
    except wikiapi.ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_NETWORK
    except (UsageError, wikiapi.LangError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
