"""RED: src-layout package structure for content_autopilot."""

from __future__ import annotations

import importlib.util

from conftest import PACKAGE_ROOT, SRC_ROOT


def test_src_layout_directory_exists() -> None:
    assert SRC_ROOT.is_dir(), "src/ directory required for src layout"
    assert PACKAGE_ROOT.is_dir(), "src/content_autopilot package directory required"


def test_package_init_module_exists() -> None:
    assert (PACKAGE_ROOT / "__init__.py").is_file()


def test_cli_module_with_main_exists() -> None:
    cli_module = PACKAGE_ROOT / "cli.py"
    assert cli_module.is_file(), "content_autopilot.cli module required"
    source = cli_module.read_text(encoding="utf-8")
    assert "def main(" in source


def test_config_module_exists() -> None:
    assert (PACKAGE_ROOT / "config.py").is_file(), (
        "content_autopilot.config required for secure env loading"
    )


def test_cli_output_module_exists() -> None:
    assert (PACKAGE_ROOT / "cli_output.py").is_file(), (
        "content_autopilot.cli_output required for structured CLI messages"
    )


def test_content_autopilot_importable_from_src_layout() -> None:
    spec = importlib.util.find_spec("content_autopilot")
    assert spec is not None, "content_autopilot must be importable via pythonpath=src"
