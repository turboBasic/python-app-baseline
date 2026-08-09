from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import ENV_PREFIX, Settings, load_settings


def test_loads_defaults_from_settings_file() -> None:
    assert load_settings().log_level == "INFO"


def test_env_switcher_selects_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_ENV", "production")
    assert load_settings().log_level == "WARNING"


def test_envvar_overrides_file_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_LEVEL", "DEBUG")
    assert load_settings().log_level == "DEBUG"


def test_undeclared_settings_keys_are_dropped() -> None:
    load_settings()  # dynaconf injects ENV and friends; extra="forbid" must never see them


def test_model_is_frozen() -> None:
    settings = load_settings()
    with pytest.raises(ValidationError):
        settings.log_level = "DEBUG"  # pyright: ignore[reportAttributeAccessIssue]


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"log_level": "INFO", "nope": 1})


def test_secret_is_not_reprable() -> None:
    settings = Settings(api_key=SecretStr("sk-test-abc"))
    assert "sk-test-abc" not in repr(settings)
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "sk-test-abc"


def test_log_level_argument_overrides_file_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_LEVEL", "DEBUG")
    assert load_settings(log_level="ERROR").log_level == "ERROR"


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"log_level": "NOPE"})


def test_log_file_defaults_to_none_meaning_the_platform_location() -> None:
    assert load_settings().log_file is None


def test_log_file_envvar_is_coerced_to_a_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_FILE", "/tmp/from-env.log")
    assert load_settings().log_file == Path("/tmp/from-env.log")


def test_log_file_argument_overrides_file_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_FILE", "/tmp/from-env.log")
    assert load_settings(log_file=Path("from-arg.log")).log_file == Path("from-arg.log")
