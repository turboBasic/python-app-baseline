# python-app-baseline

[![CI](https://github.com/turboBasic/python-app-baseline/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/turboBasic/python-app-baseline/actions/workflows/ci.yml?query=branch%3Amain)

Baseline conventions for Python applications: mise tasks, ruff, pyright strict, pytest, and CI.
Kept current rather than pinned to a point in time.

The deliverable is [`docs/ai-instructions.md`](docs/ai-instructions.md). `src/python_app_baseline/`
and `tests/` exist to prove those rules hold — a Typer CLI and a Dynaconf loader with nothing else in
them. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers setup and the task loop.

## Instantiating

`python_app_baseline` is a deliberate placeholder. Renaming it:

1. `git mv src/python_app_baseline src/<your_package>`
2. Rewrite the `from python_app_baseline …` import lines in `src/` and `tests/`.
3. Update `[project].name`, `[project.scripts]`, `known-first-party`, and the wheel `packages` entry
   in `pyproject.toml` together — the distribution name is the import name with hyphens.
4. `uv lock`, then update the `PYTHON_APP_BASELINE_` prefix named in `settings.toml`.

Nothing beyond that: everything else the application calls itself derives from the package name —
see [Application identity](docs/ai-instructions.md#application-identity).

## License

[MIT](LICENSE). Fork it, copy from it, no attribution beyond the notice.
