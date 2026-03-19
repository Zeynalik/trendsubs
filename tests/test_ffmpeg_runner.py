from pathlib import Path

from trendsubs.core.ffmpeg_runner import build_ffmpeg_command


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
