# AI Instructions — Python platform conventions

Single source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

Scope: the Python platform. Application conventions live in a separate document that references
this one.

## Tooling hierarchy

1. **Project task** — a `mise.toml` task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **Pre-commit** — `mise exec -- pre-commit run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages.

Never `pip install`. Never activate a venv by hand.

## mise

`mise.toml` pins every runtime and CLI. Nothing is installed globally.

- Pin `python = "3.14"` and uv.
- `[env]` sets `_.python.venv = { path = ".venv", create = true }`.
- Tasks: `setup`, `fmt`, `lint`, `typecheck`, `test`, `ci` (`depends = ["lint", "typecheck", "test"]`).
- Tasks needing secrets wrap their command in `op run --env-file=.env.template --`.

## uv

- `pyproject.toml` + `uv.lock`, both committed. No `setup.py`, `setup.cfg`, or `requirements.txt`.
- `requires-python = ">=3.14"`.
- `src/<package>/` layout with `__init__.py`. Never a flat top-level package.
- Runtime deps in `[project].dependencies`, dev deps in `[dependency-groups].dev`.
- `uv sync --locked` in setup and CI. Run `uv lock` after editing dependencies and commit the
  result in the same change.

Extend `pyproject.toml`, `mise.toml`, and `.pre-commit-config.yaml`; never regenerate them.
Renaming the package changes `[project].name`, `[project.scripts]`, `known-first-party`, and the
wheel `packages` entry together.

Introducing a new file type or framework updates `.editorconfig`, `.gitattributes`, and
`.gitignore` in the same change.

## Python

Python 3.14. No compatibility shims or version guards for earlier releases.

- `X | None`, not `typing.Optional`. Built-in `dict`/`list`/`tuple`, not `typing.Dict`.
- No `from __future__ import annotations`.
- No `if TYPE_CHECKING:` guard except to break an import cycle.
- Full type hints on every signature, tests included.
- No blocking I/O in an async path; wrap unavoidable blocking calls in `asyncio.to_thread`.

## ruff

Pre-commit is the linting entry point. Never call `ruff` directly.

- ruff for lint and format. No black, isort, flake8, or pylint.
- Configured in `pyproject.toml`, with `target-version = "py314"`.
- Rules: `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `C4`, `RUF`, plus `ASYNC` in async projects.
- Set `known-first-party`.
- When pre-commit reformats files, re-stage and re-run.
- Fix lint errors as they appear.

`.pre-commit-config.yaml` runs ruff plus the hygiene hooks: `trailing-whitespace`,
`end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files`,
`check-merge-conflict`.

## pyright

`typeCheckingMode = "strict"` and `pythonVersion = "3.14"`, run as a local pre-commit hook via
`uv run pyright`. Set `venvPath = "."` and `venv = ".venv"`.

A dependency without a `py.typed` marker resolves to `Any`, which pyright accepts silently. When
adding one: check for `py.typed`, else add a `types-<name>` stubs package, else confine the library
behind a small annotated adapter module.

Never use a blanket `# type: ignore` or loosen the mode to clear an error. Narrow per-line ignores
are acceptable only at a library boundary.

## CLI

Typer for the CLI layer, Rich for terminal rendering. The CLI is a thin shell: it parses
arguments, builds dependencies, and delegates. No business logic in a command function.

`src/app/cli.py` is the reference for command shape; follow it.

- **Always use the `Annotated` style** for arguments and options. Never pass `typer.Argument(...)`
  or `typer.Option(...)` as a parameter default.
- Rich writes to stdout, logging to stderr.
- An `async` implementation is invoked from a sync command via a single `asyncio.run` at that
  boundary. Never call `asyncio.run` below the CLI layer.

## Data models

Pydantic v2 for anything crossing a boundary — external API responses, persisted rows, tool inputs
and outputs. No bare dicts for long-lived data.

## Configuration

`src/app/config.py` owns settings loading; extend `Settings` and `settings.toml` there.

- Never construct a `Dynaconf` instance outside that module. Everything else imports `Settings`
  and `load_settings`.
- Add non-secret defaults to `settings.toml`, secrets as `APP_`-prefixed environment variables.
- Call `load_settings()` once at startup, at the entry point.

## Secrets

Secrets are read from the environment, injected at process start — never from a file.

- `.env.template` holds `op://` references only, and is committed.
- Real `.env` files are git-ignored.
- Reach secrets via `op run --env-file=.env.template -- <command>`, exposed as a mise task.
- Never write a literal credential anywhere, tests included. Use `sk-test-…`-style fakes.
- Secret fields are `SecretStr`, never entries in a settings file. Never log a resolved secret.

## Logging

Structured JSON to stderr, one object per line. Rich owns stdout.

- Namespace loggers under the package name; `propagate = False` on the package root.
- Configure once, at the entry point — never at import time.
- No `print()` for diagnostics.

## Testing

- pytest. No `unittest.TestCase` classes.
- `pytest-asyncio` with `asyncio_mode = "auto"` in async projects.
- Config in `pyproject.toml` under `[tool.pytest.ini_options]`. Set `testpaths`.
- `tests/` mirrors `src/`, annotated like any other code.
- Tests needing network or real credentials are marked, deselected via
  `addopts = ["-m", "not <marker>", "-ra"]`, and given their own task. They never run in CI.
- Do not run the suite after every edit — run it when asked or when verifying a fix.
- A test failing after a change is fixed before the work is reported done.

## Comments and docs

- No docstrings. The sole exception is a Typer command function, where the docstring is the
  `--help` text.
- Comments only where the WHY is non-obvious, never restating what the code does.
- No multi-line comment blocks.
- Match surrounding comment density, naming, and idiom.
- Update the single source of truth and link to it rather than creating parallel docs.

## Git

- Conventional Commits.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret or a generated cache directory.

## CI

- Pin actions to a full SHA or explicit tag, never `@main`.
- Use mise so tool versions match local development.
- Lint, typecheck, test only. `mise run ci` reproduces CI locally.
- Secrets via CI environment secrets or OIDC.

## Behavior

- Read the file, run the tool, check the config rather than guessing at structure or conventions.
- Ask when genuinely ambiguous; take the sensible default otherwise and say so.
- Match existing patterns over personal preference.
- Scope to the request. No refactoring adjacent code or improving what was not asked about.
