# `ai-news-digest` skill — status, decisions, and what is left

Updated 2026-09-03. Replaces the handoff written by session
`session_01DurrNSDNuj5sHouP8cF7Z2`, which described an earlier design.

## What the skill does

A daily AI newsletter for SiDi's AI strategy committee:

1. Collects the last 24h from ~35 sources (labs, press, regulation, engineering,
   research, Brazilian press).
2. Classifies each item by **temperature** — HIGH, MEDIUM or LOW — measuring
   relevance to the committee, not popularity of the news.
3. Selects the **15 most relevant**.
4. Publishes a **card-format newsletter** (Adaptive Card) to a Teams channel, and
   archives the markdown version in `reports/`.

## Decisions made with the user

| Topic | Decision |
| --- | --- |
| Output format | **Cards, no PDF.** The original request called for a PDF; the user dropped it after seeing that a Teams channel webhook cannot attach a file. The card carries the whole newsletter. |
| Delivery | Teams channel webhook, created through **Workflows** (Power Automate). The legacy connector is deprecated. |
| Scheduling | **Scheduled cloud routine** (`/schedule`), weekdays at 08:00 BRT. Runs without depending on the user's machine. |
| Language | **Newsletter in English**, and every repository file in English. Exception: cards whose main source is Brazilian stay in Portuguese. Decided after the first implementation, which was entirely in pt-BR. |
| Triage lenses | All four: corporate strategy, regulation/governance, engineering/agentic coding, research/papers. |
| Secret | `TEAMS_WEBHOOK_URL` in the environment; in the cloud, as an **API credential**, never as an environment variable. |
| Branch | `claude/ai-research-skill-xoqo0i` |

## Status: implemented and tested

```
.claude/skills/ai-news-digest/
├── SKILL.md                        # flow, temperature rubric, writing rules
├── assets/
│   ├── sources.json                # 35 sources, validated against the network
│   └── report-template.md
├── scripts/
│   ├── fetch_feeds.py              # parallel RSS/Atom aggregator, dedup, topic filter
│   ├── build_card.py               # digest.json -> Adaptive Card, with size trimming
│   └── post_to_teams.py            # POST to the webhook, retry with backoff, secret redaction
├── references/
│   ├── digest-schema.md
│   ├── sources.md
│   ├── teams-delivery.md
│   └── scheduling.md
└── evals/
    ├── evals.json                  # 4 script cases + 4 editorial-judgment cases
    ├── run_script_evals.py         # runs the 4 script cases (23 checks)
    └── fixtures/
```

Measured on 2026-09-03, against the live network:

- Full collection in ~3s. 32 of 35 feeds respond.
- 24h window: 93 items after the topic filter and deduplication.
- `run_script_evals.py`: 23 checks, all passing.

### Catalog fixes

Half the original catalog pointed at dead addresses. Fixed against the network:
`microsoft-ai`, `mistral`, `google-ai`, `venturebeat-ai`, `tecmundo`, `hn-ai`.
Removed: `zdnet-ai` (404 on every path). No public feed, site only: `anthropic`,
`meta-ai`, `marktechpost`. Added to cover the four lenses: `eu-ai-act`,
`latent-space`, `infoq-ai`, `google-research`, `mit-news-ai`, `meta-engineering`,
`mobile-time`.

### Topic filter

General-tech sources were filling the window with phones, games and retail
promos. In validation the filter cut 42 of 50 Canaltech items and 23 of 26
TecMundo items, taking the collection from 183 to 93 without losing any AI
coverage.

## What is left before it runs on its own

Three steps, all on the user's side:

1. **Create the Teams channel webhook** and store the URL. Step by step in
   `references/teams-delivery.md`.
2. **Publish the repo to GitHub** — the routine clones
   `werner-denzin/claude-labs` on every run, so the skill has to be committed and
   pushed.
3. **Create the routine** with `/schedule`, pointing at an environment with
   **Network access = Custom or Full**. The `Default` environment is *Trusted* and
   blocks every news source (`403 host_not_allowed`). Cost, limits and details in
   `references/scheduling.md`.

Until then the skill runs manually: collection, triage and `--preview` all work
without a webhook; only the final POST needs the secret.

## Earlier blocker, resolved

The old handoff recorded the cloud environment at *Network access = Trusted*,
which prevented validating the feeds. In this session the network was open and
every feed was tested for real. **The same adjustment is still required on
whichever environment the routine uses** — it is the most likely cause of an
empty newsletter at 08:00.

The video that inspired the request (https://youtu.be/dHxMu6TGu88) is still
unread. It stopped being a blocker: the user specified both phases directly.

## Ideas left out of scope

- Reading the previous day's `reports/` entry to say what changed since
  yesterday.
- Brazilian regulatory sources (PL 2338, ANPD) once that agenda heats up.
- An LLM judge running the `type: judgment` evals over the published newsletter.
