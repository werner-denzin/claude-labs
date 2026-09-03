# claude-labs

A lab for Claude Code experiments.

## The `ai-news-digest` skill

A daily radar on **software engineering with AI** for SiDi's AI strategy
committee: it collects the last 24h from 20 sources, classifies each item by
temperature (HIGH/MEDIUM/LOW), selects 20, and publishes a card-format newsletter
to a Teams channel.

The lens shares are engineering 10, strategy 5, research 3, regulation 2 of the
20. Engineering leads by design: it is what the committee is here for.
Engineering reaches the radar through Latent Space, GitHub Changelog and
`arXiv cs.SE`, plus whatever the press writes about tooling; there is no
coding-agent release feed, because the cloud sandbox scopes GitHub access to the
cloned repository and returns 403 for every other repo. Strategy and regulation
come from the labs themselves, the press covering them, and the investors.

**The catalog does not yet supply that share.** The two engineering sources
produced 5 items in the last 24h and 12 in a week (measured 2026-09-03), so ten
engineering cards a day depends on the press supplying the rest, judged by lens
rather than by source. Closing that gap means adding engineering sources — the
backlog item below.

`assets/sources.json` is the base of truth for all of this. When it changes,
`CLAUDE.md`, `README.md`, `SKILL.md` and `references/sources.md` change with it.

- Skill: `.claude/skills/ai-news-digest/SKILL.md`
- Published newsletters: `reports/`

### Not live yet

The skill runs manually today — collection, triage and
`build_card.py --preview` all work without a webhook; only the final POST needs
the secret. Three steps to make it run on its own:

1. Create the Teams channel webhook and store the URL — steps in
   `references/teams-delivery.md`.
2. Push this repo to GitHub: the routine clones `werner-denzin/claude-labs` on
   every run, so the skill has to be on the remote.
3. Create the routine with `/schedule`, pointing at an environment with
   **Network access = Custom or Full**. The `Default` environment is *Trusted*
   and blocks every news source (`403 host_not_allowed`) — the most likely cause
   of an empty newsletter at 08:00. Cost and limits in `references/scheduling.md`.

Rules that hold for any change to the skill:

- **The Teams webhook URL is a credential.** Never in a repository file, a log, a
  commit, or a reply to the user. It lives in `TEAMS_WEBHOOK_URL` (or in the file
  pointed to by `TEAMS_WEBHOOK_FILE`).
- **The scripts use only the Python standard library.** The VM has no `pip`, and
  the cloud environment may not either. No new dependencies.
- **A source that failed goes into the newsletter as a declared failure**, never
  as silence. The reader has to know the collection was partial.

### Backlog

- Read the previous day's `reports/` entry to say what changed since yesterday.
- **Add engineering sources to support the 10-of-20 share.** Reachable
  candidates that are not GitHub release feeds: Simon Willison's
  `ai-assisted-programming` tag, Sourcegraph, JetBrains AI, the MCP spec, InfoQ,
  the Pragmatic Engineer, Martin Fowler, Cursor's changelog.
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
