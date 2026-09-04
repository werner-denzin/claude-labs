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
import re
import sys
from datetime import date, datetime

# The archived report is the complete edition; this card is a view of it, and it
# is allowed to be shorter. Teams rejects a payload above ~28 KB, so this ceiling
# is a safety net under that -- not a limit on the newsletter. When the payload
# would overflow, the coldest cards are left out of the *card* and the footer
# points at the report, which still carries all of them.
#
# The number stops mattering once the Teams layout is designed and the card
# carries a deliberate top-N instead of "as many as fit".
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

# Every card carries a label: one or two words naming what kind of news it is,
# shown between the title and the description. The ceiling is what keeps it a
# label and not a second headline -- and what keeps the card scannable, since a
# reader takes it in at a glance next to fourteen others.
LABEL_MAX_WORDS = 2
LABEL_MAX_CHARS = 24

# "Worth Trying": the cards an engineer could pick up and evaluate this week.
# Capped on purpose -- if every edition nominates six things, the section is a
# list nobody acts on. Three is a week's worth of curiosity for one team.
TRY_MAX_PER_EDITION = 3
TRY_EFFORT_MAX_CHARS = 32

# The shares SKILL.md's lens table targets, in the order the report shows them.
# Rendered as got/target so a short lens is legible without knowing the table:
# "engineering 9/10" says on its own that the day came up one short.
LENS_TARGETS = (
    ("engineering", 10),
    ("strategy", 5),
    ("research", 3),
    ("regulation", 2),
)

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


def normalize_label(value: str) -> str:
    """Collapses the whitespace and holds the label to one or two words."""
    label = re.sub(r"\s+", " ", (value or "")).strip()
    if not label:
        raise ValueError("the label is empty")
    words = label.split(" ")
    if len(words) > LABEL_MAX_WORDS:
        raise ValueError(
            f"label {label!r} has {len(words)} words "
            f"(use at most {LABEL_MAX_WORDS}, e.g. 'Model launch')"
        )
    if len(label) > LABEL_MAX_CHARS:
        raise ValueError(
            f"label {label!r} is {len(label)} characters "
            f"(use at most {LABEL_MAX_CHARS})"
        )
    return label


def try_list(cards: list[dict]) -> str:
    """The report's "Worth Trying" body, built from the cards that carry try_it."""
    lines = []
    for index, card in enumerate(cards, start=1):
        suggestion = card.get("try_it")
        if not suggestion:
            continue
        effort = (suggestion.get("effort") or "").strip()
        lines.append(
            f"- **{card['title']}** (card {index})"
            + (f" — *{effort}*" if effort else "")
            + f"\n  {suggestion['what'].strip()}"
        )
    return "\n".join(lines) if lines else "Nothing this edition."


def validate_try_it(card: dict) -> None:
    """A suggestion with no concrete first step is not a suggestion."""
    suggestion = card.get("try_it")
    if suggestion is None:
        return
    if not isinstance(suggestion, dict):
        raise ValueError("try_it must be an object with a 'what'")
    what = (suggestion.get("what") or "").strip()
    if not what:
        raise ValueError(
            "try_it needs a 'what': the concrete first step, not a topic"
        )
    effort = (suggestion.get("effort") or "").strip()
    if len(effort) > TRY_EFFORT_MAX_CHARS:
        raise ValueError(
            f"try_it effort {effort!r} is {len(effort)} characters "
            f"(use at most {TRY_EFFORT_MAX_CHARS}, e.g. 'an afternoon')"
        )


def lens_mix(cards: list[dict]) -> str:
    """The report header's lens line: got against target, per lens.

    Computed rather than counted by hand -- a number a human tallies every
    morning is a number that goes wrong quietly, which is the whole reason this
    line exists.
    """
    counted = [c.get("lens", "").strip().lower() for c in cards]
    parts = [
        f"{lens} {counted.count(lens)}/{target}" for lens, target in LENS_TARGETS
    ]
    known = {lens for lens, _ in LENS_TARGETS}
    unclassified = sum(1 for lens in counted if lens not in known)
    if unclassified:
        parts.append(f"unclassified {unclassified}")
    return " · ".join(parts)


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
        text_block(
            normalize_label(item["label"]).upper(),
            size="Small",
            weight="Bolder",
            isSubtle=True,
            spacing="Small",
        ),
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
    """Builds the card, leaving out the coldest items until it fits Teams.

    `digest["cards"]` is never mutated -- the sort produces a new list and the
    pops happen there. That is deliberate and load-bearing: step 7 writes the
    archived report from the same digest, so the report keeps every card the
    editorial step selected even when the card ships fewer.
    """
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
                        f"✂️ {dropped} cooler item(s) are not shown on this card. "
                        "The complete edition is in the archived report.",
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
        lines.append(f"        [{normalize_label(item['label']).upper()}]")
        lines.append(f"        {item['description']}")
        lines.append(f"        source: {item['source_name']} — {item['source_url']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="src", required=True, help="digest.json")
    parser.add_argument("--out", default="-", help="payload file, or - for stdout")
    parser.add_argument(
        "--try-list",
        action="store_true",
        help="print the report's 'Worth Trying' section body and exit",
    )
    parser.add_argument(
        "--lens-mix",
        action="store_true",
        help="print the report header's lens line (got/target per lens) and exit",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="print the newsletter as readable text; with --out, also write the payload",
    )
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
    nominated = sum(1 for c in digest["cards"] if c.get("try_it"))
    if nominated > TRY_MAX_PER_EDITION:
        raise SystemExit(
            f"error: {nominated} cards carry try_it "
            f"(at most {TRY_MAX_PER_EDITION} per edition — pick the best ones)"
        )
    for card in digest["cards"]:
        for field in ("title", "label", "description", "temperature", "source_name", "source_url"):
            if not card.get(field):
                raise SystemExit(
                    f"error: card {card.get('title', '?')!r} is missing the field '{field}'"
                )
        try:
            normalize_temperature(card["temperature"])
        except ValueError as exc:
            raise SystemExit(f"error: card {card['title']!r}: {exc}")
        try:
            normalize_label(card["label"])
        except ValueError as exc:
            raise SystemExit(f"error: card {card['title']!r}: {exc}")
        try:
            validate_try_it(card)
        except ValueError as exc:
            raise SystemExit(f"error: card {card['title']!r}: {exc}")
        if not str(card["source_url"]).startswith("http"):
            raise SystemExit(
                f"error: card {card['title']!r} has an invalid source_url: "
                f"{card['source_url']!r}"
            )

    # --preview used to return here, which silently threw away an --out the
    # caller had asked for: a scheduled run passed both, got no card.json, and
    # the next step died on a missing file. Both now do what they say.
    if args.lens_mix:
        print(lens_mix(digest["cards"]))
        return 0

    if args.try_list:
        print(try_list(digest["cards"]))
        return 0

    if args.preview:
        print(preview(digest))
        if args.out == "-":
            return 0

    payload, dropped = fit_to_limit(digest, args.max_bytes)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out == "-":
        # Only reachable without --preview; printing both to stdout would
        # interleave the readable newsletter with the payload.
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
