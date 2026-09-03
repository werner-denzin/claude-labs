#!/usr/bin/env python3
"""Agregador de feeds RSS/Atom para o radar de IA.

Le assets/sources.json, busca todos os feeds em paralelo, filtra pela janela de
tempo, deduplica e escreve um JSON com os candidatos para a triagem.

Somente biblioteca padrao (Python 3.11+), para rodar em ambiente restrito sem pip.

Uso:
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

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Parametros de rede/limpeza que o autor da skill pode querer ajustar.
MAX_BYTES = 4 * 1024 * 1024
SUMMARY_CHARS = 600
JACCARD_THRESHOLD = 0.60
# Sobreposicao mais frouxa: nao funde, apenas sinaliza para a triagem olhar.
OVERLAP_HINT_THRESHOLD = 0.34

# Parametros de query descartados na canonicalizacao de URL (rastreadores).
TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "hsa_", "at_")
TRACKING_KEYS = {"ref", "source", "fbclid", "gclid", "igshid", "mkt_tok", "cmp", "sh"}

# Namespaces usados pelos feeds atendidos.
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss1": "http://purl.org/rss/1.0/",
}

# Fontes de tecnologia em geral entram no catalogo com "topic_filter": true.
# So passam itens que mencionem o assunto; sem isso o feed inunda a janela com
# celular, games e promocao.
TOPIC_RE = re.compile(
    r"\b("
    r"a\.?i\.?|artificial intelligence|inteligencia artificial|intelig[eê]ncia artificial|"
    r"machine learning|aprendizado de m[aá]quina|deep learning|rede neural|neural network|"
    r"llm|large language model|modelo de linguagem|generative|generativ[ao]|transformer|"
    r"chatbot|copilot|agente de ia|ai agent|agentic|rag|embedding|fine-?tuning|"
    r"openai|anthropic|chatgpt|gpt-?\d|claude|gemini|llama|mistral|deepseek|qwen|grok|"
    r"hugging ?face|nvidia|midjourney|stable diffusion|perplexity|copilot|"
    r"agi|superintelig|alucina|hallucinat|prompt|datacenter|data center|gpu"
    r")\b",
    re.IGNORECASE,
)

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
NONWORD_RE = re.compile(r"[^\w\s]", re.UNICODE)

# Palavras sem valor discriminante na comparacao de titulos.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has",
    "how", "in", "is", "it", "its", "new", "of", "on", "or", "that", "the", "then",
    "this", "to", "up", "was", "what", "when", "why", "with", "you", "your",
    "a", "as", "ao", "aos", "com", "como", "da", "das", "de", "do", "dos", "e",
    "em", "na", "nas", "no", "nos", "o", "os", "para", "por", "que", "sao", "se",
    "sem", "sobre", "um", "uma",
}


# --------------------------------------------------------------------------- #
# Rede
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
    # ISO com fracao de segundo longa demais para fromisoformat antigo
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


# --------------------------------------------------------------------------- #
# Normalizacao e deduplicacao
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
    """Coeficiente de sobreposicao: tolera titulos de tamanhos bem diferentes."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def deduplicate(items: list[dict], threshold: float = JACCARD_THRESHOLD) -> list[dict]:
    """Agrupa a mesma noticia publicada por varios veiculos.

    O representante do grupo e o item de maior peso de fonte; os demais entram em
    `also_covered_by`, para o relatorio poder dizer quantos veiculos cobriram.
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
# Coleta
# --------------------------------------------------------------------------- #

def collect_source(source: dict, cutoff: datetime, max_per_source: int, timeout: int) -> dict:
    result = {
        "source": source,
        "items": [],
        "error": None,
        "skipped_old": 0,
        "undated": 0,
        "off_topic": 0,
    }
    feed = source.get("feed")
    if not feed:
        result["error"] = "sem feed RSS declarado (usar o campo 'site' via WebFetch)"
        return result
    try:
        raw = fetch_url(feed, timeout)
        entries = parse_feed(raw)
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}"
        return result
    except ET.ParseError as exc:
        result["error"] = f"XML invalido: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001 - qualquer falha de rede vira relatorio
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    topic_filter = bool(source.get("topic_filter"))
    cap = min(max_per_source, source.get("max_items", max_per_source))

    for entry in entries:
        published = entry.pop("_published_dt")
        if published is None:
            result["undated"] += 1
            continue
        if published < cutoff:
            result["skipped_old"] += 1
            continue
        if topic_filter and not TOPIC_RE.search(f"{entry['title']} {entry['summary']}"):
            result["off_topic"] += 1
            continue
        entry.update(
            {
                "source_id": source["id"],
                "source_name": source["name"],
                "source_category": source.get("category", "news"),
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
    parser.add_argument("--sources", default=DEFAULT_SOURCES, help="caminho do sources.json")
    parser.add_argument("--hours", type=int, default=24, help="janela em horas (padrao 24 = D-1)")
    parser.add_argument("--max-per-source", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--only", default="", help="lista de ids separados por virgula")
    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=JACCARD_THRESHOLD,
        help="similaridade de titulo para fundir automaticamente (padrao 0.60)",
    )
    parser.add_argument("--out", default="-", help="arquivo de saida ou - para stdout")
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
                    "undated": result["undated"],
                }
            )
        items.extend(result["items"])

    raw_count = len(items)
    items = deduplicate(items, args.merge_threshold)
    for index, item in enumerate(items, start=1):
        item["id"] = f"n{index:03d}"
    for item in items:
        # Nao sao duplicatas confirmadas: sao pares parecidos o bastante para a
        # triagem checar se contam a mesma historia (util entre idiomas).
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
            f"{len(items)} itens ({raw_count} antes da deduplicacao) de "
            f"{len(ok)}/{len(sources)} fontes -> {args.out}",
            file=sys.stderr,
        )
        if failed:
            print(f"{len(failed)} fontes falharam:", file=sys.stderr)
            for entry in failed:
                print(f"  - {entry['name']}: {entry['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
