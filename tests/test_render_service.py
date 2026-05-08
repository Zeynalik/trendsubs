from pathlib import Path

from PIL import Image

from trendsubs.core.models import RenderOptions, SubtitleCue, WordSlice
from trendsubs.core.render_service import (
    _apply_caption_word_limit,
    _build_mascot_overlay_cues,
    _default_mascot_path,
    _non_word_pill_mascot_anchor_offset,
    render_preview_frame,
    render_subtitled_video,
)


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
        mascot_enabled=False,
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
            mascot_enabled=False,
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
            mascot_enabled=False,
        ),
        command_runner=lambda command: None,
    )

    assert result.ass_path is not None
    ass_text = result.ass_path.read_text(encoding="utf-8")
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == 3


def test_render_subtitled_video_word_pill_uses_jump_overlay_renderer(tmp_path: Path, monkeypatch):
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
    called = {}

    def fake_runner(command: list[str]) -> None:
        captured.append(command)

    def fake_overlay_renderer(**kwargs) -> Path:
        called.update(kwargs)
        overlay_path = kwargs["output_path"]
        overlay_path.write_bytes(b"overlay")
        return overlay_path

    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_overlay", fake_overlay_renderer)

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
            mode="word-pill",
            max_words_per_line=2,
            character_name="alt_girl",
            mascot_enabled=False,
            mascot_position="right",
        ),
        command_runner=fake_runner,
    )

    assert result.ass_path is None
    assert called["font_path"] == font_path
    assert called["play_res"] == (1920, 1080)
    assert called["max_words_per_line"] == 2
    assert called["active_fill_color"] == (255, 216, 77, 255)
    assert called["active_text_color"] == (255, 255, 255, 255)
    assert called["inactive_text_color"] == (255, 255, 255, 230)
    assert called["outline_color"] == (16, 16, 16, 230)
    assert called["outline_width"] == 3
    assert called["mascot_enabled"] is False
    assert called["mascot_image_path"] == _default_mascot_path("alt_girl")
    assert called["mascot_position"] == "right"
    assert captured
    assert "-filter_complex" in captured[-1]
    assert "overlay=0:0:format=auto" in captured[-1][captured[-1].index("-filter_complex") + 1]


def test_render_subtitled_video_word_pill_passes_two_character_layers(tmp_path: Path, monkeypatch):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text("1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n", encoding="utf-8")
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    called = {}

    def fake_overlay_renderer(**kwargs) -> Path:
        called.update(kwargs)
        overlay_path = kwargs["output_path"]
        overlay_path.write_bytes(b"overlay")
        return overlay_path

    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_overlay", fake_overlay_renderer)

    render_subtitled_video(
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
            mode="word-pill",
            mascot_enabled=True,
            character_name="alt_girl",
            mascot_position="left",
            character_2_name="man",
            character_2_position="below",
        ),
        command_runner=lambda command: None,
    )

    assert called["mascot_layers"] == [
        (_default_mascot_path("alt_girl"), "left"),
        (_default_mascot_path("man"), "below"),
    ]


def test_render_subtitled_video_word_pill_applies_auto_font_scale(tmp_path: Path, monkeypatch):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\n"
        "This is a very long subtitle line that should scale down for word pill rendering\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    called = {}

    def fake_overlay_renderer(**kwargs) -> Path:
        called.update(kwargs)
        overlay_path = kwargs["output_path"]
        overlay_path.write_bytes(b"overlay")
        return overlay_path

    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_overlay", fake_overlay_renderer)

    render_subtitled_video(
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#FFD84D",
            font_size=100,
            bottom_margin=120,
            keep_ass=False,
            mode="word-pill",
            auto_font_scale=True,
        ),
        command_runner=lambda command: None,
    )

    assert called["font_size"] == 62


def test_render_subtitled_video_word_pill_can_disable_stroke(tmp_path: Path, monkeypatch):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    called = {}

    def fake_overlay_renderer(**kwargs) -> Path:
        called.update(kwargs)
        overlay_path = kwargs["output_path"]
        overlay_path.write_bytes(b"overlay")
        return overlay_path

    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_overlay", fake_overlay_renderer)

    render_subtitled_video(
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#00A3FF",
            font_size=64,
            bottom_margin=120,
            keep_ass=False,
            mode="word-pill",
            mascot_enabled=False,
            stroke_enabled=False,
        ),
        command_runner=lambda command: None,
    )

    assert called["active_fill_color"] == (0, 163, 255, 255)
    assert called["outline_width"] == 0


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
            mascot_enabled=False,
        ),
        command_runner=fake_runner,
    )

    assert out == preview_path
    assert preview_path.exists()
    assert captured and "-frames:v" in captured[0]
    assert captured[0][captured[0].index("-ss") + 1] == "1.200"
    assert not preview_path.with_suffix(".preview.ass").exists()


def test_render_preview_frame_word_pill_uses_jump_overlay_frame(tmp_path: Path, monkeypatch):
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
    called = {}

    def fake_runner(command: list[str]) -> None:
        captured.append(command)
        preview_path.write_bytes(b"png")

    def fake_overlay_frame(**kwargs) -> Path:
        called.update(kwargs)
        overlay_path = kwargs["output_path"]
        overlay_path.write_bytes(b"overlay png")
        return overlay_path

    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_frame", fake_overlay_frame)

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
            mode="word-pill",
            max_words_per_line=2,
            mascot_enabled=False,
        ),
        command_runner=fake_runner,
    )

    assert out == preview_path
    assert called["at_ms"] == 1200
    assert called["play_res"] == (1920, 1080)
    assert called["max_words_per_line"] == 2
    assert called["active_fill_color"] == (255, 216, 77, 255)
    assert called["mascot_enabled"] is False
    assert captured and "-filter_complex" in captured[0]
    assert "overlay=0:0:format=auto" in captured[0][captured[0].index("-filter_complex") + 1]
    assert not preview_path.with_suffix(".word_jump.png").exists()
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
            mascot_enabled=False,
        ),
        command_runner=fake_runner,
    )

    assert captured
    assert captured[0][captured[0].index("-ss") + 1] == "11.000"


def test_render_subtitled_video_non_word_pill_can_overlay_mascot(tmp_path: Path, monkeypatch):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    mascot_path = tmp_path / "mascot.png"
    output_path = tmp_path / "output.mp4"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(mascot_path)

    captured: list[list[str]] = []
    called = {}

    def fake_runner(command: list[str]) -> None:
        captured.append(command)

    def fake_overlay_renderer(**kwargs) -> Path:
        called.update(kwargs)
        overlay_out = kwargs["output_path"]
        overlay_out.write_bytes(b"overlay")
        return overlay_out

    monkeypatch.setattr("trendsubs.core.render_service._default_mascot_path", lambda character_name="farik": mascot_path)
    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_overlay", fake_overlay_renderer)

    render_subtitled_video(
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
            mode="word",
            mascot_enabled=True,
            mascot_position="left",
        ),
        command_runner=fake_runner,
    )

    assert called["draw_subtitles"] is False
    assert called["mascot_anchor_offset_y"] == 77
    assert called["mascot_enabled"] is True
    assert called["mascot_image_path"] == mascot_path
    assert called["mascot_position"] == "left"
    assert len(captured) == 2
    assert "-filter_complex" in captured[1]
    assert "overlay=0:0:format=auto" in captured[1][captured[1].index("-filter_complex") + 1]


def test_render_preview_frame_non_word_pill_can_overlay_mascot(tmp_path: Path, monkeypatch):
    srt_path = tmp_path / "input.srt"
    video_path = tmp_path / "input.mp4"
    font_path = tmp_path / "font.ttf"
    mascot_path = tmp_path / "mascot.png"
    preview_path = tmp_path / "preview.png"

    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello brave world\n",
        encoding="utf-8",
    )
    video_path.write_bytes(b"video")
    font_path.write_bytes(b"font")
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(mascot_path)

    called = {}

    def fake_runner(command: list[str]) -> None:
        if command and command[-1].endswith(".png"):
            Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)).save(command[-1])

    def fake_overlay_frame(**kwargs) -> Path:
        called.update(kwargs)
        Image.new("RGBA", (1920, 1080), (0, 0, 255, 80)).save(kwargs["output_path"])
        return kwargs["output_path"]

    monkeypatch.setattr("trendsubs.core.render_service._default_mascot_path", lambda character_name="farik": mascot_path)
    monkeypatch.setattr("trendsubs.core.render_service.render_word_jump_frame", fake_overlay_frame)

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
            mode="word",
            mascot_enabled=True,
            mascot_position="below",
        ),
        command_runner=fake_runner,
    )

    assert out == preview_path
    assert preview_path.exists()
    assert called["draw_subtitles"] is False
    assert called["mascot_anchor_offset_y"] == 48
    assert called["mascot_enabled"] is True
    assert called["mascot_image_path"] == mascot_path
    assert called["mascot_position"] == "below"


def test_non_word_pill_mascot_anchor_offset_places_character_on_ass_text():
    assert _non_word_pill_mascot_anchor_offset(80) == 96


def test_default_mascot_path_can_select_alt_girl_asset():
    mascot_path = _default_mascot_path("alt_girl")

    assert mascot_path is not None
    assert mascot_path.name == "alt_girl_character.png"
    assert mascot_path.exists()


def test_default_mascot_path_can_select_man_asset():
    mascot_path = _default_mascot_path("man")

    assert mascot_path is not None
    assert mascot_path.name == "man_character.png"
    assert mascot_path.exists()


def test_word_mode_mascot_overlay_cues_follow_single_displayed_words():
    cue = SubtitleCue(
        index=1,
        start_ms=0,
        end_ms=900,
        text="one two",
        lines=["one two"],
        word_slices=[
            WordSlice(text="one", start_ms=0, end_ms=450, is_punctuation=False),
            WordSlice(text="two", start_ms=450, end_ms=900, is_punctuation=False),
        ],
    )

    overlay_cues = _build_mascot_overlay_cues([cue], mode="word", preset="social-pop")

    assert [cue.text for cue in overlay_cues] == ["one", "two"]
    assert [cue.start_ms for cue in overlay_cues] == [0, 450]
    assert [cue.end_ms for cue in overlay_cues] == [450, 900]


def test_word_mode_mascot_overlay_cues_match_ass_grouped_word_units():
    cue = SubtitleCue(
        index=1,
        start_ms=0,
        end_ms=500,
        text="da qadınlar",
        lines=["da qadınlar"],
        word_slices=[
            WordSlice(text="da", start_ms=0, end_ms=90, is_punctuation=False),
            WordSlice(text="qadınlar", start_ms=90, end_ms=500, is_punctuation=False),
        ],
    )

    overlay_cues = _build_mascot_overlay_cues([cue], mode="word", preset="social-pop")

    assert [cue.text for cue in overlay_cues] == ["da qadınlar"]
    assert [cue.start_ms for cue in overlay_cues] == [0]
    assert [cue.end_ms for cue in overlay_cues] == [500]
