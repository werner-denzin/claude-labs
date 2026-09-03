# Delivery to Microsoft Teams

The newsletter goes to a Teams channel as an **Adaptive Card**, via webhook. No
file is attached: the card carries the whole newsletter.

## Creating the channel webhook

Microsoft retired the *Office 365 Connectors* (the old "Incoming Webhook"). The
current path is **Workflows**, the Power Automate built into Teams:

1. On the target channel, click the `...` next to the channel name.
2. **Workflows**.
3. Pick the template **"Post to a channel when a webhook request is received"**.
4. Confirm the account, the team and the channel. The flow is created.
5. Copy the generated **HTTP POST URL**. It is long and ends with a signature
   (`?api-version=...&sig=...`).

If your organization still has the legacy connector enabled, it works too and
accepts the same payload. It is not worth adopting a deprecated path for a new
workflow.

## Storing the URL

**The URL is the credential.** Whoever holds it can post to the channel. It never
goes into the repository, a log, a message, or a reply to the user.

Locally, to run the skill on your machine:

```bash
# in ~/.zshrc, or in a file outside the repo with mode 600
export TEAMS_WEBHOOK_URL='https://prod-XX.brazilsouth.logic.azure.com:443/workflows/...'
# alternative: point at a file containing only the URL
export TEAMS_WEBHOOK_FILE="$HOME/.config/sidi/teams-webhook"
```

In the cloud routine, do **not** use the Claude environment's environment-variable
field: the documentation states those are visible to anyone who uses that
environment. Store the URL as an **API credential** of the environment instead.
See `scheduling.md`.

## Payload format

The Workflows webhook expects the Teams message envelope:

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

`build_card.py` produces exactly that. `post_to_teams.py` rejects any other shape
before spending a network call.

## Limits the code already handles

| Limit | Handling |
| --- | --- |
| Messages above ~28 KB are rejected | `build_card.py` builds the card, measures its size **on the wire** (compact JSON) and drops the lowest-temperature items until it fits, with a footer note. `post_to_teams.py` refuses anything above 28 KB as a backstop. |
| `429` and `5xx` from Power Automate | Up to 4 attempts with exponential backoff, honouring `Retry-After`. |
| Network timeout | Same retry policy. |

## What the Adaptive Card accepts

`TextBlock` supports a reduced markdown: **bold**, _italic_, `[link](url)` and
lists. It does **not** support tables or headings — which is why the newsletter's
titles are `TextBlock`s with `size`/`weight` rather than `#`.

Emoji work and are what carries the temperature visually (🔴 🟠 🔵). The
`TextBlock` colour (`attention`, `warning`, `accent`) reinforces it, but some
Teams clients render it differently — which is why the textual label
(HIGH/MEDIUM/LOW) always travels alongside.

## Testing without publishing

```bash
python3 scripts/build_card.py --in digest.json --preview        # newsletter as text
python3 scripts/build_card.py --in digest.json --out card.json  # payload
python3 scripts/post_to_teams.py --payload card.json --dry-run  # validates, sends nothing
```

To see the card rendered before sending it to the channel, paste the contents of
`attachments[0].content` into <https://adaptivecards.io/designer/> (select the
"Microsoft Teams" host).
