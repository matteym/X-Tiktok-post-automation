"""RED: structured CLI output helpers without stack traces on user errors."""

from __future__ import annotations

import json
import re

import pytest


def test_emit_info_writes_structured_message(capsys: pytest.CaptureFixture[str]) -> None:
    from content_autopilot.cli_output import emit_info

    emit_info("content-autopilot ready", detail="scaffold")
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["level"] == "info"
    assert payload["message"] == "content-autopilot ready"
    assert payload["detail"] == "scaffold"


def test_emit_error_writes_structured_message(capsys: pytest.CaptureFixture[str]) -> None:
    from content_autopilot.cli_output import emit_error

    emit_error("configuration missing", detail="DATABASE_URL is unset")
    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip())
    assert payload["level"] == "error"
    assert payload["message"] == "configuration missing"
    assert payload["detail"] == "DATABASE_URL is unset"


def test_user_facing_error_handler_avoids_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    from content_autopilot.cli_output import UserFacingError, run_cli

    def failing_main() -> None:
        raise UserFacingError("invalid input", detail="description is required")

    exit_code = run_cli(failing_main)
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "invalid input" in captured.err
    assert "description is required" in captured.err
    assert not re.search(r"Traceback \(most recent call last\)", captured.err)


def test_unexpected_exception_is_sanitized_without_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    from content_autopilot.cli_output import run_cli

    def exploding_main() -> None:
        raise RuntimeError("internal boom")

    exit_code = run_cli(exploding_main)
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unexpected error" in captured.err.lower()
    assert not re.search(r"Traceback \(most recent call last\)", captured.err)
