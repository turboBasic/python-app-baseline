from typing import Any, cast

# dynaconf ships py.typed but no stubs pyright accepts; this module is the boundary that
# contains the resulting Any.
from dynaconf import Dynaconf  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict, SecretStr


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    log_level: str = "INFO"
    api_key: SecretStr | None = None


def load_settings() -> Settings:
    # The only place a Dynaconf instance exists; everything else imports Settings.
    raw = cast(
        dict[str, Any],
        Dynaconf(
            settings_files=["settings.toml"],
            environments=True,
            envvar_prefix="APP",
            # envvar_prefix does not rename the switcher; without this it stays ENV_FOR_DYNACONF.
            env_switcher="APP_ENV",
        ).as_dict(),
    )
    lowered = {key.lower(): value for key, value in raw.items()}
    # Declared fields only: dynaconf injects keys such as ENV that extra="forbid" would reject.
    return Settings.model_validate(
        {name: lowered[name] for name in Settings.model_fields if name in lowered}
    )
