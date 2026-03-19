from __future__ import annotations

from pathlib import Path

import typer

from trendsubs.core.models import RenderOptions
from trendsubs.core.render_service import render_subtitled_video
from trendsubs.gui.app import launch_gui


app = typer.Typer(help="Render trendy burned-in subtitles from SRT.")


@app.callback()
def main() -> None:
    """Root CLI application."""


@app.command("render")
def render_command(
    video: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False),
    subs: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False),
    out: Path = typer.Option(..., file_okay=True, dir_okay=False),
    font: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False),
    preset: str = typer.Option("social-pop"),
    accent: str = typer.Option("#FFD84D"),
    size: int = typer.Option(40),
    bottom_margin: int = typer.Option(120),
    keep_ass: bool = typer.Option(False),
) -> None:
    render_subtitled_video(
        video_path=video,
        srt_path=subs,
        output_path=out,
        options=RenderOptions(
            preset=preset,
            font_path=str(font),
            accent_color=accent,
            font_size=size,
            bottom_margin=bottom_margin,
            keep_ass=keep_ass,
        ),
    )
    typer.echo(f"Rendered video: {out}")


@app.command("gui")
def gui_command() -> None:
    launch_gui()


if __name__ == "__main__":
    app()
