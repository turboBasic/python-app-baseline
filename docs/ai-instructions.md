# AI Instructions — Python platform conventions

Single source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

**Scope: this file is application-independent.** It describes the Python platform — tooling,
layout, typing, testing, logging, secrets — and says nothing about what this project *does*.
Application-level conventions belong in a separate document that references this one.

**This file is self-contained by design.** It does not depend on any user-level or global
instruction file, and deliberately restates rules that may also exist globally. Assume a clean
environment: a tool not named here is not available, and a rule not stated here is not in force.

## Tooling hierarchy

Run tools in this order of preference. Check for `mise.toml` before assuming anything.

1. **Project task runner** — if `mise.toml` defines a `lint`, `test`, `typecheck`, or `fmt` task,
   use it. Never bypass it with a raw tool invocation.
2. **Pre-commit** — for linting and formatting: `mise exec -- pre-commit run`.
3. **`uv run <tool>`** — for project-local Python tools (pytest, pyright, ruff).
4. **`mise exec -- <tool>`** — for system-level tools mise manages.
5. **Direct invocation** — only when none of the above apply.

Never `pip install`. Never activate a venv by hand — `uv run` and mise handle it.

## Tool version management — mise

`mise.toml` pins every runtime and CLI the project needs. Nothing is assumed to be installed
globally.

- Pin Python and uv explicitly. Add other CLIs (e.g. the 1Password CLI) as the project needs them.
- Use `[env]` with `_.python.venv = { path = ".venv", create = true }` so the venv is automatic.
- Define tasks for at least: `setup`, `fmt`, `lint`, `typecheck`, `test`, and `ci`
  (`ci` = `depends = ["lint", "typecheck", "test"]`).
- A task that needs secrets wraps its command in `op run --env-file=.env.template --`.

## Dependency management — uv

- `pyproject.toml` + `uv.lock`, both committed. No `setup.py`, `setup.cfg`, or `requirements.txt`.
- Runtime deps in `[project].dependencies`; dev deps in `[dependency-groups].dev`.
- `uv sync --locked` in setup and CI — never an unpinned resolve.
- Before adding a dependency, check whether something already in the tree covers the need.

## Project layout

```text
.
├── mise.toml                  # tool versions + dev tasks
├── pyproject.toml             # deps + ruff/pyright/pytest config
├── uv.lock
├── .env.template              # op:// secret references only
├── .editorconfig              # mandatory
├── .gitattributes             # LF normalization + binary types
├── .pre-commit-config.yaml
├── CLAUDE.md                  # pointer to docs/ai-instructions.md
├── .github/copilot-instructions.md   # pointer to the same
├── docs/ai-instructions.md    # this file
├── src/<package>/             # src layout, with __init__.py
└── tests/                     # mirrors src/
```

`src/<package>/` layout always — never a flat top-level package. Tests in `tests/` at the repo
root, mirroring the `src/` tree.

**Keep the tree above current** — update it in the same change that adds or removes a top-level
directory. When introducing a new file type, language, or framework, update `.editorconfig`,
`.gitattributes`, and `.gitignore` in the same change.

## Python language rules

Target the pinned Python version and use its features. No compatibility shims for older versions.

- `X | None`, never `typing.Optional`. Built-in `dict` / `list` / `tuple`, never `typing.Dict`
  and friends.
- **No `from __future__ import annotations`.** Modern Python does not need it.
- No `if TYPE_CHECKING:` guard unless genuinely required to break an import cycle.
- Full type hints on every function signature, including tests.
- `pathlib.Path` over `os.path`. `datetime.now(UTC)` over naive datetimes.
- Async-first where the project is async: don't put blocking I/O in an async path. Wrap
  unavoidable blocking calls in `asyncio.to_thread`.

## Linting and formatting — ruff via pre-commit

**Pre-commit is the linting entry point.** Never call `ruff` directly — go through
`mise exec -- pre-commit run` or the project's `lint` task.

- ruff for both lint and format. No black, isort, flake8, or pylint.
- Configure ruff in `pyproject.toml` (`[tool.ruff]`, `[tool.ruff.lint]`), not a separate file.
- Enable at minimum: `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `C4`, `RUF`. Add `ASYNC` for async
  projects.
- Set `known-first-party` so import sorting is stable.
- **Auto-fix hooks are expected.** When pre-commit reformats files, re-stage them and re-run —
  that is normal, not an error to investigate.
- Fix lint errors as they appear. Never defer them to a cleanup pass.

Also run `pre-commit` with the standard hygiene hooks: `trailing-whitespace`, `end-of-file-fixer`,
`check-yaml`, `check-toml`, `check-added-large-files`, `check-merge-conflict`.

## Type checking — pyright strict

`typeCheckingMode = "strict"` in `[tool.pyright]`, wired as a local pre-commit hook running
`uv run pyright`. Strict is mandatory, not preferred.

Set `venvPath = "."` and `venv = ".venv"` so pyright resolves the project environment.

**Untyped third-party libraries are the main hazard under strict mode.** A library without a
`py.typed` marker resolves to `Any`, and `Any` propagates silently — pyright reports **0 errors**
while giving you no checking at all. When adopting a dependency:

1. Check for a `py.typed` marker in the installed package.
2. If absent, look for a stubs package (`types-<name>`) and add it as a dev dependency.
3. If neither exists, do not let `Any` spread. Wrap the library in a narrow typed adapter at the
   boundary — a small module exposing explicitly annotated functions — and keep the untyped
   surface confined there.

Never add a blanket `# type: ignore` or loosen the global mode to make an error go away. Narrow
per-line ignores with a stated reason are acceptable at a library boundary; nowhere else.

## Data models and configuration

**Pydantic v2 for structured data.** Anything crossing a boundary — external API responses,
persisted rows, tool inputs and outputs — is a Pydantic model. Avoid bare dicts for anything
long-lived; a `dict[str, Any]` is a typing dead end.

**Configuration: state the choice explicitly in the project's own docs.** Two viable options,
with a real trade-off under pyright strict:

| | `pydantic-settings` | `dynaconf` |
|---|---|---|
| Static typing | Fields are declared and typed; pyright checks every access | `Dynaconf` has no `py.typed`; **every attribute access types as `Any`** |
| Validation | At startup, from the model | Manual, or none |
| Layered files / envs | Basic | Strong (multi-file, per-environment, merging) |
| Secrets | `SecretStr` prevents accidental logging | Plain values |

**Default to `pydantic-settings`** in a pyright-strict project: settings are read everywhere, so
`Any`-typed settings access erases type checking across the whole codebase. Verified with pyright
strict — `settings.some_key` on a `Dynaconf` instance reveals as `Any` and raises no error, so
a typo in a settings key is silently unchecked.

**If `dynaconf` is chosen** for its layered-environment features, contain the damage:

- Instantiate it in exactly one module and never import the `Dynaconf` object elsewhere.
- In that module, expose a frozen, fully annotated Pydantic model built from it, and validate at
  startup. Application code imports only that model.
- That module is the only place `Any` from `dynaconf` is permitted.

Either way, environment variables get a project-specific prefix, and secrets are never read from
a committed file.

## Secrets

**Secrets never live in files.** They are read from the environment, injected at process start.

- `.env.template` contains **only** `op://` references — never a real value. It is committed.
- Real `.env` files are git-ignored and never created with live credentials.
- Run anything needing secrets through `op run --env-file=.env.template -- <command>`, exposed as
  a mise task.
- Never write a literal credential anywhere, including tests and examples. Use obviously fake
  values such as `sk-test-…`.
- Wrap secret-valued settings in a type that resists accidental logging (e.g. `SecretStr`), and
  never log a resolved secret.

## Logging

Structured JSON logging to **stderr**, so log output never collides with program output on stdout.

- Configure a single formatter emitting one JSON object per line: timestamp (UTC, ISO 8601),
  level, logger name, message, plus any structured extras.
- Namespace loggers under the package name and set `propagate = False` on the package root to
  avoid duplicate records.
- Never `print()` for diagnostics. Never log secrets, tokens, or credentials.
- Configure logging once, at the entry point — never at import time in a library module.

## Testing

- pytest. No `unittest.TestCase` classes unless extending code that already uses them.
- `pytest-asyncio` for async projects, with `asyncio_mode = "auto"`.
- Config in `pyproject.toml` under `[tool.pytest.ini_options]`. Set `testpaths`.
- `tests/` mirrors `src/`. Type-annotate test functions like any other code.
- Tests that need network or real credentials are **marked and deselected by default** — declare
  the marker, add `addopts = ["-m", "not <marker>", "-ra"]`, and give them a separate task. Never
  let them run in the default suite or in CI.
- **Do not run the test suite after every edit.** Run it when asked, or when verifying a fix.
- If a test fails after a change, fix it before reporting the work done.

## Documentation and comments

- **No docstrings.** Not module-level, not class-level, not function-level. The sole exception is
  a framework that consumes the docstring as user-facing text — for example a CLI library that
  renders it as `--help`. Applies only where the docstring is functional, never as documentation.
- **Comments only where the WHY is non-obvious.** Never restate what the code does. Never leave a
  comment addressed to a reviewer rather than the next reader.
- No multi-line comment blocks.
- Match the surrounding code's comment density, naming, and idiom.
- Before adding a new doc, check for duplication. Prefer updating the single source of truth and
  linking to it over creating parallel content.

## Git conventions

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`.
- Commit or push only when asked. If on the default branch, create a branch first.
- Never commit a real secret, a lock-file conflict, or a generated cache directory.

## CI

- Pin action versions to a full SHA or an explicit tag — never `@main`.
- Use mise in CI so tool versions match local development.
- Keep workflows minimal: lint, typecheck, test. The `ci` mise task should reproduce CI locally.
- Secrets via CI environment secrets or OIDC — never hardcoded.

## AI behavior guidelines

- **Verify before assuming.** Read the file, run the tool, check the config. Do not guess at
  project structure or conventions.
- **Match existing patterns.** Read neighbouring files for style before writing new code.
  Consistency beats personal preference.
- **Scope to the request.** Do not refactor adjacent code, add features, or "improve" things that
  were not asked about.
- **Don't design for hypothetical requirements.** No abstraction whose only justification is a
  future need. No error handling for conditions that cannot occur.
- **When genuinely ambiguous, ask.** One clarifying question is cheaper than a wrong
  implementation. When a sensible default exists, take it and say so.
- **Report honestly.** Distinguish what was verified by running from what is inferred. If
  something was skipped or left broken, say so plainly.
