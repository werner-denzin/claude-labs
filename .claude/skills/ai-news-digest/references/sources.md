# Source catalog

Edit `assets/sources.json`. Each entry:

| Field | Use |
| --- | --- |
| `id` | Unique key. Used by `--only` and in failure reports. |
| `name` | The name shown on the card. |
| `enabled` | `true` = read on every run. `false` = retired: kept in the file with its note and weight, skipped by the collector, and reported under `sources_disabled`. Absent means enabled. |
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

Thirty sources, in the two tiers the `_comment` in `sources.json` describes, plus
an engineering core that is the reason the radar exists.

**Engineering — twelve sources, the largest group.** The agenda EVOLV
development exercises: LangGraph and agent frameworks, harness engineering,
context engineering, prompt engineering, MCP, agent memory, guardrails, evals and
observability, tool use, and the coding agents themselves.

| Source | What it covers that nothing else does |
| --- | --- |
| Anthropic Engineering | Context engineering, harness design, agent skills, advanced tool use, Claude Code internals. About one post a month; each is worth a card. |
| LangChain Blog | LangGraph, LangSmith, MCP integration, agent memory. The only source on that stack. |
| Simon Willison | Daily practice with Claude Code, Codex and every new model. |
| Latent Space | Agentic coding, editorially — it stands in for the release feeds the sandbox blocks. |
| GitHub AI & ML, GitHub Changelog | Copilot practice and evaluation; platform and governance changes. |
| InfoQ AI/ML | Production practice: context engineering, prompt compression, agent architecture. |
| Hugging Face | Agent memory, structured outputs, evaluation, with runnable code. |
| Cursor, Zed, Sourcegraph | The agents' own shipping notes. |
| Martin Fowler | LLM practice for software teams. |

**Primary — chosen by the user.** The labs (OpenAI, Anthropic, DeepMind,
Google's Keyword blog), the people building them (Karpathy, Boris Cherny,
Thariq, Sam Altman, Andrew Ng's The Batch), the investors (a16z, Y Combinator,
Sequoia) and NVIDIA. The announcement is born here; when an item appears both at
the source and in the press, the card carries the source's link.

**Supporting press.** TechCrunch AI for funding and M&A, The Decoder for what
the founders say, Ars Technica AI for depth and for legal and policy. The
primary tier cannot report on itself.

**Research.** arXiv cs.SE, capped at 10 items a day.

### Why the engineering core was rebuilt

Measured on 2026-09-03 across the then-20 sources, over 30 days: **zero** items
on LangGraph or LangChain, one on MCP, one on context engineering, two on harness
engineering. 44 items in a month touched the agenda at all — 1.5 a day, against a
target of ten engineering cards a day.

Ten sources closed that gap, each validated live before being added. After the
change, 19 of 44 items in a 24h window are on the agenda. The cost is real and
was accepted deliberately: collection went from 20 sources to 30 and from ~39 to
~44 candidates a day, which is a larger triage context and a more expensive run.

### What this catalog still cannot see

**Coding agent releases.** GitHub `releases.atom` is the fastest, least mediated
signal there is, and the cloud sandbox returns 403 for every repo but the cloned
one. Cursor's changelog is the only agent shipping-notes feed reachable; Claude
Code, Cline, Codex and goose are covered only through Simon Willison, Latent
Space and the press.

**MCP itself.** The spec site publishes no feed at any conventional path. MCP
news arrives through LangChain, Anthropic Engineering and InfoQ.

**Regulation.** No source covers it directly. The EU AI Act, LGPD/ANPD and court
rulings reach the radar only through Ars Technica and TechCrunch.

**The local market.** No Brazilian source is in the catalog today, so the
Portuguese-language rule in `SKILL.md` is currently inert.

**The people.** Karpathy, Boris Cherny, Thariq and Sam Altman publish on X.
Measured over seven days, all four produced nothing.

## Weights

`weight` breaks ties in triage and picks the representative when two items
deduplicate into one.

**5 — the primary source of its own news.** OpenAI, Anthropic (news and
engineering), DeepMind, Simon Willison, and the three Claude Code people.

**4 — strong analysis and reporting.** Google's Keyword blog, Sam Altman, The
Batch, NVIDIA, TechCrunch AI, The Decoder, Ars Technica AI, Latent Space,
LangChain, GitHub AI, Cursor.

**3 — context and volume.** The three investor blogs, GitHub Changelog, InfoQ,
Hugging Face, Zed, Sourcegraph, Martin Fowler and arXiv cs.SE.

## Sources with no feed

Three ways to cover a source that publishes no RSS, best first.

**A sitemap with `<lastmod>`.** Many sites publish one even when they publish no
feed, and it carries exactly what the window filter needs: a URL and a date. Set
`sitemap` and leave `feed` null. Anthropic News, Anthropic Engineering, a16z, The
Batch and LangChain are read this way, which is why none of them appears in the
failure line any more.

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

And a sitemap can lie about what is new. LangChain's re-stamps `lastmod` on
every rebuild: 92 posts over 30 days carried only 23 distinct timestamps, with
one cluster of 21 posts sharing a single second. A 24h window can therefore fill
with posts from months ago. The entry limits the damage with `max_items: 4` and a
`topic_exclude` for newsletters and customer stories, and `SKILL.md` tells triage
to open a LangChain post before writing its card. A source that did this and had
no editorial step behind it would not be worth adding.

**WebFetch on the `site`.** Works, but costs a model call per source and returned
empty content for two sites in a cloud run. Use it when there is no sitemap.

**Drop the source.** A source that appears in the failure line every single day
trains the reader to ignore failure lines.

## Historical note: feedless sources

Some entries carry `"feed": null` because the source publishes no RSS at all.
Where a sitemap exists the collector uses it and the source behaves like any
other; where it does not, the entry shows up in `sources_failed` with "no RSS
feed declared", which is not a defect — it is the catalog telling you to read it
from the site. All three feedless entries in the catalog today have a sitemap, so
none of them reports a failure.

| Source | In the catalog | Situation as of 2026-09-03 |
| --- | --- | --- |
| Anthropic News | yes, `anthropic` | Publishes no RSS. `/rss.xml`, `/news/rss.xml`, `/feed.xml` and `/engineering/rss.xml` all 404. Read from `/sitemap.xml`, filtered to `/news/`. |
| Anthropic Engineering | yes, `anthropic-engineering` | Same site, same sitemap, filtered to `/engineering/` — 25 posts, roughly one a month, and the canonical source for context engineering and harness design. |
| LangChain | yes, `langchain` | Webflow site: `/rss/` and `/feed/` return the page itself. Read from `www.langchain.com/sitemap.xml`, filtered to `/blog/`. Its `lastmod` is bulk-stamped on a rebuild — see the caveat below. |
| a16z | yes, `a16z` | No working feed path. Read from its sitemap. |
| DeepLearning.AI | yes, `the-batch` | `/feed/`, `/rss.xml` and `/the-batch/rss.xml` all 404. Read from `/sitemap.xml`, excluding tag and issue pages. `andrewng.org` has neither feed nor sitemap, so Andrew Ng is covered here rather than as a source of his own. |
| Meta AI Blog | no, left in `deeec82` | `ai.meta.com` returned 400 for every feed path. `engineering.fb.com` (ML Applications) does publish one, if the source is ever wanted back. |
| MarkTechPost | no, never added | The feed returns 403 even with a browser User-Agent (WAF). |

## Validating the feeds

Feeds move without warning — which is what had happened to half the original
catalog. `fetch_feeds.py` reports each failure with its reason:

```bash
python3 scripts/fetch_feeds.py --hours 168 --out /tmp/check.json
```

`HTTP 404` or `410` = the address moved; find the new one and fix the JSON.
`invalid XML` = the source returned an HTML error page.

`HTTP 403` has two causes that look identical from the collector, so it now
reports which one it saw. `x-deny-reason: host_not_allowed` in the message means
the sandbox's network allowlist refused the host — add it to the environment
(`references/scheduling.md`). No `x-deny-reason` means the source itself refused
us. Without that distinction a dead source gets explained away as a policy block,
or a missing allowlist entry gets blamed on the source: the 2026-09-04 routine
run reported Karpathy's 403 as "expected — no fetchable feed" when the feed
answers `200` from a laptop.

## Not publishing the same story twice

The collector compares what it found against the newest file in `reports/` and
gives two different verdicts.

**Same canonical URL: dropped.** The committee has read that article. There is
no new information in serving it again, so it never reaches triage, and
`counts.items_already_published` records how many went.

**Similar title, different URL: flagged, never dropped.** A story that comes back
usually comes back because something changed — "NVIDIA agrees to acquire" becomes
"the deal closed" — and a mechanical drop would lose the part that matters. The
item arrives carrying `in_previous_report` with the matched title and a
similarity score, and triage decides. This follows the same principle as
cross-language deduplication: where a machine cannot tell repetition from
development, it hands the judgment over instead of guessing.

The threshold is `PREV_TITLE_THRESHOLD = 0.45`, looser than the 0.60 used to
merge two outlets covering the same hour, because a follow-up is written fresh
and shares fewer words. Measured against the 2026-09-03 edition: "Nvidia buys
Hugging Face, the GitHub of AI, for $13 billion" scores 0.5 against "NVIDIA
agrees to acquire Hugging Face for $12.93 billion", and "NVIDIA to Acquire
Hugging Face" scores 0.67.

**The anchor is the last report, not yesterday's.** If a run is skipped for a
holiday or a failure, the last edition the committee actually read may be three
days old, and that is the one not to repeat.

**Only the source lines count as published.** A URL that appears in the previous
report's `Left out` section was considered and rejected, which is not the same as
published — if it turns out to matter, it must still be collectable. The
regression test for that is in the eval suite.

## Retiring a source

Set `"enabled": false`. Do not delete the entry.

The entry carries the reasoning that took work to establish — why the feed is
read from a sitemap, which paths returned 404, what its volume was, why its
topic gate is shaped the way it is. Deleting it throws that away and the next
person re-derives it. Disabling keeps it as history, and turning the source back
on is one word rather than an afternoon.

The collector skips disabled sources, counts them in
`counts.sources_disabled`, and lists them under `sources_disabled` so a run's
`28/28` is never quietly a `28/30`. Two escape hatches: `--only <id>` reads a
named source whether or not it is enabled, which is how you test one you have
just disabled, and `--include-disabled` reads the whole file.

**What justifies disabling one.** The `Blocked / Unexpected Behaviors` section of
each archived report is the evidence: a source that appears there repeatedly is
the case for retirement. `grep -l "<source name>" reports/*.md` gives the
history. A single bad day is not a pattern — a transient DNS failure and a TLS
timeout both showed up in local runs on 2026-09-03 and both were gone on retry.

## How we identify ourselves

The collector sends `ai-news-digest/1.0 (+<repo url>; SiDi AI Radar feed reader)`
— a real name and a link an operator can follow to find out who is fetching.

It used to send a spoofed Chrome string, and that spoof was load-bearing:
`karpathy.bearblog.dev` answers `403` to a plain client and `200` to anything
that looks like a browser. Two things made the swap easy. Its `robots.txt` says
`User-agent: *` / `Allow: /` and disallows only `/hit`, `/upvote` and `/email` —
so the feed is explicitly permitted, and the UA filter is a blunt bot screen that
contradicts the site's own stated policy (it blocks `robots.txt` itself for
non-browser clients, so a crawler cannot read the rule that allows it). And it
costs nothing: measured on 2026-09-04, 30/30 sources answer with the honest
string, 135 items against 136.

What this project reads is public RSS and Atom that sites publish to be read, one
request per source per run, once a day, no authentication and no paywall. That is
feed consumption, not scraping. The line is at disguise: **if a source blocks
this user agent, it goes into the newsletter as a declared failure or it leaves
the catalog. Never a rotated IP, a spoofed UA, or a proxy to get around a block.**
A source that does not want to be read is entitled to that.

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

No `kind: release` source is in the catalog today: GitHub `releases.atom` is the
natural feed for a coding agent, and the cloud sandbox scopes GitHub access to
the cloned repository and returns 403 for every other repo. The machinery below
still runs and applies the day a release source is added from somewhere
reachable.

A `kind: release` source needs two things the others do not.

**Pre-release filtering.** GitHub releases feeds carry alpha, beta, rc, nightly,
snapshot, canary and internal staging tags alongside real versions. Measured on
2026-09-03, while those feeds were still in the catalog, that was 3 of 4 Zed
entries, 2 of 3 Codex entries, and the only Cline and goose entries in the
window. `PRERELEASE_RE` in `fetch_feeds.py` drops them
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
