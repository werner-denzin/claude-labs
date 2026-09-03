#!/usr/bin/env python3
"""Runs the script evals for the ai-news-digest skill.

These are the `evals.json` cases with "type": "script" -- the ones that need no
editorial judgment. The "type": "judgment" cases need a human, or an LLM judge,
reading the newsletter.

The collection eval touches the network; use --offline to skip just that one.

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
        print(f"  FAIL  {name}{': ' + detail if detail else ''}")
        failures.append(name)


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=SKILL, capture_output=True, text=True, **kwargs
    )


def text_blocks(node):
    """Walks nested body/items/columns and yields every TextBlock."""
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
    print("\n[collect-window] collection respects the window and reports failures")
    out = os.path.join(tmp, "items.json")
    proc = run(["scripts/fetch_feeds.py", "--hours", "24", "--out", out])
    check("exits 0 even with failing sources", proc.returncode == 0, proc.stderr[-200:])
    if proc.returncode != 0:
        return
    data = json.load(open(out, encoding="utf-8"))
    check("collected at least one item", data["counts"]["items_deduped"] > 0)
    check(
        "every item is dated inside the window",
        all(i["published"] >= data["window_start"] for i in data["items"]),
    )
    check(
        "every failure carries a reason",
        all(f.get("error") for f in data["sources_failed"]),
        f'got {[f.get("error") for f in data["sources_failed"]]}',
    )
    sitemap_ids = {"anthropic", "a16z"}
    failed_ids = {f["id"] for f in data["sources_failed"]}
    check(
        "sitemap sources are read, not reported as failures",
        not (sitemap_ids & failed_ids),
        f"these failed: {sitemap_ids & failed_ids}",
    )
    filtered = [s for s in data["sources_ok"] if s.get("off_topic", 0) > 0]
    check("the topic filter dropped items", bool(filtered))
    check(
        "no item duplicated by URL",
        len({i["url"] for i in data["items"]}) == len(data["items"]),
    )


def eval_card_size_limit(tmp: str) -> None:
    print("\n[card-size-limit] the card drops the coldest items first")
    out = os.path.join(tmp, "small.json")
    proc = run([
        "scripts/build_card.py", "--in", "evals/fixtures/digest-15.json",
        "--out", out, "--max-bytes", "6000",
    ])
    check("built the card", proc.returncode == 0, proc.stderr[-200:])
    if proc.returncode != 0:
        return
    payload = json.load(open(out, encoding="utf-8"))
    size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    check(f"payload within the limit ({size} <= 6000)", size <= 6000)
    kept = temperatures(payload)
    check("all 3 HIGH items survived", kept.count("HIGH") == 3, f"got {kept}")
    check("no LOW kept ahead of a MEDIUM", "LOW" not in kept, f"got {kept}")
    blocks = list(text_blocks(payload["attachments"][0]["content"]))
    check("the footer announces the trim", any("omitted" in b.get("text", "") for b in blocks))

    full = os.path.join(tmp, "full.json")
    run(["scripts/build_card.py", "--in", "evals/fixtures/digest-15.json", "--out", full])
    check("with no trim, all 15 items fit", len(temperatures(json.load(open(full)))) == 15)


def eval_digest_validation(tmp: str) -> None:
    print("\n[digest-validation] a malformed digest fails with a useful message")
    proc = run(["scripts/build_card.py", "--in", "evals/fixtures/digest-invalida.json", "--out", os.path.devnull])
    combined = proc.stdout + proc.stderr
    check("non-zero exit code", proc.returncode != 0)
    check("no traceback", "Traceback" not in combined, combined[-200:])
    check("the message names the missing field", "source_url" in combined, combined[-200:])

    bad = os.path.join(tmp, "temp-ruim.json")
    digest = json.load(open(os.path.join(FIXTURES, "digest-15.json"), encoding="utf-8"))
    digest["cards"][0]["temperature"] = "QUENTE"
    json.dump(digest, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    proc = run(["scripts/build_card.py", "--in", bad, "--out", os.path.devnull])
    combined = proc.stdout + proc.stderr
    check("invalid temperature rejected without a traceback",
          proc.returncode != 0 and "Traceback" not in combined, combined[-200:])
    check("the message lists the accepted values", "HIGH" in combined)

    alias = os.path.join(tmp, "alias.json")
    digest = json.load(open(os.path.join(FIXTURES, "digest-15.json"), encoding="utf-8"))
    for card, value in zip(digest["cards"], ["ALTA", "MEDIA", "BAIXA"]):
        card["temperature"] = value
    json.dump(digest, open(alias, "w", encoding="utf-8"), ensure_ascii=False)
    proc = run(["scripts/build_card.py", "--in", alias, "--out", os.path.join(tmp, "a.json")])
    check("ALTA/MEDIA/BAIXA accepted as aliases", proc.returncode == 0, proc.stderr[-200:])


def eval_webhook_secret(tmp: str) -> None:
    print("\n[webhook-secret] the webhook URL never leaks")
    secret = "https://exemplo.logic.azure.com/workflows/abc?api-version=1&sig=SECRET123"
    env = {**os.environ, "TEAMS_WEBHOOK_URL": secret}
    proc = run(["scripts/post_to_teams.py", "--payload", "evals/fixtures/card.json", "--dry-run"], env=env)
    combined = proc.stdout + proc.stderr
    check("dry-run exits 0", proc.returncode == 0, combined[-200:])
    check("the secret never appears in the output", "SECRET123" not in combined, combined[-200:])
    check("the query string never appears", "sig=" not in combined)

    env = {k: v for k, v in os.environ.items() if k not in ("TEAMS_WEBHOOK_URL", "TEAMS_WEBHOOK_FILE")}
    proc = run(["scripts/post_to_teams.py", "--payload", "evals/fixtures/card.json"], env=env)
    combined = proc.stdout + proc.stderr
    check("with no webhook, fails explaining how to configure it",
          proc.returncode != 0 and "TEAMS_WEBHOOK_URL" in combined, combined[-200:])

    bad = os.path.join(tmp, "payload-cru.json")
    json.dump({"text": "oi"}, open(bad, "w"))
    proc = run(["scripts/post_to_teams.py", "--payload", bad, "--dry-run"])
    check("a payload outside the Teams shape is rejected", proc.returncode != 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="skip the eval that touches the network")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        if args.offline:
            print("\n[collect-window] skipped (--offline)")
        else:
            eval_collect_window(tmp)
        eval_card_size_limit(tmp)
        eval_digest_validation(tmp)
        eval_webhook_secret(tmp)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
