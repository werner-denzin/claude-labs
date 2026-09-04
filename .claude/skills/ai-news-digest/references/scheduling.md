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

### What a run actually costs

Measured on 2026-09-03 by running the whole flow and reading the per-message
`usage` from the session transcript
(`~/.claude/projects/<project>/<session-id>.jsonl`). Not an estimate. One caveat
on the method: the transcript carries duplicate entries — 115 of 270 on that run
— so deduplicate by `message.id` before summing, or the total nearly doubles.

The run: 30/30 sources, 44 candidates, 20 cards, one WebFetch, 15 assistant
turns, 3 minutes 10 seconds wall clock.

| | Tokens |
| --- | --- |
| Fresh input | 30 |
| Cache writes | 32,753 |
| Cache reads (fresh session) | 267,709 |
| Output | 17,534 |

**Where the cost actually goes.** Billed input is almost entirely cache reads —
the conversation re-read on every turn — so a run's cost is set by the size of
the session it runs inside, not by the newsletter. The same run measured $3.00
when appended to an hour-long engineering session carrying 296K tokens of
context, and $0.78 projected for the empty session a routine starts with. The
newsletter's own work adds only ~30K tokens of context. Output was 17.5K tokens:
`digest.json` for 20 cards, the archived markdown, and the reasoning between.

| Model | Per run | 21 weekdays |
| --- | --- | --- |
| Claude Opus 5 ($5/$25 per MTok in/out) | $0.78 | $16.32 |
| **Claude Sonnet 5 ($2/$10)** — the configured model | **$0.31** | **$6.53** |

Cache rates assumed at the standard multipliers (writes 1.25x input, reads 0.10x
input); the per-million input and output rates are the published ones. The
conclusion is not sensitive to the cache assumption — with free cache reads the
Opus 5 run would still be $0.64.

**On the subscription, none of this is billed in dollars.** The table is what the
run would cost metered — under usage credits, or against the API. It is also the
number to watch when the catalog grows: collection is free (stdlib Python, no
model), but every source added enlarges `items.json`, which is the second-largest
input after the conversation itself.

### Which model

`.claude/settings.json` pins the project to **Claude Sonnet 5**, so an
interactive session in this repository and the cloud routine that clones it both
run on it. Changing that one file changes both.

The saving is real — 60% against Opus 5 — but note what is being economised on.
Collection, card building and posting are deterministic Python and cost nothing
either way; the model is spent entirely on the step that needs judgment:
consolidating the same story across seven outlets, calibrating temperature
against a committee's interests, and writing 20 cards that a reader trusts. If
the newsletter starts merging stories it should not, or marking everything
MEDIUM, the model is the first thing to put back. The `type: judgment` cases in
`evals/evals.json` exist for exactly that check.

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
| Environment | **`Full Access`** — created 2026-09-03 with **Network access = Custom**. The name says Full; the setting is Custom, which means an allowlist, which means a host missing from it fails silently. Keep the list in sync with `assets/sources.json`. |
| Connectors | Remove the ones the routine does not use — during a run it can call any tool from an included connector, writes included, without asking permission |

The routine's prompt is versioned in `references/routine-prompt.md` — the
routine stores its own copy, so that file is the source of truth and the routine
has to be re-synced when it changes. Roughly:

```
Run the ai-news-digest skill for today: collect the last 24h, classify by
temperature, select the 20 most relevant, build the card and publish it to the
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
urls=[u for x in s for u in (x.get('feed'), x.get('site'), (x.get('sitemap') or {}).get('url')) if u]
print('\n'.join(sorted({urllib.parse.urlsplit(u).netloc for u in urls})))"
```

**The `sitemap.url` matters.** A sitemap can live on a different host than the
source's `site`, and LangChain is exactly that case: `site` is
`blog.langchain.com`, while both the sitemap and the articles it points to are on
`www.langchain.com`. An allowlist built without that line has 30 hosts and
silently loses LangChain; with it, 31.

Add the Teams webhook's domain too (`*.logic.azure.com`, or whatever host your
URL uses). **This is the easy one to miss**, because the webhook is usually
configured after the environment: collection succeeds, the newsletter builds, and
only the POST fails. If publishing fails with a network error rather than a
missing-credential error, the webhook host is not on the allowlist.

The 31 hosts as of 2026-09-03:

```
a16z.com                arstechnica.com          arxiv.org
bcherny.github.io       blog.google              blog.langchain.com
blog.samaltman.com      blogs.nvidia.com         deepmind.google
export.arxiv.org        feed.infoq.com           github.blog
huggingface.co          karpathy.bearblog.dev    martinfowler.com
nvidianews.nvidia.com   openai.com               simonwillison.net
sourcegraph.com         techcrunch.com           thariq.io
the-decoder.com         www.anthropic.com        www.cursor.com
www.deeplearning.ai     www.infoq.com            www.langchain.com
www.latent.space        www.sequoiacap.com       www.ycombinator.com
zed.dev
```

Every source added to the catalog needs its host added here, or it fails with
`403 host_not_allowed` and shows up in the newsletter's failure line.

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
