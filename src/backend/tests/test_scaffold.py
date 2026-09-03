"""Scaffold tests for the content-autopilot Python CLI package."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
PACKAGE_DIR = BACKEND_ROOT / "src" / "content_autopilot"

REQUIRED_DEPENDENCIES = (
    "langgraph",
    "langchain-core",
    "pydantic-settings",
    "typer",
    "httpx",
    "python-dotenv",
)

YOUTUBE_DEPENDENCIES = (
    "google-api-python-client",
    "google-auth-oauthlib",
)

DB_DEPENDENCY_OPTIONS = ("psycopg", "asyncpg", "sqlalchemy")


def _load_pyproject() -> dict:
    assert PYPROJECT.is_file(), "pyproject.toml must exist under src/backend"
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_pyproject_has_project_metadata() -> None:
    project = _load_pyproject()["project"]

    assert project["name"] == "content-autopilot"
    assert project.get("version")
    assert project.get("description")
    assert project.get("requires-python")


def test_pyproject_lists_required_dependencies() -> None:
    project = _load_pyproject()["project"]
    deps_blob = " ".join(project.get("dependencies", [])).lower()

    for dep in REQUIRED_DEPENDENCIES:
        assert dep in deps_blob, f"missing dependency: {dep}"

    assert any(option in deps_blob for option in DB_DEPENDENCY_OPTIONS), (
        "expected one of psycopg, asyncpg, or sqlalchemy in dependencies"
    )


def test_pyproject_lists_youtube_oauth_dependencies() -> None:
    project = _load_pyproject()["project"]
    deps_blob = " ".join(project.get("dependencies", [])).lower()

    for dep in YOUTUBE_DEPENDENCIES:
        assert dep in deps_blob, f"missing YouTube dependency: {dep}"


def test_pyproject_has_build_system_and_src_layout() -> None:
    data = _load_pyproject()

    assert "build-system" in data
    assert BACKEND_ROOT.joinpath("src", "content_autopilot").is_dir()


def test_pyproject_registers_content_autopilot_console_script() -> None:
    scripts = _load_pyproject()["project"].get("scripts", {})

    assert "content-autopilot" in scripts
    assert scripts["content-autopilot"].startswith("content_autopilot.")


def test_pytest_configuration_uses_tests_directory() -> None:
    pytest_options = _load_pyproject().get("tool", {}).get("pytest", {}).get(
        "ini_options", {}
    )

    assert pytest_options.get("testpaths") == ["tests"]
    assert pytest_options.get("pythonpath") == ["src"]


def test_package_directory_has_init_and_cli_modules() -> None:
    assert PACKAGE_DIR.is_dir()
    assert (PACKAGE_DIR / "__init__.py").is_file()
    assert (PACKAGE_DIR / "cli.py").is_file()


def test_package_imports() -> None:
    import content_autopilot

    assert content_autopilot is not None


def test_package_exposes_version() -> None:
    import content_autopilot

    assert hasattr(content_autopilot, "__version__")
    assert isinstance(content_autopilot.__version__, str)
    assert content_autopilot.__version__


def test_cli_main_is_callable() -> None:
    from content_autopilot.cli import main

    assert callable(main)


def test_cli_main_exits_zero() -> None:
    from content_autopilot.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


def test_console_script_entry_point_registered() -> None:
    scripts = entry_points(group="console_scripts")
    names = {entry.name for entry in scripts}

    assert "content-autopilot" in names


def test_installed_console_script_exits_zero() -> None:
    # Invoke the registered console script via the active interpreter. Windows
    # application control policies often block freshly built .venv/*.exe wrappers
    # spawned by `uv run content-autopilot`, while python.exe remains allowed.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from importlib.metadata import entry_points; "
                "main = next("
                "iter(entry_points(group='console_scripts', name='content-autopilot'))"
                ").load(); "
                "main()"
            ),
        ],
        cwd=BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
