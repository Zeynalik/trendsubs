from __future__ import annotations

from trendsubs.core.models import SubtitleCue

import pysubs2


def parse_srt_text(raw_srt: str) -> list[SubtitleCue]:
    normalized = raw_srt.lstrip("\ufeff")
    subtitles = pysubs2.SSAFile.from_string(normalized)

    cues: list[SubtitleCue] = []
    for event in subtitles:
        text = event.plaintext.strip()
        lines = text.splitlines() or [""]
        cues.append(
            SubtitleCue(
                index=len(cues) + 1,
                start_ms=int(event.start),
                end_ms=int(event.end),
                text=text,
                lines=lines,
            )
        )

    return cues
