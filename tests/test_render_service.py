from pathlib import Path

from trendsubs.core.models import RenderOptions, SubtitleCue, WordSlice
from trendsubs.core.render_service import _apply_caption_word_limit, render_preview_frame, render_subtitled_video


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


def test_render_subtitled_video_splits_long_cue_by_max_words_per_caption(tmp_path: Path):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:05,000\none two three four five six seven eight nine\n",
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
            keep_ass=True,
            max_words_per_caption=4,
        ),
        command_runner=lambda command: None,
    )

    assert result.ass_path is not None
    ass_text = result.ass_path.read_text(encoding="utf-8")
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == 3


def test_apply_caption_word_limit_balances_chunks_without_one_word_tail():
    cue = SubtitleCue(
        index=1,
        start_ms=0,
        end_ms=600,
        text="one two three four five six",
        lines=["one two three four five six"],
        word_slices=[
            WordSlice(text="one", start_ms=0, end_ms=100, is_punctuation=False),
            WordSlice(text="two", start_ms=100, end_ms=200, is_punctuation=False),
            WordSlice(text="three", start_ms=200, end_ms=300, is_punctuation=False),
            WordSlice(text="four", start_ms=300, end_ms=400, is_punctuation=False),
            WordSlice(text="five", start_ms=400, end_ms=500, is_punctuation=False),
            WordSlice(text="six", start_ms=500, end_ms=600, is_punctuation=False),
        ],
    )

    limited = _apply_caption_word_limit([cue], max_words_per_caption=5)

    assert len(limited) == 2
    assert [len(chunk.word_slices) for chunk in limited] == [3, 3]
    assert limited[0].text == "one two three"
    assert limited[1].text == "four five six"


def test_render_preview_frame_runs_ffmpeg_preview_and_cleans_ass(tmp_path: Path):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    preview_path = tmp_path / "preview.png"
    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    captured: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        captured.append(command)
        preview_path.write_bytes(b"png")

    out = render_preview_frame(
        video_path=video_path,
        srt_path=srt_path,
        output_image_path=preview_path,
        at_seconds=1.2,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#FFD84D",
            font_size=40,
            bottom_margin=120,
            keep_ass=False,
        ),
        command_runner=fake_runner,
    )

    assert out == preview_path
    assert preview_path.exists()
    assert captured and "-frames:v" in captured[0]
    assert captured[0][captured[0].index("-ss") + 1] == "1.200"
    assert not preview_path.with_suffix(".preview.ass").exists()


def test_render_preview_frame_shifts_to_nearest_subtitle_when_requested_second_has_no_text(tmp_path: Path):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    preview_path = tmp_path / "preview.png"
    srt_path.write_text(
        "1\n00:00:10,000 --> 00:00:12,000\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    captured: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        captured.append(command)
        preview_path.write_bytes(b"png")

    render_preview_frame(
        video_path=video_path,
        srt_path=srt_path,
        output_image_path=preview_path,
        at_seconds=1.0,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#FFD84D",
            font_size=40,
            bottom_margin=120,
            keep_ass=False,
        ),
        command_runner=fake_runner,
    )

    assert captured
    assert captured[0][captured[0].index("-ss") + 1] == "11.000"
