# `digest.json` schema

The file the triage step writes and `build_card.py` consumes. UTF-8 JSON.

```jsonc
{
  "date": "2026-09-03",              // required, ISO. The newsletter's day, not the collection's
  "window_hours": 24,                // window used for collection
  "generated_at": "2026-09-03T11:04:00-03:00",
  "headline": "One line, in English: what the story of the day was.",

  "cards": [                          // required, 1 to 20 items. All of them reach the report; the Teams card may show fewer
    {
      "rank": 1,                      // editorial order within the temperature band
      "title": "NVIDIA acquires Hugging Face for $12.9 billion",
      "label": "Acquisition",         // required, 1-2 words, max 24 chars. What kind of news this is
      "description": "3 to 5 lines (~200-400 chars). What happened, the number that matters, why the committee should care. In English -- unless the main source is a Brazilian one, in which case this card stays in Portuguese.",
      "temperature": "HIGH",          // HIGH | MEDIUM | LOW (ALTA/MEDIA/BAIXA accepted as aliases)
      "lens": "engineering",          // engineering (~10 of 20) | strategy (~5) | research (~3) | regulation (~2)
      "source_name": "NVIDIA Blog",   // main source: prefer the primary one
      "source_url": "https://blogs.nvidia.com/...",
      "also_covered_by": [            // optional; the card shows up to 3
        { "source": "TechCrunch AI", "url": "https://..." }
      ]
    }
  ],

  "not_relevant": [                   // optional, in English: what dominated the volume and does not deserve attention
    "consumer hardware launches"
  ],
  "anomalies": [                      // optional; feeds the report's "Blocked / Unexpected Behaviors" section
    { "source": "Andrej Karpathy",
      "detail": "HTTP 403 with no x-deny-reason header, so the source refused us rather than the sandbox. The feed answers 200 from a laptop, so this is cloud-egress filtering, not a dead feed." }
  ],
  "sources_failed": [                 // copy from items.json + the blocks from step 2
    { "name": "Sequoia Capital", "error": "HTTP 403" }
  ],
  "stats": {
    "items_considered": 44,
    "sources_ok": 30,
    "sources_total": 30
  }
}
```

## The label

One or two words, shown between the title and the description, naming what kind
of news the card carries: `Acquisition`, `Model launch`, `Security`, `Funding`,
`Regulation`, `Benchmark`, `Research`, `Pricing`, `Deprecation`, `Outage`,
`Partnership`, `Agent memory`. The list is a starting point, not an enumeration —
write the two words that fit the story.

It is not the `lens`. The lens says which committee interest the card serves and
comes from a fixed set of four; the label says what happened, and is free text.
A `strategy` card can be labelled `Acquisition` or `Funding` or `Pricing`, and
the reader learns something different from each.

Follow the card's language: an English card gets an English label, and a card
kept in Portuguese gets a Portuguese one. `build_card.py` renders it uppercase,
so capitalisation in the digest does not matter.

## Validation

`build_card.py` rejects the file and explains why when:

- `date` or `cards` is missing, or `cards` is empty;
- a card lacks `title`, `label`, `description`, `temperature`, `source_name` or
  `source_url`;
- `temperature` is not one of the accepted values;
- `label` is empty, runs past two words, or past 24 characters;
- `source_url` does not start with `http`.

Run `build_card.py --in digest.json --preview` to read the newsletter as text
before generating the payload.

## Field notes

- `rank` is editorial ordering only. Temperature decides the final position:
  `build_card.py` groups HIGH, then MEDIUM, then LOW, and uses `rank` to break
  ties inside each band.
- `lens` renders on the card next to the temperature, exactly as you write it.
  Leave it empty if the item fits none of the four.
- `label` renders under the title, uppercased. It is required and cannot be left
  empty: a card with nothing to categorise it is a card the reader has to open
  the description to place.
- `anomalies` is what a human reviews to decide whether a source should be
  disabled or removed. It is wider than `sources_failed`: a source that answered
  `200` and returned nothing it normally would, a sitemap re-stamping old posts
  as new, a feed that moved, a source whose entire output was dropped by the
  topic filter. `build_card.py` does not render it — the Teams card keeps its
  one-line failure summary, and the detail lives in the archived report where the
  decision gets made. Recurrence is the signal: `grep -l "<source name>"
  reports/*.md` shows whether today was an accident or a pattern.
- `also_covered_by` comes from `items.json`, but it is editable: if you merged
  items the script did not (the typical case being English and Portuguese
  covering the same story), add them here.
