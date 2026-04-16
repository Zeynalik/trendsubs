from __future__ import annotations

from pathlib import Path

from trendsubs.core.models import MemeOverlay


def build_ffmpeg_command(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
    font_path: Path | None = None,
    meme_overlays: list[MemeOverlay] | None = None,
) -> list[str]:
    filter_expr = _build_ass_filter_expr(ass_path=ass_path, font_path=font_path)
    overlays = meme_overlays or []
    if not overlays:
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

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
    ]
    for overlay in overlays:
        command.extend(["-ignore_loop", "0", "-i", str(overlay.gif_path)])

    filter_parts = [f"[0:v]{filter_expr}[v0]"]
    last_video_label = "v0"
    for index, overlay in enumerate(overlays, start=1):
        gif_label = f"g{index}"
        composed_label = f"v{index}"
        start_sec = max(0.0, overlay.start_ms / 1000.0)
        end_sec = max(start_sec + 0.05, overlay.end_ms / 1000.0)
        filter_parts.append(f"[{index}:v]fps=15,scale=320:-1:flags=lanczos,format=rgba[{gif_label}]")
        filter_parts.append(
            f"[{last_video_label}][{gif_label}]overlay="
            f"x={overlay.x}:y={overlay.y}:shortest=1:enable='between(t,{start_sec:.3f},{end_sec:.3f})'"
            f"[{composed_label}]"
        )
        last_video_label = composed_label

    command.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            f"[{last_video_label}]",
            "-map",
            "0:a?",
        ]
    )
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )
    return command


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
