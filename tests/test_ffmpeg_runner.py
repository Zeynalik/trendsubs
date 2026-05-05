from pathlib import Path

from trendsubs.core.ffmpeg_runner import (
    build_ffmpeg_command,
    build_overlay_command,
    build_overlay_preview_command,
    build_preview_command,
)


def test_build_ffmpeg_command_targets_ass_filter_and_h264_output():
    command = build_ffmpeg_command(
        video_path=Path("input.mp4"),
        ass_path=Path("temp.ass"),
        output_path=Path("output.mp4"),
        font_path=Path("C:/Fonts/Caveat.ttf"),
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "input.mp4"]
    assert any(part.startswith("ass=filename=") and "temp.ass" in part for part in command)
    assert any("fontsdir=" in part for part in command)
    assert "libx264" in command
    assert "aac" in command
    assert command[-1] == "output.mp4"


def test_build_preview_command_targets_single_frame_png():
    command = build_preview_command(
        video_path=Path("input.mp4"),
        ass_path=Path("temp.ass"),
        output_image_path=Path("preview.png"),
        at_seconds=1.5,
        font_path=Path("C:/Fonts/Caveat.ttf"),
    )

    assert command[:2] == ["ffmpeg", "-y"]
    assert "-frames:v" in command
    assert "1" in command
    assert command[-1] == "preview.png"


def test_build_overlay_command_composites_transparent_overlay_video():
    command = build_overlay_command(
        video_path=Path("input.mp4"),
        overlay_path=Path("word_jump.mov"),
        output_path=Path("output.mp4"),
    )

    assert command[:6] == ["ffmpeg", "-y", "-i", "input.mp4", "-i", "word_jump.mov"]
    assert "-filter_complex" in command
    assert "[0:v][1:v]overlay=0:0:format=auto:eof_action=pass[v]" in command
    assert "-map" in command
    assert "[v]" in command
    assert "0:a?" in command
    assert command[-1] == "output.mp4"


def test_build_overlay_preview_command_composites_single_transparent_frame():
    command = build_overlay_preview_command(
        video_path=Path("input.mp4"),
        overlay_image_path=Path("word_jump.png"),
        output_image_path=Path("preview.png"),
        at_seconds=2.5,
    )

    assert command[:6] == ["ffmpeg", "-y", "-ss", "2.500", "-i", "input.mp4"]
    assert "-filter_complex" in command
    assert "[0:v][1:v]overlay=0:0:format=auto[v]" in command
    assert "-frames:v" in command
    assert command[-1] == "preview.png"
