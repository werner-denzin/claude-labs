# Scheduling — weekdays, 08:00 (Brasilia time)

Decision made: **scheduled cloud routine**. The other two recipes are documented
below as alternatives.

## Chosen option: cloud routine

A routine is a saved Claude Code configuration (prompt + repositories +
environment + connectors) that runs on Anthropic-managed infrastructure,
independent of your machine.

### Cost

Routines draw down the subscription the same way an interactive session does:
same tokens, no infrastructure fee, no per-session charge. On top of the normal
usage limits there is a **daily cap on runs per account** — the number is shown
at <https://claude.ai/code/routines>. One run per weekday comes nowhere near any
plan's cap. Once the cap is hit, further runs are rejected until the window
resets, unless the organization enables *usage credits*, which turns the overage
into metered billing.

Available on Pro, Max, Team and Enterprise. Requires a claude.ai login — it does
not work with a Console API key, nor with Bedrock/Foundry.

### Creating it

```
/schedule daily AI radar newsletter, weekdays at 8am
```

Claude asks for the rest and saves it. You can also create it at
<https://claude.ai/code/routines>. Afterwards: `/schedule list`,
`/schedule update`, `/schedule run`.

### Routine configuration

| Field | Value |
| --- | --- |
| Repository | `werner-denzin/claude-labs` — the skill has to be committed, since the routine clones the repo on every run |
| Trigger | Schedule, **weekdays** preset, 08:00 |
| Timezone | **Convert nothing.** The time is entered in your local zone and converted automatically; the routine runs at 08:00 Brasilia time. |
| Environment | One with **Network access = Custom or Full** (see below) |
| Connectors | Remove the ones the routine does not use — during a run it can call any tool from an included connector, writes included, without asking permission |

The routine's prompt, roughly:

```
Run the ai-news-digest skill for today: collect the last 24h, classify by
temperature, select the 15 most relevant, build the card and publish it to the
Teams channel. If the webhook is not configured, stop before publishing and
explain what is missing.
```

### Network: the thing that breaks if forgotten

The **Default** environment ships with *Network access = Trusted*, which allows
only the default allowlist (package registries, cloud APIs). Every news source
falls outside it: each request comes back `403` with
`x-deny-reason: host_not_allowed` and the newsletter comes out empty.

On the routine's environment, set **Network access** to **Full**, or **Custom**
with the domains from `assets/sources.json`. To extract the list:

```bash
python3 -c "
import json,urllib.parse
s=json.load(open('.claude/skills/ai-news-digest/assets/sources.json'))['sources']
d={urllib.parse.urlsplit(u).netloc for x in s for u in (x.get('feed'),x.get('site')) if u}
print('\n'.join(sorted(d)))"
```

Add the Teams webhook's domain too (`*.logic.azure.com`, or whatever host your
URL uses).

### The webhook secret

Environment variables on a cloud environment **are visible to anyone who uses
that environment**. Store the webhook URL as an **API credential** of the
environment, not as an environment variable, and never in the repository.

### Operational details

- Runs may start a few minutes after 08:00: there is a deliberate *stagger*,
  constant per routine.
- Minimum interval between runs: 1 hour.
- A green status in the run list means the session started and exited without an
  infrastructure error — **not** that the newsletter went out. Open the run and
  read the transcript. Blocked requests and task-level failures show up there,
  not in the status indicator.
- The routine belongs to your individual account and is not shared with the team.
  What it publishes goes out as you.
- A Team/Enterprise Owner can disable routines for the whole organization at
  `claude.ai/admin-settings/claude-code`. If `/schedule` disappears, that is the
  first place to look.

## Alternative A: local timer on WSL

Free to run, but it **only fires with WSL up at 08:00** — and WSL does not start
by itself with Windows. Good for manual testing, risky for production.

`~/.config/systemd/user/ai-radar.service`:

```ini
[Unit]
Description=AI Radar - daily newsletter

[Service]
Type=oneshot
WorkingDirectory=%h/git/claude-labs
Environment=TEAMS_WEBHOOK_FILE=%h/.config/sidi/teams-webhook
ExecStart=/usr/bin/claude -p "Run the ai-news-digest skill and publish today's newsletter to Teams."
```

`~/.config/systemd/user/ai-radar.timer`:

```ini
[Unit]
Description=AI Radar at 08:00 on weekdays

[Timer]
OnCalendar=Mon..Fri 08:00 America/Sao_Paulo
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now ai-radar.timer
systemctl --user list-timers ai-radar.timer
loginctl enable-linger "$USER"   # so the timer survives logout
```

With `cron` instead of systemd the equivalent is `0 8 * * 1-5` — but then the
timezone is the system's, so check it with `timedatectl`.

## Alternative B: GitHub Actions

Always runs, versioned logs. Two caveats: the Actions cron is **in UTC** (08:00
BRT = `0 11 * * 1-5`, and Brazil has had no DST since 2019, so the conversion is
fixed), and Actions has no interactive Claude — triage would have to go through
the API with an `ANTHROPIC_API_KEY` in secrets, or the newsletter comes out
uncurated. `TEAMS_WEBHOOK_URL` goes in *Repository secrets*.

```yaml
on:
  schedule:
    - cron: "0 11 * * 1-5"   # 08:00 America/Sao_Paulo
  workflow_dispatch:
```

Worth it only if you want the subscription out of the critical path.
