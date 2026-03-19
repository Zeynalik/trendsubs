from __future__ import annotations

from pathlib import Path

from trendsubs.core.font_utils import resolve_ass_font_name
from trendsubs.core.models import RenderOptions, SubtitleCue
from trendsubs.core.presets import PRESETS


def build_ass_document(
    cues: list[SubtitleCue],
    options: RenderOptions,
    play_res: tuple[int, int] = (1920, 1080),
) -> str:
    preset = PRESETS[options.preset]
    font_name = resolve_ass_font_name(options.font_path)
    accent_color = _hex_to_ass_bgr(options.accent_color)
    style_name = str(preset["style_name"])
    play_res_x, play_res_y = play_res
    effective_font_size = _resolve_effective_font_size(
        requested_size=options.font_size,
        play_res_y=play_res_y,
        cues=cues,
    )

    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            f"PlayResX: {play_res_x}",
            f"PlayResY: {play_res_y}",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding",
            "Style: "
            f"{style_name},{font_name},{effective_font_size},{preset['primary_color']},{accent_color},"
            f"{preset['outline_color']},&H00000000,{preset['bold']},0,0,0,100,100,0,0,1,"
            f"{preset['outline']},{preset['shadow']},{preset['alignment']},80,80,{options.bottom_margin},1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
    )

    dialogue_lines = [
        "Dialogue: 0,"
        f"{_format_ass_timestamp(cue.start_ms)},{_format_ass_timestamp(cue.end_ms)},{style_name},,"
        "0,0,0,,"
        f"{_build_karaoke_text(cue, options.preset)}"
        for cue in cues
    ]
    return f"{header}\n" + "\n".join(dialogue_lines) + "\n"


def _build_karaoke_text(cue: SubtitleCue, preset: str) -> str:
    parts: list[str] = []
    break_index = _resolve_line_break_index(cue)
    for index, word in enumerate(cue.word_slices):
        duration_cs = max(1, round((word.end_ms - word.start_ms) / 10))
        token = word.text.upper() if preset == "impact-caps" else word.text
        if break_index is not None and index == break_index:
            token = r"\N" + token
        parts.append(rf"{{\k{duration_cs}}}{token}")
    return " ".join(parts)


def _resolve_line_break_index(cue: SubtitleCue) -> int | None:
    token_count = len(cue.word_slices)
    if token_count < 2:
        return None

    if len(cue.lines) > 1:
        first_line_words = len(cue.lines[0].split())
        if 0 < first_line_words < token_count:
            return first_line_words

    words = [token.text for token in cue.word_slices]
    joined = " ".join(words)
    if token_count < 5 and len(joined) <= 28:
        return None

    half = len(joined) / 2
    best_index = None
    best_delta = None
    for index in range(1, token_count):
        left_len = len(" ".join(words[:index]))
        delta = abs(left_len - half)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_index = index

    return best_index


def _format_ass_timestamp(milliseconds: int) -> str:
    total_seconds, centiseconds = divmod(milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds // 10:02d}"


def _hex_to_ass_bgr(color: str) -> str:
    normalized = color.lstrip("#")
    red = normalized[0:2]
    green = normalized[2:4]
    blue = normalized[4:6]
    return f"&H00{blue}{green}{red}".upper()


def _resolve_effective_font_size(requested_size: int, play_res_y: int, cues: list[SubtitleCue]) -> int:
    longest_line = 0
    for cue in cues:
        text = cue.text.replace("\n", " ").strip()
        longest_line = max(longest_line, len(text))

    length_factor = 1.0
    if longest_line >= 56:
        length_factor = 0.62
    elif longest_line >= 44:
        length_factor = 0.72
    elif longest_line >= 34:
        length_factor = 0.82

    resolution_factor = min(1.0, max(0.65, play_res_y / 1080))
    return max(24, round(requested_size * length_factor * resolution_factor))
