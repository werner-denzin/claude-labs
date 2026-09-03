#!/usr/bin/env python3
"""Executa os evals de script da skill ai-news-digest.

Sao os casos de `evals.json` com "type": "script" — os que nao dependem de
julgamento editorial. Os de "type": "judgment" precisam de um humano ou de um
juiz LLM lendo o boletim.

O eval de coleta toca a rede; use --offline para pular so ele.

    python3 evals/run_script_evals.py
    python3 evals/run_script_evals.py --offline
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(SKILL, "evals", "fixtures")
EMOJI = ("\U0001f534", "\U0001f7e0", "\U0001f535")

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok    {name}")
    else:
        print(f"  FALHA {name}{': ' + detail if detail else ''}")
        failures.append(name)


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=SKILL, capture_output=True, text=True, **kwargs
    )


def text_blocks(node):
    """Percorre body/items/columns aninhados e devolve todos os TextBlock."""
    if isinstance(node, dict):
        if node.get("type") == "TextBlock":
            yield node
        for key in ("body", "items", "columns"):
            for child in node.get(key) or []:
                yield from text_blocks(child)
    elif isinstance(node, list):
        for child in node:
            yield from text_blocks(child)


def temperatures(payload: dict) -> list[str]:
    card = payload["attachments"][0]["content"]
    out = []
    for block in text_blocks(card):
        text = block.get("text", "")
        if text.startswith(EMOJI):
            for label in ("HIGH", "MEDIUM", "LOW"):
                if f"**{label}**" in text:
                    out.append(label)
    return out


# --------------------------------------------------------------------------- #

def eval_collect_window(tmp: str) -> None:
    print("\n[collect-window] coleta respeita a janela e reporta falhas")
    out = os.path.join(tmp, "items.json")
    proc = run(["scripts/fetch_feeds.py", "--hours", "24", "--out", out])
    check("sai com codigo 0 mesmo com fontes falhando", proc.returncode == 0, proc.stderr[-200:])
    if proc.returncode != 0:
        return
    data = json.load(open(out, encoding="utf-8"))
    check("coletou algum item", data["counts"]["items_deduped"] > 0)
    check(
        "todo item tem data dentro da janela",
        all(i["published"] >= data["window_start"] for i in data["items"]),
    )
    no_feed = {f["id"] for f in data["sources_failed"] if "sem feed" in f["error"]}
    check(
        "fontes sem feed aparecem em sources_failed com motivo",
        no_feed >= {"anthropic", "meta-ai"},
        f"veio {no_feed}",
    )
    filtered = [s for s in data["sources_ok"] if s.get("off_topic", 0) > 0]
    check("o filtro de assunto descartou itens", bool(filtered))
    check(
        "nenhum item duplicado por URL",
        len({i["url"] for i in data["items"]}) == len(data["items"]),
    )


def eval_card_size_limit(tmp: str) -> None:
    print("\n[card-size-limit] o cartao corta os itens mais frios primeiro")
    out = os.path.join(tmp, "small.json")
    proc = run([
        "scripts/build_card.py", "--in", "evals/fixtures/digest-15.json",
        "--out", out, "--max-bytes", "6000",
    ])
    check("gerou o cartao", proc.returncode == 0, proc.stderr[-200:])
    if proc.returncode != 0:
        return
    payload = json.load(open(out, encoding="utf-8"))
    size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    check(f"payload dentro do limite ({size} <= 6000)", size <= 6000)
    kept = temperatures(payload)
    check("os 3 itens HIGH sobreviveram", kept.count("HIGH") == 3, f"veio {kept}")
    check("nenhum LOW passou na frente de um MEDIUM", "LOW" not in kept, f"veio {kept}")
    blocks = list(text_blocks(payload["attachments"][0]["content"]))
    check("o rodape avisa do corte", any("omitted" in b.get("text", "") for b in blocks))

    full = os.path.join(tmp, "full.json")
    run(["scripts/build_card.py", "--in", "evals/fixtures/digest-15.json", "--out", full])
    check("sem corte, os 15 itens entram", len(temperatures(json.load(open(full)))) == 15)


def eval_digest_validation(tmp: str) -> None:
    print("\n[digest-validation] digest malformado falha com mensagem util")
    proc = run(["scripts/build_card.py", "--in", "evals/fixtures/digest-invalida.json", "--out", os.path.devnull])
    combined = proc.stdout + proc.stderr
    check("codigo de saida diferente de zero", proc.returncode != 0)
    check("sem traceback", "Traceback" not in combined, combined[-200:])
    check("a mensagem nomeia o campo que faltou", "source_url" in combined, combined[-200:])

    bad = os.path.join(tmp, "temp-ruim.json")
    digest = json.load(open(os.path.join(FIXTURES, "digest-15.json"), encoding="utf-8"))
    digest["cards"][0]["temperature"] = "QUENTE"
    json.dump(digest, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    proc = run(["scripts/build_card.py", "--in", bad, "--out", os.path.devnull])
    combined = proc.stdout + proc.stderr
    check("temperatura invalida recusada sem traceback",
          proc.returncode != 0 and "Traceback" not in combined, combined[-200:])
    check("a mensagem explica os valores aceitos", "HIGH" in combined)

    alias = os.path.join(tmp, "alias.json")
    digest = json.load(open(os.path.join(FIXTURES, "digest-15.json"), encoding="utf-8"))
    for card, value in zip(digest["cards"], ["ALTA", "MEDIA", "BAIXA"]):
        card["temperature"] = value
    json.dump(digest, open(alias, "w", encoding="utf-8"), ensure_ascii=False)
    proc = run(["scripts/build_card.py", "--in", alias, "--out", os.path.join(tmp, "a.json")])
    check("ALTA/MEDIA/BAIXA aceitos como alias", proc.returncode == 0, proc.stderr[-200:])


def eval_webhook_secret(tmp: str) -> None:
    print("\n[webhook-secret] a URL do webhook nunca vaza")
    secret = "https://exemplo.logic.azure.com/workflows/abc?api-version=1&sig=SEGREDO123"
    env = {**os.environ, "TEAMS_WEBHOOK_URL": secret}
    proc = run(["scripts/post_to_teams.py", "--payload", "evals/fixtures/card.json", "--dry-run"], env=env)
    combined = proc.stdout + proc.stderr
    check("dry-run sai com codigo 0", proc.returncode == 0, combined[-200:])
    check("o segredo nao aparece na saida", "SEGREDO123" not in combined, combined[-200:])
    check("a query string nao aparece", "sig=" not in combined)

    env = {k: v for k, v in os.environ.items() if k not in ("TEAMS_WEBHOOK_URL", "TEAMS_WEBHOOK_FILE")}
    proc = run(["scripts/post_to_teams.py", "--payload", "evals/fixtures/card.json"], env=env)
    combined = proc.stdout + proc.stderr
    check("sem webhook, falha explicando como configurar",
          proc.returncode != 0 and "TEAMS_WEBHOOK_URL" in combined, combined[-200:])

    bad = os.path.join(tmp, "payload-cru.json")
    json.dump({"text": "oi"}, open(bad, "w"))
    proc = run(["scripts/post_to_teams.py", "--payload", bad, "--dry-run"])
    check("payload fora do formato do Teams e recusado", proc.returncode != 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="pula o eval que toca a rede")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        if args.offline:
            print("\n[collect-window] pulado (--offline)")
        else:
            eval_collect_window(tmp)
        eval_card_size_limit(tmp)
        eval_digest_validation(tmp)
        eval_webhook_secret(tmp)

    print()
    if failures:
        print(f"{len(failures)} verificacao(oes) falharam: {', '.join(failures)}")
        return 1
    print("todas as verificacoes passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
