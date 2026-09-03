# Schema do `digest.json`

Arquivo que a etapa de triagem escreve e que `build_card.py` consome. JSON UTF-8.

```jsonc
{
  "date": "2026-09-03",              // obrigatorio, ISO. Dia do boletim, nao da coleta
  "window_hours": 24,                // janela usada na coleta
  "generated_at": "2026-09-03T11:04:00-03:00",
  "headline": "One line, in English: what the story of the day was.",

  "cards": [                          // obrigatorio, 1 a 15 itens
    {
      "rank": 1,                      // ordem editorial dentro da temperatura
      "title": "NVIDIA acquires Hugging Face for $12.9 billion",
      "description": "3 to 5 lines (~200-400 chars). What happened, the number that matters, why the committee should care. In English -- unless the main source is a Brazilian one, in which case this card stays in Portuguese.",
      "temperature": "HIGH",          // HIGH | MEDIUM | LOW (aceita ALTA/MEDIA/BAIXA)
      "lens": "strategy",             // strategy | regulation | engineering | research
      "source_name": "NVIDIA Blog",   // fonte principal: prefira a primaria
      "source_url": "https://blogs.nvidia.com/...",
      "also_covered_by": [            // opcional; o cartao mostra ate 3
        { "source": "TechCrunch AI", "url": "https://..." }
      ]
    }
  ],

  "not_relevant": [                   // opcional, em ingles: o que dominou o volume e nao merece atencao
    "consumer hardware launches"
  ],
  "sources_failed": [                 // copiar de items.json + bloqueios da etapa 2
    { "name": "MarkTechPost", "error": "HTTP 403" }
  ],
  "stats": {
    "items_considered": 93,
    "sources_ok": 32,
    "sources_total": 35
  }
}
```

## Validacao

`build_card.py` recusa o arquivo e explica o motivo quando:

- falta `date` ou `cards`, ou `cards` esta vazio;
- algum card nao tem `title`, `description`, `temperature`, `source_name` ou `source_url`;
- `temperature` nao e um dos valores aceitos;
- `source_url` nao comeca com `http`.

Rode `build_card.py --in digest.json --preview` para ver o boletim em texto antes
de gerar o payload.

## Notas de campo

- `rank` e so ordenacao editorial. Quem decide a posicao final e a temperatura:
  `build_card.py` agrupa HIGH, depois MEDIUM, depois LOW, e usa `rank` para
  desempatar dentro de cada faixa.
- `lens` aparece no cartao ao lado da temperatura, literalmente como voce
  escrever. Deixe vazio se o item nao se encaixar em nenhuma das quatro.
- `also_covered_by` sai do `items.json`, mas cabe editar: se voce fundiu itens que
  o script nao fundiu (o caso tipico entre ingles e portugues), acrescente aqui.
