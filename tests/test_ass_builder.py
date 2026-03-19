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


def test_build_ass_document_can_disable_auto_font_scale():
    cue = SubtitleCue(
        index=1,
        start_ms=0,
        end_ms=2000,
        text="long subtitle text for testing disabled scaling behavior in style output",
        lines=["long subtitle text for testing disabled scaling behavior in style output"],
    )
    cue.word_slices = [WordSlice(text="word", start_ms=0, end_ms=2000, is_punctuation=False)]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        auto_font_scale=False,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert "Style: SocialPop,MyFont,40," in ass_text


def test_build_ass_document_reveal_mode_adds_incremental_dialogues_without_k_tags():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two three",
        lines=["one two three"],
    )
    cue.word_slices = [
        WordSlice(text="one", start_ms=1000, end_ms=1600, is_punctuation=False),
        WordSlice(text="two", start_ms=1600, end_ms=2200, is_punctuation=False),
        WordSlice(text="three", start_ms=2200, end_ms=3000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        mode="reveal",
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]

    assert len(dialogue_lines) == 3
    assert "\\k" not in ass_text
    assert dialogue_lines[0].endswith("one")
    assert dialogue_lines[1].endswith("one two")
    assert dialogue_lines[2].endswith("one two three")


def test_build_ass_document_applies_safe_area_and_max_words_per_line():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two three four five",
        lines=["one two three four five"],
    )
    cue.word_slices = [
        WordSlice(text="one", start_ms=1000, end_ms=1400, is_punctuation=False),
        WordSlice(text="two", start_ms=1400, end_ms=1800, is_punctuation=False),
        WordSlice(text="three", start_ms=1800, end_ms=2200, is_punctuation=False),
        WordSlice(text="four", start_ms=2200, end_ms=2600, is_punctuation=False),
        WordSlice(text="five", start_ms=2600, end_ms=3000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        mode="reveal",
        safe_area_offset=30,
        max_words_per_line=2,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert ",80,80,150,1" in ass_text
    assert "\\N" in ass_text


def test_build_ass_document_max_words_per_line_applies_multiple_breaks():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=4000,
        text="one two three four five six seven eight nine",
        lines=["one two three four five six seven eight nine"],
    )
    cue.word_slices = [
        WordSlice(text="one", start_ms=1000, end_ms=1300, is_punctuation=False),
        WordSlice(text="two", start_ms=1300, end_ms=1600, is_punctuation=False),
        WordSlice(text="three", start_ms=1600, end_ms=1900, is_punctuation=False),
        WordSlice(text="four", start_ms=1900, end_ms=2200, is_punctuation=False),
        WordSlice(text="five", start_ms=2200, end_ms=2500, is_punctuation=False),
        WordSlice(text="six", start_ms=2500, end_ms=2800, is_punctuation=False),
        WordSlice(text="seven", start_ms=2800, end_ms=3100, is_punctuation=False),
        WordSlice(text="eight", start_ms=3100, end_ms=3400, is_punctuation=False),
        WordSlice(text="nine", start_ms=3400, end_ms=4000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        mode="highlight",
        max_words_per_line=4,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert ass_text.count("\\N") >= 2


def test_build_ass_document_reveal_mode_applies_multiple_breaks():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=4000,
        text="one two three four five six seven eight nine",
        lines=["one two three four five six seven eight nine"],
    )
    cue.word_slices = [
        WordSlice(text="one", start_ms=1000, end_ms=1300, is_punctuation=False),
        WordSlice(text="two", start_ms=1300, end_ms=1600, is_punctuation=False),
        WordSlice(text="three", start_ms=1600, end_ms=1900, is_punctuation=False),
        WordSlice(text="four", start_ms=1900, end_ms=2200, is_punctuation=False),
        WordSlice(text="five", start_ms=2200, end_ms=2500, is_punctuation=False),
        WordSlice(text="six", start_ms=2500, end_ms=2800, is_punctuation=False),
        WordSlice(text="seven", start_ms=2800, end_ms=3100, is_punctuation=False),
        WordSlice(text="eight", start_ms=3100, end_ms=3400, is_punctuation=False),
        WordSlice(text="nine", start_ms=3400, end_ms=4000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        mode="reveal",
        max_words_per_line=4,
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]

    assert dialogue_lines[-1].endswith("one two three four\\Nfive six seven eight\\Nnine")


def test_build_ass_document_highlight_mode_uses_accent_as_primary_color():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=2000,
        text="hello world",
        lines=["hello world"],
    )
    cue.word_slices = [
        WordSlice(text="hello", start_ms=1000, end_ms=1500, is_punctuation=False),
        WordSlice(text="world", start_ms=1500, end_ms=2000, is_punctuation=False),
    ]
    options = RenderOptions(
        preset="social-pop",
        font_path="C:\\Fonts\\MyFont.ttf",
        accent_color="#FFD84D",
        font_size=40,
        bottom_margin=120,
        keep_ass=False,
        mode="highlight",
    )

    ass_text = build_ass_document([cue], options, play_res=(1920, 1080))

    assert "&H004DD8FF,&H00FFFFFF" in ass_text
