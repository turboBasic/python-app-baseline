# Verified facts — OpenRouter via the Anthropic Messages API

Empirical observations confirmed against the live OpenRouter API. **Do not re-derive these and do
not WebFetch to "check" them** — they were established by real calls, and the probe commands to
re-establish them are at the bottom of this file.

This file contains **no rules**. It is evidence that the normative document
(`../ai-instructions-application.md`) cites by fact number, and that
`build-terminal-coding-agent.prompt.md` cites per rung. Keep it that way: a rule belongs in the
application doc, an observation belongs here.

- **Facts 1–6 confirmed**: 2026-08-09
- **Facts 7–8 confirmed**: 2026-08-09
- **Endpoint**: `POST https://openrouter.ai/api/v1/messages`
- **Staleness risk**: Model IDs and `:free` tier availability rotate on OpenRouter's side. Re-probe before trusting facts 4, 7, or 8 after a long gap.

---

## 1. OpenRouter exposes an Anthropic-native Messages endpoint

`POST https://openrouter.ai/api/v1/messages`. It is NOT only the OpenAI-compatible
`/chat/completions` path.

## 2. The official `anthropic` Python SDK works against it directly

```python
anthropic.AsyncAnthropic(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],  # sent as x-api-key; OpenRouter accepts it
)
```

## 3. Verified working through that endpoint, for BOTH DeepSeek and Anthropic models

- non-streaming `messages.create`
- `stream=True` SSE (`message_start` / `content_block_start` / `content_block_delta` with
  `thinking_delta` + `text_delta` / `content_block_stop` / `message_delta` / `message_stop`)
- tool use: returns `stop_reason: "tool_use"` and a `tool_use` block with parsed `input`

## 4. Model IDs are namespaced on OpenRouter

A bare `claude-opus-5` will 404. Use:

| Purpose                    | OpenRouter model ID                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| Cheap+fast driver          | `deepseek/deepseek-v4-flash`                                                                             |
| DeepSeek pinned snapshot   | `deepseek/deepseek-v4-flash-0731`                                                                        |
| DeepSeek heavier tier      | `deepseek/deepseek-v4-pro`                                                                               |
| Anthropic flagship         | `anthropic/claude-opus-5`                                                                                |
| Anthropic balanced         | `anthropic/claude-sonnet-5`                                                                              |
| Anthropic cheap            | `anthropic/claude-haiku-4.5`                                                                             |
| Floating "latest" pointers | `~anthropic/claude-opus-latest`, `~anthropic/claude-sonnet-latest`, `~deepseek/deepseek-v4-flash-latest` |

## 5. DeepSeek V4 Flash always emits a leading `thinking` block

With `signature: ""`. Anthropic models via OpenRouter do not, unless asked.

## 6. `usage` carries OpenRouter extras

`cost`, `is_byok`, `cost_details`, `output_tokens_details.thinking_tokens`, and `provider`,
alongside the standard Anthropic fields. These are not in the SDK's typed `usage` — reading them
requires an untyped access.

## 7. `poolside/laguna-s-2.1:free` works over the same `/v1/messages` endpoint

Verified end to end at zero cost (`usage.cost: 0`, `is_byok: false`):

- tool use: returns `stop_reason: "tool_use"` and a `tool_use` block with parsed `input`.
  Tool-call IDs are OpenAI-style (`chatcmpl-tool-<hex>`), not `toolu_…` — never pattern-match on
  the ID format.
- a two-turn round trip works: replaying the `tool_use` block and answering with a `tool_result`
  block keyed by `tool_use_id` returns `stop_reason: "end_turn"`.
- `stream=True` SSE emits `message_start` / `content_block_start` / `content_block_delta` /
  `content_block_stop` / `message_delta` / `message_stop`.

## 8. `poolside/laguna-s-2.1:free` always emits a leading `thinking` block with `signature: ""`

Whether or not `thinking` is requested; passing `thinking: {"type": "adaptive"}` is accepted but
changes nothing. Its `thinking_tokens` can consume the entire `max_tokens` budget — a 600-token
cap yielded `thinking_tokens: 600`, a lone `thinking` block, and `stop_reason: "max_tokens"` with
no text block at all. Budget generously on this model, and treat "assistant turn with zero text
blocks" as a real case the loop must survive. Replaying such a block verbatim on a later turn
(empty `signature` included) is accepted.

---

## Known unverified

Do not assume these; probe before use, then add a numbered fact.

- Whether `cache_control` is **honored** on OpenRouter. The response carries
  `cache_read_input_tokens`, but a non-zero read across turns has not been demonstrated.
- Whether `output_config`/`effort`, `task_budget`, `betas=[...]`, or server-side tools are
  accepted on OpenRouter. All are first-party-confirmed only.

## How to re-probe

Key lives in 1Password. Resolve it with:

```bash
KEY=$(op read "op://Personal/ai.openrouter/api-key")
```

Then, for any fact, the minimal shape is:

```bash
curl -sS -w '\nHTTP %{http_code}\n' https://openrouter.ai/api/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "poolside/laguna-s-2.1:free",
    "max_tokens": 256,
    "messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}],
    "tools": [{
      "name": "get_weather",
      "description": "Get current weather for a city.",
      "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
      }
    }]
  }'
```

Vary `model` for fact 4, add `"stream": true` for the SSE event list, and append an assistant
`tool_use` block plus a user `tool_result` block for the two-turn round trip. Record whatever you
find — **including negative results** — as a numbered fact or a bullet under "Known unverified".
