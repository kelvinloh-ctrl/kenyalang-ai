#!/usr/bin/env python3
"""
Kenyalang.AI v5 · Truth Gate Fetcher

读 sources.yaml → 并发抓 URL → status 200 + 非空 + 未见 → 写 candidates.json
给 routine summarizer 用。

硬规则：
- 抓到 != 200 → 该 URL 本次不进 candidates.json（防止 LLM 编造）
- 抓到的内容才进 LLM；LLM 不能自己 "记得" URL

Usage:
  python3 fetcher.py
Outputs:
  fetch-log.json      所有 fetch 记录（含失败）
  candidates.json     给 LLM 的 ground-truth 候选
  seen.json           更新去重池
"""
import json
import re
import sys
import yaml
import urllib.request
import urllib.error
import hashlib
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES_PATH = ROOT / "sources.yaml"
SEEN_PATH = ROOT / "seen.json"
FETCH_LOG_PATH = ROOT / "fetch-log.json"
CANDIDATES_PATH = ROOT / "candidates.json"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 15
MAX_CONCURRENT = 10
SEEN_RETENTION_DAYS = 90
EXCERPT_CHARS = 2000

# v5.1
RSS_MAX_ENTRIES = 10
SUBPAGE_MAX_PER_SOURCE = 3
SUBPAGE_MIN_HOMEPAGE_NAV_RATIO = 0.6  # if home page > 60% nav-looking, follow sub-pages

# Path tokens that look like article URLs
ARTICLE_PATH_TOKENS = (
    "/blog/", "/news/", "/post/", "/posts/", "/article/", "/articles/",
    "/announce", "/release/", "/releases/", "/changelog/", "/p/",
    "/index/",  # OpenAI-style /index/article-name
    "/research/", "/insights/", "/stories/",
)

# Skip these paths (not articles)
NON_ARTICLE_PATH_TOKENS = (
    "/about", "/contact", "/pricing", "/docs", "/api/", "/careers",
    "/privacy", "/terms", "/legal", "/login", "/signup", "/signin",
    "/cdn-cgi/", "/assets/", "/static/", "/_next/", ".css", ".js",
    ".pdf", ".zip", ".png", ".jpg", ".gif", ".svg", ".ico",
    "javascript:", "mailto:", "#",
)


# Python 3 urllib doesn't follow 308 redirects by default — many CDNs return 308.
def _follow_308(url, headers, max_hops=3):
    """Manual 308 redirect chain. Returns final response (or raises last exception)."""
    last_exc = None
    for _ in range(max_hops + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            if e.code in (308, 307, 301, 302) and e.headers.get("Location"):
                from urllib.parse import urljoin
                url = urljoin(url, e.headers["Location"])
                last_exc = e
                continue
            raise
    if last_exc:
        raise last_exc


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def strip_html(html):
    """Minimal HTML → text. Not perfect but stdlib-only."""
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"&#\d+;", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def extract_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return strip_html(m.group(1))[:200]
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.DOTALL | re.IGNORECASE)
    if h1:
        return strip_html(h1.group(1))[:200]
    return ""


def fetch_one(source):
    """Fetch a single source. Returns dict with status + content (or err)."""
    url = source["url"]
    started = now_iso()
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with _follow_308(url, headers) as r:
            status = r.getcode()
            raw = r.read(500_000)  # cap 500KB
            try:
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = raw.decode("latin-1", errors="replace")
            return {
                "url": url,
                "name": source["name"],
                "bucket": source.get("_bucket"),
                "subcategory": source.get("_subcategory"),
                "weight": source.get("weight", 0),
                "tags": source.get("tags", []),
                "aggregator": source.get("aggregator", False),
                "type": source.get("type", "web"),
                "status": status,
                "fetched_at": started,
                "title": extract_title(body),
                "content": strip_html(body)[:EXCERPT_CHARS] if status == 200 else "",
                "raw_html": body if status == 200 else "",  # v5.1 — for RSS parse + subpage scan
                "err": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "name": source["name"],
            "bucket": source.get("_bucket"),
            "subcategory": source.get("_subcategory"),
            "weight": source.get("weight", 0),
            "aggregator": source.get("aggregator", False),
            "type": source.get("type", "web"),
            "status": e.code,
            "fetched_at": started,
            "title": "",
            "content": "",
            "err": f"HTTPError {e.code}",
        }
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        return {
            "url": url,
            "name": source["name"],
            "bucket": source.get("_bucket"),
            "subcategory": source.get("_subcategory"),
            "weight": source.get("weight", 0),
            "aggregator": source.get("aggregator", False),
            "type": source.get("type", "web"),
            "status": 0,
            "fetched_at": started,
            "title": "",
            "content": "",
            "err": f"URLError {e}",
        }
    except Exception as e:
        return {
            "url": url,
            "name": source["name"],
            "bucket": source.get("_bucket"),
            "subcategory": source.get("_subcategory"),
            "weight": source.get("weight", 0),
            "aggregator": source.get("aggregator", False),
            "type": source.get("type", "web"),
            "status": -1,
            "fetched_at": started,
            "title": "",
            "content": "",
            "err": f"Other {type(e).__name__}: {e}",
        }


def parse_rss_entries(content_raw, base_url, max_entries=RSS_MAX_ENTRIES):
    """Parse RSS/Atom feed XML, return list of entry dicts."""
    try:
        import feedparser
    except ImportError:
        return []
    feed = feedparser.parse(content_raw)
    entries = []
    for e in (feed.entries or [])[:max_entries]:
        link = getattr(e, "link", "") or ""
        title = getattr(e, "title", "") or ""
        summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""
        published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
        if not link:
            continue
        # absolutize relative links
        if link.startswith("/"):
            from urllib.parse import urljoin
            link = urljoin(base_url, link)
        clean_summary = strip_html(summary)[:EXCERPT_CHARS]
        entries.append({
            "link": link,
            "title": strip_html(title)[:200],
            "summary": clean_summary,
            "published": published,
        })
    return entries


def find_subpage_links(html, base_url, max_links=SUBPAGE_MAX_PER_SOURCE):
    """Scan HTML for likely article sub-page links. Returns list of absolute URLs."""
    from urllib.parse import urljoin, urlparse
    base = urlparse(base_url)
    base_domain = base.netloc.lower()

    # find all <a href="..."> tags with text
    pattern = re.compile(
        r'<a\s+[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*?>(.{5,300}?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    candidates = {}  # url -> (score, anchor_text)
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        anchor = strip_html(m.group(2)).strip()
        if not href or not anchor:
            continue

        # filter
        if any(t in href.lower() for t in NON_ARTICLE_PATH_TOKENS):
            continue

        abs_url = urljoin(base_url, href)
        u = urlparse(abs_url)
        if u.netloc.lower() != base_domain:
            continue
        if u.path in ("", "/", base.path):
            continue
        # skip very shallow paths (e.g., /blog as just landing)
        path_segs = [p for p in u.path.split("/") if p]
        if len(path_segs) < 2 and not any(t.strip("/") in path_segs for t in ARTICLE_PATH_TOKENS):
            continue

        # score
        score = 0
        if any(t in u.path.lower() for t in ARTICLE_PATH_TOKENS):
            score += 2
        if 20 <= len(anchor) <= 200:
            score += 1
        if re.search(r"/20\d{2}/\d{1,2}/", u.path):  # /YYYY/MM/
            score += 2
        if re.search(r"\b(20\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", anchor):
            score += 1

        # dedupe by URL, keep highest score
        existing = candidates.get(abs_url)
        if not existing or existing[0] < score:
            candidates[abs_url] = (score, anchor)

    ranked = sorted(candidates.items(), key=lambda kv: -kv[1][0])
    return [(url, anchor) for url, (score, anchor) in ranked[:max_links] if score >= 2]


def fetch_subpage(url, anchor_hint, parent):
    """Fetch a sub-page found from a parent home page. Inherit parent metadata."""
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    started = now_iso()
    try:
        with _follow_308(url, headers) as r:
            status = r.getcode()
            raw = r.read(500_000)
            try:
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = raw.decode("latin-1", errors="replace")
            return {
                "url": url,
                "name": f"{parent['name']} → {anchor_hint[:60]}",
                "bucket": parent.get("_bucket"),
                "subcategory": parent.get("_subcategory"),
                "weight": parent.get("weight", 0),
                "aggregator": parent.get("aggregator", False),
                "type": "subpage",
                "status": status,
                "fetched_at": started,
                "title": extract_title(body) or anchor_hint,
                "content": strip_html(body)[:EXCERPT_CHARS] if status == 200 else "",
                "err": None,
                "parent_url": parent["url"],
                "anchor_hint": anchor_hint,
            }
    except Exception as e:
        return {
            "url": url,
            "name": f"{parent['name']} → {anchor_hint[:60]}",
            "bucket": parent.get("_bucket"),
            "subcategory": parent.get("_subcategory"),
            "weight": parent.get("weight", 0),
            "aggregator": parent.get("aggregator", False),
            "type": "subpage",
            "status": 0,
            "fetched_at": started,
            "title": "",
            "content": "",
            "err": f"{type(e).__name__}: {e}",
            "parent_url": parent["url"],
            "anchor_hint": anchor_hint,
        }


def flatten_sources(data):
    """Walk yaml tree, return flat list of source dicts with _bucket/_subcategory."""
    out = []
    for bucket in ["ai", "my-law", "fitness", "stocks", "macro"]:
        b = data.get(bucket, {})
        for subcat, items in b.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and "url" in item:
                    if item.get("research_only"):
                        continue  # 仅周度研判 agent 用 · fetcher 跳过不抓
                    item["_bucket"] = bucket
                    item["_subcategory"] = subcat
                    out.append(item)
    return out


def load_seen():
    if SEEN_PATH.exists():
        try:
            with open(SEEN_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def prune_seen(seen):
    """Drop entries older than SEEN_RETENTION_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)
    pruned = {}
    for h, ts_str in seen.items():
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S+0000").replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                pruned[h] = ts_str
        except Exception:
            continue
    return pruned


def main():
    if not SOURCES_PATH.exists():
        print(f"FATAL: {SOURCES_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(SOURCES_PATH) as f:
        data = yaml.safe_load(f)

    sources = flatten_sources(data)
    print(f"[fetcher] {len(sources)} sources to fetch", file=sys.stderr)

    seen = prune_seen(load_seen())
    print(f"[fetcher] seen.json: {len(seen)} known hashes", file=sys.stderr)

    # ---- Stage 1 · fetch all sources (home pages / feeds) ----
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as ex:
        futures = {ex.submit(fetch_one, s): s for s in sources}
        for fut in as_completed(futures):
            results.append(fut.result())

    # tally
    s200 = sum(1 for r in results if r["status"] == 200)
    s4xx = sum(1 for r in results if 400 <= r["status"] < 500)
    s5xx = sum(1 for r in results if 500 <= r["status"] < 600)
    sErr = sum(1 for r in results if r["status"] in (0, -1))
    print(f"[fetcher] stage1: 200={s200} · 4xx={s4xx} · 5xx={s5xx} · err={sErr}", file=sys.stderr)

    # ---- Stage 2 · v5.1: expand RSS entries + collect sub-page links ----
    rss_entries = []  # list of (parent_result, entry_dict)
    subpage_targets = []  # list of (parent_source_dict, url, anchor_hint)

    # build lookup from URL → original source dict (with _bucket/_subcategory)
    src_by_url = {s["url"]: s for s in sources}

    for r in results:
        if r["status"] != 200 or not r.get("raw_html"):
            continue
        parent_src = src_by_url.get(r["url"], {})

        if r.get("type") == "rss":
            entries = parse_rss_entries(r["raw_html"], r["url"])
            for e in entries:
                rss_entries.append((r, e))
        else:
            # web → look for sub-pages
            links = find_subpage_links(r["raw_html"], r["url"])
            for link_url, anchor in links:
                subpage_targets.append((parent_src, link_url, anchor))

    print(f"[fetcher] stage2: {len(rss_entries)} RSS entries · {len(subpage_targets)} subpages to fetch", file=sys.stderr)

    # ---- Stage 3 · fetch sub-pages ----
    subpage_results = []
    if subpage_targets:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as ex:
            sub_futures = {
                ex.submit(fetch_subpage, url, anchor, parent): (url, parent)
                for parent, url, anchor in subpage_targets
            }
            for fut in as_completed(sub_futures):
                subpage_results.append(fut.result())

    sp200 = sum(1 for r in subpage_results if r["status"] == 200)
    print(f"[fetcher] stage3: {sp200}/{len(subpage_results)} subpages fetched OK", file=sys.stderr)

    # ---- Truth Gate · build candidates ----
    candidates = []
    new_seen = dict(seen)
    deduped = 0

    def add_candidate(c):
        nonlocal deduped
        h = url_hash(c["url"])
        if h in seen or h in new_seen:
            deduped += 1
            return False
        c["url_hash"] = h
        new_seen[h] = c["fetched_at"]
        candidates.append(c)
        return True

    # 1. home page candidates (only for non-RSS — RSS gets entries instead)
    for r in results:
        if r["status"] != 200:
            continue
        if r.get("type") == "rss":
            continue  # RSS entries handled separately
        if not r["content"] or len(r["content"]) < 50:
            continue
        add_candidate({
            "bucket": r["bucket"],
            "subcategory": r["subcategory"],
            "source_name": r["name"],
            "url": r["url"],
            "weight": r["weight"],
            "is_aggregator": r.get("aggregator", False),
            "title": r["title"],
            "content_excerpt": r["content"],
            "fetched_at": r["fetched_at"],
            "candidate_type": "home",
        })

    # 2. RSS entries → each becomes a candidate
    for parent_r, entry in rss_entries:
        if not entry.get("link"):
            continue
        if not entry.get("summary") and not entry.get("title"):
            continue
        excerpt = entry.get("summary") or entry.get("title") or ""
        if len(excerpt) < 30:
            continue
        add_candidate({
            "bucket": parent_r["bucket"],
            "subcategory": parent_r["subcategory"],
            "source_name": f'{parent_r["name"]} (RSS entry)',
            "url": entry["link"],
            "weight": parent_r["weight"],
            "is_aggregator": parent_r.get("aggregator", False),
            "title": entry["title"],
            "content_excerpt": excerpt[:EXCERPT_CHARS],
            "fetched_at": parent_r["fetched_at"],
            "published": entry.get("published", ""),
            "candidate_type": "rss_entry",
            "parent_feed": parent_r["url"],
        })

    # 3. sub-page candidates
    for sr in subpage_results:
        if sr["status"] != 200 or len(sr.get("content", "")) < 50:
            continue
        add_candidate({
            "bucket": sr["bucket"],
            "subcategory": sr["subcategory"],
            "source_name": sr["name"],
            "url": sr["url"],
            "weight": sr["weight"],
            "is_aggregator": sr.get("aggregator", False),
            "title": sr["title"],
            "content_excerpt": sr["content"],
            "fetched_at": sr["fetched_at"],
            "candidate_type": "subpage",
            "parent_url": sr.get("parent_url"),
        })

    print(f"[fetcher] candidates={len(candidates)} (home + RSS entries + subpages) · deduped={deduped}", file=sys.stderr)

    # Write outputs
    with open(FETCH_LOG_PATH, "w") as f:
        json.dump({
            "generated_at": now_iso(),
            "total_sources": len(sources),
            "stage1_results": [
                {k: v for k, v in r.items() if k not in ("content", "raw_html")}
                | {"content_len": len(r.get("content", ""))}
                for r in results
            ],
            "stage3_subpage_results": [
                {k: v for k, v in r.items() if k != "content"}
                | {"content_len": len(r.get("content", ""))}
                for r in subpage_results
            ],
            "summary": {
                "stage1_status_200": s200, "stage1_status_4xx": s4xx, "stage1_status_5xx": s5xx, "stage1_err": sErr,
                "rss_entries_emitted": len(rss_entries),
                "subpages_attempted": len(subpage_results),
                "subpages_status_200": sp200,
            },
        }, f, indent=2, ensure_ascii=False)

    # Candidates grouped by bucket for easier LLM consumption
    by_bucket = {"ai": [], "my-law": [], "fitness": [], "stocks": [], "macro": []}
    for c in candidates:
        by_bucket.setdefault(c["bucket"], []).append(c)
    # Sort each bucket by weight desc
    for b in by_bucket:
        by_bucket[b].sort(key=lambda x: -x["weight"])

    # bot-blocked sources → routine will retry these via Claude WebFetch
    bot_blocked = [
        {
            "name": r["name"],
            "url": r["url"],
            "bucket": r["bucket"],
            "subcategory": r["subcategory"],
            "weight": r["weight"],
            "status": r["status"],
            "err": r.get("err", ""),
        }
        for r in results
        if r["status"] not in (200,) and r["status"] in (400, 401, 403, 405, 406, 429, 0)
    ]

    with open(CANDIDATES_PATH, "w") as f:
        json.dump({
            "generated_at": now_iso(),
            "fetch_summary": {
                "total_sources": len(sources),
                "fetched_200": s200,
                "fetched_4xx_5xx": s4xx + s5xx,
                "fetched_err": sErr,
                "deduped": deduped,
                "candidates_count": len(candidates),
                "rss_entries": len(rss_entries),
                "subpages_fetched": sp200,
                "by_bucket": {b: len(v) for b, v in by_bucket.items()},
            },
            "candidates_by_bucket": by_bucket,
            "bot_blocked_sources": bot_blocked,
            "acts_watch_list": data.get("my-law", {}).get("acts_watch_list", {}),
            "daily_output_rules": data.get("daily_output", {}),
        }, f, indent=2, ensure_ascii=False)

    with open(SEEN_PATH, "w") as f:
        json.dump(new_seen, f, indent=2)

    print(f"[fetcher] DONE → {FETCH_LOG_PATH.name} / {CANDIDATES_PATH.name} / {SEEN_PATH.name}", file=sys.stderr)
    print(f"[fetcher] by bucket: {dict(zip(by_bucket.keys(), [len(v) for v in by_bucket.values()]))}", file=sys.stderr)


if __name__ == "__main__":
    main()
