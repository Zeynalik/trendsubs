from trendsubs.core.word_timing import split_cue_into_word_slices


def test_split_cue_into_word_slices_covers_full_duration_and_marks_punctuation():
    slices = split_cue_into_word_slices(
        text="Hello, brave new world!",
        start_ms=1000,
        end_ms=2600,
    )

    assert [item.text for item in slices] == ["Hello,", "brave", "new", "world!"]
    assert slices[0].is_punctuation is False
    assert slices[-1].is_punctuation is False
    assert slices[0].start_ms == 1000
    assert slices[-1].end_ms == 2600
    assert all(item.start_ms < item.end_ms for item in slices)


def test_split_cue_into_word_slices_marks_pure_punctuation_token():
    slices = split_cue_into_word_slices(
        text="Hello , world",
        start_ms=0,
        end_ms=900,
    )

    assert [item.text for item in slices] == ["Hello", ",", "world"]
    assert slices[1].is_punctuation is True
