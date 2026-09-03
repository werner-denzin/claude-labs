#!/usr/bin/env python3
"""Converte o digest triado em um Adaptive Card para o Microsoft Teams.

Entrada: digest.json (escrito pela etapa de triagem da skill; schema em
references/digest-schema.md). Saida: o envelope pronto para POST no webhook.

Somente biblioteca padrao. Uso:
    python3 build_card.py --in digest.json --out card.json
    python3 build_card.py --in digest.json --preview
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

# Teams rejeita cartoes acima de ~28 KB. Ficamos abaixo com folga e cortamos os
# itens mais frios antes de estourar, em vez de deixar o POST falhar.
MAX_PAYLOAD_BYTES = 25_000  # ajustavel via --max-bytes

TEMPERATURES = {
    "ALTA": {"emoji": "\U0001f534", "label": "ALTA", "color": "attention", "rank": 0},
    "MEDIA": {"emoji": "\U0001f7e0", "label": "MEDIA", "color": "warning", "rank": 1},
    "BAIXA": {"emoji": "\U0001f535", "label": "BAIXA", "color": "accent", "rank": 2},
}
# Aceita os rotulos em ingles do pedido original.
ALIASES = {"HIGH": "ALTA", "MEDIUM": "MEDIA", "MÉDIA": "MEDIA", "LOW": "BAIXA"}

WEEKDAYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
MONTHS = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def normalize_temperature(value: str) -> dict:
    key = (value or "").strip().upper()
    key = ALIASES.get(key, key)
    if key not in TEMPERATURES:
        raise ValueError(
            f"temperatura invalida: {value!r} (use ALTA, MEDIA ou BAIXA)"
        )
    return TEMPERATURES[key]


def format_date(iso: str) -> str:
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{WEEKDAYS[day.weekday()]}, {day.day} de {MONTHS[day.month - 1]} de {day.year}"


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
        source += f"  ·  tambem em {extra}"
        if rest > 0:
            source += f" (+{rest})"
    body.append(
        text_block(source, size="Small", isSubtle=True, spacing="Small")
    )
    return {"type": "Container", "separator": True, "spacing": "Medium", "items": body}


def build_card(digest: dict, items: list[dict]) -> dict:
    counts = {"ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    for item in items:
        counts[normalize_temperature(item["temperature"])["label"]] += 1
    stats = digest.get("stats", {})

    header = [
        text_block(
            f"Radar de IA — {format_date(digest['date'])}",
            size="Large",
            weight="Bolder",
        ),
        text_block(
            f"{len(items)} destaques  ·  "
            f"\U0001f534 {counts['ALTA']} alta  "
            f"\U0001f7e0 {counts['MEDIA']} media  "
            f"\U0001f535 {counts['BAIXA']} baixa"
            + (
                f"  ·  {stats['items_considered']} itens de "
                f"{stats.get('sources_ok', '?')} fontes nas ultimas "
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
                "**Ficou de fora:** " + "; ".join(digest["not_relevant"]),
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
                f"⚠️ {len(failed)} fonte(s) nao responderam: {names}"
                + (f" (+{rest})" if rest > 0 else ""),
                size="Small",
                isSubtle=True,
                color="warning",
                spacing="Small",
            )
        )
    footer.append(
        text_block(
            "Gerado pela skill `ai-news-digest`. "
            "Temperatura = relevancia para a estrategia de IA, nao popularidade.",
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
    """Monta o cartao cortando os itens mais frios ate caber no limite do Teams."""
    order = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
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
                        f"✂️ {dropped} item(ns) de menor temperatura ficaram "
                        "de fora por limite de tamanho da mensagem do Teams.",
                        size="Small",
                        isSubtle=True,
                    )
                )
            return payload, dropped
        items.pop()
        dropped += 1
    raise SystemExit("erro: nem o cabecalho do cartao cabe no limite do Teams")


def preview(digest: dict) -> str:
    lines = [f"Radar de IA — {format_date(digest['date'])}"]
    if digest.get("headline"):
        lines.append(digest["headline"])
    lines.append("")
    for index, item in enumerate(digest["cards"], start=1):
        temp = normalize_temperature(item["temperature"])
        lines.append(f"{temp['emoji']} {temp['label']:5} {index}. {item['title']}")
        lines.append(f"        {item['description']}")
        lines.append(f"        fonte: {item['source_name']} — {item['source_url']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="src", required=True, help="digest.json")
    parser.add_argument("--out", default="-", help="arquivo do payload ou - para stdout")
    parser.add_argument("--preview", action="store_true", help="imprime texto legivel em vez do JSON")
    parser.add_argument("--max-bytes", type=int, default=MAX_PAYLOAD_BYTES,
                        help="teto do payload; acima disso corta os itens mais frios")
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as handle:
        digest = json.load(handle)

    for field in ("date", "cards"):
        if field not in digest:
            raise SystemExit(f"erro: digest.json sem o campo obrigatorio '{field}'")
    if not digest["cards"]:
        raise SystemExit("erro: digest.json sem nenhum card")
    for card in digest["cards"]:
        for field in ("title", "description", "temperature", "source_name", "source_url"):
            if not card.get(field):
                raise SystemExit(
                    f"erro: card {card.get('title', '?')!r} sem o campo '{field}'"
                )
        try:
            normalize_temperature(card["temperature"])
        except ValueError as exc:
            raise SystemExit(f"erro: card {card['title']!r}: {exc}")
        if not str(card["source_url"]).startswith("http"):
            raise SystemExit(
                f"erro: card {card['title']!r} com source_url invalida: "
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
        note = f", {dropped} item(ns) cortado(s) por tamanho" if dropped else ""
        print(
            f"cartao com {len(digest['cards']) - dropped} itens, "
            f"{size} bytes na rede{note} -> {args.out}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
