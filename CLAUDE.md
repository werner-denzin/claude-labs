# claude-labs

Laboratorio de experimentos com Claude Code.

## Skill `ai-news-digest`

Radar diario de noticias de IA para o comite de estrategia de IA da SiDi:
coleta as ultimas 24h de ~35 fontes, classifica cada item por temperatura
(ALTA/MEDIA/BAIXA), seleciona os 15 mais relevantes e publica um boletim em
cards num canal do Teams.

- Skill: `.claude/skills/ai-news-digest/SKILL.md`
- Estado, decisoes e o que falta: `docs/HANDOFF-ai-news-digest.md`
- Boletins publicados: `reports/`

Regras que valem para qualquer mexida na skill:

- **A URL do webhook do Teams e credencial.** Nunca em arquivo do repositorio,
  em log, em commit ou em resposta ao usuario. Ela vive em `TEAMS_WEBHOOK_URL`
  (ou no arquivo apontado por `TEAMS_WEBHOOK_FILE`).
- **Os scripts usam so a biblioteca padrao do Python.** A VM nao tem `pip`, e o
  ambiente de nuvem pode nao ter. Nada de dependencia nova.
- **Fonte que falhou entra no boletim como falha declarada**, nunca como
  silencio. O leitor precisa saber que a coleta foi parcial.

## Preferencias do usuario

- Responder em portugues do Brasil.
- Relatorios e artefatos gerados tambem em portugues do Brasil, salvo pedido em
  contrario. O boletim do radar sai em pt-BR.

## Ditado por voz

O usuario costuma ditar as mensagens, entao aparecem erros de transcricao.
Interpretar pela intencao, sem pedir confirmacao para casos ja conhecidos:

| Transcrito | Significa |
| --- | --- |
| caras | cards |
| the teams | no Teams |

Ao encontrar um termo novo que claramente e erro de transcricao, resolver pelo
contexto e, se o usuario confirmar, acrescentar a esta tabela.
