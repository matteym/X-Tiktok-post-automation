"""Console entry point for the content-autopilot CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from content_autopilot.orchestration import execute_run

app = typer.Typer(name="content-autopilot")


@app.callback(invoke_without_command=True)
def cli_root(ctx: typer.Context) -> None:
    """Root CLI group for content-autopilot commands."""
    if ctx.invoked_subcommand is None:
        raise typer.Exit(0)


@app.command()
def run(
    description: Annotated[str, typer.Option("--description", help="Post description")],
    video: Annotated[
        list[Path],
        typer.Option(
            "--video",
            help="Photo or video path; repeat to preserve order",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    github: Annotated[
        str | None,
        typer.Option("--github", help="GitHub repo URL appended to YouTube and X captions"),
    ] = None,
    twitter: Annotated[
        str | None,
        typer.Option("--twitter", help="X/Twitter account URL appended to the YouTube caption"),
    ] = None,
    tiktok: Annotated[
        str | None,
        typer.Option("--tiktok", help="TikTok account URL appended to YouTube and X captions"),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="Optional YouTube snippet title"),
    ] = None,
    youtube: Annotated[
        str | None,
        typer.Option(
            "--youtube",
            help="YouTube channel URL appended to the X caption",
        ),
    ] = None,
) -> None:
    """Run dedup checks, LangGraph pipeline, and metadata persistence."""
    exit_code = execute_run(
        video_paths=video,
        description=description,
        github_url=github,
        twitter_url=twitter,
        tiktok_url=tiktok,
        title=title,
        youtube_url=youtube,
        echo=typer.echo,
    )
    raise typer.Exit(code=exit_code)


def main() -> None:
    """Run the content-autopilot CLI."""
    cli_args = sys.argv[1:]
    if not cli_args:
        raise SystemExit(0)
    if all(arg.startswith("-") for arg in cli_args):
        raise SystemExit(0)

    app(prog_name="content-autopilot")
