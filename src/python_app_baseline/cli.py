import logging
from pathlib import Path
from typing import Annotated

import typer

from python_app_baseline import APP_NAME, __version__
from python_app_baseline.config import LogLevel, load_settings
from python_app_baseline.logging import configure_logging

app = typer.Typer(add_completion=False, no_args_is_help=True)

_BANNER = f"{APP_NAME} {__version__}"


@app.command()
def version() -> None:
    """Show the version."""
    typer.echo(_BANNER)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version_flag: Annotated[
        bool,
        typer.Option("--version", help="Show version and exit."),
    ] = False,
    log_level: Annotated[
        LogLevel | None,
        typer.Option("--log-level", help="Override the configured log level."),
    ] = None,
    log_file: Annotated[
        Path | None,
        typer.Option(
            "--log-file",
            help="Write logs here instead of the platform log directory. Relative to the working directory.",
        ),
    ] = None,
) -> None:
    settings = load_settings(log_level=log_level, log_file=log_file)
    resolved_log_file = configure_logging(settings.log_level, settings.log_file)
    # "configured_level", not "log_level": `level` is already this record's own severity, and the
    # two are indistinguishable under --log-level DEBUG.
    logging.getLogger(APP_NAME).debug(
        "settings loaded",
        extra={"configured_level": settings.log_level, "log_file": resolved_log_file},
    )

    if version_flag:
        typer.echo(_BANNER)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(1)
