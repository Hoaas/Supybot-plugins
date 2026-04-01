Allows use of the Mistral AI API with optional web search capabilities.

## Requirements

- `mistralai>=2` Python package (`pip install mistralai`)
- A Mistral API key from https://console.mistral.ai/

## Commands

- `mistral <text>` — Ask Mistral a question. Includes recent channel context.
- `mistralreload` — Reload the prompt template and update the agent's instructions in place. Use after changing `promptTemplate`.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `apiKey` | _(empty)_ | Your Mistral API key (required) |
| `model` | `mistral-medium-2505` | Model to use |
| `temperature` | `0.7` | Response randomness (0.0–1.0) |
| `maxResponseLength` | `400` | Max reply length in characters |
| `contextHistory` | `10` | Number of recent messages to include as context |
| `enableWebSearch` | `True` | Enable agent-based web search |
| `agentId` | _(empty)_ | Mistral agent ID. Set automatically on first run; you can also pin a specific agent here |
| `promptTemplate` | `small_channel` | Prompt template name (file in `prompts/`). Bundled: `small_channel`, `large_channel` |

## Language and reply style

When web search is enabled the plugin uses a Mistral agent. The agent's language
and personality are controlled entirely by its **system instructions**, which are
set from the prompt template at startup (or on `!mistralreload`).

To change the reply language, edit the prompt template file
(`Mistral/prompts/small_channel.txt`) to include an instruction such as:

```
Always reply in Norwegian.
```

Then run `!mistralreload` to push the updated instructions to the agent.

Alternatively, you can edit the agent's instructions directly in the
[Mistral console](https://console.mistral.ai/) and pin its ID via
`config supybot.plugins.Mistral.agentId`.

When web search is **disabled**, the plugin uses `chat.complete` directly with
the prompt template as the system message.
