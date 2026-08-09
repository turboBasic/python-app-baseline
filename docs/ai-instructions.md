# AI Instructions — Python platform conventions

Single source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

Scope: the Python platform. Application conventions live in a separate document that references
this one.

Committed configuration is authoritative for settings it already declares — read
`mise.toml`, `pyproject.toml`, `.pre-commit-config.yaml`, and `settings.toml` rather than assuming.
Extend those files; never regenerate them.

## Working style

- Read the file, run the tool, check the config rather than guessing at structure or conventions.
- Ask when genuinely ambiguous; take the sensible default otherwise and say so.
- Match existing patterns over personal preference.
- Scope to the request. No refactoring adjacent code or improving what was not asked about.

### Changes to these rules

A rule is **non-negotiable** when breaking it is irreversible, weakens security, or erases a
module boundary — leaked or committed credentials, `Dynaconf` outside `config.py`, `asyncio.run`
below the CLI layer, a blanket `# type: ignore` or a loosened tool mode, a bare dict crossing a
boundary, regenerating committed config, an unpinned CI action, `unittest.TestCase`. Everything
else here is a convention: follow it, but a request to change it is just a request.

Treat a change to a non-negotiable as a design change, not a task. Before implementing one, in a
short paragraph: name the rule, state concretely what breaks without it, and offer the smallest
alternative that still meets the underlying need. Then stop and wait.

- **Report the conflict even when it is incidental.** A change that erodes one of these as a side
  effect gets the same treatment as a request to drop it outright. Drift is how they are actually
  lost.
- **Once the objection is heard and the request restated, implement it fully.** Do not relitigate,
  hedge the implementation, or leave the old path in place as a safety net.
- **Never weaken one silently** to make a task easier — not by loosening a tool setting, not by
  adding a blanket ignore, not by routing around a boundary.
- Do not object over conventions: line length, naming, file placement, or how a test is organised
  inside the pytest idiom.

## Environment

### Tooling hierarchy

1. **Project task** — a `mise.toml` task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **Pre-commit** — `mise exec -- pre-commit run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages.

Never `pip install`. Never activate a venv by hand. Nothing is installed globally: a new runtime or
CLI is pinned in `mise.toml`. A task needing secrets wraps its command in
`op run --env-file=.env.template --`.

### Dependencies

- Runtime deps in `[project].dependencies`, dev deps in `[dependency-groups].dev`. No `setup.py`,
  `setup.cfg`, or `requirements.txt`.
- Run `uv lock` after editing dependencies and commit the result in the same change.
- Before adding a dependency, check whether one already in the tree covers the need.
- Renaming the package changes `[project].name`, `[project.scripts]`, `known-first-party`, and the
  wheel `packages` entry together, plus the `from app …` import lines. Nothing else in `src/` or
  `tests/`: see **Application identity** below.
- Introducing a new file type or framework updates `.editorconfig`, `.gitattributes`, and
  `.gitignore` in the same change.

## Code

### Python

Python 3.14. No compatibility shims or version guards for earlier releases.

- `X | None`, not `typing.Optional`. Built-in `dict`/`list`/`tuple`, not `typing.Dict`.
- No `from __future__ import annotations`.
- No `if TYPE_CHECKING:` guard except to break an import cycle.
- Full type hints on every signature, tests included.
- No blocking I/O in an async path; wrap unavoidable blocking calls in `asyncio.to_thread`.

### Application identity

`APP_NAME` in `src/app/__init__.py` is the package's own import name, and it is the single source
for every place the application names itself. Never write the name as a literal in `src/` or
`tests/` — derive it:

| Need | Source |
| --- | --- |
| Version from installed metadata | `version(APP_NAME)` |
| Logger namespace | `logging.getLogger(APP_NAME)` |
| Log file and platform log directory | `f"{APP_NAME}.log"`, `user_log_dir(APP_NAME)` |
| Environment variable prefix | `ENV_PREFIX` from `app.config` |
| CLI version banner | `_BANNER` in `src/app/cli.py` |

`ENV_PREFIX` lives in `config.py` because environment variable naming is that module's boundary.
Build and tooling files — `pyproject.toml`, `mise.toml`, `settings.toml`, `.env.template` — are read
before Python runs and necessarily spell the name out.

This assumes the distribution name matches the import name. Keep it that way: on a mismatch
`version()` raises `PackageNotFoundError` and `__version__` silently degrades to `0+unknown`, which
`test_version_is_resolved_from_installed_metadata` exists to catch.

### Module boundaries

- **CLI** — Typer for commands, Rich for rendering. The CLI is a thin shell: it parses arguments,
  builds dependencies, and delegates. No business logic in a command function. `src/app/cli.py` is
  the reference for command shape.
  - **Always use the `Annotated` style** for arguments and options. Never pass
    `typer.Argument(...)` or `typer.Option(...)` as a parameter default.
  - An `async` implementation is invoked from a sync command via a single `asyncio.run` at that
    boundary. Never call `asyncio.run` below the CLI layer.
- **Data models** — Pydantic v2 for anything crossing a boundary: external API responses, persisted
  rows, tool inputs and outputs. No bare dicts for long-lived data.
- **Configuration** — `src/app/config.py` owns settings loading. Never construct a `Dynaconf`
  instance outside it; everything else imports `Settings` and `load_settings`. Non-secret defaults
  go in `settings.toml`, secrets in `ENV_PREFIX`-prefixed environment variables. Call
  `load_settings()` once, at the entry point.
- **Logging** — structured JSON to stderr, one object per line. Rich owns stdout. Namespace loggers
  under `APP_NAME`; configure once at the entry point, never at import time. No `print()` for
  diagnostics.

### Secrets

Secrets are read from the environment, injected at process start — never from a file.

- `.env.template` holds `op://` references only.
- Reach secrets via `op run --env-file=.env.template -- <command>`, exposed as a mise task.
- Never write a literal credential anywhere, tests included. Use `sk-test-…`-style fakes.
- Secret fields are `SecretStr`, never entries in a settings file. Never log a resolved secret.

### Comments and docs

- No docstrings. The sole exception is a Typer command function, where the docstring is the
  `--help` text.
- Comments only where the WHY is non-obvious, never restating what the code does.
- No multi-line comment blocks.
- Match surrounding comment density, naming, and idiom.
- Update the single source of truth and link to it rather than creating parallel docs.
- `README.md` and `CONTRIBUTING.md` are the human layer — what the repo is, how to set it up, how
  to send a change. They link into this document instead of repeating it.
- Every change ends by checking the documentation it affects — this document, the human layer, and
  any doc naming a file, task, or convention that moved — and correcting it in the same change.
  Stale framing is a defect, not a follow-up.

## Quality gates

### Linting

- Pre-commit is the linting entry point. Never call `ruff` directly.
- ruff for lint and format. Never add black, isort, flake8, or pylint.
- When pre-commit reformats files, re-stage and re-run.
- Fix lint errors as they appear.
- cspell checks every tracked file. A legitimate term it flags goes in `.cspell/project.txt`, in
  the section it belongs to — never an inline ignore.

### Type checking

pyright strict. A dependency without a `py.typed` marker resolves to `Any`, which pyright accepts
silently. When adding one: check for `py.typed`, else add a `types-<name>` stubs package, else
confine the library behind a small annotated adapter module.

Never use a blanket `# type: ignore` or loosen the mode to clear an error. Narrow per-line ignores
are acceptable only at a library boundary, with the reason stated.

### Testing

- pytest. Never `unittest.TestCase` classes.
- `tests/` mirrors `src/`, annotated like any other code.
- Tests needing network or real credentials are marked, deselected by default, and given their own
  task. They never run in CI.
- Do not run the suite after every edit — run it when asked or when verifying a fix.
- A test failing after a change is fixed before the work is reported done.

## Shipping

### Git

- Conventional Commits, commitizen's default types. The PR title is held to the same format.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret or a generated cache directory.

### CI

- Pin actions to a full SHA or explicit tag, never `@main`.
- Use mise so tool versions match local development.
- Lint, typecheck, test only. `mise run ci` reproduces CI locally.
- Secrets via CI environment secrets or OIDC.
