---
name: ai-news-digest
description: Radar diario de noticias de inteligencia artificial. Coleta as ultimas 24h de dezenas de fontes (labs, imprensa, regulacao, engenharia, pesquisa), classifica cada item por temperatura (ALTA/MEDIA/BAIXA), seleciona os 15 mais relevantes e publica um boletim em formato de cards num canal do Microsoft Teams. Use quando o pedido for "radar de IA", "newsletter de IA", "noticias de IA do dia", "digest de IA" ou quando uma routine agendada disparar o boletim diario.
---

# Radar de IA — boletim diario

Publico: o comite de estrategia de IA da SiDi. Eles leem o cartao no Teams em
menos de dois minutos, no comeco do dia, e precisam sair sabendo o que mudou e o
que exige decisao. Escreva para esse leitor.

O idioma padrao do boletim e portugues do Brasil. Titulos originais em ingles
podem ser mantidos quando traduzir prejudicaria a busca pelo nome do produto.

## Fluxo

### 1. Coletar

```bash
python3 .claude/skills/ai-news-digest/scripts/fetch_feeds.py \
  --hours 24 --out /tmp/items.json --pretty
```

Roda em poucos segundos, em paralelo. Ajuste `--hours` quando houver feriado ou
fim de semana no meio (segunda-feira costuma pedir `--hours 72`).

Leia o `items.json`. Ele traz, alem dos itens:

- `sources_failed` — fontes que nao responderam. **Vao para o relatorio**, nunca
  viram silencio.
- `sources_ok[].off_topic` — quantos itens uma fonte de tecnologia geral perdeu
  no filtro de assunto. Util para calibrar o catalogo.
- `possible_duplicate_of` — pares parecidos que o script **nao** fundiu. Sao
  pistas, nao veredito: e onde a mesma noticia em ingles e em portugues aparece.

### 2. Completar as fontes sem feed

Fontes com `"feed": null` no catalogo (Anthropic, Meta AI, MarkTechPost) so tem
site. Leia cada uma com WebFetch e pegue o que foi publicado na janela:

```
WebFetch(url=<site>, prompt="Liste os posts publicados nas ultimas 24h com titulo, data e URL. Se nenhum, diga 'nenhum'.")
```

Pule esta etapa se a rede do ambiente bloquear o dominio — e registre o bloqueio
em `sources_failed` do digest.

### 3. Triar e dar temperatura

Consolide primeiro: a mesma noticia em sete veiculos e **um** card, com a melhor
fonte como principal (prefira a fonte primaria — o blog do lab acima do noticiario
que o cobre) e as demais em `also_covered_by`. Use `possible_duplicate_of` e o
seu julgamento; o script nao funde titulos entre idiomas.

Depois classifique cada candidato pelas quatro lentes do comite:

| Lente | O que conta |
| --- | --- |
| **Estrategia** | Move decisao de plataforma, fornecedor, build-vs-buy ou custo: lancamento e deprecacao de modelo, preco, parceria, aquisicao, mudanca de licenca. |
| **Regulacao** | EU AI Act, LGPD/ANPD, NIST, decisao judicial, exigencia de compliance, incidente de seguranca. Tudo que o comite precisa levar para a mesa. |
| **Engenharia** | Ferramentas, frameworks, praticas de agentes e coding assistants — o que muda o dia a dia dos times da SiDi. |
| **Pesquisa** | Resultado de lab ou paper que ainda nao virou produto. Sinal antecipado. |

**Temperatura** e relevancia para esse comite, nao popularidade da noticia:

- **ALTA** — muda ou pressiona uma decisao nos proximos ~90 dias. Fornecedor que
  a SiDi usa mexeu em modelo, preco ou termos; regra com data de vigencia;
  aquisicao que reorganiza o mercado de ferramentas; vulnerabilidade em algo em
  producao. Se o leitor precisa agir ou avisar alguem, e ALTA.
- **MEDIA** — vale acompanhar, ainda nao força decisao. Lancamento de concorrente,
  benchmark relevante, movimento regulatorio em consulta publica.
- **BAIXA** — contexto e sinal antecipado. Paper sem produto, opiniao bem
  fundamentada, numero de mercado.

Calibragem: um dia normal tem **2 a 5 itens ALTA**. Se voce marcou dez, o criterio
afrouxou. Se marcou zero num dia com lancamento de modelo grande, apertou demais.

### 4. Selecionar os 15

Ordene por temperatura e, dentro dela, por impacto. Corte no 15.

Cubra as quatro lentes quando houver material — um boletim com quinze itens de
engenharia falha com o comite. Mas nao invente equilibrio: se o dia foi de
regulacao, o boletim e de regulacao.

### 5. Escrever o digest

Grave `digest.json` no formato de `references/digest-schema.md`. Regras de escrita:

- **Descricao: 3 a 5 linhas** (aprox. 200-400 caracteres). Diga o que aconteceu,
  o numero que importa e por que o comite deveria se importar. Uma frase de
  contexto vale mais que tres de narrativa.
- **Nunca invente.** Toda afirmacao tem que estar na fonte. Se a fonte diz
  "segundo pessoas a par do assunto", o card diz que e apuracao, nao fato.
- **Separe anuncio, disponibilidade e rumor.** "Anunciou" nao e "ja da para usar".
- **Sem linguagem de marketing.** Nada de "revolucionario", "game changer",
  "impressionante". Numeros e verbos.
- `headline`: uma linha dizendo qual foi a historia do dia.
- `not_relevant`: o que dominou o volume mas nao merece atencao. Dizer o que
  **nao** importa e parte do servico.
- `sources_failed`: copie de `items.json` e acrescente os bloqueios da etapa 2.

### 6. Montar e publicar o cartao

```bash
python3 .claude/skills/ai-news-digest/scripts/build_card.py --in digest.json --out card.json
python3 .claude/skills/ai-news-digest/scripts/post_to_teams.py --payload card.json --dry-run
python3 .claude/skills/ai-news-digest/scripts/post_to_teams.py --payload card.json
```

`build_card.py --preview` mostra o boletim em texto para conferencia antes de
publicar. Ele tambem corta os itens mais frios se o cartao passar do limite de
tamanho do Teams, entao nunca falhe o POST por tamanho.

`post_to_teams.py` le a URL do webhook de `TEAMS_WEBHOOK_URL` (ou do arquivo em
`TEAMS_WEBHOOK_FILE`). **A URL e credencial: nunca escreva ela em arquivo do
repositorio, em log ou na resposta ao usuario.** Ver `references/teams-delivery.md`.

Quando rodar sem webhook configurado, pare no `--dry-run`, mostre o `--preview` e
diga ao usuario o que falta.

### 7. Guardar o boletim

Grave a versao em markdown em `reports/AAAA-MM-DD-radar-ia.md` seguindo
`assets/report-template.md`. E o registro legivel do que foi publicado.

## Quando algo da errado

- **Muitas fontes falhando** (mais de um quarto): avise no comeco da resposta.
  Feed que muda de endereco e a causa mais comum — o endereco novo vai para
  `assets/sources.json`.
- **Poucos itens na janela** (menos de 15 depois da triagem): publique menos
  cards e diga que o dia foi fraco. Nao complete com ruido para chegar a 15.
- **Rede bloqueada** (`403`, `host_not_allowed`): o ambiente esta com acesso
  restrito. Ver `references/scheduling.md`.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `assets/sources.json` | Catalogo de fontes. Editar aqui para incluir, remover ou repesar. |
| `assets/report-template.md` | Estrutura do boletim em markdown. |
| `references/digest-schema.md` | Schema do `digest.json` que a etapa 5 escreve. |
| `references/sources.md` | Por que cada fonte esta na lista; como validar os feeds. |
| `references/teams-delivery.md` | Como criar o webhook do canal e o formato do payload. |
| `references/scheduling.md` | Agendamento diario as 08:00 BRT, nas tres opcoes. |
