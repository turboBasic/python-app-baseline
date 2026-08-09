from typing import Annotated

import typer

from app import __version__

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"app {__version__}")
        raise typer.Exit()


@app.command()
def version() -> None:
    """Show the version."""
    typer.echo(f"app {__version__}")


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version", help="Show version and exit.", callback=_version_callback, is_eager=True
        ),
    ] = False,
) -> None:
    pass
