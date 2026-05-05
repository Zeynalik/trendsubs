from PIL import Image, ImageDraw, ImageFont

from trendsubs.core.models import SubtitleCue, WordSlice
from trendsubs.core.word_jump_overlay import _active_cue, _active_word_index, _jump_position, _layout_words


def test_active_word_index_follows_word_timings():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two",
        lines=["one two"],
        word_slices=[
            WordSlice(text="one", start_ms=1000, end_ms=2000, is_punctuation=False),
            WordSlice(text="two", start_ms=2000, end_ms=3000, is_punctuation=False),
        ],
    )

    assert _active_word_index(cue, 1200) == 0
    assert _active_word_index(cue, 2400) == 1


def test_jump_position_moves_between_words_with_arc():
    x, y = _jump_position(
        previous_center=(100, 300),
        target_center=(300, 300),
        progress=0.5,
        jump_height=80,
    )

    assert x == 200
    assert y == 220


def test_active_cue_stops_at_end_time():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=2000,
        text="one",
        lines=["one"],
        word_slices=[WordSlice(text="one", start_ms=1000, end_ms=2000, is_punctuation=False)],
    )

    assert _active_cue([cue], 1999) == cue
    assert _active_cue([cue], 2000) is None


def test_layout_words_wraps_by_max_words_per_line():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two three four",
        lines=["one two three four"],
        word_slices=[
            WordSlice(text="one", start_ms=1000, end_ms=1500, is_punctuation=False),
            WordSlice(text="two", start_ms=1500, end_ms=2000, is_punctuation=False),
            WordSlice(text="three", start_ms=2000, end_ms=2500, is_punctuation=False),
            WordSlice(text="four", start_ms=2500, end_ms=3000, is_punctuation=False),
        ],
    )
    image = Image.new("RGBA", (420, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    boxes = _layout_words(
        draw=draw,
        cue=cue,
        play_res=(420, 240),
        font=ImageFont.load_default(),
        font_size=32,
        bottom_margin=40,
        safe_area_offset=0,
        max_words_per_line=2,
    )

    assert boxes[0][1][1] == boxes[1][1][1]
    assert boxes[2][1][1] > boxes[0][1][1]
    assert boxes[2][1][0] < boxes[1][1][0]
