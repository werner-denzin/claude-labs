# Handoff — construcao da skill `ai-news-digest`

Documento de contexto para uma sessao nova continuar o trabalho sem perder nada.
Escrito pela sessao https://claude.ai/code/session_01DurrNSDNuj5sHouP8cF7Z2

## Objetivo

Criar uma skill do Claude Code que:

1. Pesquisa os principais sites que publicam noticias do universo de inteligencia artificial.
2. Acessa essas fontes e compila as informacoes do periodo (por padrao, ultimas 24h).
3. Gera um relatorio sumarizado, em portugues do Brasil.
4. Publica esse relatorio num canal do Microsoft Teams via webhook.
5. Roda de forma agendada, todo dia as 08:00 (horario de Brasilia), para um grupo de pessoas receber.

## Decisoes ja tomadas com o usuario

| Tema | Decisao |
| --- | --- |
| Entrega no Teams | **Webhook do canal** (Power Automate "Workflows" ou Incoming Webhook legado). A skill faz POST e o relatorio aparece como cartao formatado. |
| Idioma do relatorio | Portugues do Brasil por padrao, configuravel. |
| Origem do pedido | O usuario mencionou um video do YouTube como inspiracao: https://youtu.be/dHxMu6TGu88 — **ainda nao lido**, ver bloqueio abaixo. |
| Branch de trabalho | `claude/ai-research-skill-xoqo0i` |

## Bloqueio encontrado (importante)

O ambiente de nuvem `Default` (env_014mPJj8EY5bSezXDZyE3bjn) esta com
**Network access = Trusted**, que libera apenas a allowlist padrao (registries de
pacote, GitHub, SDKs de cloud). Consequencia medida nesta sessao:

- `pypi.org` -> HTTP 200
- `youtu.be`, `www.youtube.com`, `techcrunch.com`, `www.anthropic.com` -> conexao cortada pelo proxy (`000` / `EGRESS_BLOCKED`)
- `WebFetch` falha para qualquer dominio fora da allowlist
- `WebSearch` **funciona**, porque passa pelos servidores da Anthropic e nao pela rede da sessao

Para liberar: claude.ai/code -> configuracoes do ambiente -> campo **Network access**
-> **Full**, ou **Custom** com os dominios das fontes mais `youtube.com` e `youtu.be`.
A mudanca vale para sessoes abertas depois dela.

### O que ainda falta por causa do bloqueio

- Ler o video https://youtu.be/dHxMu6TGu88 e conferir se ele sugere algo diferente do
  desenho abaixo (ferramentas, formato de relatorio, fontes especificas).
- Validar os endereços de RSS das fontes em `.claude/skills/ai-news-digest/assets/sources.json`
  contra a rede real. Feeds mudam de endereco; `fetch_feeds.py` foi feito para
  reportar os que falharam justamente para essa correcao.

## Desenho da skill (acordado, ainda nao implementado por inteiro)

```
.claude/skills/ai-news-digest/
├── SKILL.md                        # fluxo principal: coletar -> triar -> sumarizar -> publicar
├── assets/
│   ├── sources.json                # catalogo de fontes (feed, site, lang, categoria, peso)
│   ├── report-template.md          # estrutura fixa do relatorio
│   └── adaptive-card-template.json # cartao do Teams
├── scripts/
│   ├── fetch_feeds.py              # agregador RSS/Atom, stdlib apenas, paralelo,
│   │                               # janela de tempo, deduplicacao, reporta falhas
│   └── post_to_teams.py            # POST no webhook, le TEAMS_WEBHOOK_URL do ambiente,
│                                   # trata limite de tamanho do Teams, retry com backoff
├── references/
│   ├── sources.md                  # por que cada fonte esta na lista, como customizar
│   ├── teams-delivery.md           # como criar o webhook, formatos de payload
│   └── scheduling.md               # agendamento 08:00 BRT = 11:00 UTC
└── evals/evals.json                # casos de teste da skill
```

### Principios de qualidade que o SKILL.md deve carregar

- Nunca inventar. Toda afirmacao com link da fonte. Fonte que falhou entra no
  relatorio como falha declarada, nao como silencio.
- Deduplicar: a mesma noticia em cinco veiculos e **um** item, com a melhor fonte.
- Separar anuncio de disponibilidade real e de rumor.
- Sem linguagem de marketing. Um leitor de Teams passa os olhos: concisao importa.
- Dizer o que **nao** importa no dia, quando for o caso.

### Detalhes tecnicos definidos

- `08:00` no horario de Brasilia (UTC-3) = `11:00` UTC. Cron de dias uteis: `0 11 * * 1-5`.
- Segredo do webhook **nunca** no repositorio: `post_to_teams.py` le a variavel de
  ambiente `TEAMS_WEBHOOK_URL`.
- Webhook do Power Automate espera o envelope
  `{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{...}}]}`;
  o Incoming Webhook legado tambem aceita `{"text":"..."}`.
- Adaptive Card suporta markdown limitado em `TextBlock` (negrito, italico, links,
  listas) — sem tabelas e sem headings, entao titulos viram `TextBlock` com
  `size`/`weight`.
- Mensagem no Teams tem limite de tamanho na casa de dezenas de KB: truncar com
  aviso e link em vez de falhar.
- Os scripts usam apenas a biblioteca padrao do Python 3.11 (a VM tem 3.11.15),
  para nao depender de `pip install` em ambiente restrito.

## Estado do repositorio

- Repo: `werner-denzin/claude-labs`, estava vazio (nenhum commit) no inicio.
- Branch de desenvolvimento: `claude/ai-research-skill-xoqo0i`.
- Este handoff e o primeiro arquivo. A skill em si ainda nao foi escrita.

## Primeiro passo sugerido para a sessao nova

1. Confirmar se a rede esta liberada: `curl -sS -o /dev/null -w '%{http_code}\n' https://youtu.be`
2. Se liberada, ler o video e ajustar o desenho acima ao que ele propoe.
3. Implementar a skill conforme a arvore de arquivos, validando os feeds contra a rede real.
