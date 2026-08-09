# Contributing

This repo is a conventions baseline. The deliverable is
[`docs/ai-instructions.md`](docs/ai-instructions.md); `src/app/` and `tests/` exist to prove those
rules hold. Forking it to suit your own conventions is an expected use — the
[MIT licence](LICENSE) asks nothing beyond keeping the notice.

Taking part means following the [Code of Conduct](CODE_OF_CONDUCT.md). Report anything exploitable
privately instead of opening an issue — see the [security policy](SECURITY.md).

## Read this first

[`docs/ai-instructions.md`](docs/ai-instructions.md) is the single source of truth and binds humans
and AI tools alike. This file does not repeat it.

Start with [Changes to these rules](docs/ai-instructions.md#changes-to-these-rules): it marks which
rules are non-negotiable and what to do when a change would trade one away. The rest covers
[tooling](docs/ai-instructions.md#tooling-hierarchy),
[dependencies](docs/ai-instructions.md#dependencies), [code](docs/ai-instructions.md#code),
[quality gates](docs/ai-instructions.md#quality-gates), and
[shipping](docs/ai-instructions.md#shipping).

## Setup

```sh
mise run setup   # uv sync --locked, then pre-commit install
```

One command; it wires up the `pre-commit` and `commit-msg` hooks together.

## The loop

```sh
mise run ci      # lint, typecheck, test — exactly what CI runs
```

`mise run lint`, `typecheck`, `test`, and `fmt` run the pieces while iterating.

## Pull requests

Branch first. Title the PR as a Conventional Commit — a squash merge takes its subject from there.
Both workflows must pass.

[The template](.github/PULL_REQUEST_TEMPLATE.md) asks why the change exists, what you verified
beyond `mise run ci`, and which docs moved with it. Agent-written code is welcome; you are still
the author of it.
