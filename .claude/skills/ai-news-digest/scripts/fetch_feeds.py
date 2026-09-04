#!/usr/bin/env python3
"""RSS/Atom aggregator for the AI radar.

Reads assets/sources.json, fetches every feed in parallel, filters by the time
window, deduplicates, and writes a JSON file with the candidates for triage.

Standard library only (Python 3.11+), so it runs in a restricted environment
with no pip.

Usage:
    python3 fetch_feeds.py --hours 24 --out /tmp/items.json
    python3 fetch_feeds.py --hours 72 --max-per-source 15 --pretty
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import gzip
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCES = os.path.join(HERE, "..", "assets", "sources.json")

# We identify ourselves honestly. This used to send a spoofed Chrome string,
# which got past bearblog's user-agent filter; measured on 2026-09-04, the
# honest string costs nothing -- 30/30 sources still answer. If a source ever
# blocks this UA, the answer is a declared failure in the newsletter or dropping
# the source, never a disguise.
USER_AGENT = (
    "ai-news-digest/1.0 "
    "(+https://github.com/werner-denzin/claude-labs; SiDi AI Radar feed reader)"
)

# Network and cleanup knobs the skill author may want to tune.
MAX_BYTES = 4 * 1024 * 1024
SUMMARY_CHARS = 600
JACCARD_THRESHOLD = 0.60
# Looser overlap: does not merge, only flags the pair for triage to inspect.
OVERLAP_HINT_THRESHOLD = 0.34

# Query parameters dropped when canonicalizing a URL (trackers).
TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "hsa_", "at_")
TRACKING_KEYS = {"ref", "source", "fbclid", "gclid", "igshid", "mkt_tok", "cmp", "sh"}

# XML namespaces used by the feeds we support.
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss1": "http://purl.org/rss/1.0/",
}

# General sources carry "topic_filter": true in the catalog. Only items mentioning
# the subject get through; without it a general feed floods the window with
# phones, games and retail promos, or with unrelated platform changelog entries.
# Portuguese terms are here on purpose: the filter has to match Brazilian sources.
TOPIC_RE = re.compile(
    r"\b("
    # --- coding agents and the tools around them -------------------------
    r"claude code|cline|cursor|copilot|codex|aider|windsurf|zed|devin|"
    r"opencode|goose|continue\.dev|sourcegraph|amp|jules|antigravity|"
    r"coding agent|agentic|agent(s|ic)? (coding|workflow|harness|loop)|"
    r"swe-?bench|terminal-?bench|mcp|model context protocol|tool use|"
    r"subagent|code review|pull request|refactor|codebase|ide|sdk|cli|"
    # --- the agent-engineering agenda the radar exists for ---------------
    r"langgraph|langchain|langsmith|llamaindex|dspy|pydantic ai|"
    r"context engineering|prompt engineering|context window|long context|"
    r"harness|scaffold|orchestrat|agent memory|guardrail|prompt injection|"
    r"jailbreak|function calling|structured output|agent skill|skills?|"
    r"eval|evals|evaluation|observability|tracing|vector (database|store)|"
    # --- general AI ------------------------------------------------------
    r"a\.?i\.?|artificial intelligence|inteligencia artificial|intelig[eê]ncia artificial|"
    r"machine learning|aprendizado de m[aá]quina|deep learning|rede neural|neural network|"
    r"llm|large language model|modelo de linguagem|generative|generativ[ao]|transformer|"
    r"chatbot|agente de ia|ai agent|rag|embedding|fine-?tuning|"
    r"openai|anthropic|chatgpt|gpt-?\d|claude|gemini|llama|mistral|deepseek|qwen|grok|"
    r"hugging ?face|nvidia|midjourney|stable diffusion|perplexity|"
    r"agi|superintelig|alucina|hallucinat|prompt|datacenter|data center|gpu"
    r")\b",
    re.IGNORECASE,
)

# Feeds de release ("kind": "release") publicam alpha, beta, nightly e tags
# internas junto com as versoes de verdade. So a versao estavel e noticia.
# Uma fonte pode optar por receber tudo com "prereleases": true.
PRERELEASE_RE = re.compile(
    r"(alpha|beta|\brc[.\-]?\d|nightly|snapshot|staging|canary|"
    r"[.\-]pre\b|[.\-]dev\b|preview\b)",
    re.IGNORECASE,
)

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
NONWORD_RE = re.compile(r"[^\w\s]", re.UNICODE)

# Words with no discriminating value when comparing titles.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has",
    "how", "in", "is", "it", "its", "new", "of", "on", "or", "that", "the", "then",
    "this", "to", "up", "was", "what", "when", "why", "with", "you", "your",
    "a", "as", "ao", "aos", "com", "como", "da", "das", "de", "do", "dos", "e",
    "em", "na", "nas", "no", "nos", "o", "os", "para", "por", "que", "sao", "se",
    "sem", "sobre", "um", "uma",
}


# --------------------------------------------------------------------------- #
# Network
# --------------------------------------------------------------------------- #

def fetch_url(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en,pt-BR;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_BYTES)
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def text_of(node) -> str:
    if node is None:
        return ""
    parts = [node.text or ""]
    for child in node:
        parts.append(text_of(child))
        parts.append(child.tail or "")
    return "".join(parts)


def clean_text(raw: str, limit: int = SUMMARY_CHARS) -> str:
    if not raw:
        return ""
    txt = html.unescape(raw)
    txt = TAG_RE.sub(" ", txt)
    txt = html.unescape(txt)
    txt = WS_RE.sub(" ", txt).strip()
    if len(txt) > limit:
        txt = txt[:limit].rsplit(" ", 1)[0] + "..."
    return txt


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    candidate = value.replace("Z", "+00:00")
    # ISO timestamps whose fractional seconds are too long for fromisoformat
    candidate = re.sub(r"(\.\d{6})\d+", r"\1", candidate)
    for text in (candidate, candidate[:19], candidate[:10]):
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def first_text(entry, paths: list[str]) -> str:
    for path in paths:
        node = entry.find(path, NS)
        if node is not None:
            value = text_of(node).strip()
            if value:
                return value
    return ""


def entry_link(entry) -> str:
    # RSS <link>, RSS 1.0 <rss1:link>, Atom <link rel="alternate" href="...">
    for path in ("link", "rss1:link"):
        node = entry.find(path, NS)
        if node is not None and (node.text or "").strip():
            return node.text.strip()
    alt = ""
    for node in entry.findall("atom:link", NS):
        href = node.get("href", "").strip()
        if not href:
            continue
        rel = node.get("rel", "alternate")
        if rel == "alternate":
            return href
        alt = alt or href
    guid = entry.find("guid", NS)
    if guid is not None and (guid.text or "").strip().startswith("http"):
        return guid.text.strip()
    return alt


def parse_feed(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    entries = (
        root.findall(".//item")
        + root.findall(".//rss1:item", NS)
        + root.findall(".//atom:entry", NS)
    )
    out = []
    for entry in entries:
        title = clean_text(
            first_text(entry, ["title", "rss1:title", "atom:title"]), 300
        )
        link = entry_link(entry)
        if not title or not link:
            continue
        summary = clean_text(
            first_text(
                entry,
                [
                    "description",
                    "rss1:description",
                    "atom:summary",
                    "content:encoded",
                    "atom:content",
                ],
            )
        )
        published = parse_date(
            first_text(
                entry,
                [
                    "pubDate",
                    "atom:published",
                    "atom:updated",
                    "dc:date",
                    "published",
                    "updated",
                ],
            )
        )
        out.append(
            {
                "title": title,
                "url": link,
                "summary": summary,
                "published": published.astimezone(timezone.utc).isoformat()
                if published
                else None,
                "_published_dt": published,
            }
        )
    return out


def parse_sitemap(raw: bytes, contains: str, excludes: tuple[str, ...] = ()) -> list[dict]:
    """Turns a sitemap.xml into items.

    Some sources publish no feed but do publish a sitemap carrying <lastmod>
    dates, which is enough to know what is new. The title comes from the URL
    slug and there is no summary, so triage should read the page before writing
    a card.

    <lastmod> is usually a date with no time, so those items are marked
    date_only and the window comparison is made on whole days.

    A sitemap mixes articles with index pages that live under the same path --
    The Batch keeps its tag listings and its weekly roundup under /the-batch/,
    and both are touched whenever an article is. `excludes` drops those URLs
    before they become items.
    """
    root = ET.fromstring(raw)
    out = []
    for url in root.iter():
        if url.tag.rsplit("}", 1)[-1] != "url":
            continue
        loc = mod = ""
        for child in url:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "loc":
                loc = (child.text or "").strip()
            elif tag == "lastmod":
                mod = (child.text or "").strip()
        if not loc or contains not in loc:
            continue
        if any(bad in loc for bad in excludes):
            continue
        published = parse_date(mod)
        if published is None:
            continue
        slug = loc.rstrip("/").rsplit("/", 1)[-1]
        title = slug.replace("-", " ").replace("_", " ").strip()
        if not title:
            continue
        out.append(
            {
                "title": title[:1].upper() + title[1:],
                "url": loc,
                "summary": "",
                "published": published.astimezone(timezone.utc).isoformat(),
                "_published_dt": published,
                "_date_only": len(mod) <= 10,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Normalization and deduplication
# --------------------------------------------------------------------------- #

def canonical_url(url: str) -> str:
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    query = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(TRACKING_PREFIXES) and k.lower() not in TRACKING_KEYS
    ]
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), netloc, path, urllib.parse.urlencode(query), "")
    )


def title_tokens(title: str) -> frozenset[str]:
    folded = unicodedata.normalize("NFKD", title.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = NONWORD_RE.sub(" ", folded)
    return frozenset(
        tok for tok in folded.split() if len(tok) > 2 and tok not in STOPWORDS
    )


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Overlap coefficient: tolerates titles of very different lengths."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def deduplicate(items: list[dict], threshold: float = JACCARD_THRESHOLD) -> list[dict]:
    """Groups the same story as published by several outlets.

    The group's representative is the item from the highest-weighted source; the
    rest go into `also_covered_by`, so the report can say how many outlets
    covered it.
    """
    items.sort(key=lambda i: (-i["weight"], i["published"] or "", i["title"]))
    kept: list[dict] = []
    by_url: dict[str, dict] = {}
    for item in items:
        curl = canonical_url(item["url"])
        master = by_url.get(curl)
        if master is None:
            tokens = item["_tokens"]
            for candidate in kept:
                if jaccard(tokens, candidate["_tokens"]) >= threshold:
                    master = candidate
                    break
        if master is not None:
            if master["source_id"] != item["source_id"]:
                master["also_covered_by"].append(
                    {
                        "source": item["source_name"],
                        "url": item["url"],
                        "title": item["title"],
                    }
                )
            continue
        item["also_covered_by"] = []
        item["_hints"] = [
            candidate
            for candidate in kept
            if candidate["source_id"] != item["source_id"]
            and overlap(item["_tokens"], candidate["_tokens"]) >= OVERLAP_HINT_THRESHOLD
        ]
        kept.append(item)
        by_url[curl] = item
    return kept


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #

def collect_source(source: dict, cutoff: datetime, max_per_source: int, timeout: int) -> dict:
    result = {
        "source": source,
        "items": [],
        "error": None,
        "skipped_old": 0,
        "undated": 0,
        "off_topic": 0,
        "prerelease": 0,
    }
    feed = source.get("feed")
    sitemap = source.get("sitemap")
    if not feed and not sitemap:
        result["error"] = "no RSS feed declared (read the 'site' field via WebFetch)"
        return result
    try:
        if feed:
            raw = fetch_url(feed, timeout)
            entries = parse_feed(raw)
        else:
            raw = fetch_url(sitemap["url"], timeout)
            entries = parse_sitemap(
                raw,
                sitemap.get("contains", ""),
                tuple(sitemap.get("excludes", ())),
            )
    except urllib.error.HTTPError as exc:
        # A 403 has two very different causes and they look identical from here:
        # the sandbox's network allowlist refusing the host, or the source
        # refusing us. The sandbox marks its own with x-deny-reason, so read it
        # -- otherwise a dead source gets explained away as a policy block, or
        # the reverse.
        detail = ""
        if exc.code == 403:
            deny = (exc.headers or {}).get("x-deny-reason")
            detail = (
                f" (x-deny-reason: {deny} — blocked by the environment's network "
                "allowlist, not by the source)"
                if deny
                else " (no x-deny-reason header, so the source refused the "
                "request rather than the sandbox)"
            )
        result["error"] = f"HTTP {exc.code}{detail}"
        return result
    except ET.ParseError as exc:
        result["error"] = f"invalid XML: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001 - any network failure becomes a report line
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    # A source can narrow the gate to its own vocabulary, and can exclude its own
    # off-topic beat. NVIDIA is the case that needs both: its name is itself a
    # topic keyword, so without an exclusion every gaming post would pass.
    topic_filter = bool(source.get("topic_filter") or source.get("topic_terms"))
    include_re = (
        re.compile(source["topic_terms"], re.IGNORECASE)
        if source.get("topic_terms")
        else TOPIC_RE
    )
    exclude_re = (
        re.compile(source["topic_exclude"], re.IGNORECASE)
        if source.get("topic_exclude")
        else None
    )
    is_release = source.get("kind") == "release"
    drop_pre = is_release and not source.get("prereleases")
    cap = min(max_per_source, source.get("max_items", max_per_source))

    for entry in entries:
        published = entry.pop("_published_dt")
        if published is None:
            result["undated"] += 1
            continue
        # Um item so-data cai a meia-noite, o que descartaria um post de ontem
        # a tarde. Para esses, a comparacao e por dia inteiro.
        if entry.pop("_date_only", False):
            too_old = published.date() < cutoff.date()
        else:
            too_old = published < cutoff
        if too_old:
            result["skipped_old"] += 1
            continue
        if drop_pre and PRERELEASE_RE.search(entry["title"]):
            result["prerelease"] += 1
            continue
        haystack = f"{entry['title']} {entry['summary']}"
        if topic_filter and not include_re.search(haystack):
            result["off_topic"] += 1
            continue
        if exclude_re is not None and exclude_re.search(haystack):
            result["off_topic"] += 1
            continue
        entry.update(
            {
                "source_id": source["id"],
                "source_name": source["name"],
                "source_category": source.get("category", "news"),
                "source_kind": source.get("kind", "article"),
                "source_lang": source.get("lang", "en"),
                "weight": source.get("weight", 3),
            }
        )
        entry["_tokens"] = title_tokens(entry["title"])
        result["items"].append(entry)
        if len(result["items"]) >= cap:
            break
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", default=DEFAULT_SOURCES, help="path to sources.json")
    parser.add_argument("--hours", type=int, default=24, help="window in hours (default 24 = D-1)")
    parser.add_argument("--max-per-source", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--only", default="", help="comma-separated list of source ids")
    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=JACCARD_THRESHOLD,
        help="title similarity required to merge automatically (default 0.60)",
    )
    parser.add_argument("--out", default="-", help="output file, or - for stdout")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    with open(args.sources, encoding="utf-8") as handle:
        sources = json.load(handle)["sources"]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        sources = [s for s in sources if s["id"] in wanted]

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.hours)

    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(
            pool.map(
                lambda s: collect_source(s, cutoff, args.max_per_source, args.timeout),
                sources,
            )
        )

    items: list[dict] = []
    ok, failed = [], []
    for result in results:
        source = result["source"]
        if result["error"]:
            failed.append(
                {
                    "id": source["id"],
                    "name": source["name"],
                    "feed": source.get("feed"),
                    "site": source.get("site"),
                    "error": result["error"],
                }
            )
        else:
            ok.append(
                {
                    "id": source["id"],
                    "name": source["name"],
                    "in_window": len(result["items"]),
                    "too_old": result["skipped_old"],
                    "off_topic": result["off_topic"],
                    "prerelease": result["prerelease"],
                    "undated": result["undated"],
                }
            )
        items.extend(result["items"])

    raw_count = len(items)
    items = deduplicate(items, args.merge_threshold)
    for index, item in enumerate(items, start=1):
        item["id"] = f"n{index:03d}"
    for item in items:
        # Not confirmed duplicates: pairs similar enough for triage to check
        # whether they tell the same story (useful across languages).
        item["possible_duplicate_of"] = [hint["id"] for hint in item.pop("_hints", [])]
        item.pop("_tokens", None)

    items.sort(key=lambda i: (i["published"] or "", i["weight"]), reverse=True)

    payload = {
        "generated_at": now.isoformat(),
        "window_hours": args.hours,
        "window_start": cutoff.isoformat(),
        "counts": {
            "sources_total": len(sources),
            "sources_ok": len(ok),
            "sources_failed": len(failed),
            "items_raw": raw_count,
            "items_deduped": len(items),
        },
        "sources_ok": sorted(ok, key=lambda s: -s["in_window"]),
        "sources_failed": failed,
        "items": items,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(
            f"{len(items)} items ({raw_count} before deduplication) from "
            f"{len(ok)}/{len(sources)} sources -> {args.out}",
            file=sys.stderr,
        )
        if failed:
            print(f"{len(failed)} source(s) failed:", file=sys.stderr)
            for entry in failed:
                print(f"  - {entry['name']}: {entry['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
