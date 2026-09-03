# claude-labs

A lab for Claude Code experiments.

## The `ai-news-digest` skill

A daily AI news radar for SiDi's AI strategy committee: it collects the last 24h
from ~35 sources, classifies each item by temperature (HIGH/MEDIUM/LOW), selects
the 15 most relevant, and publishes a card-format newsletter to a Teams channel.

- Skill: `.claude/skills/ai-news-digest/SKILL.md`
- Status, decisions and what is left: `docs/HANDOFF-ai-news-digest.md`
- Published newsletters: `reports/`

Rules that hold for any change to the skill:

- **The Teams webhook URL is a credential.** Never in a repository file, a log, a
  commit, or a reply to the user. It lives in `TEAMS_WEBHOOK_URL` (or in the file
  pointed to by `TEAMS_WEBHOOK_FILE`).
- **The scripts use only the Python standard library.** The VM has no `pip`, and
  the cloud environment may not either. No new dependencies.
- **A source that failed goes into the newsletter as a declared failure**, never
  as silence. The reader has to know the collection was partial.

## User preferences

- English, everywhere: conversation, repository files, and the newsletter.
- **One exception, in the newsletter only:** cards whose main source is Brazilian
  (`"lang": "pt-BR"` in the catalog — Olhar Digital, TecMundo, Canaltech, Mobile
  Time) keep their title and description in Portuguese, because they are
  local-market stories written for that market.
- The `TOPIC_RE` regex in `fetch_feeds.py` also keeps Portuguese terms on
  purpose: it has to match the content of Brazilian sources.

## Voice dictation

The user often dictates messages, so transcription errors show up. Read for
intent; do not ask for confirmation on cases already known:

| Transcribed | Means |
| --- | --- |
| caras | cards |
| the teams | in Teams |

When a new term is clearly a transcription error, resolve it from context and, if
the user confirms, add it to this table.
