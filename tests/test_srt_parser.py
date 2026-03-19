from trendsubs.core.srt_parser import parse_srt_text


def test_parse_srt_text_preserves_multiline_text_and_timings():
    raw_srt = (
        "\ufeff1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "Hello world\n"
        "Second line\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:05,000\n"
        "Final cue\n"
    )

    cues = parse_srt_text(raw_srt)

    assert len(cues) == 2
    assert cues[0].index == 1
    assert cues[0].start_ms == 1000
    assert cues[0].end_ms == 3500
    assert cues[0].lines == ["Hello world", "Second line"]
    assert cues[0].text == "Hello world\nSecond line"
    assert cues[1].text == "Final cue"
