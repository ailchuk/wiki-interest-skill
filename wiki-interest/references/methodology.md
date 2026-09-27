# Methodology

How `analyze` turns pageviews into metrics and a confidence level. Thresholds live at the top of `scripts/metrics.py`.

## Data

- Source: [Wikimedia Pageviews API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html), `agent=user` (bots and crawlers excluded), `all-access` (desktop, mobile web, app).
- Article per language: Wikidata sitelinks of the chosen item. No sitelink = `MISSING`, never guessed.
- Topic basket: `analyze` accepts up to 5 comma-separated Wikidata items, and a language's daily series is then the sum of its articles' series. Summing is only valid because the parts come from the same days and the same language edition; the adjusted metric stays correct too, since the whole-Wikipedia total it divides by is the same for every article of that language. Per-article views/day are computed over the same 12 months as the combined figure, so the parts add up to the total. A language holding only part of the basket is marked: its total is smaller for that reason alone, which the summary, the answer rules and the PDF assumptions all say out loud. An `--article` override replaces that language's whole basket, because which item a hand-picked title stands for cannot be inferred.
- Period: the last N complete months (default 24, minimum 24). The current month is never used. Wikimedia pageviews start in 2015-07; a longer period is trimmed to that month and `analyze` says so, because months without data are not months without interest.
- Per article: daily views, plus 14 days before the period as a warm-up for spike detection (see below). Per Wikipedia: monthly total human views (for the adjusted metric).
- Cache: `~/.cache/wiki-interest/` (override with `WI_CACHE_DIR`). Complete months never change, so pageviews are cached forever; Wikidata and search lookups for 7 days, the list of Wikipedias for 30 days.

## Metrics (per language)

| Metric | Definition |
|---|---|
| views/day | Views in the last 12 months / days. Audience size of that language edition. |
| growth | Views in the last 12 months / previous 12 months - 1. Same calendar months on both sides, so seasonality cancels out. |
| w/o spikes | Same, after replacing spike days with the usual level. |
| adjusted | Change of the article's share of all views of that Wikipedia (spike-free views / whole-Wikipedia views). Main interest signal. |
| months up | How many of the last 12 months beat the same month a year earlier (spike-free). |
| whole wiki | Growth of total human views of that Wikipedia. |
| year by year | With `--months 36` or more: w/o-spikes and adjusted growth for every full 12-month block vs the block before, plus a label from the last two years' adjusted growth: `improving` / `worsening` (change over 5 points) or `about the same`. |

**Spike:** a day with views > 3x its local median (median of +-14 days) and at least 30 views above it. Replaced by the local median. Events that last longer than about two weeks raise the median and count as real interest. The 14 days fetched before the period give its first days a full window, so the same question returns the same numbers whether it was asked with `--months 24` or `--months 36`. The last days of the period have no such margin; there the median is taken over the days available.

## Confidence

LOW if any of:
- views/day < 20;
- no views in the first month(s) of the period: the article was created or renamed inside it;
- no views in the previous 12 months (growth undefined);
- growth is spike-driven: |growth| >= 5% and, without spikes, it changes direction or shrinks by more than half.

HIGH if all of:
- views/day >= 100;
- at least 9 of 12 months move in the trend direction (a trend within +-5% counts as flat and passes);
- growth without spikes and adjusted growth have the same direction (up / flat / down, flat = within +-5%).

Otherwise MEDIUM. Every level is printed with its reasons.

What counts as a usable audience depends on the niche, so the two volume thresholds are arguments: `--low-views` (default 20) and `--high-views` (default 100). Raising `--low-views` doubles as an audience floor, because the default ranking already sends LOW rows to the bottom. A changed threshold goes into the run folder name, the rerun command, the `analyze` summary and the PDF assumptions, so a report never misdescribes how its confidence was set.

## Ranking

Default: by adjusted growth; LOW-confidence languages go last. Confidence only demotes unreliable rows: a confident decline never outranks a stable or growing language. `--sort growth` ignores confidence; `--sort volume` ranks by views/day.

## Answer and report checks

Both the chat answer (`check`) and the PDF (`report`) are verified against the run with the same code, because the answer the user reads first deserves the same gate as the document.

- `check` reads a draft answer in any language and splits its output in two. **Problems** are what code can judge on its own: numbers that are not in the data (same rules as below) and flag emoji, which turn a language edition into a country. Problems set exit code 3, so the agent must rewrite before replying; `--force` reports them and exits 0.
- **Check yourself** is the rest: languages that returned no data, confidence levels the answer never names, the two mandatory limitations, the 2025 bot note when the period covers it, and the ban on causes. These are hints, not verdicts - the answer is written in the user's own words, so their absence is detected by matching stems from all 14 locales plus English, and a synonym can slip through. They are never a reason to block.
- `report` compares every number in `findings.md` (except the `Question:` line) with the run's metrics. Mismatch = no PDF; `--force` skips the check.
  - Percentages: tolerance +-1 point. A percentage written with an explicit `+` or `-` must also match the direction, so calling a decline `+34%` is rejected. Without a sign the direction lives in the surrounding words ("fell by 34%"), so only the magnitude is compared.
  - `N/12`: must be one of the months-up or months-down counts.
  - Plain numbers from 10 up: must be within 10% of something the tool prints (views/day of a language and of each basket article, spike-day views and multipliers, month counts, years of the period). This catches an invented audience size such as "4200 views per day" when the article has 6. Dates and numbers below 10 are ignored, since those are counts of languages or bullets rather than data.
- Always one A4 page: text shrinks down to 76%, otherwise `report` fails and asks for shorter findings.
- Labels (table, assumptions, limitations): `scripts/locales/<lang>.json` for en, uk, pl, cs, de, es, fr, pt, tr, vi, ja, zh, ar, hi; other languages get English. Texts other than English and Ukrainian were machine-translated and not reviewed by native speakers.
- Fonts: DejaVu Sans (bundled with matplotlib) for Latin, Cyrillic, Greek. For CJK, Arabic, Hebrew, Devanagari, Bengali and Thai, `scripts/fonts.py` downloads the needed Noto font on first use from a pinned commit, checks its SHA-256 and caches it in `~/.cache/wiki-interest/fonts/`. Arabic, Hebrew and Indic text is shaped with HarfBuzz (`uharfbuzz`); Arabic reports are right-aligned.
- Charts use the report language only for Latin/Cyrillic scripts; otherwise English (matplotlib cannot shape Arabic or Indic text).
- The numbers check also reads Arabic-Indic and full-width digits (`٥٠٪`, `５０％`).

## Errors

Every failure is reported as a single `ERROR:` line that names the fix; the agent never sees a traceback. Exit codes separate the kinds of fix: `0` success, `1` environment (no Python 3.10+, venv could not be created), `2` wrong input (unknown language code or QID, bad `--article` or `--end`, missing file, topic not found), `3` the answer or the findings do not match the data, or the findings do not fit one page, `4` network or dependency install.

Partial failures never stop a run: a language without an article becomes `MISSING`, a wrong title becomes `NO VIEWS`, a font that will not download leaves a warning and blank glyphs rather than no PDF, and findings that are too long shrink to 76% before being rejected. Requests are retried five times with exponential backoff on 429 and 5xx; each wait prints a `[wi]` line so the pause is not mistaken for a hang. HTTP 404 means "no data", not an error.

## Limitations

- Views show curiosity, not willingness to pay.
- A language edition is not a country; many people read Wikipedia in another language.
- The chosen articles (one, or a basket) are a proxy for a topic; other related articles, search, AI assistants and video are not covered.
- Total Wikipedia traffic is falling: in 2025 Wikimedia improved bot detection and reclassified March-August 2025 traffic, and reported about 8% fewer human pageviews than a year earlier ([source](https://diff.wikimedia.org/2025/10/17/new-user-trends-on-wikipedia/)). Prefer `adjusted` over raw growth.
- Page views of redirects (old titles) are not added; a rename inside the period shows up as `LOW` (article appeared).
