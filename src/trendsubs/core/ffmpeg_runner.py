from __future__ import annotations

from pathlib import Path


def build_ffmpeg_command(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
    font_path: Path | None = None,
) -> list[str]:
    filter_expr = _build_ass_filter_expr(ass_path=ass_path, font_path=font_path)
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


def build_overlay_command(
    video_path: Path,
    overlay_path: Path,
    output_path: Path,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(overlay_path),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto:eof_action=pass[v]",
        "-map",
        "[v]",
        "-map",
        "0:a?",
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


def build_overlay_preview_command(
    video_path: Path,
    overlay_image_path: Path,
    output_image_path: Path,
    at_seconds: float,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0.0, at_seconds):.3f}",
        "-i",
        str(video_path),
        "-i",
        str(overlay_image_path),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map",
        "[v]",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(output_image_path),
    ]


def build_preview_command(
    video_path: Path,
    ass_path: Path,
    output_image_path: Path,
    at_seconds: float,
    font_path: Path | None = None,
) -> list[str]:
    filter_expr = _build_ass_filter_expr(ass_path=ass_path, font_path=font_path)

    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0.0, at_seconds):.3f}",
        "-i",
        str(video_path),
        "-vf",
        filter_expr,
        "-frames:v",
        "1",
        str(output_image_path),
    ]


def _build_ass_filter_expr(ass_path: Path, font_path: Path | None = None) -> str:
    escaped_ass_path = _escape_filter_path(ass_path)
    filter_expr = f"ass=filename='{escaped_ass_path}'"
    if font_path is not None:
        escaped_fonts_dir = _escape_filter_path(font_path.parent)
        filter_expr += f":fontsdir='{escaped_fonts_dir}'"
    return filter_expr


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:")
