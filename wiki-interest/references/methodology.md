# Methodology

How `analyze` turns pageviews into metrics and a confidence level. Thresholds live at the top of `scripts/metrics.py`.

## Data

- Source: [Wikimedia Pageviews API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html), `agent=user` (bots and crawlers excluded), `all-access` (desktop, mobile web, app).
- Article per language: Wikidata sitelinks of the chosen item. No sitelink = `MISSING`, never guessed.
- Period: the last N complete months (default 24, minimum 24). The current month is never used.
- Per article: daily views. Per Wikipedia: monthly total human views (for the adjusted metric).
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

**Spike:** a day with views > 3x its local median (median of +-14 days) and at least 30 views above it. Replaced by the local median. Events that last longer than about two weeks raise the median and count as real interest.

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

## Ranking

Default: by adjusted growth; LOW-confidence languages go last. Confidence only demotes unreliable rows: a confident decline never outranks a stable or growing language. `--sort growth` ignores confidence; `--sort volume` ranks by views/day.

## Report checks

- `report` compares every percentage and `N/12` in `findings.md` (except the `Question:` line) with the run's metrics, tolerance +-1 point. Mismatch = no PDF; `--force` skips the check.
- Always one A4 page: text shrinks down to 76%, otherwise `report` fails and asks for shorter findings.
- Labels (table, assumptions, limitations): `scripts/locales/<lang>.json` for en, uk, pl, cs, de, es, fr, pt, tr, vi, ja, zh, ar, hi; other languages get English. Texts other than English and Ukrainian were machine-translated and not reviewed by native speakers.
- Fonts: DejaVu Sans (bundled with matplotlib) for Latin, Cyrillic, Greek. For CJK, Arabic, Hebrew, Devanagari, Bengali and Thai, `scripts/fonts.py` downloads the needed Noto font on first use from a pinned commit, checks its SHA-256 and caches it in `~/.cache/wiki-interest/fonts/`. Arabic, Hebrew and Indic text is shaped with HarfBuzz (`uharfbuzz`); Arabic reports are right-aligned.
- Charts use the report language only for Latin/Cyrillic scripts; otherwise English (matplotlib cannot shape Arabic or Indic text).
- The numbers check also reads Arabic-Indic and full-width digits (`٥٠٪`, `５０％`).

## Limitations

- Views show curiosity, not willingness to pay.
- A language edition is not a country; many people read Wikipedia in another language.
- One article is a proxy for a topic; search, AI assistants and video are not covered.
- Total Wikipedia traffic is falling: in 2025 Wikimedia improved bot detection and reclassified March-August 2025 traffic, and reported about 8% fewer human pageviews than a year earlier ([source](https://diff.wikimedia.org/2025/10/17/new-user-trends-on-wikipedia/)). Prefer `adjusted` over raw growth.
- Page views of redirects (old titles) are not added; a rename inside the period shows up as `LOW` (article appeared).
