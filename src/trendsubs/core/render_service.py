from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from trendsubs.core.ass_builder import build_ass_document
from trendsubs.core.ffmpeg_runner import build_ffmpeg_command
from trendsubs.core.models import RenderOptions
from trendsubs.core.srt_parser import parse_srt_text
from trendsubs.core.word_timing import split_cue_into_word_slices


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

    play_res = _probe_video_resolution(video_path)
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
