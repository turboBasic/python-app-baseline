import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings, load_settings


def test_loads_defaults_from_settings_file() -> None:
    assert load_settings().log_level == "INFO"


def test_env_switcher_selects_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    assert load_settings().log_level == "WARNING"


def test_envvar_overrides_file_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LOG_LEVEL", "DEBUG")
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
