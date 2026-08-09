import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from python_app_baseline import APP_NAME, __version__
from python_app_baseline.cli import app
from python_app_baseline.config import ENV_PREFIX

runner = CliRunner()

EXPECTED = f"{APP_NAME} {__version__}"


@pytest.fixture(autouse=True)
def _isolated_log_file(  # pyright: ignore[reportUnusedFunction]
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every invocation configures logging; without this it would write into the real
    # platform log directory on every test run. pytest collects autouse fixtures by
    # name via reflection, invisible to pyright.
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_FILE", str(tmp_path / "run.log"))


def test_version_is_resolved_from_installed_metadata() -> None:
    # A distribution name that stops matching the import name would silently degrade to the
    # fallback rather than fail; this turns that into a test failure. Hyphen-versus-underscore is
    # not a mismatch: version() normalises both sides.
    assert __version__ != "0+unknown"


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


@pytest.mark.parametrize(
    "argv", [["--log-level", "DEBUG", "--version"], ["--log-level", "DEBUG", "version"]]
)
def test_settings_loaded_is_logged_as_json_to_stderr(argv: list[str]) -> None:
    result = runner.invoke(app, argv)
    line = result.stderr.strip().splitlines()[0]
    payload = json.loads(line)
    assert payload["logger"] == APP_NAME
    assert payload["message"] == "settings loaded"
    assert payload["configured_level"] == "DEBUG"


@pytest.mark.parametrize("argv", [["--version"], ["version"]])
def test_settings_loaded_is_not_on_console_at_default_level(argv: list[str]) -> None:
    result = runner.invoke(app, argv)
    assert result.stderr == ""


@pytest.mark.parametrize(
    "argv", [["--log-level", "DEBUG", "--version"], ["--log-level", "DEBUG", "version"]]
)
def test_log_level_option_overrides_configured_level(argv: list[str]) -> None:
    result = runner.invoke(app, argv)
    line = result.stderr.strip().splitlines()[0]
    assert json.loads(line)["configured_level"] == "DEBUG"


def test_record_severity_is_distinct_from_the_configured_level(tmp_path: Path) -> None:
    target = tmp_path / "levels.log"
    runner.invoke(app, ["--log-file", str(target), "version"])

    payload = json.loads(target.read_text().splitlines()[0])
    assert payload["level"] == "DEBUG"
    assert payload["configured_level"] == "INFO"


def test_invalid_log_level_option_is_rejected() -> None:
    result = runner.invoke(app, ["--log-level", "bogus", "version"])
    assert result.exit_code != 0


def test_log_file_option_writes_to_the_given_path(tmp_path: Path) -> None:
    target = tmp_path / "chosen.log"
    result = runner.invoke(app, ["--log-file", str(target), "--log-level", "DEBUG", "version"])

    assert result.exit_code == 0
    assert json.loads(target.read_text().splitlines()[0])["log_file"] == str(target)


def test_log_file_option_accepts_a_path_relative_to_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--log-file", "relative.log", "--log-level", "DEBUG", "version"])

    assert result.exit_code == 0
    assert (tmp_path / "relative.log").exists()


def test_log_file_option_overrides_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_FILE", str(tmp_path / "from-env.log"))
    target = tmp_path / "from-flag.log"

    result = runner.invoke(app, ["--log-file", str(target), "--log-level", "DEBUG", "version"])

    assert result.exit_code == 0
    assert target.exists()
    assert not (tmp_path / "from-env.log").exists()
