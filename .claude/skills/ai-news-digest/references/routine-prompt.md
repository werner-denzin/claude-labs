# The routine's prompt

The scheduled routine stores its prompt in its own configuration on Anthropic's
side (`job_config.ccr.events[].data.message.content`), not in this repository.
That makes it the only part of the system that is not versioned — and it drifted
for exactly that reason: on 2026-09-04 it was still telling every run that
"Anthropic and a16z must be read with WebFetch" and that fewer than 15 items
meant a thin day, weeks after both had stopped being true.

**This file is the source of truth. The routine holds a copy.** When this file
changes, the routine has to be re-synced, or the drift starts again.

- Routine: `AI Radar (archive)`, `trig_01M3gcVsY2GipoQNvYtffPRA`
- Last synced: **2026-09-04**, applied with `RemoteTrigger update` and confirmed
  byte-identical in the response's stored prompt. Update this line with the date
  whenever you apply a change.

## Keep it thin

Every sentence here is a sentence that can go stale, because `SKILL.md` is
versioned and this is not. So the prompt carries **only what is specific to a
scheduled run** — archive-only mode, the window, where to write and what to
commit. Anything about the catalog, the lenses, temperature, the writing rules,
how feedless sources are read, or how failures are reported belongs in
`SKILL.md`, and the prompt says so in its first paragraph rather than repeating
it.

If you find yourself adding a fact about *the newsletter* here, put it in
`SKILL.md` instead and let the prompt keep pointing at it.

## The prompt

```text
Produce today's AI Radar in archive-only mode.

Read .claude/skills/ai-news-digest/SKILL.md first and follow it exactly. It is
the source of truth for the source catalog, the temperature rubric, the lens
shares, how feedless sources are read, how blocks are reported, and the writing
rules. Do not rely on anything in this prompt that contradicts it - the skill is
versioned in the repo and this prompt is not, so the skill wins. Paths in the
skill's Files table are relative to .claude/skills/ai-news-digest/, not to the
repository root.

This prompt sets only what is specific to the scheduled run:

ARCHIVE-ONLY. Do not publish to Teams. Run post_to_teams.py only with
--dry-run, to prove the payload is valid. No webhook is configured and
publishing is deliberately disabled.

WINDOW. Use --hours 24, except on Mondays where --hours 72 covers the weekend.

URL DISCIPLINE. Before building the card, verify that every source_url and every
also_covered_by url in digest.json appears in the collected items.json. Never
reconstruct a URL from a headline. If one does not match, fix it or drop the
item.

OUTPUT. Write the complete edition to reports/YYYY-MM-DD-ai-radar.md following
assets/report-template.md - every card in digest.json, including any the Teams
card would leave off for size. Commit ONLY that file. Push it to main with:
git push origin HEAD:main. The commit message states the counts by temperature,
how many sources answered out of the total, and anything notable that failed.

IF THE REPORT FOR TODAY ALREADY EXISTS, do not overwrite it with a worse-sourced
version. Compare what you collected against what is already there, and only
replace it if yours is materially better. Otherwise commit nothing and say why.

STOP AND DO NOT COMMIT if collection was blocked rather than merely partial: a
403 carrying x-deny-reason means the environment's network allowlist refused the
host, so say the environment needs its allowlist updated and write no report. A
403 without that header is the source refusing us - a declared failure, not a
blocker, and the run continues.

Everything else - what counts as a block worth recording, how many cards, what
is expected to be quiet - is in SKILL.md. Follow it there.
```

## How to sync

Apply it with the `RemoteTrigger` tool (`/schedule` drives the same API):

```
RemoteTrigger update, trigger_id: trig_01M3gcVsY2GipoQNvYtffPRA
  body.job_config.ccr.events[0].data.message.content = <the block above>
```

`events[].data.message` must keep its API shape — `{"role": "user", "content":
"..."}`, with `role` present. Re-read the routine afterwards with
`RemoteTrigger get` and confirm the stored prompt matches this file, then update
the **Last synced** line above.

The prompt can also be edited by hand at
<https://claude.ai/code/routines> — if you do that, paste from this file so the
two do not diverge.
