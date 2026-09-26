"""Wikimedia APIs: Wikipedia list, Wikidata lookup, Wikipedia search, pageviews.

Every response is cached as a JSON file. Pageview requests always cover complete
past months, so they never change and are cached forever; lookups expire after a week.
"""
import difflib
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "wiki-interest-skill/0.1 (https://github.com/ailchuk/case)"
PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
WIKIDATA = "https://www.wikidata.org/w/api.php"
META = "https://meta.wikimedia.org/w/api.php"

WEEK = 7 * 24 * 3600
MONTH = 30 * 24 * 3600

CACHE_DIR = Path(
    os.environ.get("WI_CACHE_DIR")
    or Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "wiki-interest"
)


class ApiError(RuntimeError):
    pass


class LangError(ValueError):
    pass


def get_json(url, params=None, ttl=None):
    """GET JSON with file cache. ttl=None caches forever. Returns None on HTTP 404."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    path = CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if path.exists() and (ttl is None or time.time() - path.stat().st_mtime < ttl):
        return json.loads(path.read_text("utf-8"))["body"]
    body = _fetch(url)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"url": url, "body": body}, ensure_ascii=False), "utf-8")
    tmp.replace(path)
    return body


def _retrying(host, attempt, delay, why):
    """Say why the wait happens, so a waiting agent does not read it as a hang."""
    print(f"[wi] {host} {why}; retry {attempt + 1}/4 in {delay:.0f}s", file=sys.stderr)


def _fetch(url):
    host = urllib.parse.urlparse(url).netloc
    delay = 1.0
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                _retrying(host, attempt, delay, f"answered HTTP {e.code}")
                time.sleep(delay)
                delay *= 2
                continue
            raise ApiError(f"HTTP {e.code} from {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4:
                _retrying(host, attempt, delay, "did not answer")
                time.sleep(delay)
                delay *= 2
                continue
            raise ApiError(f"Network error for {url}: {e}. Check internet access.") from e


# --- Wikipedia language editions -------------------------------------------------

def wikipedias():
    """All open Wikipedias: {code: {code, name, english, dbname, project}}."""
    data = get_json(META, {
        "action": "sitematrix", "smtype": "language", "format": "json", "formatversion": 2,
        "smsiteprop": "url|dbname|code", "smlangprop": "code|name|localname|site", "uselang": "en",
    }, ttl=MONTH)
    wikis = {}
    for key, lang in data["sitematrix"].items():
        if key == "count":
            continue
        for site in lang.get("site", []):
            if site["code"] == "wiki" and not site.get("closed"):
                host = urllib.parse.urlparse(site["url"]).netloc
                code = host.split(".")[0]
                wikis[code] = {
                    "code": code,
                    "name": lang.get("name", ""),
                    "english": lang.get("localname", ""),
                    "dbname": site["dbname"],
                    "project": host.removesuffix(".org"),
                }
    return wikis


def resolve_langs(spec):
    """'pl, cs, Ukrainian' -> [wiki dicts]. Accepts codes, English names, native names."""
    wikis = wikipedias()
    by_name = {}
    for w in wikis.values():
        by_name.setdefault(w["english"].lower(), w)
        by_name.setdefault(w["name"].lower(), w)
    out, errors = [], []
    for raw in [s.strip() for s in spec.split(",") if s.strip()]:
        key = raw.lower()
        w = wikis.get(key) or by_name.get(key)
        if w:
            if w not in out:
                out.append(w)
            continue
        close = difflib.get_close_matches(key, list(wikis) + list(by_name), n=3, cutoff=0.6)
        hints = [f"{by_name[c]['code']} ({by_name[c]['english']})" if c in by_name
                 else f"{c} ({wikis[c]['english']})" for c in close]
        errors.append(f"'{raw}' is not a Wikipedia language code" + (f"; did you mean: {', '.join(hints)}?" if hints else "."))
    if errors:
        raise LangError(" ".join(errors) + " Codes: https://meta.wikimedia.org/wiki/List_of_Wikipedias")
    return out


# --- Wikidata and search -----------------------------------------------------------

def search_entities(query, lang, limit=3):
    """Wikidata items matching `query` written in language `lang`."""
    data = get_json(WIKIDATA, {
        "action": "wbsearchentities", "search": query, "language": lang, "uselang": lang,
        "type": "item", "limit": limit, "format": "json",
    }, ttl=WEEK) or {}
    return [{"qid": x["id"], "label": x.get("label", ""), "description": x.get("description", "")}
            for x in data.get("search", [])]


def entities(qids, label_langs):
    """{qid: {labels: {lang: text}, descriptions: {...}, sitelinks: {dbname: title}}}."""
    langs = "|".join(dict.fromkeys(list(label_langs) + ["en"]))
    data = get_json(WIKIDATA, {
        "action": "wbgetentities", "ids": "|".join(qids), "props": "labels|descriptions|sitelinks",
        "languages": langs, "format": "json",
    }, ttl=WEEK) or {}
    out = {}
    for qid, ent in data.get("entities", {}).items():
        if "missing" in ent:
            continue
        out[qid] = {
            "labels": {k: v["value"] for k, v in ent.get("labels", {}).items()},
            "descriptions": {k: v["value"] for k, v in ent.get("descriptions", {}).items()},
            "sitelinks": {k: v["title"] for k, v in ent.get("sitelinks", {}).items()},
        }
    return out


def search_wiki(project, query, limit=3):
    """Article titles in one Wikipedia matching a free-text query."""
    data = get_json(f"https://{project}.org/w/api.php", {
        "action": "query", "list": "search", "srsearch": query, "srlimit": limit,
        "srnamespace": 0, "format": "json",
    }, ttl=WEEK) or {}
    return [x["title"] for x in data.get("query", {}).get("search", [])]


# --- Pageviews ---------------------------------------------------------------------

def article_daily(project, title, start, end):
    """Daily human views of one article: {'YYYYMMDD': views}. Days without views are absent."""
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"{PAGEVIEWS}/per-article/{project}/all-access/user/{t}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00"
    data = get_json(url)
    return {} if data is None else {it["timestamp"][:8]: it["views"] for it in data["items"]}


def project_monthly(project, start, end):
    """Monthly human views of a whole Wikipedia: {'YYYY-MM': views}."""
    url = f"{PAGEVIEWS}/aggregate/{project}/all-access/user/monthly/{start:%Y%m%d}00/{end:%Y%m%d}00"
    data = get_json(url)
    if data is None:
        raise ApiError(f"No aggregate pageviews for {project} in {start}..{end}")
    return {f"{it['timestamp'][:4]}-{it['timestamp'][4:6]}": it["views"] for it in data["items"]}
