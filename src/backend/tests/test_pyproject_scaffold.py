"""RED: pyproject.toml scaffold expectations for content-autopilot."""

from __future__ import annotations

import tomllib

from conftest import PYPROJECT


def _load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _project_dependencies(data: dict) -> list[str]:
    project = data.get("project", {})
    deps = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        deps.extend(group)
    for group in data.get("dependency-groups", {}).values():
        deps.extend(group)
    return deps


def test_pyproject_project_name() -> None:
    data = _load_pyproject()
    assert data["project"]["name"] == "content-autopilot"


def test_pyproject_has_pytest_dev_dependency() -> None:
    data = _load_pyproject()
    dev_deps = data.get("dependency-groups", {}).get("dev", [])
    assert any("pytest" in dep for dep in dev_deps)


def test_pyproject_console_script_entry_point() -> None:
    data = _load_pyproject()
    scripts = data.get("project", {}).get("scripts", {})
    assert "content-autopilot" in scripts
    target = scripts["content-autopilot"]
    assert target.startswith("content_autopilot.")


def test_pyproject_pytest_config() -> None:
    data = _load_pyproject()
    pytest_cfg = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_cfg.get("testpaths") == ["tests"]
    assert "src" in pytest_cfg.get("pythonpath", [])


def test_pyproject_runtime_dependencies_include_cli_langgraph_postgres_http() -> None:
    data = _load_pyproject()
    deps_text = " ".join(_project_dependencies(data)).lower()
    assert "typer" in deps_text or "click" in deps_text, "CLI framework dependency required"
    assert "langgraph" in deps_text, "LangGraph dependency required"
    assert any(
        name in deps_text for name in ("psycopg", "asyncpg", "psycopg2")
    ), "PostgreSQL client dependency required"
    assert "httpx" in deps_text or "requests" in deps_text, "HTTP client dependency required"
    assert "python-dotenv" in deps_text or "dotenv" in deps_text, (
        "python-dotenv required for secure env loading"
    )


def test_pyproject_src_layout_hatch_config() -> None:
    data = _load_pyproject()
    packages = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", [])
    )
    assert any("content_autopilot" in pkg for pkg in packages), (
        "hatch wheel packages must include src/content_autopilot"
    )
