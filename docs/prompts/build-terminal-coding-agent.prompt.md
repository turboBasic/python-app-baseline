# Build an agentic AI learning lab — a terminal coding agent on the Anthropic API

The task and the build order. The conventions this application is held to live in
[`../ai-instructions-application.md`](../ai-instructions-application.md); the platform conventions
underneath them live in [`../ai-instructions.md`](../ai-instructions.md). This file adds no rules of
its own — where it needs one, it points there.

---

## The task

Turn this repository — currently a bare Python application baseline — into a **terminal coding
agent**: a CLI that takes a task in natural language, runs a hand-rolled async tool-use loop
against the Anthropic Messages API, gives the model filesystem and shell tools behind an
interactive permission gate, and persists resumable sessions in SQLite.

Build it **one rung at a time**, in the order given in "Learning ladder". Each rung ships working
software and at least one `docs/api-notes.md` entry. **Stop and report after every rung** — do not
run ahead into the next one.

### Where to start

1. **Read [`prompts/openrouter-verified-facts.md`](openrouter-verified-facts.md) in full** — it is
   cited by fact number throughout, and it is not a reference for later. Then
   `../ai-instructions-application.md` end to end, then `../ai-instructions.md`.
2. **Rename the `python_app_baseline` placeholder** per README's "Instantiating" section. This is
   the first code change, before anything in the ladder; `src/<package>/` in the application doc's
   "Structure" section means the renamed package.
3. **Add the two mise tasks the application doc assumes**: `run` (launch the CLI) and `test-live`,
   alongside the existing `setup`, `fmt`, `lint`, `typecheck`, `test`, `ci`. Neither exists yet.
4. **Then rung 0.** Ask before starting if any of the above left a question open.

### Scope boundary

There is deliberately no overall "done" — the ladder is a stop-anywhere sequence and rung 6 is not
a finish line. The unit of completion is the rung, and I decide at each boundary whether to
continue, change direction, or stop. Rungs 0–2 make the agent genuinely usable; everything above
that is Anthropic API surface I want to reach through working code.

## Learning ladder — build in this order, stop anywhere

Each rung must leave the project **working, runnable, and useful on its own**, with lint,
typecheck, and tests green, and at least one `docs/api-notes.md` entry. Do not start a rung you
cannot finish — a half-implemented rung is worse than an absent one. Stop and report after each rung
rather than running ahead; I may want to stop, or change direction, at any boundary.

Every rung below states three things. **Depends on** lists what is *additionally* load-bearing for
that rung — re-read it before starting; a rung built without it will be subtly wrong even if it
runs. **Deliver** is the scope. **Done when** is the falsifiable check: if you cannot demonstrate
it, the rung is not finished, regardless of how much code exists.

**Both instruction documents govern every rung and are never repeated in a `Depends on` list.**
They are in force continuously — a `Depends on` field that omits them is not permission to ignore
them. If a rung's implementation would violate either to satisfy its own `Deliver`, the documents
win: stop and tell me, rather than working around the rule.

### Rung 0 — foundation

- **Depends on:** facts 1, 2, 4 · application doc → Backends and models · Structure · Reconciling
  with the platform doc
- **Deliver:** `models.py` registry, `providers/`, the `Settings` extensions the application doc
  describes, and a smoke script that hits first-party `claude-sonnet-5` and prints the response.
- **Done when:** the smoke script prints a real response on first-party `claude-sonnet-5`, and
  the same script prints one via `--backend openrouter` on the free model — both shown to me,
  before any loop code exists.

### Rung 1 — the loop, correct

Develop against the **free OpenRouter backend** so no credits go to mechanics. This is where
everything that is *not* Anthropic-specific gets settled; all of it is part of this rung, not a
follow-up.

- **Depends on:** facts 7, 8 · application doc → The tool-use loop — required behaviors (all of
  it) · Permission gate · Structure
- **Deliver:** `tools/` + permission gate with unit tests; `agent/loop.py` + `ui/`; `storage/`;
  `cli.py` extensions. Specifically:
  - Append the full `response.content` as the assistant turn; return **all** `tool_result` blocks
    for a turn in a **single** user message.
  - Execute independent tool calls concurrently with `asyncio.gather` — permission prompts still
    serialize, execution does not.
  - Configurable iteration cap (~25 default) with a clear surfaced message when hit.
  - `stop_reason` handled exhaustively: `end_turn`, `tool_use`, `max_tokens` distinctly, and
    `refusal`/unknown without crashing. Check `stop_reason` before touching `content[0]`.
  - Survive an assistant turn with zero text blocks (fact 8) — thinking-only turns are real.
  - A real system prompt: role, working directory, tool guidance.
- **Done when:** `"create hello.py that prints hi and run it"` completes end to end on both
  backends, prompting before the write and before the shell run; and mocked-provider tests cover
  plain reply, single tool call, parallel tool calls, tool error, max-iteration cap, and
  `max_tokens` truncation.

### Rung 2 — thinking blocks and multi-turn replay

First rung with live tests.

- **Depends on:** facts 5, 8 · application doc → the tool-use loop's `thinking` bullet (the replay
  rule is an API requirement, not a style choice) · its persistence rule specifically: blocks must
  round-trip losslessly, empty `signature` included
- **Deliver:** `--show-thinking` rendering (dimmed, hidden by default); persistence that
  round-trips thinking blocks byte-for-byte; the replay policy exercised across turns.
- **Done when:** a two-turn tool-use conversation replays stored thinking blocks without a 400,
  demonstrated live on both a Claude model and a thinking-emitting OpenRouter model, and the
  result — including what happens when blocks are replayed to a *different* model — is recorded
  in `api-notes.md`. Verify it; do not guess.

### Rung 3 — usage and cost accounting

- **Depends on:** fact 6 (OpenRouter extras are absent from the SDK's typed `usage` — reading
  them needs an untyped access)
- **Deliver:** read `usage` per turn, accumulate across the session, surface it in the UI.
  Include `cost` and `output_tokens_details.thinking_tokens` where present.
- **Done when:** a multi-turn session reports a running token total, and a cost figure on any
  backend that supplies one.

### Rung 4 — prompt caching

The main cost lever in an agent loop, and the rung where the prefix-match invariant gets learned
the hard way. First-party only.

- **Depends on:** facts file → "Known unverified" (whether OpenRouter honors `cache_control` is
  untested; if you probe it, record the result there) · **rung 3**, since the check below is a
  `usage` reading — attempting this rung first leaves you no way to tell whether it worked
- **Deliver:** `cache_control` placement on the system prompt and tool definitions.
- **Done when:** `cache_read_input_tokens` is demonstrably non-zero on a second turn — a zero
  reading means it is not working, however plausible the placement looks.

### Rung 5 — effort and task budgets

- **Depends on:** facts file → "Known unverified" — `effort` and `task_budget` are
  first-party-confirmed only, so both need a capability flag before use
- **Deliver:** `output_config.effort` exposed as `--effort`; `task_budget` for the agentic loop.
- **Done when:** the same task run at two effort levels shows a measured difference in tool-call
  count or turn length, recorded in `api-notes.md`.

### Rung 6 — long conversations

- **Depends on:** **rung 1**'s full-`response.content` rule (compaction requires appending the
  blocks, not just their text) · the platform doc's schema-versioning expectation, since this rung
  changes the persisted shape
- **Deliver:** compaction and/or context editing.
- **Done when:** a conversation long enough to trigger the mechanism continues coherently, with
  the returned compaction blocks preserved on the following turn.

## Acceptance criteria

Per rung: its own "Done when" check, plus lint, typecheck (pyright strict), tests green, and a
`docs/api-notes.md` entry — the same `mise run lint` / `mise run typecheck` / `mise run test`
commands already established by `mise.toml`.

On top of that, the application doc's **Standing invariants** must hold at the end of every rung
from rung 1 onward, not just once. Re-read them before declaring a rung done.

**Report honestly at the end of every rung:** what you verified by running versus what is
inferred or untested, which probes failed, and anything you left out. An unverified claim in
`docs/api-notes.md` is worse than no entry — this project's whole output is knowing what is
actually true.
