from importlib.metadata import version as metadata_version

import pytest
from typer.testing import CliRunner

from app import __version__
from app.cli import app

runner = CliRunner()

EXPECTED = f"app {__version__}"


def test_version_matches_package_metadata() -> None:
    assert __version__ == metadata_version("app")


@pytest.mark.parametrize("argv", [["--version"], ["version"]])
def test_version_prints_version_and_exits_cleanly(argv: list[str]) -> None:
    result = runner.invoke(app, argv)
    assert result.exit_code == 0
    assert result.stdout.strip() == EXPECTED


def test_version_command_and_flag_agree() -> None:
    from_command = runner.invoke(app, ["version"]).stdout.strip()
    from_flag = runner.invoke(app, ["--version"]).stdout.strip()
    assert from_command == from_flag == EXPECTED


def test_short_v_flag_is_not_offered() -> None:
    assert runner.invoke(app, ["-V"]).exit_code != 0


def test_version_command_is_listed_in_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.stdout


def test_no_args_shows_help_not_missing_command_error() -> None:
    result = runner.invoke(app, [])
    assert "Usage:" in result.stdout
    assert "Missing command" not in result.stdout
