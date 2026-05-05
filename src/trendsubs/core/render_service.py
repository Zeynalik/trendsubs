from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from trendsubs.core.ass_builder import build_ass_document, resolve_effective_font_size
from trendsubs.core.ffmpeg_runner import (
    build_ffmpeg_command,
    build_overlay_command,
    build_overlay_preview_command,
    build_preview_command,
)
from trendsubs.core.models import RenderOptions, SubtitleCue
from trendsubs.core.presets import PRESETS
from trendsubs.core.srt_parser import parse_srt_text
from trendsubs.core.word_timing import split_cue_into_word_slices
from trendsubs.core.word_jump_overlay import render_word_jump_frame, render_word_jump_overlay


@dataclass(slots=True)
class RenderResult:
    ass_path: Path | None


def render_subtitled_video(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    options: RenderOptions,
    command_runner=None,
) -> RenderResult:
    cues = parse_srt_text(srt_path.read_text(encoding="utf-8-sig"))
    for cue in cues:
        cue.word_slices = split_cue_into_word_slices(
            text=cue.text.replace("\n", " "),
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
        )
    cues = _apply_caption_word_limit(cues, max_words_per_caption=options.max_words_per_caption)

    play_res = _probe_video_resolution(video_path)
    if options.mode == "word-pill":
        runner = command_runner or _run_command
        overlay_path = output_path.with_suffix(".word_jump.mov")
        effective_font_size = resolve_effective_font_size(
            requested_size=options.font_size,
            play_res_y=play_res[1],
            cues=cues,
            auto_font_scale=options.auto_font_scale,
        )
        style = _resolve_word_pill_style(options)
        try:
            render_word_jump_overlay(
                cues=cues,
                output_path=overlay_path,
                play_res=play_res,
                font_path=Path(options.font_path),
                font_size=effective_font_size,
                bottom_margin=options.bottom_margin,
                safe_area_offset=options.safe_area_offset,
                max_words_per_line=options.max_words_per_line,
                active_fill_color=style["active_fill_color"],
                active_text_color=style["active_text_color"],
                inactive_text_color=style["inactive_text_color"],
                outline_color=style["outline_color"],
                outline_width=style["outline_width"],
                command_runner=runner,
            )
            command = build_overlay_command(
                video_path=video_path,
                overlay_path=overlay_path,
                output_path=output_path,
            )
            runner(command)
        finally:
            overlay_path.unlink(missing_ok=True)
        return RenderResult(ass_path=None)

    ass_text = build_ass_document(cues, options, play_res=play_res)
    ass_path = output_path.with_suffix(".ass")
    ass_path.write_text(ass_text, encoding="utf-8")

    runner = command_runner or _run_command
    command = build_ffmpeg_command(
        video_path=video_path,
        ass_path=ass_path,
        output_path=output_path,
        font_path=Path(options.font_path),
    )
    runner(command)

    if not options.keep_ass:
        ass_path.unlink(missing_ok=True)
        return RenderResult(ass_path=None)

    return RenderResult(ass_path=ass_path)


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _resolve_word_pill_style(options: RenderOptions) -> dict[str, tuple[int, int, int, int] | int]:
    preset = PRESETS[options.preset]
    active_fill = _hex_to_rgba(options.accent_color, alpha=235)
    return {
        "active_fill_color": active_fill,
        "active_text_color": _contrast_text_color(active_fill),
        "inactive_text_color": _ass_bgr_to_rgba(str(preset["primary_color"]), alpha=230),
        "outline_color": _ass_bgr_to_rgba(str(preset["outline_color"]), alpha=230),
        "outline_width": int(preset["outline"]),
    }


def _hex_to_rgba(color: str, *, alpha: int) -> tuple[int, int, int, int]:
    normalized = color.strip().lstrip("#")
    if len(normalized) != 6:
        normalized = "FFD84D"
    return (
        int(normalized[0:2], 16),
        int(normalized[2:4], 16),
        int(normalized[4:6], 16),
        alpha,
    )


def _ass_bgr_to_rgba(color: str, *, alpha: int) -> tuple[int, int, int, int]:
    normalized = color.replace("&H", "").strip()
    if len(normalized) != 8:
        normalized = "00FFFFFF"
    return (
        int(normalized[6:8], 16),
        int(normalized[4:6], 16),
        int(normalized[2:4], 16),
        alpha,
    )


def _contrast_text_color(background: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    red, green, blue, _alpha = background
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    if luminance > 180:
        return (0, 0, 0, 255)
    return (255, 255, 255, 255)


def render_preview_frame(
    video_path: Path,
    srt_path: Path,
    output_image_path: Path,
    options: RenderOptions,
    at_seconds: float = 1.5,
    command_runner=None,
) -> Path:
    cues = parse_srt_text(srt_path.read_text(encoding="utf-8-sig"))
    for cue in cues:
        cue.word_slices = split_cue_into_word_slices(
            text=cue.text.replace("\n", " "),
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
        )
    cues = _apply_caption_word_limit(cues, max_words_per_caption=options.max_words_per_caption)
    preview_seconds = _resolve_preview_seconds(cues, requested_seconds=at_seconds)

    play_res = _probe_video_resolution(video_path)
    if options.mode == "word-pill":
        overlay_image_path = output_image_path.with_suffix(".word_jump.png")
        runner = command_runner or _run_command
        effective_font_size = resolve_effective_font_size(
            requested_size=options.font_size,
            play_res_y=play_res[1],
            cues=cues,
            auto_font_scale=options.auto_font_scale,
        )
        style = _resolve_word_pill_style(options)
        try:
            render_word_jump_frame(
                cues=cues,
                output_path=overlay_image_path,
                at_ms=round(preview_seconds * 1000),
                play_res=play_res,
                font_path=Path(options.font_path),
                font_size=effective_font_size,
                bottom_margin=options.bottom_margin,
                safe_area_offset=options.safe_area_offset,
                max_words_per_line=options.max_words_per_line,
                active_fill_color=style["active_fill_color"],
                active_text_color=style["active_text_color"],
                inactive_text_color=style["inactive_text_color"],
                outline_color=style["outline_color"],
                outline_width=style["outline_width"],
            )
            command = build_overlay_preview_command(
                video_path=video_path,
                overlay_image_path=overlay_image_path,
                output_image_path=output_image_path,
                at_seconds=preview_seconds,
            )
            runner(command)
        finally:
            overlay_image_path.unlink(missing_ok=True)
        return output_image_path

    ass_text = build_ass_document(cues, options, play_res=play_res)
    ass_path = output_image_path.with_suffix(".preview.ass")
    ass_path.write_text(ass_text, encoding="utf-8")

    runner = command_runner or _run_command
    command = build_preview_command(
        video_path=video_path,
        ass_path=ass_path,
        output_image_path=output_image_path,
        at_seconds=preview_seconds,
        font_path=Path(options.font_path),
    )
    runner(command)
    ass_path.unlink(missing_ok=True)
    return output_image_path


def _resolve_preview_seconds(cues: list, requested_seconds: float) -> float:
    normalized_seconds = max(0.0, requested_seconds)
    requested_ms = round(normalized_seconds * 1000)
    if not cues:
        return normalized_seconds

    for cue in cues:
        if cue.start_ms <= requested_ms <= cue.end_ms:
            return normalized_seconds

    nearest_cue = min(
        cues,
        key=lambda cue: abs(((cue.start_ms + cue.end_ms) // 2) - requested_ms),
    )
    midpoint_ms = (nearest_cue.start_ms + nearest_cue.end_ms) // 2
    return midpoint_ms / 1000.0


def _apply_caption_word_limit(cues: list[SubtitleCue], max_words_per_caption: int) -> list[SubtitleCue]:
    if max_words_per_caption <= 0:
        return cues

    limited: list[SubtitleCue] = []
    index = 1
    for cue in cues:
        words = cue.word_slices
        if len(words) <= max_words_per_caption:
            limited.append(
                SubtitleCue(
                    index=index,
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                    text=cue.text,
                    lines=cue.lines,
                    word_slices=words,
                )
            )
            index += 1
            continue

        for chunk in _balanced_word_chunks(words, max_words_per_caption=max_words_per_caption):
            if not chunk:
                continue

            chunk_text = " ".join(word.text for word in chunk).strip()
            limited.append(
                SubtitleCue(
                    index=index,
                    start_ms=chunk[0].start_ms,
                    end_ms=chunk[-1].end_ms,
                    text=chunk_text,
                    lines=[chunk_text],
                    word_slices=chunk,
                )
            )
            index += 1

    return limited


def _balanced_word_chunks(words: list, max_words_per_caption: int) -> list[list]:
    if len(words) <= max_words_per_caption:
        return [words]

    chunk_count = (len(words) + max_words_per_caption - 1) // max_words_per_caption
    base_size = len(words) // chunk_count
    remainder = len(words) % chunk_count

    chunks: list[list] = []
    cursor = 0
    for index in range(chunk_count):
        size = base_size + (1 if index < remainder else 0)
        next_cursor = cursor + size
        chunks.append(words[cursor:next_cursor])
        cursor = next_cursor

    return [chunk for chunk in chunks if chunk]


def _probe_video_resolution(video_path: Path) -> tuple[int, int]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        resolution = result.stdout.strip().splitlines()[0]
        width_str, height_str = resolution.split("x", maxsplit=1)
        width = int(width_str)
        height = int(height_str)
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass

    return (1920, 1080)
