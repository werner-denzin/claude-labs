#!/usr/bin/env python3
"""Turns the triaged digest into an Adaptive Card for Microsoft Teams.

Input: digest.json (written by the skill's triage step; schema in
references/digest-schema.md). Output: the envelope ready to POST to the webhook.

Standard library only. Usage:
    python3 build_card.py --in digest.json --out card.json
    python3 build_card.py --in digest.json --preview
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

# Teams rejects cards above ~28 KB. We stay comfortably below and drop the
# coldest items before overflowing, rather than letting the POST fail.
MAX_PAYLOAD_BYTES = 25_000  # tunable via --max-bytes

# The newsletter is written in English. Items from Brazilian sources keep their
# title and description in Portuguese; only the card frame is rendered here.
TEMPERATURES = {
    "HIGH": {"emoji": "\U0001f534", "label": "HIGH", "color": "attention", "rank": 0},
    "MEDIUM": {"emoji": "\U0001f7e0", "label": "MEDIUM", "color": "warning", "rank": 1},
    "LOW": {"emoji": "\U0001f535", "label": "LOW", "color": "accent", "rank": 2},
}
# Portuguese labels accepted as aliases, so older digests still build.
ALIASES = {"ALTA": "HIGH", "MEDIA": "MEDIUM", "MÉDIA": "MEDIUM", "BAIXA": "LOW"}

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def normalize_temperature(value: str) -> dict:
    key = (value or "").strip().upper()
    key = ALIASES.get(key, key)
    if key not in TEMPERATURES:
        raise ValueError(
            f"invalid temperature: {value!r} (use HIGH, MEDIUM or LOW)"
        )
    return TEMPERATURES[key]


def format_date(iso: str) -> str:
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{WEEKDAYS[day.weekday()]}, {MONTHS[day.month - 1]} {day.day}, {day.year}"


def text_block(text: str, **kwargs) -> dict:
    block = {"type": "TextBlock", "text": text, "wrap": True}
    block.update(kwargs)
    return block


def build_item(index: int, item: dict) -> dict:
    temp = normalize_temperature(item["temperature"])
    body = [
        text_block(
            f"{temp['emoji']} **{temp['label']}**"
            + (f"  ·  {item['lens']}" if item.get("lens") else ""),
            size="Small",
            weight="Bolder",
            color=temp["color"],
            spacing="None",
        ),
        text_block(f"**{index}. {item['title']}**", spacing="Small"),
        text_block(item["description"], size="Small", spacing="Small"),
    ]

    source = f"[{item['source_name']}]({item['source_url']})"
    others = item.get("also_covered_by") or []
    if others:
        extra = ", ".join(f"[{o['source']}]({o['url']})" for o in others[:3])
        rest = len(others) - 3
        source += f"  ·  also in {extra}"
        if rest > 0:
            source += f" (+{rest})"
    body.append(
        text_block(source, size="Small", isSubtle=True, spacing="Small")
    )
    return {"type": "Container", "separator": True, "spacing": "Medium", "items": body}


def build_card(digest: dict, items: list[dict]) -> dict:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in items:
        counts[normalize_temperature(item["temperature"])["label"]] += 1
    stats = digest.get("stats", {})

    header = [
        text_block(
            f"AI Radar — {format_date(digest['date'])}",
            size="Large",
            weight="Bolder",
        ),
        text_block(
            f"{len(items)} highlights  ·  "
            f"\U0001f534 {counts['HIGH']} high  "
            f"\U0001f7e0 {counts['MEDIUM']} medium  "
            f"\U0001f535 {counts['LOW']} low"
            + (
                f"  ·  {stats['items_considered']} items from "
                f"{stats.get('sources_ok', '?')} sources in the last "
                f"{digest.get('window_hours', 24)}h"
                if stats.get("items_considered")
                else ""
            ),
            size="Small",
            isSubtle=True,
            spacing="None",
        ),
    ]
    if digest.get("headline"):
        header.append(
            text_block(digest["headline"], weight="Bolder", spacing="Medium")
        )

    body = header + [build_item(i, item) for i, item in enumerate(items, start=1)]

    footer = []
    if digest.get("not_relevant"):
        footer.append(
            text_block(
                "**Left out:** " + "; ".join(digest["not_relevant"]),
                size="Small",
                isSubtle=True,
                spacing="Medium",
                separator=True,
            )
        )
    failed = digest.get("sources_failed") or []
    if failed:
        names = ", ".join(f["name"] for f in failed[:6])
        rest = len(failed) - 6
        footer.append(
            text_block(
                f"⚠️ {len(failed)} source(s) did not respond: {names}"
                + (f" (+{rest})" if rest > 0 else ""),
                size="Small",
                isSubtle=True,
                color="warning",
                spacing="Small",
            )
        )
    footer.append(
        text_block(
            "Generated by the `ai-news-digest` skill. "
            "Temperature = relevance to AI strategy, not popularity.",
            size="Small",
            isSubtle=True,
            spacing="Medium",
            separator=True,
        )
    )

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body + footer,
    }
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card,
            }
        ],
    }


def fit_to_limit(digest: dict, max_bytes: int = MAX_PAYLOAD_BYTES) -> tuple[dict, int]:
    """Builds the card, dropping the coldest items until it fits the Teams limit."""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items = sorted(
        digest["cards"],
        key=lambda c: (
            order[normalize_temperature(c["temperature"])["label"]],
            c.get("rank", 999),
        ),
    )
    dropped = 0
    while items:
        payload = build_card(digest, items)
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        if size <= max_bytes:
            if dropped:
                payload["attachments"][0]["content"]["body"].append(
                    text_block(
                        f"✂️ {dropped} lower-temperature item(s) omitted "
                        "due to the Teams message size limit.",
                        size="Small",
                        isSubtle=True,
                    )
                )
            return payload, dropped
        items.pop()
        dropped += 1
    raise SystemExit("error: not even the card header fits the Teams limit")


def preview(digest: dict) -> str:
    lines = [f"AI Radar — {format_date(digest['date'])}"]
    if digest.get("headline"):
        lines.append(digest["headline"])
    lines.append("")
    for index, item in enumerate(digest["cards"], start=1):
        temp = normalize_temperature(item["temperature"])
        lines.append(f"{temp['emoji']} {temp['label']:6} {index}. {item['title']}")
        lines.append(f"        {item['description']}")
        lines.append(f"        source: {item['source_name']} — {item['source_url']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="src", required=True, help="digest.json")
    parser.add_argument("--out", default="-", help="payload file, or - for stdout")
    parser.add_argument("--preview", action="store_true", help="print readable text instead of the JSON")
    parser.add_argument("--max-bytes", type=int, default=MAX_PAYLOAD_BYTES,
                        help="payload ceiling; above it the coldest items are dropped")
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as handle:
        digest = json.load(handle)

    for field in ("date", "cards"):
        if field not in digest:
            raise SystemExit(f"error: digest.json is missing the required field '{field}'")
    if not digest["cards"]:
        raise SystemExit("error: digest.json contains no cards")
    for card in digest["cards"]:
        for field in ("title", "description", "temperature", "source_name", "source_url"):
            if not card.get(field):
                raise SystemExit(
                    f"error: card {card.get('title', '?')!r} is missing the field '{field}'"
                )
        try:
            normalize_temperature(card["temperature"])
        except ValueError as exc:
            raise SystemExit(f"error: card {card['title']!r}: {exc}")
        if not str(card["source_url"]).startswith("http"):
            raise SystemExit(
                f"error: card {card['title']!r} has an invalid source_url: "
                f"{card['source_url']!r}"
            )

    if args.preview:
        print(preview(digest))
        return 0

    payload, dropped = fit_to_limit(digest, args.max_bytes)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        note = f", {dropped} item(s) dropped for size" if dropped else ""
        print(
            f"card with {len(digest['cards']) - dropped} items, "
            f"{size} bytes on the wire{note} -> {args.out}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
