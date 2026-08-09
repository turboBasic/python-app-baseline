# python-app-baseline

Baseline conventions for Python applications: mise tasks, ruff, pyright strict, pytest, and CI.
Kept current rather than pinned to a point in time.

The deliverable is [`docs/ai-instructions.md`](docs/ai-instructions.md). `src/app/` and `tests/`
exist to prove those rules hold — a Typer CLI and a Dynaconf loader with nothing else in them.

## Instantiating

`app` is a deliberate placeholder. Renaming it touches `[project].name`, `[project.scripts]`,
`known-first-party`, and the wheel `packages` entry together, plus the `APP_` environment prefix
in `src/app/config.py` and `settings.toml`.

```sh
mise run setup   # dependencies and pre-commit hooks
mise run ci      # lint, typecheck, test — what CI runs
```

## License

[MIT](LICENSE). Fork it, copy from it, no attribution beyond the notice.
