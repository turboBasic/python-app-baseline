# AI Instructions — application

Application conventions for this repository: an agentic AI learning lab, built as a terminal coding
agent against the Anthropic Messages API, with OpenRouter as an opt-in cheap/zero-cost backend.

This is the document [`ai-instructions.md`](ai-instructions.md) refers to when it scopes itself to
"the Python platform". That file is the platform doc; this one sits above it and adds only what is
specific to this application: the Anthropic/OpenRouter domain, the tool-use loop, the permission
gate, and the model registry. **Where a rule here duplicates or contradicts the platform doc, the
platform doc wins** — see "Reconciling with the platform doc" for the two points that need care.

Both documents are conventions, in force continuously. The build sequence that produced the
application is a separate, task-shaped document:
[`prompts/build-terminal-coding-agent.prompt.md`](prompts/build-terminal-coding-agent.prompt.md).
Read that one to know what is built and in what order; read this one to know the rules that hold
regardless.

**Companion file:** [`prompts/openrouter-verified-facts.md`](prompts/openrouter-verified-facts.md)
holds the live-API observations this file cites by fact number (confirmed 2026-08-09). This file is
normative — every rule lives here; that file is empirical and carries no rules.

**Status:** the application is not built yet. Until it is, "Structure" and the loop/gate sections
below describe the target these rules bind, not code that exists — the repository is still the bare
platform baseline.

---

## Goal — read this first, it governs every trade-off below

**This is a learning lab. Its product is my understanding of the Anthropic API, not the agent.**

The code is a means to that end and is expected to be rewritten several times. When a decision
trades implementation elegance against exposure to real Anthropic API mechanics, **exposure
wins** — even when that means more code, more branches, or a less tidy abstraction.

### What that implies concretely

- **First-party Anthropic is the reference path.** Default to `api.anthropic.com` with real
  model IDs and no `base_url` override, so that caching, `output_config.effort`, task budgets,
  beta headers, and server-side tools are all actually reachable. OpenRouter is an opt-in
  backend for cheap iteration, never the default.
- **Never hide a wire shape behind a neutral abstraction.** The loop works in the SDK's own
  content blocks. Do NOT invent a provider-neutral message model — a flattened assistant turn
  (`content: str` plus a separate `tool_calls` list) cannot represent `thinking` blocks,
  `cache_control`, or compaction blocks, and papering over that defeats the entire point of the
  project. This is the one place this project's Pydantic-everywhere rule (see the platform doc's
  "Data models" section) does not apply — see "Non-negotiable design decisions" for exactly what
  the abstraction is allowed to cover.
- **Capabilities are declared, not assumed.** Optional request parameters differ by model and by
  backend. A single set of "uniform params" sent everywhere is the bug class this project exists
  to understand — `temperature` alone is rejected outright on Opus 5 / Opus 4.8 / Opus 4.7 /
  Fable 5 and rejected non-default on Sonnet 5.
- **Verify against the live API; write down what you learn.** Behavior that cannot be confirmed
  from docs must be probed with a real call, and the finding recorded (see "Learning notes").

### Non-goals

Not building a product. Do not add multi-user support, a plugin system, config profiles,
telemetry backends, retry/fallback/multi-model routing, or any abstraction whose only
justification is a hypothetical future requirement.

### What is NOT negotiable despite this being a lab

Keep all of the following — each one is load-bearing *for the learning goal*, not ceremony. These
are additional to, not a replacement for, the non-negotiables already listed in
[`ai-instructions.md`](ai-instructions.md):

- **The permission gate.** It is the only thing between a model and my filesystem, and it is
  where tool-call interception is learned.
- **SQLite session persistence.** Resumable sessions are what make multi-turn thinking-block
  replay testable at all; without stored turns there is nothing to re-send.
- **The live opt-in test suite.** Several questions in this domain can only be settled against
  the real API. (This instantiates the platform doc's existing "tests needing network or real
  credentials are marked, deselected by default" rule — it is not a new rule.)

## Verified facts

`prompts/openrouter-verified-facts.md` holds eight numbered facts, confirmed against the live
OpenRouter API, that this file cites by number — the Anthropic-native Messages endpoint, the SDK
client shape, namespaced model IDs, and the tool-use / streaming / thinking-block behavior of the
free and cheap backends. It also lists what is **not** yet verified.

Do not re-derive those facts and do not WebFetch to "check" them. If a fact turns out to be
wrong, say so explicitly and record the correction there — do not silently work around it.

That file is evidence only; it contains no rules. Every rule lives here.

## Backends and models

Three backends, in priority order. **First-party is the default and the reference.**

| # | Backend | `base_url` | Key | Default model | Role |
|---|---|---|---|---|---|
| 1 | Anthropic first-party | *(none — SDK default)* | `ANTHROPIC_API_KEY` | `claude-sonnet-5` | **Default.** Reference path; the only one where every capability below is reachable. |
| 2 | OpenRouter — free tier | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `poolside/laguna-s-2.1:free` | Zero-cost tool-loop iteration: plumbing, permission-gate, and cap work. |
| 3 | OpenRouter — paid | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `deepseek/deepseek-v4-flash` | Cheap non-Anthropic model that reliably emits `thinking` blocks (see fact 5). |

`claude-sonnet-5` is the default because it reaches everything — adaptive thinking on by default,
the full `low`→`max` effort ladder, prompt caching, 1M context — at $3/$15 per MTok. Do NOT
default to Haiku 4.5: no `effort` parameter and 200K context puts several capabilities out of reach.

**Backend 2 is the zero-cost iteration path.** Anything that is pure plumbing (loop shape,
`stop_reason` handling, iteration cap, permission gate, tool errors) is developed against the free
model so no credits go to mechanics — facts 7–8 confirm it does tool use, multi-turn `tool_result`
round trips, and streaming over the Messages endpoint. Free `:free` variants are rate-limited and
rotate on OpenRouter's side — treat it as an experimentation backend, never as a default, and make
sure a rate-limit response surfaces as a clear error rather than a hang.

## Non-negotiable design decisions

- **No agent framework.** Hand-rolled async tool-use loop against the raw `anthropic` SDK.
  Do NOT introduce LangChain, LangGraph, Pydantic AI, CrewAI, AutoGen, or similar.
- **One SDK, one wire format.** Everything speaks the Anthropic Messages format. Do NOT add the
  `openai` package or an OpenAI-compatible code path. OpenRouter is reached as an
  Anthropic-compatible endpoint via `base_url`, nothing more.
- **The loop works in the SDK's content blocks — no neutral message model.** Append the full
  `response.content` back as the assistant turn and persist that shape. Do NOT define parallel
  Pydantic mirrors of `TextBlock` / `ThinkingBlock` / `ToolUseBlock`, and do NOT flatten an
  assistant turn to a text field plus a separate `tool_calls` list. Pydantic is still mandatory
  for everything that is genuinely mine (tool params, tool results, persisted row envelopes,
  the `Settings` extensions below) — just not as a re-encoding of the wire format.
- **Provider abstraction covers exactly two things: client construction and capability
  declaration.** Since all three backends speak Messages, there is no translation layer to
  write. A `Provider` supplies the configured `AsyncAnthropic` client plus a capability record
  (does this backend/model accept `cache_control`, `output_config.effort`, `task_budget`, beta
  headers, server-side tools, `thinking.display`?). The loop consults that record before adding
  an optional parameter. If you find yourself writing a `_to_provider_message()` function, the
  design has gone wrong — stop and re-read the Goal section.
- **Only `providers/*` imports `anthropic` for construction.** The loop receives a client; it
  never builds one and never reads config to decide which backend it is on. It may import
  `anthropic.types` for block types — that is the point of the previous two rules. This is the
  same shape as the platform doc's CLI/config/logging module boundaries — one more boundary in
  the same style, not a new pattern.
- **Model IDs never appear as literals outside the registry.** One module owns the tables from
  "Backends and models" above, with a `ModelSpec` per entry: id, backend, family, context
  window, max output, whether it's a floating alias, and the capability flags. Never branch on
  `"deepseek" in model_id` or `"claude" in model_id` scattered through the codebase — ask the
  registry. This module is where the `temperature` question below gets answered once.
- **`temperature` and other sampling params are per-model, not global.** `temperature`, `top_p`,
  and `top_k` are **rejected with a 400** on Opus 5 / Opus 4.8 / Opus 4.7 / Fable 5, and
  rejected when non-default on Sonnet 5. Never send them unconditionally. Either omit them
  entirely (preferred — steer with prompting) or gate them on a registry capability flag. A
  config field holding a default sampling value that is then always passed through is a bug, not
  a default.
- **Every filesystem write and every shell command passes through a permission gate** before
  executing. No tool bypasses it on a production path; only test fixtures may use a
  non-interactive auto-approve gate.

## Reconciling with the platform doc

Two places where a straight carry-over of agent-project conventions will contradict
[`ai-instructions.md`](ai-instructions.md). Resolve both in favor of the platform doc, per its own
precedence rule:

- **Config stays Dynaconf, not `pydantic-settings`.** The platform doc's config section is
  explicit and non-negotiable: `config.py` owns settings loading, nothing else
  constructs a `Dynaconf` instance. Extend the existing `Settings` model with the fields this
  application needs — backend keys, default model/backend, workdir, permission mode,
  `max_tokens`, iteration cap — rather than introducing a second settings mechanism. No global
  `temperature` field, per the design decision above.
- **Secret env vars go through the `ENV_PREFIX` prefix, not the SDK's own names.** The platform doc
  requires secrets to arrive as `ENV_PREFIX`-prefixed environment variables read by
  `load_settings()`, where the prefix derives from the package name.
  The Anthropic SDK's own convention (bare `ANTHROPIC_API_KEY`) is a default lookup, not a
  requirement — `AsyncAnthropic(api_key=...)` accepts an explicit value. So: `.env.template`
  declares `<PREFIX>_ANTHROPIC_API_KEY` and `<PREFIX>_OPENROUTER_API_KEY` as `op://` references; `Settings`
  exposes them as `SecretStr | None` fields; `providers/*` reads them from `Settings` and passes
  them explicitly to the client constructor. Never let the SDK do its own environment lookup — that
  routes a secret around the config boundary.

Do not duplicate the platform doc's Python-style, logging, CLI/Rich, testing, linting, or git
rules here — those already apply as written; this file only adds what they don't cover.

## Tech stack — additions on top of the platform doc

- **Models:** Pydantic v2 for tool params, tool results, and persisted row envelopes — per the
  platform doc's "Data models" rule, with the one exception above (no re-encoding of provider
  content blocks).
- **Persistence:** SQLite via `aiosqlite` — sessions + message history, resumable. Store
  assistant turns in a form that round-trips content blocks losslessly, including `thinking`
  blocks and their `signature` field (even when empty). The schema is versioned.
- **Tests:** unit tests mock the provider client. The live suite (see "What is NOT negotiable")
  is marked `@pytest.mark.live` and runs under the `mise run test-live` task.
- **Comments — where the platform doc's WHY-only exception is expected to fire in this project:**
  thinking-block replay rules, empty `signature` handling, `stop_reason` branches, `cache_control`
  placement, capability gating of optional params. One or two lines, stating the constraint and
  ideally the consequence of violating it. This is not a new comment rule — it names the spots in
  *this* application where the platform doc's existing "WHY is non-obvious" test is expected to be
  met.

Everything else — Python 3.14 style, `uv`/`mise` tooling hierarchy, Typer/Rich for the CLI,
structured JSON logging to stderr, ruff/pyright/pytest quality gates, Conventional Commits, CI —
is already established by [`ai-instructions.md`](ai-instructions.md) and
`mise.toml`/`.pre-commit-config.yaml` and is not repeated here.

## Structure

`src/<package>/` below is this repository's package — the platform doc's
[Application identity](ai-instructions.md#application-identity) section governs how it is named.

```text
src/<package>/
├── cli.py            # one-shot task + interactive REPL, --model, --backend,
│                     #   --show-thinking, --effort, --version
├── config.py         # Settings/load_settings: backend keys, default model, workdir,
│                     #   permission mode, max_tokens, iteration cap. NO global temperature.
├── models.py         # ModelSpec registry — the ONLY place model IDs are written; owns the
│                     #   capability flags the loop gates optional params on
├── providers/
│   ├── base.py       # Provider protocol: client construction + capability record. NOT a
│   │                 #   message translation layer.
│   ├── anthropic.py  # first-party AsyncAnthropic (default, no base_url)
│   ├── openrouter.py # AsyncAnthropic with base_url override (free + paid model sets)
│   └── registry.py   # name -> Provider; never branch on provider name elsewhere
├── agent/
│   ├── loop.py       # the hand-rolled tool-use loop
│   └── session.py    # conversation state (SDK content blocks), token + cost accounting
├── tools/
│   ├── base.py       # Tool protocol + JSON schema declaration
│   ├── permissions.py# the gate
│   ├── fs.py         # read_file, write_file, edit_file, glob, grep
│   └── shell.py      # run_command
├── storage/          # db.py + repository.py (lossless content-block round-trip, versioned)
└── ui/               # Rich console rendering for streamed output + thinking display
docs/api-notes.md     # running record of verified API behavior — a primary deliverable
tests/                # mirrors src/, plus tests/integration (live, opt-in)
```

There is deliberately no module for message or content-block models: conversation state holds
the SDK's content blocks directly, so there is nothing for such a module to contain.

## The tool-use loop — required behaviors

- Loop until `stop_reason == "end_turn"`; keep going while it is `"tool_use"`. Cap iterations
  (configurable, default ~25) and surface a clear message when the cap is hit.
- Append the **full `response.content`** back as the assistant turn — never just the extracted
  text. Return **all** `tool_result` blocks for a turn in a **single** user message, each with the
  matching `tool_use_id`.
- Execute independent tool calls **concurrently** (`asyncio.gather`), because a single assistant
  turn can contain multiple `tool_use` blocks.
- On tool failure, return a `tool_result` with `is_error: True` and a useful message. Never drop
  a `tool_result` — a missing one wedges the conversation.
- Parse `tool_use.input` as the already-decoded object the SDK gives you. Never string-match
  serialized JSON. Treat `tool_use.id` as an opaque token — never validate or pattern-match its
  format (fact 7: OpenRouter-proxied models return `chatcmpl-tool-…`, not `toolu_…`).
- An assistant turn can contain **zero text blocks** — thinking-only turns are real (fact 8).
  Never assume `content[0]` is text, and never derive the assistant turn by extracting text.
- Handle `stop_reason == "max_tokens"` distinctly from `"end_turn"`, and handle
  `"refusal"`/unknown values without crashing (check `stop_reason` before touching `content[0]`).
- **`thinking` blocks:** render them dimmed if the user passes `--show-thinking`, otherwise hide
  them. DeepSeek's have an empty `signature`. The replay rule is a hard API requirement, not a
  style choice: **thinking blocks must be echoed back unchanged when continuing on the same
  model** — read but never edit or reconstruct them; a modified block is rejected. Blocks replayed
  to a *different* model are dropped from the prompt rather than rendered. Empty-text blocks
  still get echoed verbatim.
- Stream by default. Use the SDK's stream context manager and `get_final_message()` so you get
  the accumulated message without hand-rolling event accumulation, while still rendering
  `text_delta`s live. Do NOT build an index-keyed dict accumulator over raw SSE events — if you
  are concatenating `partial_json` fragments by hand, you are reimplementing the SDK.
- Set `max_tokens` generously (streaming, so timeouts aren't the constraint) — ~16k, from config.
  Remember `max_tokens` caps **thinking plus response text together**: a value tuned for a
  thinking-off model will truncate mid-answer once thinking is on.
- **Never send an optional parameter a backend hasn't been verified to accept.** The portable core
  is `model`, `max_tokens`, `system`, `messages`, `tools`, `tool_choice`, `stream`. Anything
  beyond that is gated on a registry capability flag — check the facts file (numbered facts for
  what is confirmed, "Known unverified" for what is not), probe with curl if it is unlisted, set
  the flag, then use it. This is the mechanism, not a one-off: adding an ungated param anywhere
  is the bug class from the Goal section.
- Do NOT add retry/fallback/multi-model routing. Single model per session; the SDK's built-in
  retries are enough.

## Permission gate

Three modes from config/CLI: `ask` (interactive Rich prompt, default), `auto` (allow), `deny`.
Prompt shows the concrete action — for shell, the exact command; for writes, the path and a diff
for edits. Support "allow once" vs "allow for this session" per tool. Confine every filesystem
path to the configured working directory: resolve to canonical form and reject anything that
escapes it (`..`, symlinks, absolute paths outside root). Reject shell operator chaining unless
the user explicitly opted into it.

## Learning notes — `docs/api-notes.md`

Maintain `docs/api-notes.md` as a running record of what was actually learned. This file is a
**primary deliverable**, not documentation-after-the-fact.

Do not confuse it with the companion facts file: `prompts/openrouter-verified-facts.md` is an
**input** covering OpenRouter behavior already probed, and is not yours to rewrite (only to
correct, if you disprove a fact). `api-notes.md` is an **output** to grow — chiefly about
first-party Anthropic behavior, which the facts file does not cover.

Structure it as dated entries, newest first, each with:

- **Claim** — the behavior, in one line.
- **How verified** — live call / SDK source / docs, with the model and backend named.
- **Surprise** — what differed from what you expected going in. Omit if nothing did.
- **Open question** — what remains unknown, if anything.

Rules:

- Add an entry whenever a live call settles a question or contradicts an assumption.
- Record **negative** findings too: params rejected, endpoints that 404'd, blocks silently
  dropped. Those are the most valuable entries and the easiest to lose.
- Never write an entry claiming live verification for something that was not actually run.
  Mark inference as inference.

## Standing invariants

These hold at the end of every change, not just once:

- `mise run lint`, `mise run typecheck`, and `mise run test` all pass. Fix lint errors as they
  appear; do not defer them.
- An end-to-end agent run works on **both** backends with zero code changes between them. A change
  that breaks the cheap backend has regressed, even if its own check passes.
- `grep -rn "openai" src/` returns nothing.
- `grep -rn "claude-\|deepseek/\|poolside/" src/` returns hits only in `models.py`.
- No local mirror of a provider message or content-block type, and no function that translates
  between one and a provider message type.
- `grep -rn "temperature" src/` shows it either absent or gated on a registry capability flag —
  never unconditionally passed.
- `git grep -iE "sk-or-|sk-ant-"` finds nothing outside obviously-fake test values.
- Live suite stays **cheap and narrow**: small `max_tokens`, few calls, run manually via
  `mise run test-live`, never in CI, never in `mise run ci`.

**Report honestly:** what was verified by running versus what is inferred or untested, which probes
failed, and anything left out. An unverified claim in `docs/api-notes.md` is worse than no entry —
this project's whole output is knowing what is actually true.
