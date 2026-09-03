# Source catalog

Edit `assets/sources.json`. Each entry:

| Field | Use |
| --- | --- |
| `id` | Unique key. Used by `--only` and in failure reports. |
| `name` | The name shown on the card. |
| `feed` | RSS/Atom. `null` when the source publishes no feed — then use `sitemap`, or fall back to reading `site` with WebFetch. |
| `sitemap` | Optional, for sources with no feed: `{"url": "...", "contains": "/news/"}`. The collector reads the sitemap, keeps URLs containing that substring, and dates them by `<lastmod>`. Add `"excludes": ["/tag/"]` to drop index pages that share the path. |
| `site` | Human-facing page. Fallback when the feed dies, and the WebFetch target. |
| `lang` | `en` or `pt-BR`. **Decides the card's language**: an item whose main source is `pt-BR` stays in Portuguese; the rest of the newsletter is English. |
| `category` | In use today: `lab`, `people`, `investor`, `hardware`, `press`, `engineering`, `research`. |
| `weight` | 1-5. Breaks ties in triage and picks the representative during deduplication. 5 = primary source. |
| `kind` | Optional. `release` = a version feed. Pre-releases are dropped automatically and triage folds a day's releases per tool into one card. |
| `topic_filter` | Optional. `true` = general source; only items matching the global `TOPIC_RE` get through. |
| `topic_terms` | Optional regex replacing `TOPIC_RE` for this source, when its vocabulary differs from the global one. Implies filtering. |
| `topic_exclude` | Optional regex dropping items even when they matched, for a source whose off-topic beat shares vocabulary with its on-topic one. |
| `prereleases` | Optional. `true` on a `release` source keeps alpha/beta/rc/nightly builds. Off by default. |
| `max_items` | Optional. Its own ceiling, lower than the global one. |
| `note` | Optional. Why the source is configured this way. |

## The catalog today

Twenty sources, in the two tiers the `_comment` in `sources.json` describes.
Fewer sources means a smaller triage context and a cheaper run, so every addition
has to earn its place against that cost.

**Primary — chosen by the user.** The labs (OpenAI, Anthropic, DeepMind, Google's
Keyword blog), the people building them (Karpathy, Boris Cherny, Thariq, Sam
Altman, Andrew Ng's The Batch), the investors (a16z, Y Combinator, Sequoia) and
NVIDIA. The announcement is born here; everyone else covers it afterwards, so
when an item appears both at the source and in the press, the card carries the
source's link.

**Supporting — because the primary tier cannot report on itself.** The labs
announce but do not analyse, the people mostly publish on X which has no
fetchable feed, and the VC firms blog about portfolio companies rather than
deals. So: TechCrunch AI for funding and M&A, The Decoder for what the founders
say, Ars Technica AI for depth and for legal and policy, Latent Space for
agentic coding, arXiv cs.SE for research an engineer could act on, and GitHub
Changelog for Copilot's enterprise controls and model deprecations.

### What this catalog cannot see

Worth knowing before you conclude a quiet day means a quiet market.

**Coding agents.** There is no release feed in the catalog. GitHub
`releases.atom` would be the fastest, least mediated signal there is — the notes
land before anyone writes about them — but the cloud sandbox scopes GitHub
access to the cloned repository and returns 403 for every other repo. Latent
Space and GitHub Changelog stand in for it, editorially and partially. The
`kind: release` machinery in `fetch_feeds.py` still works and is ready for the
day a coding agent is added from somewhere reachable.

**The people.** Karpathy, Boris Cherny, Thariq and Sam Altman publish on X.
Their blogs are real but rare — measured over a seven-day window, all four
produced nothing. Expect those categories empty most days and pick up what they
said through the press.

**Regulation.** No source covers it directly since the catalog was cut. The EU AI
Act, LGPD/ANPD and court rulings reach the radar only through Ars Technica and
TechCrunch. If the Brazilian regulatory agenda heats up (PL 2338, ANPD), that gap
has to be closed with local sources.

**The local market.** No Brazilian source is in the catalog today, so the
Portuguese-language rule in `SKILL.md` is currently inert — correct, and waiting
for a `pt-BR` source to return.

## Weights

`weight` breaks ties in triage and picks the representative when two items
deduplicate into one.

**5 — the primary source of its own news.** OpenAI, Anthropic, DeepMind, and the
three Claude Code people whose posts, when they come, are first-hand.

**4 — strong analysis and reporting.** Google's Keyword blog, Sam Altman, The
Batch, NVIDIA (blog and newsroom), TechCrunch AI, The Decoder, Ars Technica AI
and Latent Space. The Batch earns this tier: Andrew Ng's weekly letter is one of
the few places where someone with a practitioner's standing says what a week of
releases means, and DeepLearning.AI's roundup around it is written for engineers.

**3 — context and volume.** The three investor blogs, GitHub Changelog and arXiv
cs.SE. They rarely carry the day on their own, but they are the only window onto
deal flow, platform governance and research.

## Sources with no feed

Three ways to cover a source that publishes no RSS, best first.

**A sitemap with `<lastmod>`.** Many sites publish one even when they publish no
feed, and it carries exactly what the window filter needs: a URL and a date. Set
`sitemap` and leave `feed` null. Anthropic, a16z and The Batch are read this way,
which is why none of them appears in the failure line any more.

Three caveats. The title is derived from the URL slug, so
`/news/enterprise-frontier-safeguards` becomes "Enterprise frontier safeguards" —
close to the real headline but not it, and there is no summary at all. Triage
should read the page before writing a card. And `<lastmod>` usually carries a
date with no time, so those items would land at midnight and a post from
yesterday afternoon would fall outside a 24h window; the collector marks them
`date_only` and compares whole days instead.

And a sitemap mixes articles with index pages living under the same path, all
touched whenever an article is: `/the-batch/` covers 2298 articles but also 381
tag listings and 383 weekly roundups, and every one of them would have come out
as an item. `excludes` drops them by substring. For The Batch the roundup
(`/the-batch/issue-368`) is excluded on purpose and loses nothing — it only
collects the same week's stories, and Andrew Ng's letter has its own URL.

**WebFetch on the `site`.** Works, but costs a model call per source and returned
empty content for two sites in a cloud run. Use it when there is no sitemap.

**Drop the source.** A source that appears in the failure line every single day
trains the reader to ignore failure lines.

## Historical note: feedless sources

Some entries carry `"feed": null` because the source publishes no RSS at all.
Where a sitemap exists the collector uses it and the source behaves like any
other; where it does not, the entry shows up in `sources_failed` with "no RSS
feed declared", which is not a defect — it is the catalog telling you to read it
from the site:

| Source | Situation as of 2026-09-03 |
| --- | --- |
| Anthropic News | Publishes no RSS. `/rss.xml`, `/news/rss.xml`, `/feed.xml` and `/engineering/rss.xml` all 404. |
| Meta AI Blog | `ai.meta.com` returns 400 for every feed path. The `engineering.fb.com` feed (ML Applications) is in the catalog as `meta-engineering` and works. |
| MarkTechPost | The feed returns 403 even with a browser User-Agent (WAF). Optional source. |
| DeepLearning.AI | `/feed/`, `/rss.xml` and `/the-batch/rss.xml` all 404. Read via the sitemap as `the-batch`. `andrewng.org` has neither feed nor sitemap, so Andrew Ng is covered here rather than as a source of his own. |

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

General-tech sources are entered with `"topic_filter": true`: only items matching
the global `TOPIC_RE` get through. Three sources use the gate today — the two
NVIDIA feeds and GitHub Changelog — all of them beats that are mostly not about
AI. The measurement that justified the gate came from the Brazilian general-tech
press, since removed from the catalog: it cut 42 of 50 Canaltech items and 23 of
26 TecMundo items, taking a collection from 183 to 93 without losing any AI
coverage.

The term list lives in `TOPIC_RE`, at the top of `fetch_feeds.py`. It carries
Portuguese terms on purpose: no `pt-BR` source is in the catalog right now, but
the list has to keep working the day one returns. A new model name that is not
there yet (the market invents one a month) should be added.

**One global list does not fit every source**, and both sources using the gate
show a different failure direction.

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
