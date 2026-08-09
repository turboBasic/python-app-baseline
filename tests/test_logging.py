import json
import logging
import os
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import cast

import pytest

from python_app_baseline import APP_NAME
from python_app_baseline import logging as app_logging
from python_app_baseline.logging import configure_logging


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    # configure_logging() reassigns root's handlers; without restoring them pytest's own
    # capture handlers stay detached for the rest of the session.
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    package = logging.getLogger(APP_NAME)
    saved_package_level, saved_propagate = package.level, package.propagate
    yield
    for handler in root.handlers:
        if handler not in saved_handlers:
            handler.close()
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    package.handlers.clear()
    package.setLevel(saved_package_level)
    package.propagate = saved_propagate


def _format(record: logging.LogRecord) -> dict[str, object]:
    formatter = _console_handler().formatter
    assert formatter is not None
    parsed: dict[str, object] = json.loads(formatter.format(record))
    return parsed


def _lines(log_file: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in log_file.read_text().splitlines() if line]


def _console_handlers() -> list[logging.Handler]:
    # RotatingFileHandler subclasses StreamHandler, so matching on StreamHandler alone would
    # also pick up the file handler.
    return [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
    ]


def _file_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
    ]


def _console_handler() -> logging.Handler:
    handlers = _console_handlers()
    assert len(handlers) == 1
    return handlers[0]


def _file_handler() -> logging.Handler:
    handlers = _file_handlers()
    assert len(handlers) == 1
    return handlers[0]


def test_envelope_carries_the_standard_fields(tmp_path: Path) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    payload = _format(logger.makeRecord(APP_NAME, logging.INFO, __file__, 0, "hello", (), None))

    assert payload["level"] == "INFO"
    assert payload["logger"] == APP_NAME
    assert payload["message"] == "hello"
    assert payload["pid"] == os.getpid()
    assert isinstance(payload["run_id"], str)
    assert isinstance(payload["source"], str)


def test_every_emitted_record_is_one_line_of_json(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    logger.info("first")
    logger.warning("second")
    _file_handler().flush()

    raw = log_file.read_text().splitlines()
    assert len(raw) == 2
    assert [json.loads(line)["message"] for line in raw] == ["first", "second"]


def test_timestamp_is_utc_rfc3339_with_milliseconds(tmp_path: Path) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    payload = _format(logger.makeRecord(APP_NAME, logging.INFO, __file__, 0, "hello", (), None))

    timestamp = payload["timestamp"]
    assert isinstance(timestamp, str)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00", timestamp)
    assert datetime.fromisoformat(timestamp).utcoffset() == UTC.utcoffset(None)


def test_exception_is_rendered_with_type_message_and_traceback(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    try:
        raise ValueError("bad value")
    except ValueError:
        logger.exception("operation failed")
    _file_handler().flush()

    error = _lines(log_file)[0]["error"]
    assert isinstance(error, dict)
    error_fields = cast(dict[str, str], error)
    assert error_fields["type"] == "ValueError"
    assert error_fields["message"] == "bad value"
    assert "ValueError: bad value" in error_fields["traceback"]


def test_stack_info_is_captured_under_its_own_key(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logging.getLogger(APP_NAME).info("with stack", stack_info=True)
    _file_handler().flush()

    stack = _lines(log_file)[0]["stack"]
    assert isinstance(stack, str)
    assert "Stack (most recent call last)" in stack


def test_extra_fields_are_included_in_the_payload(tmp_path: Path) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    record = logger.makeRecord(
        APP_NAME,
        logging.INFO,
        __file__,
        0,
        "settings loaded",
        (),
        None,
        extra={"log_level": "DEBUG"},
    )

    assert _format(record)["log_level"] == "DEBUG"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Path("/tmp/run.log"), "/tmp/run.log"),
        (uuid.UUID("00000000-0000-4000-8000-000000000000"), "00000000-0000-4000-8000-000000000000"),
        (object, "<class 'object'>"),
    ],
)
def test_non_serializable_extra_is_stringified_rather_than_losing_the_record(
    tmp_path: Path, value: object, expected: str
) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logging.getLogger(APP_NAME).info("with object", extra={"value": value})
    _file_handler().flush()

    assert _lines(log_file)[0]["value"] == expected


def test_extra_cannot_overwrite_an_envelope_key(tmp_path: Path) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    record = logger.makeRecord(
        APP_NAME,
        logging.INFO,
        __file__,
        0,
        "collide",
        (),
        None,
        extra={"level": "PWNED", "timestamp": "nope"},
    )
    payload = _format(record)

    assert payload["level"] == "INFO"
    assert payload["timestamp"] != "nope"
    assert payload["extra_level"] == "PWNED"
    assert payload["extra_timestamp"] == "nope"


def test_formatter_set_attributes_do_not_leak_in_as_extras(tmp_path: Path) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)
    record = logger.makeRecord(APP_NAME, logging.INFO, __file__, 0, "hi %s", ("there",), None)

    # A handler with a %(asctime)s format sets `asctime` and `message` on the shared record
    # before ours sees it.
    logging.Formatter("%(asctime)s %(message)s").format(record)
    payload = _format(record)

    assert "asctime" not in payload
    assert payload["message"] == "hi there"


def test_unicode_is_not_escaped(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logging.getLogger(APP_NAME).info("ok", extra={"city": "Zürich"})
    _file_handler().flush()

    assert "Zürich" in log_file.read_text()


def test_console_handler_respects_configured_level(tmp_path: Path) -> None:
    configure_logging("WARNING", tmp_path / "run.log")
    assert _console_handler().level == logging.WARNING


def test_console_suppresses_records_below_the_configured_level(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("WARNING", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    logger.info("quiet")
    logger.warning("loud")

    stderr = capsys.readouterr().err
    assert "quiet" not in stderr
    assert json.loads(stderr.strip())["message"] == "loud"


def test_file_handler_always_captures_debug_regardless_of_console_level(tmp_path: Path) -> None:
    log_file = configure_logging("WARNING", tmp_path / "run.log")
    logging.getLogger(APP_NAME).debug("only visible in the file")
    _file_handler().flush()

    assert _lines(log_file)[0]["message"] == "only visible in the file"


def test_third_party_logger_output_is_json_on_both_handlers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")

    logging.getLogger("httpx").warning("connection reset")
    _file_handler().flush()

    assert json.loads(capsys.readouterr().err.strip())["logger"] == "httpx"
    assert _lines(log_file)[0]["logger"] == "httpx"


def test_log_file_is_not_created_by_an_invocation_that_never_logs(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "run.log")
    assert not log_file.exists()


def test_file_handler_rotates_instead_of_growing_without_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_logging, "_MAX_BYTES", 512)
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logger = logging.getLogger(APP_NAME)

    for index in range(40):
        logger.info("padding %s", "x" * 40, extra={"index": index})
    _file_handler().flush()

    assert (tmp_path / "run.log.1").exists()
    assert log_file.stat().st_size <= 1024


def test_reconfiguring_does_not_duplicate_handlers_or_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO", tmp_path / "run.log")
    log_file = configure_logging("INFO", tmp_path / "run.log")
    logging.getLogger(APP_NAME).info("once")
    _file_handler().flush()

    assert len(_console_handlers()) == 1
    assert len(_file_handlers()) == 1
    assert len(capsys.readouterr().err.strip().splitlines()) == 1
    assert len(_lines(log_file)) == 1


def test_unwritable_log_directory_leaves_console_logging_working(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir(mode=0o500)

    configure_logging("INFO", blocked / "nested" / "run.log")
    logging.getLogger(APP_NAME).info("still logging")

    stderr = capsys.readouterr().err
    assert len(_console_handlers()) == 1
    assert _file_handlers() == []
    assert "file logging disabled" in stderr
    assert any(
        json.loads(line)["message"] == "still logging"
        for line in stderr.splitlines()
        if line.startswith("{")
    )


def test_defaults_to_the_platform_log_directory_when_none_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_user_log_dir(
        appname: str | None = None,
        appauthor: str | None = None,
        version: str | None = None,
        opinion: bool = True,
        ensure_exists: bool = False,
        use_site_for_root: bool = False,
    ) -> str:
        return str(tmp_path)

    monkeypatch.setattr(app_logging, "user_log_dir", fake_user_log_dir)
    log_file = configure_logging("INFO", None)
    assert log_file == tmp_path / f"{APP_NAME}.log"


def test_explicit_log_file_name_is_honoured(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "debug.log")
    logging.getLogger(APP_NAME).info("named")
    _file_handler().flush()

    assert log_file == tmp_path / "debug.log"
    assert _lines(log_file)[0]["message"] == "named"


def test_relative_log_file_resolves_against_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    configure_logging("INFO", Path("nested/relative.log"))
    logging.getLogger(APP_NAME).info("relative")
    _file_handler().flush()

    assert _lines(tmp_path / "nested" / "relative.log")[0]["message"] == "relative"


def test_user_home_is_expanded_in_the_log_file_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    log_file = configure_logging("INFO", Path("~/tilde.log"))
    assert log_file == tmp_path / "tilde.log"


def test_missing_parent_directories_are_created(tmp_path: Path) -> None:
    log_file = configure_logging("INFO", tmp_path / "a" / "b" / "run.log")
    logging.getLogger(APP_NAME).info("deep")
    _file_handler().flush()

    assert _lines(log_file)[0]["message"] == "deep"
