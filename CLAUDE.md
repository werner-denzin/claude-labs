# claude-labs

A lab for Claude Code experiments.

## The `ai-news-digest` skill

A daily radar on **software engineering with AI** for SiDi's AI strategy
committee: it collects the last 24h from 30 sources, classifies each item by
temperature (HIGH/MEDIUM/LOW), selects 20, and publishes a card-format newsletter
to a Teams channel.

The lens shares are engineering 10, strategy 5, research 3, regulation 2 of the
20. Engineering leads by design: it is what the committee is here for.

**Engineering means the agenda EVOLV development exercises** — LangGraph and
agent frameworks, harness engineering, context engineering, prompt engineering,
MCP, agent memory, guardrails, evals and observability, tool use, and the coding
agents themselves (Claude Code, Codex, Cursor, Copilot, Zed). Twelve of the
thirty sources exist for it, led by Anthropic Engineering, LangChain, Simon
Willison, GitHub AI, InfoQ and Hugging Face. On a measured day, 19 of 44
candidates touch that agenda.

There is still no coding-agent release feed: the cloud sandbox scopes GitHub
access to the cloned repository and returns 403 for every other repo, so Cursor's
changelog is the only agent shipping notes the collector can read. Strategy and
regulation come from the labs themselves, the press covering them, and the
investors.

`assets/sources.json` is the base of truth for all of this. When it changes,
`CLAUDE.md`, `README.md`, `SKILL.md` and `references/sources.md` change with it.

- Skill: `.claude/skills/ai-news-digest/SKILL.md`
- Published newsletters: `reports/`

### Live, in archive-only mode

The routine `AI Radar (archive)` runs weekdays at 08:00 BRT (`0 11 * * 1-5` UTC)
on the `Full Access` environment, on Claude Sonnet 5, cloning this repo each run.
Two of the three activation steps are done: the repo is on the remote, and the
routine exists and works — verified 2026-09-04, 29/30 sources answered through
the environment's allowlist and the run pushed its own report to `main`.

**One step left.** No Teams webhook is configured, so the routine stops at
`--dry-run` and publishes nothing to the channel; it commits the markdown report
instead. To finish it, create the channel webhook and put the URL in the
routine's environment — steps in `references/teams-delivery.md`. Never in a
repository file.

Rules that hold for any change to the skill:

- **The Teams webhook URL is a credential.** Never in a repository file, a log, a
  commit, or a reply to the user. It lives in `TEAMS_WEBHOOK_URL` (or in the file
  pointed to by `TEAMS_WEBHOOK_FILE`).
- **The scripts use only the Python standard library.** The VM has no `pip`, and
  the cloud environment may not either. No new dependencies.
- **A source that failed goes into the newsletter as a declared failure**, never
  as silence. The reader has to know the collection was partial.
- **The collector identifies itself honestly** and never disguises itself to get
  past a block. If a source refuses `ai-news-digest/1.0`, it becomes a declared
  failure or it leaves the catalog — no spoofed user agent, rotated IP or proxy.
  Details and the measurement in `references/sources.md`.
- **A block or an oddity goes in the report's `Blocked / Unexpected Behaviors`
  section**, always rendered, saying "None." on a clean run. It records what was
  observed *and what it means* — a `403` carrying `x-deny-reason` is the
  environment's allowlist, one without it is the source refusing us — because
  this is the evidence a source gets disabled or removed on. Never write
  "expected" without saying why.
- **Two artifacts, deliberately different lengths.** `reports/*.md` is the
  complete and detailed edition — every card the editorial step selected. The
  Teams card is the short version of it: if the payload would exceed what Teams
  accepts, the coolest cards are left off *the card* and its footer points at the
  report. The digest is never modified, so the archive never loses anything.
  Selection is never constrained by how the card will render. The Teams layout
  itself is still to be designed; until then "short" means "as many as fit".
- **The last edition is not published twice.** The collector drops an item whose
  canonical URL was already published and *flags* one whose title merely
  resembles a published title — because a story usually returns when something
  changed, and dropping that silently loses real news. The anchor is the newest
  file in `reports/`, not yesterday's date.
- **The routine's prompt is versioned in
  `references/routine-prompt.md`, and the routine holds a copy.** After any
  change to `SKILL.md` or to how the skill behaves, read that file and ask
  whether the prompt still tells the truth. If it does not: edit the file, apply
  it to the routine, and update its **Last synced** line. Skipping the apply
  leaves the live routine drifting, which is the failure this file exists to
  prevent — the prompt spent weeks telling every run that "Anthropic and a16z
  must be read with WebFetch" and that fewer than 15 items meant a thin day.
  Keep the prompt thin: anything about the newsletter itself belongs in
  `SKILL.md`, which is versioned, not in the prompt, which is a copy.
- **A retired source is disabled, not deleted.** `"enabled": false` keeps the
  entry, its note and the reasoning that took work to establish; the collector
  skips it and reports it under `sources_disabled`, so `28/28` is never quietly
  `28/30`. `--only <id>` still reads it, which is how you test one you just
  disabled.
- **The model is pinned to Claude Sonnet 5** in `.claude/settings.json`, which
  covers both an interactive session here and the cloud routine that clones the
  repo. A measured run costs $0.31 metered, against $0.78 on Opus 5 — the
  breakdown, and what the saving trades against, is in
  `references/scheduling.md`. Triage is the only step that spends model tokens,
  so if the editorial quality drops, the model is the first thing to put back.

### Backlog

- Say what changed since the last edition, not just what is new — the
  comparison against the last report already flags returning stories with
  `in_previous_report`, so the material is there.
- Watch the LangChain sitemap: it bulk-stamps `lastmod` on a rebuild, so a day
  with several same-dated LangChain items may be old posts resurfacing.
- Review the `Blocked / Unexpected Behaviors` sections across `reports/` every
  so often — `grep -l "<source name>" reports/*.md` — and disable whatever keeps
  appearing there.
- Still uncovered on the engineering agenda: the MCP spec (no feed anywhere),
  Cline, Codex's own changelog. Optional low-volume additions measured and left
  out: JetBrains AI, the Pragmatic Engineer, Hamel Husain, Chip Huyen.
- Add Brazilian regulatory sources (PL 2338, ANPD) once that agenda heats up.
  Nothing in the catalog covers regulation directly today; it arrives only when
  Ars Technica or TechCrunch reports it.
- Run the `type: judgment` evals with an LLM judge over the published newsletter.

## User preferences

- English, everywhere: conversation, repository files, and the newsletter.
- **One exception, in the newsletter only:** cards whose main source is Brazilian
  (`"lang": "pt-BR"` in the catalog) keep their title and description in
  Portuguese, because they are local-market stories written for that market. The
  rule stands, but no `pt-BR` source is in the catalog today — the Brazilian
  press left it when the catalog was cut — so nothing triggers it right now.
- The `TOPIC_RE` regex in `fetch_feeds.py` also keeps Portuguese terms on
  purpose: it has to go on matching the day a Brazilian source returns.

## Voice dictation

The user often dictates messages, so transcription errors show up. Read for
intent; do not ask for confirmation on cases already known:

| Transcribed | Means |
| --- | --- |
| caras | cards |
| the teams | in Teams |

When a new term is clearly a transcription error, resolve it from context and, if
the user confirms, add it to this table.
