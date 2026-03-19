from trendsubs.core.ass_builder import build_ass_document
from trendsubs.core.models import RenderOptions, SubtitleCue, WordSlice


def test_build_ass_document_includes_style_and_dialogue_line():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=2400,
        text="hello world",
        lines=["hello world"],
    )
    cue.word_slices = [  # type: ignore[attr-defined]
        WordSlice(text="hello", start_ms=1000, end_ms=1600, is_punctuation=False),
        WordSlice(text="world", start_ms=1600, end_ms=2400, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=64,
        bottom_margin=120,
        keep_ass=False,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert "Style: SocialPop,MyFont" in ass_text
    assert "PlayResX: 1920" in ass_text
    assert "PlayResY: 1080" in ass_text
    assert "\\k60" in ass_text
    assert "\\k80" in ass_text
    assert "Dialogue:" in ass_text
    assert "hello" in ass_text
    assert "world" in ass_text


def test_build_ass_document_wraps_long_single_line_into_two_lines():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two three four five six",
        lines=["one two three four five six"],
    )
    cue.word_slices = [
        WordSlice(text="one", start_ms=1000, end_ms=1300, is_punctuation=False),
        WordSlice(text="two", start_ms=1300, end_ms=1600, is_punctuation=False),
        WordSlice(text="three", start_ms=1600, end_ms=1900, is_punctuation=False),
        WordSlice(text="four", start_ms=1900, end_ms=2200, is_punctuation=False),
        WordSlice(text="five", start_ms=2200, end_ms=2600, is_punctuation=False),
        WordSlice(text="six", start_ms=2600, end_ms=3000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=48,
        bottom_margin=120,
        keep_ass=False,
    )

    ass_text = build_ass_document([cue], options, play_res=(1080, 1920))

    assert "\\N" in ass_text


def test_build_ass_document_reduces_font_size_for_very_long_lines():
    cue = SubtitleCue(
        index=1,
        start_ms=0,
        end_ms=2500,
        text="this is a very long subtitle line that should trigger automatic font size reduction for readability",
        lines=[
            "this is a very long subtitle line that should trigger automatic font size reduction for readability"
        ],
    )
    cue.word_slices = [
        WordSlice(text="this", start_ms=0, end_ms=250, is_punctuation=False),
        WordSlice(text="is", start_ms=250, end_ms=500, is_punctuation=False),
        WordSlice(text="a", start_ms=500, end_ms=700, is_punctuation=False),
        WordSlice(text="very", start_ms=700, end_ms=950, is_punctuation=False),
        WordSlice(text="long", start_ms=950, end_ms=1200, is_punctuation=False),
        WordSlice(text="subtitle", start_ms=1200, end_ms=1450, is_punctuation=False),
        WordSlice(text="line", start_ms=1450, end_ms=1700, is_punctuation=False),
        WordSlice(text="that", start_ms=1700, end_ms=1900, is_punctuation=False),
        WordSlice(text="should", start_ms=1900, end_ms=2100, is_punctuation=False),
        WordSlice(text="trigger", start_ms=2100, end_ms=2300, is_punctuation=False),
        WordSlice(text="automatic", start_ms=2300, end_ms=2500, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert "Style: SocialPop,MyFont,25," in ass_text
