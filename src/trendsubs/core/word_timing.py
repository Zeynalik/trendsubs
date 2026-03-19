from __future__ import annotations

from trendsubs.core.models import WordSlice


PUNCTUATION_CHARS = ",.!?:;"


def split_cue_into_word_slices(text: str, start_ms: int, end_ms: int) -> list[WordSlice]:
    tokens = [token for token in text.split() if token]
    if not tokens:
        return []

    total_duration = max(end_ms - start_ms, len(tokens))
    base_duration = total_duration // len(tokens)
    remainder = total_duration % len(tokens)

    slices: list[WordSlice] = []
    cursor = start_ms
    for index, token in enumerate(tokens):
        extra = 1 if index < remainder else 0
        duration = base_duration + extra
        next_cursor = cursor + duration
        if index == len(tokens) - 1:
            next_cursor = end_ms

        slices.append(
            WordSlice(
                text=token,
                start_ms=cursor,
                end_ms=next_cursor,
                is_punctuation=token[-1] in PUNCTUATION_CHARS,
            )
        )
        cursor = next_cursor

    return slices
