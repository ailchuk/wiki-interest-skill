---
name: wiki-interest
description: Measures and compares public interest in a topic across Wikipedia language editions from Wikimedia pageview data - growth, trust level, charts and a one-page PDF report. Use when the user asks whether interest in a topic is growing, compares interest between languages or markets, decides which course, topic or language to launch or localize next, or wants a Wikipedia-based trend report. Requests may be in any language, e.g. Ukrainian "інтерес до теми", "Вікіпедія", "мовні розділи", "порівняй зростання інтересу", "чи зростає інтерес".
compatibility: Requires bash, Python 3.10+ and internet access to Wikimedia APIs. The first run installs matplotlib, fpdf2 and uharfbuzz into the skill's .venv (1-2 min); PDFs in CJK, Arabic or Indic scripts download a Noto font on first use.
---

# Wikipedia interest research

Run every command as `bash <skill-dir>/scripts/wi <command>`, where `<skill-dir>` is the absolute path of the folder containing this SKILL.md. Run from the user's working directory; results go to `./wiki-research/`.

## Workflow

1. **Find the article.**
   `bash <skill-dir>/scripts/wi find "<topic as the user wrote it>" --langs pl,cs --query-lang uk`
   - `--langs`: Wikipedia codes (Polish pl, Czech cs, Ukrainian uk, German de, Spanish es, Norwegian no). A wrong code prints the right one.
   - `--query-lang`: language the topic is written in.
   - Pick the candidate that matches the user's meaning. If two fit and the answer would differ, ask the user.
   - `MISSING` = no article in that language: interest there cannot be measured, say so. Never invent a title. Never replace it with a broader or different topic (e.g. "fasting" for "intermittent fasting") and never compare such a substitute with other languages. Use `--article pl:"Title"` only for the same concept, and call it a proxy.
2. **Analyze.** Run the `Next:` command printed by `find`. Options: `--months 36` (min 24), `--sort growth|volume`, `--article lang:"Title"`.
3. **Answer** from the `analyze` output only (see rules).
4. **Report** only when the user asks for a report, PDF or something to share (see below).

## How to read `analyze` output

- `growth`: last 12 months vs previous 12 (seasonality cancels out).
- `w/o spikes`: same, with news/event days replaced by the usual level.
- `adjusted`: change in the article's share of all views of that Wikipedia. **Main interest signal**: total Wikipedia traffic is falling (AI answers, bot reclassification in 2025), so raw declines are often not lost interest.
- `confidence` HIGH / MEDIUM / LOW with reasons, computed by the tool. LOW = trend not confirmed.
- Rank: by adjusted growth, LOW confidence last. `--sort volume` if the user cares about audience size.
- Multi-year questions: run with `--months 36` (or more) and use the `Year by year` block with its `improving / worsening / about the same` labels. The main table always compares the last 12 months with the previous 12.

## Rules

- Follow the `## Answer rules` printed at the end of `analyze` output.
- Cite only numbers printed by the tool. Do not compute new percentages.
- Every claim about a trend states its confidence and the reason. HIGH = reliable, MEDIUM = plausible but unconfirmed, LOW = not confirmed.
- Claim only what views show: nothing about competition, market readiness, money or causes. Recommend which audiences to research next and what to check there.
- End every answer with limitations: a language edition is not a country; interest is not willingness to pay.
- Answer in the user's language.
- Follow-ups (other period, languages, sorting): rerun the printed `Rerun` command with the changed parameter. Data is cached, so this is instant. Run `find` again only for a new topic.
- Broad intents ("learning English"): analyze 2-3 related articles (e.g. English language Q1860 and IELTS) and say they are proxies.

## If a command fails

Output starting with `ERROR:` says what to fix: fix exactly that and run the same command again. Never route around a failure by inventing an article title, a number or a trend, and never silently drop a language the user asked about. Exit code 2 = wrong input, 3 = findings do not match the data, 4 = network or install.

- `No Wikidata item found` - rerun `find` with the topic's English name, then with a more specific term. Still nothing: tell the user the topic could not be located on Wikidata.
- `not a Wikipedia language code` - use the code the message suggests.
- `Network error` / exit 4 - retry the command once. If it fails again, tell the user the Wikimedia API is unreachable and stop. Lines starting with `[wi]` are retries in progress, not failures.
- `NUMBERS DO NOT MATCH THE DATA` - correct `findings.md` from the values printed below the message, then run `report` again.

## Report (PDF, one page)

Write `findings.md` in the user's language:

```
# <Short title>
Question: <the user's question>

## Findings
- <3-5 bullets, numbers only from analyze output, each with its confidence>

## Recommendation
<2-3 sentences: which audiences to research next, why, and what to verify there>
```

Keep `Question:` as a plain line; use `-` bullets. Limitations and assumptions are added to the PDF automatically.

Then run `bash <skill-dir>/scripts/wi report <run-dir> --findings findings.md --lang <code>` with the user's language: `en uk pl cs de es fr pt tr vi ja zh ar hi` (others get English labels). The run dir is printed by `analyze`. Fonts for Chinese, Japanese, Korean, Arabic, Hebrew and Indic scripts download automatically on first use. If `report` lists numbers that do not match the data, fix `findings.md` and run it again. Give the user the PDF path.

Metric details and thresholds: [references/methodology.md](references/methodology.md).
