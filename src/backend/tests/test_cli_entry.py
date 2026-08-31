"""RED: CLI entry point and console script wiring."""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import entry_points

from conftest import BACKEND_ROOT


def test_cli_main_is_callable() -> None:
    from content_autopilot.cli import main

    assert callable(main)


def test_module_execution_exits_zero(capsys) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "content_autopilot", "--help"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "content-autopilot" in (result.stdout + result.stderr).lower()


def test_console_script_entry_point_registered() -> None:
    console_scripts = {
        ep.name: ep for ep in entry_points(group="console_scripts")
    }
    assert "content-autopilot" in console_scripts
    target = console_scripts["content-autopilot"].value
    assert target.startswith("content_autopilot.")

    # uv run content-autopilot uses a Windows .exe wrapper that Smart App Control may
    # block; verify the installed entry point through uv's Python interpreter instead.
    result = subprocess.run(
        ["uv", "run", "python", "-m", "content_autopilot", "--help"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
