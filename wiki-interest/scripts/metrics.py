"""Interest metrics from daily pageviews. Pure functions, no network.

Rules and thresholds are explained in references/methodology.md.
"""
import calendar
from datetime import date, timedelta
from statistics import median

SPIKE_FACTOR = 3.0     # a day is a spike if views > 3x its local median...
SPIKE_MIN_EXCESS = 30  # ...and at least 30 views above it (ignores noise at tiny volumes)
SPIKE_WINDOW = 14      # local median = median of +-14 days
SPIKE_WARMUP = SPIKE_WINDOW  # days fetched before the period so its first days get a full window
DATA_START = "2015-07"  # Wikimedia pageviews start here; earlier months hold no data, not zero interest
LOW_VOLUME = 20        # views/day below this -> LOW confidence
HIGH_VOLUME = 100      # views/day needed for HIGH confidence
FLAT = 0.05            # |change| below 5% counts as flat
STABLE_MONTHS = 9      # months (of 12) moving in the trend direction needed for HIGH

SORTS = ("confidence", "growth", "volume")


# --- months ----------------------------------------------------------------------

def last_complete_month(today):
    """Latest month whose data is surely complete (pageviews lag about a day)."""
    ref = today - timedelta(days=2)
    y, m = ref.year, ref.month - 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


def month_list(end, n):
    """n consecutive months ending with `end` ('YYYY-MM'), oldest first."""
    y, m = map(int, end.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def month_bounds(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def _days(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


# --- core metrics ----------------------------------------------------------------

def detect_spikes(values):
    """Replace spike days with their local median. Returns (cleaned, spike_indexes, medians)."""
    n = len(values)
    cleaned, spikes, medians = list(values), [], []
    for i, v in enumerate(values):
        med = median(values[max(0, i - SPIKE_WINDOW):min(n, i + SPIKE_WINDOW + 1)])
        medians.append(med)
        if v > SPIKE_FACTOR * med and v - med >= SPIKE_MIN_EXCESS:
            spikes.append(i)
            cleaned[i] = med
    return cleaned, spikes, medians


def change(new, old):
    return None if not old else new / old - 1


def sign(x):
    if x is None or abs(x) < FLAT:
        return 0
    return 1 if x > 0 else -1


def analyze_series(daily, wiki_monthly, months, warmup=0):
    """Metrics for one article.

    daily: {'YYYYMMDD': views} (missing days = 0); wiki_monthly: {'YYYY-MM': views of the
    whole Wikipedia}; months: >= 24 complete months, oldest first.

    warmup: days present in `daily` before the period. Spikes are detected over the longer
    series and the warm-up is then dropped, so the metrics do not depend on how far back the
    caller asked. Without it the first days of the baseline year get a truncated median window.
    """
    if len(months) < 24:
        raise ValueError("need at least 24 months: growth compares the last 12 months with the previous 12")
    start = month_bounds(months[0])[0]
    days = _days(start - timedelta(days=warmup), month_bounds(months[-1])[1])
    values = [daily.get(d.strftime("%Y%m%d"), 0) for d in days]
    cleaned, spike_idx, medians = detect_spikes(values)
    if warmup:
        days, values, cleaned, medians = days[warmup:], values[warmup:], cleaned[warmup:], medians[warmup:]
        spike_idx = [i - warmup for i in spike_idx if i >= warmup]

    monthly = {m: 0 for m in months}
    monthly_clean = {m: 0.0 for m in months}
    for d, v, c in zip(days, values, cleaned):
        key = f"{d.year:04d}-{d.month:02d}"
        monthly[key] += v
        monthly_clean[key] += c

    last, prev = months[-12:], months[-24:-12]

    def total(series, ms):
        return sum(series.get(m, 0) for m in ms)

    wiki_last, wiki_prev = total(wiki_monthly, last), total(wiki_monthly, prev)
    share_last = total(monthly_clean, last) / wiki_last if wiki_last else None
    share_prev = total(monthly_clean, prev) / wiki_prev if wiki_prev else None
    days_last = (month_bounds(last[-1])[1] - month_bounds(last[0])[0]).days + 1

    leading_zero = 0
    for m in months:
        if monthly[m]:
            break
        leading_zero += 1

    # Year-over-year for every full 12-month block (oldest first), so --months 36+ adds real history.
    blocks = [months[len(months) - 12 * (k + 1):len(months) - 12 * k] for k in range(len(months) // 12)][::-1]
    yearly = []
    for i in range(1, len(blocks)):
        cur, old = blocks[i], blocks[i - 1]
        w_cur, w_old = total(wiki_monthly, cur), total(wiki_monthly, old)
        c_cur, c_old = total(monthly_clean, cur), total(monthly_clean, old)
        yearly.append({
            "period": f"{cur[0]}..{cur[-1]}", "vs": f"{old[0]}..{old[-1]}",
            "growth_clean": change(c_cur, c_old),
            "adj_growth": change(c_cur / w_cur, c_old / w_old) if w_cur and w_old and c_old else None,
        })

    all_views = sum(values)
    top = sorted(spike_idx, key=lambda i: values[i] - medians[i], reverse=True)[:3]
    return {
        "views_per_day": total(monthly, last) / days_last,
        "views_last12": total(monthly, last),
        "views_prev12": total(monthly, prev),
        "growth": change(total(monthly, last), total(monthly, prev)),
        "growth_clean": change(total(monthly_clean, last), total(monthly_clean, prev)),
        "adj_growth": change(share_last, share_prev) if share_last is not None else None,
        "wiki_growth": change(wiki_last, wiki_prev),
        "months_up": sum(monthly_clean[a] > monthly_clean[b] for a, b in zip(last, prev)),
        "months_down": sum(monthly_clean[a] < monthly_clean[b] for a, b in zip(last, prev)),
        "leading_zero_months": leading_zero if leading_zero < len(months) else 0,
        "spike_days": len(spike_idx),
        "spike_share": sum(values[i] - medians[i] for i in spike_idx) / all_views if all_views else 0.0,
        "top_spikes": [{"date": days[i].isoformat(), "views": values[i], "normal": round(medians[i]),
                        "times": round(values[i] / max(medians[i], 1), 1)} for i in top],
        "yearly": yearly,
        "total_views": all_views,
        "monthly": monthly,
        "monthly_clean": {k: round(v) for k, v in monthly_clean.items()},
    }


def confidence(m):
    """(level, reasons). Reasons are (code, params) pairs; texts live in i18n.py."""
    g, gc, adj = m["growth"], m["growth_clean"], m["adj_growth"]
    vpd = m["views_per_day"]

    low = []
    if vpd < LOW_VOLUME:
        low.append(("low_volume", {"vpd": vpd, "min": LOW_VOLUME}))
    if m["leading_zero_months"]:
        low.append(("appeared", {"months": m["leading_zero_months"]}))
    if g is None:
        low.append(("no_baseline", {}))
    elif abs(g) >= FLAT and (sign(g) != sign(gc) or abs(gc) < 0.5 * abs(g)):
        low.append(("spike_driven", {"growth": g, "clean": gc}))
    if low:
        return "LOW", low

    direction = sign(gc)
    steady = m["months_up"] if direction > 0 else m["months_down"]
    checks = [
        (vpd >= HIGH_VOLUME, ("volume_ok", {"vpd": vpd}), ("moderate_volume", {"vpd": vpd, "min": HIGH_VOLUME})),
        (direction == 0 or steady >= STABLE_MONTHS,
         ("steady", {"n": steady, "dir": direction}), ("unsteady", {"n": steady, "need": STABLE_MONTHS, "dir": direction})),
        (sign(gc) == sign(adj), ("agree", {}), ("disagree", {"clean": gc, "adj": adj, "wiki": m["wiki_growth"]})),
    ]
    if all(ok for ok, _, _ in checks):
        return "HIGH", [good for _, good, _ in checks]
    return "MEDIUM", [bad for ok, _, bad in checks if not ok]


def trend(m):
    """'up' / 'down' / 'flat' by growth without spikes."""
    return {1: "up", -1: "down", 0: "flat"}[sign(m["growth_clean"])]


def rank(rows, by="confidence"):
    """Order languages. rows: dicts with status, confidence, metrics. Missing ones go last."""
    if by not in SORTS:
        raise ValueError(f"--sort must be one of {', '.join(SORTS)}")
    ok = [r for r in rows if r["status"] == "ok"]
    rest = [r for r in rows if r["status"] != "ok"]

    def adj(r):
        a = r["metrics"]["adj_growth"]
        return -a if a is not None else float("inf")

    # Confidence only demotes unreliable (LOW) rows; it must not lift a confident decline above real growth.
    keys = {
        "confidence": lambda r: (r["confidence"] == "LOW", adj(r)),
        "growth": adj,
        "volume": lambda r: -r["metrics"]["views_per_day"],
    }
    ok.sort(key=keys[by])
    for i, r in enumerate(ok, 1):
        r["rank"] = i
    for r in rest:
        r["rank"] = None
    return ok + rest
