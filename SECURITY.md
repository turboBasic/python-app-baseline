# Security policy

## What this repo is

A conventions baseline that people copy. It ships no service, is published to no package index, and
`src/python_app_baseline/` is a Typer CLI and a settings loader with no logic beyond proving the
rules hold. Almost nothing here runs in production anywhere; what spreads is the shape of it.

Two things are in scope, and the second matters more:

- **A vulnerability in `src/python_app_baseline/`** — a resolved secret reaching a log record or the
  terminal, the settings loader trusting input it should not, a log file landing somewhere it should
  not. A small surface, but it is copied verbatim into other repos.
- **A convention in [`docs/ai-instructions.md`](docs/ai-instructions.md) that leads a contributor
  somewhere unsafe** — a rule that invites credential leakage, a quality gate weak enough to wave
  something through, a dependency or pinned action that should not be trusted. This is the one worth
  hunting for: a weak default here propagates into every repo forked from this one.

There are no supported versions to list. `main` is the only thing maintained; if you forked, you own
your copy.

## Reporting

Use [private vulnerability reporting](https://github.com/turboBasic/python-app-baseline/security/advisories/new).
It is enabled on this repo and keeps the report unpublished while it is being looked at.

Do not open a public issue for something exploitable. For a convention you think is merely
ill-advised, a public issue is the right place — that is a design argument, not a disclosure.

Expect a reply within a week. This is a personal project, not a staffed product; if that is too slow
for what you found, say so in the report and disclose on your own timeline.

## Secrets

If you find a live credential committed anywhere in this repo's history, report it privately. Secrets
belong in the environment, injected at process start — see
[Secrets](docs/ai-instructions.md#secrets). `.env.template` holds `op://` references only, and every
example credential is a visible fake such as `sk-test-…`.

Push protection and secret scanning are on, so a recognised token format will be blocked at push
time. Neither catches everything.
