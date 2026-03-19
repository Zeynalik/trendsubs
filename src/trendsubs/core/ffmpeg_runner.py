from __future__ import annotations

from pathlib import Path


def build_ffmpeg_command(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
    font_path: Path | None = None,
) -> list[str]:
    escaped_ass_path = _escape_filter_path(ass_path)
    filter_expr = f"ass=filename='{escaped_ass_path}'"
    if font_path is not None:
        escaped_fonts_dir = _escape_filter_path(font_path.parent)
        filter_expr += f":fontsdir='{escaped_fonts_dir}'"

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        filter_expr,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        str(output_path),
    ]


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:")
