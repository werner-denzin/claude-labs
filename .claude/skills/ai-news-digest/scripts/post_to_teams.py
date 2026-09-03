#!/usr/bin/env python3
"""Publishes the AI radar card to a Microsoft Teams channel via webhook.

The webhook URL is a secret: it never lives in the repository. The script reads,
in this order, --webhook-env (default TEAMS_WEBHOOK_URL) or the file pointed to
by TEAMS_WEBHOOK_FILE.

Standard library only. Usage:
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
            f"error: webhook not configured. Set {env_name} or TEAMS_WEBHOOK_FILE.\n"
            "See references/teams-delivery.md to create the channel webhook."
        )
    if not url.startswith("https://"):
        raise SystemExit("error: the webhook URL must start with https://")
    return url


def redact(url: str) -> str:
    """Never print the full URL: it is the credential."""
    head, _, _ = url.partition("?")
    return head[:60] + "...[redacted]"


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
                    f"error: Teams responded HTTP {exc.code} at {redact(url)}\n{body}"
                )
            wait = float(exc.headers.get("Retry-After") or BACKOFF_BASE ** attempt)
            print(
                f"HTTP {exc.code}, retrying in {wait:.0f}s "
                f"({attempt}/{attempts - 1})",
                file=sys.stderr,
            )
            time.sleep(wait)
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == attempts:
                raise SystemExit(f"network error while posting to Teams: {exc}")
            wait = BACKOFF_BASE ** attempt
            print(f"{type(exc).__name__}, retrying in {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
            last = exc
    raise SystemExit(f"error: failed to post to Teams: {last}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--payload", required=True, help="JSON produced by build_card.py, or - for stdin")
    parser.add_argument("--webhook-env", default="TEAMS_WEBHOOK_URL")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--dry-run", action="store_true", help="validate and report the size without posting")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.payload == "-" else open(args.payload, encoding="utf-8").read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: payload is not valid JSON: {exc}")
    if payload.get("type") != "message" or not payload.get("attachments"):
        raise SystemExit(
            "error: payload is not in the shape Teams expects "
            '(must be {"type":"message","attachments":[...]}). '
            "Generate it with build_card.py."
        )

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    size = len(body)
    if size > 28_000:
        raise SystemExit(
            f"error: payload is {size} bytes; Teams rejects anything above ~28 KB. "
            "build_card.py should have trimmed it -- check the digest."
        )

    if args.dry_run:
        blocks = len(payload["attachments"][0]["content"]["body"])
        print(f"dry-run: payload valid, {size} bytes, {blocks} blocks. Nothing posted.")
        return 0

    url = read_webhook(args.webhook_env)
    status, response = post(url, body, args.timeout, args.attempts)
    print(f"posted to Teams: HTTP {status} ({size} bytes) at {redact(url)}")
    if response.strip() and response.strip() not in {"1", "OK"}:
        print(f"response: {response.strip()[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
