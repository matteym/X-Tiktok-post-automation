"""Console entry point for the content-autopilot CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from content_autopilot.media.run_inputs import collect_run_media

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
        typer.Option("--github", help="Optional GitHub URL for context"),
    ] = None,
    tiktok: Annotated[
        str | None,
        typer.Option("--tiktok", help="Optional TikTok input URL for context"),
    ] = None,
) -> None:
    """Validate media inputs and compute ordered fingerprints for publishing."""
    try:
        collected = collect_run_media(
            video_paths=video,
            description=description,
            github_url=github,
            tiktok_url=tiktok,
        )
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"description: {collected.description}")
    typer.echo(f"media_fingerprints: {','.join(collected.media_fingerprints)}")
    typer.echo(f"media_set_hash: {collected.media_set_hash}")


def main() -> None:
    """Run the content-autopilot CLI."""
    cli_args = sys.argv[1:]
    if not cli_args:
        raise SystemExit(0)
    if all(arg.startswith("-") for arg in cli_args):
        raise SystemExit(0)

    app(prog_name="content-autopilot")
