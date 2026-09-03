# Source catalog

Edit `assets/sources.json`. Each entry:

| Field | Use |
| --- | --- |
| `id` | Unique key. Used by `--only` and in failure reports. |
| `name` | The name shown on the card. |
| `feed` | RSS/Atom. `null` when the source publishes no feed — the skill then reads `site` with WebFetch. |
| `site` | Human-facing page. Fallback when the feed dies, and the WebFetch target. |
| `lang` | `en` or `pt-BR`. **Decides the card's language**: an item whose main source is `pt-BR` stays in Portuguese; the rest of the newsletter is English. |
| `category` | `lab`, `infra`, `open-source`, `news`, `analysis`, `engineering`, `research`, `regulation`, `community`. |
| `weight` | 1-5. Breaks ties in triage and picks the representative during deduplication. 5 = primary source. |
| `topic_filter` | Optional. `true` = general-tech source; only items mentioning AI get through. |
| `max_items` | Optional. Its own ceiling, lower than the global one. |
| `note` | Optional. Why the source is configured this way. |

## Why these sources

**Weight 5 — primary labs.** OpenAI, Anthropic, DeepMind. The announcement is
born here; everyone else covers it afterwards. When an item appears both at the
lab and in the press, the card carries the lab's link.

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

## Feedless sources

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
