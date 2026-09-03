# Agendamento — dias uteis, 08:00 (horario de Brasilia)

Decisao tomada: **routine agendada na nuvem**. As outras duas receitas ficam
documentadas abaixo como alternativa.

## Opcao escolhida: routine na nuvem

Uma routine e uma configuracao salva do Claude Code (prompt + repositorios +
ambiente + conectores) que roda em infraestrutura da Anthropic, independente da
sua maquina.

### Custo

Routines consomem a assinatura do mesmo jeito que uma sessao interativa: mesmos
tokens, sem taxa de infraestrutura e sem cobranca por sessao. Existe, alem dos
limites normais de uso, um **teto diario de execucoes por conta** — o numero
aparece em <https://claude.ai/code/routines>. Uma execucao por dia util nao
chega perto de nenhum plano. Estourado o teto, as execucoes seguintes sao
recusadas ate a janela reabrir, a menos que a organizacao ligue *usage credits*,
que transforma o excedente em cobranca medida.

Disponivel em Pro, Max, Team e Enterprise. Exige login claude.ai — nao funciona
com API key do Console nem com Bedrock/Foundry.

### Criar

```
/schedule boletim diario do radar de IA, dias uteis as 8h
```

O Claude pergunta o resto e salva. Tambem da para criar em
<https://claude.ai/code/routines>. Depois: `/schedule list`, `/schedule update`,
`/schedule run`.

### Configuracao da routine

| Campo | Valor |
| --- | --- |
| Repositorio | `werner-denzin/claude-labs` — a skill precisa estar commitada, a routine clona o repo a cada execucao |
| Trigger | Schedule, preset **weekdays**, 08:00 |
| Fuso | **Nao converta nada.** O horario e informado no seu fuso local e convertido automaticamente; a routine roda as 08:00 de Brasilia. |
| Ambiente | Um com **Network access = Custom ou Full** (ver abaixo) |
| Conectores | Remova os que a routine nao usa — durante a execucao ela pode chamar qualquer ferramenta de um conector incluido, inclusive de escrita, sem pedir permissao |

Prompt da routine, algo como:

```
Execute a skill ai-news-digest para o dia de hoje: colete as ultimas 24h,
classifique por temperatura, selecione os 15 mais relevantes, monte o cartao e
publique no canal do Teams. Se o webhook nao estiver configurado, pare antes de
publicar e explique o que falta.
```

### Rede: o ponto que quebra se esquecido

O ambiente **Default** vem com *Network access = Trusted*, que libera so a
allowlist padrao (registries de pacote, APIs de cloud). Todas as fontes de
noticia ficam de fora: cada requisicao volta `403` com
`x-deny-reason: host_not_allowed` e o boletim sai vazio.

No ambiente da routine, mude **Network access** para **Full**, ou **Custom** com
os dominios de `assets/sources.json`. Para extrair a lista:

```bash
python3 -c "
import json,urllib.parse
s=json.load(open('.claude/skills/ai-news-digest/assets/sources.json'))['sources']
d={urllib.parse.urlsplit(u).netloc for x in s for u in (x.get('feed'),x.get('site')) if u}
print('\n'.join(sorted(d)))"
```

Acrescente tambem o dominio do webhook do Teams
(`*.logic.azure.com`, ou o host que a sua URL usar).

### Segredo do webhook

Variaveis de ambiente do ambiente de nuvem **ficam visiveis para qualquer pessoa
que use aquele ambiente**. Guarde a URL do webhook como **API credential** do
ambiente, nao como variavel de ambiente, e nunca no repositorio.

### Detalhes de operacao

- As execucoes podem comecar alguns minutos depois das 08:00: ha um *stagger*
  deliberado, constante para cada routine.
- Intervalo minimo entre execucoes: 1 hora.
- Status verde na lista significa que a sessao subiu e terminou sem erro de
  infraestrutura — **nao** que o boletim saiu. Abra a execucao e leia a
  transcricao. Requisicao bloqueada e falha de tarefa aparecem la, nao no status.
- A routine pertence a sua conta individual e nao e compartilhada com o time. O
  que ela publica sai como voce.
- Owner de Team/Enterprise pode desligar routines para toda a organizacao em
  `claude.ai/admin-settings/claude-code`. Se `/schedule` sumir, e o primeiro
  lugar para olhar.

## Alternativa A: timer local no WSL

Roda de graca, mas **so dispara com o WSL de pe as 08:00** — e o WSL nao sobe
sozinho com o Windows. Bom para teste manual, arriscado para producao.

`~/.config/systemd/user/radar-ia.service`:

```ini
[Unit]
Description=Radar de IA - boletim diario

[Service]
Type=oneshot
WorkingDirectory=%h/git/claude-labs
Environment=TEAMS_WEBHOOK_FILE=%h/.config/sidi/teams-webhook
ExecStart=/usr/bin/claude -p "Execute a skill ai-news-digest e publique o boletim de hoje no Teams."
```

`~/.config/systemd/user/radar-ia.timer`:

```ini
[Unit]
Description=Radar de IA as 08:00 nos dias uteis

[Timer]
OnCalendar=Mon..Fri 08:00 America/Sao_Paulo
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now radar-ia.timer
systemctl --user list-timers radar-ia.timer
loginctl enable-linger "$USER"   # para o timer sobreviver ao logout
```

Com `cron` em vez de systemd, o equivalente e `0 8 * * 1-5` — mas ai o fuso e o
do sistema, entao confira com `timedatectl`.

## Alternativa B: GitHub Actions

Sempre roda, log versionado. Duas ressalvas: o cron do Actions e **em UTC**
(08:00 BRT = `0 11 * * 1-5`, e o Brasil nao tem mais horario de verao desde 2019,
entao a conversao e fixa), e o Actions nao tem o Claude interativo — a triagem
teria que ir por API com uma `ANTHROPIC_API_KEY` nos secrets, ou o boletim sai
sem curadoria. O `TEAMS_WEBHOOK_URL` entra em *Repository secrets*.

```yaml
on:
  schedule:
    - cron: "0 11 * * 1-5"   # 08:00 America/Sao_Paulo
  workflow_dispatch:
```

Vale a pena so se voce ja quiser tirar a assinatura do caminho critico.
