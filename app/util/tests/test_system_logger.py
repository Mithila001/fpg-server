from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from app.util.logger.system_logger import SystemLogger, configure_application_logging


@pytest.fixture
def isolated_system_logger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for handler in SystemLogger._handlers:
        handler.close()
    monkeypatch.setattr(SystemLogger, "_logger", None)
    monkeypatch.setattr(SystemLogger, "_handlers", ())
    monkeypatch.setattr(SystemLogger, "_process_id", None)
    monkeypatch.setattr(SystemLogger, "_log_file", None)
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))

    yield

    for logger_name in (
        "fpg.pipeline",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "optuna",
    ):
        logging.getLogger(logger_name).handlers.clear()
    for handler in SystemLogger._handlers:
        handler.close()
    SystemLogger._logger = None
    SystemLogger._handlers = ()
    SystemLogger._process_id = None
    SystemLogger._log_file = None


def test_logging_writes_one_structured_record_to_console_and_file(
    isolated_system_logger: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_file = configure_application_logging()
    assert configure_application_logging() == log_file

    SystemLogger.log_event("test", "artifact_created", "INFO", {"count": 1})
    for handler in SystemLogger._handlers:
        handler.flush()

    console_lines = capsys.readouterr().out.strip().splitlines()
    file_lines = log_file.read_text(encoding="utf-8").strip().splitlines()

    assert len(console_lines) == 1
    assert len(file_lines) == 1
    assert json.loads(console_lines[0])["event"] == "artifact_created"
    assert json.loads(file_lines[0]) == json.loads(console_lines[0])
    assert log_file.parent.parent.name == "logs"
