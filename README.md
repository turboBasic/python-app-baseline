# python-app-baseline

Baseline conventions for Python applications: mise tasks, ruff, pyright strict, pytest, and CI.
Kept current rather than pinned to a point in time.

The deliverable is [`docs/ai-instructions.md`](docs/ai-instructions.md). `src/python_app_baseline/`
and `tests/` exist to prove those rules hold — a Typer CLI and a Dynaconf loader with nothing else in
them. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers setup and the task loop.

## Instantiating

`python_app_baseline` is a deliberate placeholder, named after the repo rather than shortened to
`app`: `app` is the conventional name for the Typer instance, and a package sharing it makes
`from app.cli import app` read as though a thing imports itself. The long name also keeps a leftover
reference obvious rather than plausible. Renaming it means:

1. `git mv src/python_app_baseline src/<your_package>`
2. Rewrite the `from python_app_baseline …` import lines in `src/` and `tests/`.
3. Update `[project].name`, `[project.scripts]`, `known-first-party`, and the wheel `packages` entry
   in `pyproject.toml` together — the distribution name is the import name with hyphens.
4. `uv lock`, then update the `PYTHON_APP_BASELINE_` prefix named in `settings.toml`.

Nothing beyond that. `APP_NAME` in `src/python_app_baseline/__init__.py` is the package's own import
name, and the logger namespace, log file, log directory, environment variable prefix (`ENV_PREFIX` in
`src/python_app_baseline/config.py`), and version banner all derive from it — see
[Application identity](docs/ai-instructions.md#application-identity).

## License

[MIT](LICENSE). Fork it, copy from it, no attribution beyond the notice.
