import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, override

from platformdirs import user_log_dir

from app import APP_NAME
from app.config import LogLevel

_LOG_FILE_NAME = f"{APP_NAME}.log"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

# Every attribute a plain LogRecord carries, plus the two that Formatter.format() sets on the
# record after construction; anything beyond this set came in via `extra=`.
_RESERVED_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | frozenset({"message", "asctime"})

_ENVELOPE_KEYS = frozenset({"timestamp", "level", "logger", "message", "pid", "run_id", "source"})

# One id per process, stamped on every line, so a single invocation stays separable in a log
# file that successive runs append to.
_RUN_ID = uuid.uuid4().hex[:12]


class _JSONFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pid": record.process,
            "run_id": _RUN_ID,
            "source": f"{record.module}.{record.funcName}:{record.lineno}",
        }

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["error"] = {
                "type": exc_type.__name__ if exc_type is not None else None,
                "message": str(exc_value) if exc_value is not None else None,
                "traceback": self.formatException(record.exc_info),
            }
        elif record.exc_text:
            payload["error"] = {"traceback": record.exc_text}

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        # Prefixed rather than dropped: a caller passing extra={"level": ...} still gets the
        # value through without displacing the envelope an ingester keys on.
        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_ATTRS:
                continue
            payload[f"extra_{key}" if key in _ENVELOPE_KEYS else key] = value

        # default=str keeps a Path, UUID or datetime in `extra=` from killing the record.
        return json.dumps(payload, default=str, ensure_ascii=False)


def _build_file_handler(log_file: Path) -> logging.Handler | None:
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # delay=True keeps an invocation that never logs, such as `--version`, from creating
        # the file.
        handler = RotatingFileHandler(
            log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, delay=True
        )
    except OSError as exc:
        # A read-only or unwritable log directory must not take the CLI down with it; console
        # logging alone is enough to keep working.
        print(f"warning: file logging disabled ({exc})", file=sys.stderr)
        return None
    handler.setFormatter(_JSONFormatter())
    # Always DEBUG on disk, regardless of console verbosity, so a failure is diagnosable from
    # the file alone without needing to reproduce it under --log-level DEBUG.
    handler.setLevel(logging.DEBUG)
    return handler


def _reset(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


def default_log_file() -> Path:
    return Path(user_log_dir(APP_NAME)) / _LOG_FILE_NAME


def configure_logging(log_level: LogLevel, log_file: Path | None = None) -> Path:
    # expanduser so a shell-quoted "~/run.log" still lands in the home directory; resolve so a
    # relative path is anchored to the working directory once, and the returned path stays
    # meaningful to whoever reads it later.
    log_file = default_log_file() if log_file is None else log_file.expanduser().resolve()

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(_JSONFormatter())
    console_handler.setLevel(log_level)

    # Handlers live on root, not on the package logger: third-party records (httpx, dynaconf)
    # would otherwise reach lastResort as plain text on the same stderr, in a second format,
    # and never land in the file.
    root = logging.getLogger()
    _reset(root)
    root.addHandler(console_handler)
    file_handler = _build_file_handler(log_file)
    if file_handler is not None:
        root.addHandler(file_handler)
    # INFO on root, DEBUG on the package: our own debug records reach the file while a chatty
    # dependency's do not. Propagation consults the originating logger's level, not root's.
    root.setLevel(logging.INFO)

    package_logger = logging.getLogger(APP_NAME)
    _reset(package_logger)
    package_logger.setLevel(logging.DEBUG)
    package_logger.propagate = True

    return log_file
