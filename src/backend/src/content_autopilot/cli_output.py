"""Structured CLI output helpers without stack traces on user errors."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import TextIO


class UserFacingError(Exception):
    def __init__(self, message: str, *, detail: str = "") -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


def _emit(level: str, message: str, *, detail: str, stream: TextIO) -> None:
    payload = {"level": level, "message": message, "detail": detail}
    print(json.dumps(payload), file=stream)


def emit_info(message: str, *, detail: str = "") -> None:
    _emit("info", message, detail=detail, stream=sys.stdout)


def emit_error(message: str, *, detail: str = "") -> None:
    _emit("error", message, detail=detail, stream=sys.stderr)


def run_cli(main: Callable[[], None]) -> int:
    try:
        main()
        return 0
    except UserFacingError as exc:
        emit_error(exc.message, detail=exc.detail)
        return 1
    except Exception:
        emit_error("Unexpected error", detail="An internal error occurred")
        return 1
