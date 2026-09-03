# Entrega no Microsoft Teams

O boletim vai para um canal do Teams como **Adaptive Card**, via webhook. Nenhum
arquivo e anexado: o cartao carrega o boletim inteiro.

## Criar o webhook do canal

A Microsoft aposentou os *Office 365 Connectors* (o antigo "Incoming Webhook").
O caminho atual e o **Workflows**, que e o Power Automate embutido no Teams:

1. No canal de destino, clique nos `...` ao lado do nome do canal.
2. **Workflows** (ou **Fluxos de trabalho**).
3. Escolha o modelo **"Post to a channel when a webhook request is received"**
   ("Publicar em um canal quando uma solicitacao de webhook for recebida").
4. Confirme a conta, o time e o canal. O fluxo e criado.
5. Copie a **URL HTTP POST** gerada. Ela e longa e termina com uma assinatura
   (`?api-version=...&sig=...`).

Se a sua organizacao ainda tiver o conector legado habilitado, ele tambem
funciona e aceita o mesmo payload. Nao vale a pena adotar um caminho em
descontinuacao para um fluxo novo.

## Guardar a URL

**A URL e a credencial.** Quem a tem publica no canal. Ela nunca entra no
repositorio, em log, em mensagem ou em resposta ao usuario.

Local, para rodar a skill na sua maquina:

```bash
# no ~/.zshrc, ou num arquivo fora do repo com permissao 600
export TEAMS_WEBHOOK_URL='https://prod-XX.brazilsouth.logic.azure.com:443/workflows/...'
# alternativa: apontar para um arquivo que contem so a URL
export TEAMS_WEBHOOK_FILE="$HOME/.config/sidi/teams-webhook"
```

Na routine da nuvem, **nao** use o campo de variaveis de ambiente do ambiente
Claude: a documentacao diz que elas ficam visiveis para qualquer pessoa que use
aquele ambiente. Guarde a URL como **API credential** do ambiente. Ver
`scheduling.md`.

## Formato do payload

O webhook do Workflows espera o envelope de mensagem do Teams:

```json
{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": { "type": "AdaptiveCard", "version": "1.4", "body": [] }
    }
  ]
}
```

`build_card.py` produz exatamente isso. `post_to_teams.py` recusa qualquer outra
forma antes de gastar uma chamada de rede.

## Limites que o codigo ja trata

| Limite | Tratamento |
| --- | --- |
| Mensagem acima de ~28 KB e recusada | `build_card.py` monta o cartao, mede o tamanho **na rede** (JSON compacto) e vai cortando os itens de menor temperatura ate caber, com um aviso no rodape. `post_to_teams.py` recusa acima de 28 KB por garantia. |
| `429` e `5xx` do Power Automate | Ate 4 tentativas com backoff exponencial, respeitando `Retry-After`. |
| Timeout de rede | Mesma politica de retry. |

## O que o Adaptive Card aceita

`TextBlock` suporta um markdown reduzido: **negrito**, _italico_, `[link](url)` e
listas. **Nao** suporta tabelas nem headings — por isso os titulos do boletim sao
`TextBlock` com `size`/`weight`, e nao `#`.

Emoji funcionam e sao o que carrega a temperatura visualmente (🔴 🟠 🔵). A cor do
`TextBlock` (`attention`, `warning`, `accent`) reforca, mas alguns clientes do
Teams a renderizam de forma diferente — por isso o rotulo textual (ALTA/MEDIA/
BAIXA) sempre acompanha.

## Testar sem publicar

```bash
python3 scripts/build_card.py --in digest.json --preview        # boletim em texto
python3 scripts/build_card.py --in digest.json --out card.json  # payload
python3 scripts/post_to_teams.py --payload card.json --dry-run  # valida, nao envia
```

Para ver o cartao renderizado antes de mandar para o canal, cole o conteudo de
`attachments[0].content` em <https://adaptivecards.io/designer/> (selecione o host
"Microsoft Teams").
