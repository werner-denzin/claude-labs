# Source catalog

Edit `assets/sources.json`. Each entry:

| Field | Use |
| --- | --- |
| `id` | Unique key. Used by `--only` and in failure reports. |
| `name` | The name shown on the card. |
| `feed` | RSS/Atom. `null` when the source publishes no feed — then use `sitemap`, or fall back to reading `site` with WebFetch. |
| `sitemap` | Optional, for sources with no feed: `{"url": "...", "contains": "/news/"}`. The collector reads the sitemap, keeps URLs containing that substring, and dates them by `<lastmod>`. |
| `site` | Human-facing page. Fallback when the feed dies, and the WebFetch target. |
| `lang` | `en` or `pt-BR`. **Decides the card's language**: an item whose main source is `pt-BR` stays in Portuguese; the rest of the newsletter is English. |
| `category` | `lab`, `infra`, `open-source`, `news`, `analysis`, `engineering`, `research`, `regulation`, `community`. |
| `weight` | 1-5. Breaks ties in triage and picks the representative during deduplication. 5 = primary source. |
| `kind` | Optional. `release` = a version feed. Pre-releases are dropped automatically and triage folds a day's releases per tool into one card. |
| `topic_filter` | Optional. `true` = general source; only items matching the global `TOPIC_RE` get through. |
| `topic_terms` | Optional regex replacing `TOPIC_RE` for this source, when its vocabulary differs from the global one. Implies filtering. |
| `topic_exclude` | Optional regex dropping items even when they matched, for a source whose off-topic beat shares vocabulary with its on-topic one. |
| `prereleases` | Optional. `true` on a `release` source keeps alpha/beta/rc/nightly builds. Off by default. |
| `max_items` | Optional. Its own ceiling, lower than the global one. |
| `note` | Optional. Why the source is configured this way. |

## The engineering core

The radar's focus is software engineering with AI, so the sources that matter
most are the quiet ones.

**Coding agents, via GitHub `releases.atom`.** Claude Code, Cline, Codex, Gemini
CLI, Continue, Zed, opencode and goose all publish a releases feed, and Cursor
publishes a real changelog feed. This is the fastest, least mediated signal there
is: the release notes land before anyone writes about them. It is also the
noisiest, which is what `kind: release` handles.

**Protocol and evaluation.** MCP spec, MCP servers and SWE-bench move slowly, but
a change in any of them reaches every tool downstream.

**Practice.** GitHub's AI blog and Changelog, Sourcegraph, JetBrains AI, Simon
Willison's `ai-assisted-programming` tag, Latent Space, InfoQ, the Pragmatic
Engineer and Martin Fowler.

**Research that an engineer could act on.** `arXiv cs.SE` rather than only cs.AI
and cs.CL — it is where agent harnesses, prompt engineering and repair show up.

These feeds publish far less than the AI press. On volume they lose every time,
which is exactly why the triage step has a target share instead of picking by
recency.

## Why these sources

**Weight 5 — primary labs and the agents themselves.** OpenAI, Anthropic,
DeepMind, plus Claude Code, Cline, Simon Willison's AI-assisted-programming tag
and Latent Space. The announcement is born here; everyone else covers it
afterwards. When an item appears both at the source and in the press, the card
carries the source's link.

**Weight 4 — strong press and engineering sources.** TechCrunch, The Verge, Ars
Technica, MIT Tech Review, Hugging Face, Latent Space, Simon Willison, Google/
Microsoft/Meta, EU AI Act. They bring context and reporting the lab's blog omits.

**Weight 3 — broad coverage.** The Decoder, VentureBeat, WIRED, The Register,
InfoQ, NVIDIA, AWS, Mistral, Import AI, Raschka, Google Research, HN.

**Weight 2 — volume and local market.** arXiv, MIT News, and the Brazilian press
(Olhar Digital, TecMundo, Canaltech, Mobile Time). They rarely reach HIGH on
their own, but they are what reads the local market and what actually reached the
audience here — and they are the only sources whose cards come out in Portuguese.

All four committee lenses (strategy, regulation, engineering, research) are
covered. `regulation` holds only the EU AI Act: if the Brazilian regulatory
agenda heats up (PL 2338, ANPD), it is worth adding local sources.

## Sources with no feed

Three ways to cover a source that publishes no RSS, best first.

**A sitemap with `<lastmod>`.** Many sites publish one even when they publish no
feed, and it carries exactly what the window filter needs: a URL and a date. Set
`sitemap` and leave `feed` null. Anthropic and a16z are read this way, which is
why neither appears in the failure line any more.

Two caveats. The title is derived from the URL slug, so
`/news/enterprise-frontier-safeguards` becomes "Enterprise frontier safeguards" —
close to the real headline but not it, and there is no summary at all. Triage
should read the page before writing a card. And `<lastmod>` usually carries a
date with no time, so those items would land at midnight and a post from
yesterday afternoon would fall outside a 24h window; the collector marks them
`date_only` and compares whole days instead.

**WebFetch on the `site`.** Works, but costs a model call per source and returned
empty content for two sites in a cloud run. Use it when there is no sitemap.

**Drop the source.** A source that appears in the failure line every single day
trains the reader to ignore failure lines.

## Historical note: feedless sources

Three entries carry `"feed": null` and therefore always show up in
`sources_failed` with "no RSS feed declared". That is not a defect — it is the
catalog telling you to read them from the site:

| Source | Situation as of 2026-09-03 |
| --- | --- |
| Anthropic News | Publishes no RSS. `/rss.xml`, `/news/rss.xml`, `/feed.xml` and `/engineering/rss.xml` all 404. |
| Meta AI Blog | `ai.meta.com` returns 400 for every feed path. The `engineering.fb.com` feed (ML Applications) is in the catalog as `meta-engineering` and works. |
| MarkTechPost | The feed returns 403 even with a browser User-Agent (WAF). Optional source. |

## Validating the feeds

Feeds move without warning — which is what had happened to half the original
catalog. `fetch_feeds.py` reports each failure with its reason:

```bash
python3 scripts/fetch_feeds.py --hours 168 --out /tmp/check.json
```

`HTTP 404` or `410` = the address moved; find the new one and fix the JSON.
`HTTP 403` = a WAF is blocking; usually only the site is left.
`invalid XML` = the source returned an HTML error page.

To test a single source: `--only techcrunch-ai`.

## Topic filter

General-tech sources are entered with `"topic_filter": true`. Without it,
TecMundo and Canaltech were taking 25 slots each with phones, games and retail
promos — in validation the filter cut 42 of 50 Canaltech items and 23 of 26
TecMundo items, taking the collection from 183 to 93 without losing any AI
coverage.

The term list lives in `TOPIC_RE`, at the top of `fetch_feeds.py`. It carries
Portuguese terms on purpose, since it has to match Brazilian sources. A new model
name that is not there yet (the market invents one a month) should be added.

**One global list does not fit every source**, and two cases in this catalog show
both failure directions.

*Too permissive.* `nvidia` is itself a topic term, so every post on NVIDIA's own
blog matched and the gate passed its entire gaming beat -- `'NBA 2K27' With
NVIDIA DLSS 5`, `Leading Publishers Bring Blockbuster PC Games`. Fixed with
`topic_exclude`, which drops GeForce NOW, DLSS, Gamescom and the rest.

*Too strict.* GitHub Changelog covers all of GitHub, and the global list rejected
`Enterprise-managed settings support any default model` -- a real Copilot
governance change that had already earned a card in a published newsletter. It
contains no global keyword. Fixed with `topic_terms`, a per-source vocabulary
that includes bare `model`, `agent` and `premium request`.

The lesson generalises: when a source's on-topic and off-topic output share
vocabulary, reach for `topic_exclude`; when its on-topic vocabulary is narrower
than the world's, reach for `topic_terms`.

## Release feeds

A `kind: release` source needs two things the others do not.

**Pre-release filtering.** GitHub releases feeds carry alpha, beta, rc, nightly,
snapshot, canary and internal staging tags alongside real versions. Measured on
2026-09-03, that was 3 of 4 Zed entries, 2 of 3 Codex entries, and the only Cline
and goose entries in the window. `PRERELEASE_RE` in `fetch_feeds.py` drops them
and counts them under `sources_ok[].prerelease`, so a tool that looks silent can
be told apart from one that only shipped betas.

**Consolidation.** A tool can ship several versions in a day. Triage folds them
into one card describing what changed, never one card per version. The script
does not merge them, because the release bodies differ and the judgment of what
matters across them is editorial.

## Deduplication

Two layers:

1. **Canonical URL** — the same URL minus trackers (`utm_*`, `fbclid`, ...) is a
   single item.
2. **Title similarity** — Jaccard over title tokens, minus stopwords and
   accents, above 0.60. The item with the highest `weight` becomes the
   representative; the others go into `also_covered_by`. Tunable with
   `--merge-threshold`.

What the script deliberately does **not** merge: titles in different languages.
"Nvidia buys Hugging Face" and "Nvidia anuncia compra da Hugging Face" overlap
too little lexically for any safe threshold. Those pairs come out in
`possible_duplicate_of` as a hint, and the triage step decides. The field has
false positives (a post about `llm-gemini` matches every Gemini story) — which is
why it is a hint, not a verdict.
