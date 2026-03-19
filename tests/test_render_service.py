from pathlib import Path

from trendsubs.core.models import RenderOptions
from trendsubs.core.render_service import render_subtitled_video


def test_render_subtitled_video_generates_ass_and_invokes_ffmpeg(tmp_path: Path):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")

    captured: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        captured.append(command)

    options = RenderOptions(
        preset="social-pop",
        font_path=str(font_path),
        accent_color="#FFD84D",
        font_size=64,
        bottom_margin=120,
        keep_ass=True,
    )

    result = render_subtitled_video(
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        options=options,
        command_runner=fake_runner,
    )

    assert result.ass_path is not None
    assert result.ass_path.exists()
    ass_text = result.ass_path.read_text(encoding="utf-8")
    assert "Hello" in ass_text
    assert "PlayResX: 1920" in ass_text
    assert "PlayResY: 1080" in ass_text
    assert captured and captured[0][-1] == str(output_path)
    assert any("fontsdir=" in part for part in captured[0])


def test_render_subtitled_video_removes_intermediate_ass_when_disabled(tmp_path: Path):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")

    result = render_subtitled_video(
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#FFD84D",
            font_size=64,
            bottom_margin=120,
            keep_ass=False,
        ),
        command_runner=lambda command: None,
    )

    assert result.ass_path is None
    assert not output_path.with_suffix(".ass").exists()
