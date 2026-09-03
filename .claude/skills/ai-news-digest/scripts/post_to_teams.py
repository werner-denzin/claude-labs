#!/usr/bin/env python3
"""Publica o cartao do radar de IA num canal do Microsoft Teams via webhook.

A URL do webhook e um segredo: nunca fica no repositorio. O script le, nesta
ordem, --webhook-env (padrao TEAMS_WEBHOOK_URL) ou o arquivo apontado por
TEAMS_WEBHOOK_FILE.

Somente biblioteca padrao. Uso:
    export TEAMS_WEBHOOK_URL='https://prod-XX.westus.logic.azure.com/...'
    python3 post_to_teams.py --payload card.json
    python3 post_to_teams.py --payload card.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_ATTEMPTS = 4
BACKOFF_BASE = 2.0


def read_webhook(env_name: str) -> str:
    url = os.environ.get(env_name, "").strip()
    if not url:
        path = os.environ.get("TEAMS_WEBHOOK_FILE", "").strip()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                url = handle.read().strip()
    if not url:
        raise SystemExit(
            f"erro: webhook nao configurado. Defina {env_name} ou TEAMS_WEBHOOK_FILE.\n"
            "Ver references/teams-delivery.md para criar o webhook do canal."
        )
    if not url.startswith("https://"):
        raise SystemExit("erro: a URL do webhook precisa ser https://")
    return url


def redact(url: str) -> str:
    """Nunca imprimir a URL inteira: ela e a credencial."""
    head, _, _ = url.partition("?")
    return head[:60] + "...[redigido]"


def post(url: str, payload: bytes, timeout: int, attempts: int) -> tuple[int, str]:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read(4096).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            body = exc.read(2048).decode("utf-8", "replace")
            if exc.code not in RETRY_STATUS or attempt == attempts:
                raise SystemExit(
                    f"erro: o Teams respondeu HTTP {exc.code} em {redact(url)}\n{body}"
                )
            wait = float(exc.headers.get("Retry-After") or BACKOFF_BASE ** attempt)
            print(
                f"HTTP {exc.code}, nova tentativa em {wait:.0f}s "
                f"({attempt}/{attempts - 1})",
                file=sys.stderr,
            )
            time.sleep(wait)
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == attempts:
                raise SystemExit(f"erro de rede ao publicar no Teams: {exc}")
            wait = BACKOFF_BASE ** attempt
            print(f"{type(exc).__name__}, nova tentativa em {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
            last = exc
    raise SystemExit(f"erro: falha ao publicar no Teams: {last}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--payload", required=True, help="JSON gerado por build_card.py, ou - para stdin")
    parser.add_argument("--webhook-env", default="TEAMS_WEBHOOK_URL")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--dry-run", action="store_true", help="valida e mostra o tamanho, sem publicar")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.payload == "-" else open(args.payload, encoding="utf-8").read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"erro: payload nao e JSON valido: {exc}")
    if payload.get("type") != "message" or not payload.get("attachments"):
        raise SystemExit(
            "erro: payload fora do formato esperado pelo Teams "
            '(precisa ser {"type":"message","attachments":[...]}). '
            "Gere-o com build_card.py."
        )

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    size = len(body)
    if size > 28_000:
        raise SystemExit(
            f"erro: payload com {size} bytes; o Teams recusa acima de ~28 KB. "
            "build_card.py deveria ter cortado — verifique o digest."
        )

    if args.dry_run:
        blocks = len(payload["attachments"][0]["content"]["body"])
        print(f"dry-run: payload valido, {size} bytes, {blocks} blocos. Nada publicado.")
        return 0

    url = read_webhook(args.webhook_env)
    status, response = post(url, body, args.timeout, args.attempts)
    print(f"publicado no Teams: HTTP {status} ({size} bytes) em {redact(url)}")
    if response.strip() and response.strip() not in {"1", "OK"}:
        print(f"resposta: {response.strip()[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
