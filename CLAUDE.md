# claude-labs

Laboratorio de experimentos com Claude Code. O trabalho em andamento e a skill
`ai-news-digest` — ver `docs/HANDOFF-ai-news-digest.md` para o desenho completo,
as decisoes já tomadas e o que falta implementar.

## Preferencias do usuario

- Responder em portugues do Brasil.
- Relatorios e artefatos gerados tambem em portugues do Brasil, salvo pedido em contrario.

## Ditado por voz

O usuario costuma ditar as mensagens, entao aparecem erros de transcricao.
Interpretar pela intencao, sem pedir confirmacao para casos ja conhecidos:

| Transcrito | Significa |
| --- | --- |
| caras | cards |
| the teams | no Teams |

Ao encontrar um termo novo que claramente e erro de transcricao, resolver pelo
contexto e, se o usuario confirmar, acrescentar a esta tabela.
