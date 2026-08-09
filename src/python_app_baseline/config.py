from pathlib import Path
from typing import Any, cast

# dynaconf ships py.typed but no stubs pyright accepts; this module is the boundary that
# contains the resulting Any.
from dynaconf import Dynaconf  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict, SecretStr

from python_app_baseline import APP_NAME
from python_app_baseline.logging import LogLevel

ENV_PREFIX = APP_NAME.upper()


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    log_level: LogLevel = "INFO"
    # None means "use the platform default log location"; configure_logging() resolves it.
    # A relative path resolves against the working directory.
    log_file: Path | None = None
    api_key: SecretStr | None = None


def load_settings(log_level: LogLevel | None = None, log_file: Path | None = None) -> Settings:
    # The only place a Dynaconf instance exists; everything else imports Settings.
    raw = cast(
        dict[str, Any],
        Dynaconf(
            settings_files=["settings.toml"],
            environments=True,
            envvar_prefix=ENV_PREFIX,
            # envvar_prefix does not rename the switcher; without this it stays ENV_FOR_DYNACONF.
            env_switcher=f"{ENV_PREFIX}_ENV",
        ).as_dict(),
    )
    lowered = {key.lower(): value for key, value in raw.items()}
    # CLI arguments win over the settings file and the environment.
    if log_level is not None:
        lowered["log_level"] = log_level
    if log_file is not None:
        lowered["log_file"] = log_file
    # Declared fields only: dynaconf injects keys such as ENV that extra="forbid" would reject.
    return Settings.model_validate(
        {name: lowered[name] for name in Settings.model_fields if name in lowered}
    )
