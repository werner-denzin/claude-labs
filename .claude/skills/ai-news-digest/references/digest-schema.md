# `digest.json` schema

The file the triage step writes and `build_card.py` consumes. UTF-8 JSON.

```jsonc
{
  "date": "2026-09-03",              // required, ISO. The newsletter's day, not the collection's
  "window_hours": 24,                // window used for collection
  "generated_at": "2026-09-03T11:04:00-03:00",
  "headline": "One line, in English: what the story of the day was.",

  "cards": [                          // required, 1 to 15 items
    {
      "rank": 1,                      // editorial order within the temperature band
      "title": "NVIDIA acquires Hugging Face for $12.9 billion",
      "description": "3 to 5 lines (~200-400 chars). What happened, the number that matters, why the committee should care. In English -- unless the main source is a Brazilian one, in which case this card stays in Portuguese.",
      "temperature": "HIGH",          // HIGH | MEDIUM | LOW (ALTA/MEDIA/BAIXA accepted as aliases)
      "lens": "engineering",          // strategy (~6 of 15) | engineering (~4) | research (~3) | regulation (~2)
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
  "sources_failed": [                 // copy from items.json + the blocks from step 2
    { "name": "MarkTechPost", "error": "HTTP 403" }
  ],
  "stats": {
    "items_considered": 93,
    "sources_ok": 32,
    "sources_total": 35
  }
}
```

## Validation

`build_card.py` rejects the file and explains why when:

- `date` or `cards` is missing, or `cards` is empty;
- a card lacks `title`, `description`, `temperature`, `source_name` or `source_url`;
- `temperature` is not one of the accepted values;
- `source_url` does not start with `http`.

Run `build_card.py --in digest.json --preview` to read the newsletter as text
before generating the payload.

## Field notes

- `rank` is editorial ordering only. Temperature decides the final position:
  `build_card.py` groups HIGH, then MEDIUM, then LOW, and uses `rank` to break
  ties inside each band.
- `lens` renders on the card next to the temperature, exactly as you write it.
  Leave it empty if the item fits none of the four.
- `also_covered_by` comes from `items.json`, but it is editable: if you merged
  items the script did not (the typical case being English and Portuguese
  covering the same story), add them here.
