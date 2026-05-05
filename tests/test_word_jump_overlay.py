from pathlib import Path

from trendsubs.core.models import SubtitleCue, WordSlice
from trendsubs.core.word_jump_overlay import _active_word_index, _jump_position


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
