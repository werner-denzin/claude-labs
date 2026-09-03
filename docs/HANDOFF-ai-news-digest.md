# Skill `ai-news-digest` — estado, decisoes e o que falta

Atualizado em 2026-09-03. Substitui o handoff da sessao
`session_01DurrNSDNuj5sHouP8cF7Z2`, que descrevia um desenho anterior.

## O que a skill faz

Boletim diario de IA para o comite de estrategia de IA da SiDi:

1. Coleta as ultimas 24h de ~35 fontes (labs, imprensa, regulacao, engenharia,
   pesquisa, imprensa brasileira).
2. Classifica cada item por **temperatura** — HIGH, MEDIUM ou LOW — medindo
   relevancia para o comite, nao popularidade da noticia.
3. Seleciona os **15 mais relevantes**.
4. Publica um **boletim em cards** (Adaptive Card) num canal do Teams, e guarda a
   versao markdown em `reports/`.

## Decisoes tomadas com o usuario

| Tema | Decisao |
| --- | --- |
| Formato de saida | **Cards, sem PDF.** O pedido original previa PDF; o usuario descartou depois de ver que o webhook do Teams nao anexa arquivo. O cartao carrega o boletim inteiro. |
| Entrega | Webhook de canal do Teams, criado pelo **Workflows** (Power Automate). O conector legado esta em descontinuacao. |
| Agendamento | **Routine agendada na nuvem** (`/schedule`), dias uteis as 08:00 BRT. Roda sem depender da maquina do usuario. |
| Idioma | **Boletim em ingles.** Excecao: cards cuja fonte principal e brasileira ficam em portugues. Decidido depois da primeira implementacao, que saia toda em pt-BR. |
| Lentes da triagem | As quatro: estrategia corporativa, regulacao/governanca, engenharia/agentic coding, pesquisa/papers. |
| Segredo | `TEAMS_WEBHOOK_URL` no ambiente; na nuvem, como **API credential**, nunca como variavel de ambiente. |
| Branch | `claude/ai-research-skill-xoqo0i` |

## Estado: implementado e testado

```
.claude/skills/ai-news-digest/
├── SKILL.md                        # fluxo, rubrica de temperatura, regras de escrita
├── assets/
│   ├── sources.json                # 35 fontes, validadas contra a rede
│   └── report-template.md
├── scripts/
│   ├── fetch_feeds.py              # agregador RSS/Atom paralelo, dedup, filtro de assunto
│   ├── build_card.py               # digest.json -> Adaptive Card, com corte por tamanho
│   └── post_to_teams.py            # POST no webhook, retry com backoff, redacao do segredo
├── references/
│   ├── digest-schema.md
│   ├── sources.md
│   ├── teams-delivery.md
│   └── scheduling.md
└── evals/
    ├── evals.json                  # 4 casos de script + 4 de julgamento editorial
    ├── run_script_evals.py         # executa os 4 de script
    └── fixtures/
```

Medido em 2026-09-03, contra a rede real:

- Coleta completa em ~3s. 32 de 35 feeds respondem.
- Janela de 24h: 93 itens depois do filtro de assunto e da deduplicacao.
- `run_script_evals.py`: 23 verificacoes, todas passando.

### Correcoes feitas no catalogo

Metade do catalogo original apontava para enderecos mortos. Corrigido contra a
rede: `microsoft-ai`, `mistral`, `google-ai`, `venturebeat-ai`, `tecmundo`,
`hn-ai`. Removido: `zdnet-ai` (404 em todos os caminhos). Sem feed publico, so
site: `anthropic`, `meta-ai`, `marktechpost`. Acrescentadas para cobrir as quatro
lentes: `eu-ai-act`, `latent-space`, `infoq-ai`, `google-research`,
`mit-news-ai`, `meta-engineering`, `mobile-time`.

### Filtro de assunto

Fontes de tecnologia em geral (`topic_filter: true`) enchiam a janela com
celular, games e promocao. Na validacao, o filtro cortou 42 de 50 itens do
Canaltech e 23 de 26 do TecMundo, derrubando a coleta de 183 para 93 itens sem
perder nada de IA.

## O que falta para o boletim rodar sozinho

Tres passos, todos do lado do usuario:

1. **Criar o webhook do canal no Teams** e guardar a URL. Passo a passo em
   `references/teams-delivery.md`.
2. **Publicar o repo no GitHub** — a routine clona `werner-denzin/claude-labs` a
   cada execucao, entao a skill precisa estar commitada e no remoto.
3. **Criar a routine** com `/schedule`, apontando para um ambiente com
   **Network access = Custom ou Full**. O ambiente `Default` e *Trusted* e
   bloqueia todas as fontes de noticia (`403 host_not_allowed`). Detalhes,
   custo e limites em `references/scheduling.md`.

Antes disso, a skill roda manualmente: a coleta, a triagem e o `--preview`
funcionam sem webhook; so o POST final precisa do segredo.

## Bloqueio anterior, resolvido

O handoff antigo registrava o ambiente de nuvem com *Network access = Trusted*,
o que impedia validar os feeds. Nesta sessao a rede estava liberada e todos os
feeds foram testados de verdade. **O mesmo ajuste continua necessario no
ambiente que a routine usar** — e a causa mais provavel de um boletim vazio as
08:00.

O video que inspirou o pedido (https://youtu.be/dHxMu6TGu88) continua sem ser
lido. Deixou de ser bloqueio: o usuario especificou as duas fases diretamente.

## Ideias que ficaram fora do escopo

- Ler o `reports/` do dia anterior para dizer o que mudou de ontem para hoje.
- Fontes regulatorias brasileiras (PL 2338, ANPD) quando a pauta esquentar.
- Juiz LLM rodando os evals de `type: judgment` sobre o boletim publicado.
