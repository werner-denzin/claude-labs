# Catalogo de fontes

Editar `assets/sources.json`. Cada entrada:

| Campo | Uso |
| --- | --- |
| `id` | Chave unica. Usada em `--only` e nos relatorios de falha. |
| `name` | Nome que aparece no cartao. |
| `feed` | RSS/Atom. `null` quando a fonte nao publica feed — ai a skill le o `site` com WebFetch. |
| `site` | Pagina humana. Fallback quando o feed morre e destino do WebFetch. |
| `lang` | `en` ou `pt-BR`. |
| `category` | `lab`, `infra`, `open-source`, `news`, `analysis`, `engineering`, `research`, `regulation`, `community`. |
| `weight` | 1-5. Desempata a triagem e escolhe o representante na deduplicacao. 5 = fonte primaria. |
| `topic_filter` | Opcional. `true` = fonte de tecnologia em geral; so passam itens que mencionem IA. |
| `max_items` | Opcional. Teto proprio, menor que o global. |
| `note` | Opcional. Por que a fonte esta assim. |

## Por que essas fontes

**Peso 5 — labs primarios.** OpenAI, Anthropic, DeepMind. O anuncio nasce aqui;
o resto do mundo cobre depois. Quando um item aparece no lab e na imprensa, o
card leva o link do lab.

**Peso 4 — imprensa forte e fontes de engenharia.** TechCrunch, The Verge, Ars
Technica, MIT Tech Review, Hugging Face, Latent Space, Simon Willison, Google/
Microsoft/Meta, EU AI Act. Trazem contexto e apuracao que o blog do lab omite.

**Peso 3 — cobertura ampla.** The Decoder, VentureBeat, WIRED, The Register,
InfoQ, NVIDIA, AWS, Mistral, Import AI, Raschka, Google Research, HN.

**Peso 2 — volume e mercado local.** arXiv, MIT News, e a imprensa brasileira
(Olhar Digital, TecMundo, Canaltech, Mobile Time). Raramente viram ALTA sozinhos,
mas sao o que da leitura do mercado local e do que chegou ao publico daqui.

As quatro lentes do comite (estrategia, regulacao, engenharia, pesquisa) estao
todas cobertas. `regulation` tem so o EU AI Act: se a pauta regulatoria brasileira
esquentar (PL 2338, ANPD), vale acrescentar fontes daqui.

## Fontes sem feed

Tres entradas tem `"feed": null` e por isso aparecem sempre em `sources_failed`
com "sem feed RSS declarado". Nao e defeito, e o catalogo dizendo para ler pelo
site:

| Fonte | Situacao em 2026-09-03 |
| --- | --- |
| Anthropic News | Nao publica RSS. `/rss.xml`, `/news/rss.xml`, `/feed.xml`, `/engineering/rss.xml` todos 404. |
| Meta AI Blog | `ai.meta.com` devolve 400 para qualquer caminho de feed. O feed de `engineering.fb.com` (ML Applications) esta no catalogo como `meta-engineering` e funciona. |
| MarkTechPost | O feed responde 403 mesmo com User-Agent de navegador (WAF). Fonte opcional. |

## Validar os feeds

Feeds mudam de endereco sem aviso — foi o que aconteceu com metade do catalogo
original. `fetch_feeds.py` reporta cada falha com o motivo:

```bash
python3 scripts/fetch_feeds.py --hours 168 --out /tmp/check.json
```

`HTTP 404` ou `410` = endereco mudou, procure o novo e corrija o JSON.
`HTTP 403` = WAF bloqueando; normalmente so resta o site.
`XML invalido` = a fonte devolveu uma pagina de erro em HTML.

Para testar uma fonte so: `--only techcrunch-ai`.

## Filtro de assunto

Fontes de tecnologia em geral entram com `"topic_filter": true`. Sem ele,
TecMundo e Canaltech ocupavam 25 vagas cada com celular, games e promocao — na
validacao, o filtro cortou 42 de 50 itens do Canaltech e 23 de 26 do TecMundo,
derrubando a coleta de 183 para 93 itens sem perder nada de IA.

A lista de termos esta em `TOPIC_RE`, no topo de `fetch_feeds.py`. Nome de modelo
novo que ainda nao esteja la (o mercado inventa um por mes) deve ser acrescentado.

## Deduplicacao

Duas camadas:

1. **URL canonica** — mesma URL sem rastreadores (`utm_*`, `fbclid`, ...) e um
   item so.
2. **Similaridade de titulo** — Jaccard sobre os tokens do titulo, sem
   stopwords e sem acento, acima de 0.60. O item de maior `weight` vira o
   representante; os outros entram em `also_covered_by`. Ajustavel com
   `--merge-threshold`.

O que o script **nao** funde, de proposito: titulos em idiomas diferentes.
"Nvidia buys Hugging Face" e "Nvidia anuncia compra da Hugging Face" tem
sobreposicao lexical baixa demais para qualquer limiar seguro. Esses pares saem
em `possible_duplicate_of` como pista, e a etapa de triagem decide. O campo tem
falsos positivos (um post sobre `llm-gemini` casa com toda noticia de Gemini) —
por isso e pista, nao veredito.
