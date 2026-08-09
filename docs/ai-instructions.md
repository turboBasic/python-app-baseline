# AI Instructions — Python platform conventions

Single source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

This file is application-independent: it covers the Python platform only and says nothing about
what this project does. Application conventions live in a separate document that references this
one.

## Tooling hierarchy

1. **Project task** — a `mise.toml` task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **Pre-commit** — `mise exec -- pre-commit run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages.

Never `pip install`. Never activate a venv by hand.

## mise

`mise.toml` pins every runtime and CLI. Nothing is assumed installed globally.

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

`pyproject.toml`, `mise.toml`, and `.pre-commit-config.yaml` are committed and already satisfy
every tool rule below. Extend them; do not regenerate them. `[project].name`, `[project.scripts]`,
`known-first-party`, and the wheel `packages` entry all carry the placeholder package name `app`
and are renamed together.

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
- Pre-commit reformatting files is expected: re-stage and re-run.
- Fix lint errors as they appear.

`.pre-commit-config.yaml` runs ruff plus the hygiene hooks: `trailing-whitespace`,
`end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files`,
`check-merge-conflict`.

## pyright

`typeCheckingMode = "strict"` and `pythonVersion = "3.14"`, wired as a local pre-commit hook
running `uv run pyright`. Set `venvPath = "."` and `venv = ".venv"`.

A dependency without a `py.typed` marker resolves to `Any`, and pyright reports **0 errors** on
`Any` — unchecked code looks clean. When adding a dependency: check for `py.typed`, else add a
`types-<name>` stubs package, else confine the library behind a small annotated adapter module.

Never use a blanket `# type: ignore` or loosen the mode to clear an error. Narrow per-line ignores
are acceptable only at a library boundary.

## CLI

Typer for the CLI layer, Rich for terminal rendering. The CLI is a thin shell: it parses
arguments, builds dependencies, and delegates. No business logic in a command function.

- **Always use the `Annotated` style** for arguments and options. Passing `typer.Argument(...)` or
  `typer.Option(...)` as a parameter default is the deprecated idiom.
- Command docstrings are the `--help` text — the one place a docstring is written.
- `no_args_is_help=True` on the `Typer()` app.
- Rich writes to stdout; logging goes to stderr, so the two never interleave.
- An `async` implementation is invoked from a sync command via a single `asyncio.run` at that
  boundary. Never call `asyncio.run` below the CLI layer.

```python
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    task: Annotated[str, typer.Argument(help="What to do")],
    model: Annotated[str | None, typer.Option("--model")] = None,
) -> None:
    """Run a task."""
```

## Data models

Pydantic v2 for anything crossing a boundary — external API responses, persisted rows, tool inputs
and outputs. No bare dicts for long-lived data.

## Configuration

`dynaconf` loads layered settings; a frozen Pydantic model is the only surface the rest of the
codebase sees. A bare `Dynaconf` object types as `Any` under pyright strict, so the wrapper is
required.

```python
from typing import Any, cast

from dynaconf import Dynaconf
from pydantic import BaseModel, ConfigDict

_raw = Dynaconf(
    settings_files=["settings.toml"],
    environments=True,
    envvar_prefix="APP",
    env_switcher="APP_ENV",
)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    example_field: str


def load_settings() -> Settings:
    raw = cast(dict[str, Any], _raw.as_dict())
    lowered = {k.lower(): v for k, v in raw.items()}
    return Settings.model_validate(
        {name: lowered[name] for name in Settings.model_fields if name in lowered}
    )
```

- Never import a `Dynaconf` instance outside this module. Application code imports `Settings` and
  `load_settings`. The `cast` above is the only sanctioned one.
- Select fields by declared name. Passing `as_dict()` straight to `model_validate` trips
  `extra="forbid"` on dynaconf's injected `ENV` key.
- Set `env_switcher` explicitly. `envvar_prefix` does not rename it, and without it a prefixed
  switch variable is silently ignored.
- Validate at startup, at the entry point.
- Keep the model `frozen=True` and `extra="forbid"`.

## Secrets

Secrets are read from the environment, injected at process start — never from a file.

- `.env.template` holds `op://` references only, and is committed.
- Real `.env` files are git-ignored.
- Reach secrets via `op run --env-file=.env.template -- <command>`, exposed as a mise task.
- Never write a literal credential anywhere, tests included. Use `sk-test-…`-style fakes.
- Secret fields on `Settings` are `SecretStr`, never entries in a settings file. Never log a
  resolved secret.

## Logging

Structured JSON to stderr, one object per line, so it never collides with Rich output on stdout.

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
