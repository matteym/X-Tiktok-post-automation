"""CLI entry point for content-autopilot."""

from __future__ import annotations

import typer

from content_autopilot.cli_output import run_cli

app = typer.Typer(
    name="content-autopilot",
    help="Content autopilot CLI for X/TikTok post automation",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """Content autopilot command group."""


def main() -> None:
    run_cli(lambda: app(prog_name="content-autopilot"))


if __name__ == "__main__":
    main()
