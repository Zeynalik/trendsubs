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
    default_text_color = str(preset["primary_color"])
    if options.mode == "highlight":
        # Karaoke highlight should transition from default text color to the selected accent color.
        primary_color = accent_color
        secondary_color = default_text_color
    else:
        primary_color = accent_color
        secondary_color = accent_color
    play_res_x, play_res_y = play_res
    effective_font_size = _resolve_effective_font_size(
        requested_size=options.font_size,
        play_res_y=play_res_y,
        cues=cues,
        auto_font_scale=options.auto_font_scale,
    )
    margin_v = options.bottom_margin + max(0, options.safe_area_offset)

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
            f"{style_name},{font_name},{effective_font_size},{primary_color},{secondary_color},"
            f"{preset['outline_color']},&H00000000,{preset['bold']},0,0,0,100,100,0,0,1,"
            f"{preset['outline']},{preset['shadow']},{preset['alignment']},80,80,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
    )

    dialogue_lines = _build_dialogue_lines(
        cues=cues,
        style_name=style_name,
        mode=options.mode,
        preset=options.preset,
        max_words_per_line=options.max_words_per_line,
    )
    return f"{header}\n" + "\n".join(dialogue_lines) + "\n"


def _build_dialogue_lines(
    cues: list[SubtitleCue],
    style_name: str,
    mode: str,
    preset: str,
    max_words_per_line: int,
) -> list[str]:
    dialogue_lines: list[str] = []
    for cue in cues:
        if mode == "reveal":
            dialogue_lines.extend(
                _build_reveal_dialogue_lines(
                    cue=cue,
                    style_name=style_name,
                    preset=preset,
                    max_words_per_line=max_words_per_line,
                )
            )
            continue

        break_indices = _resolve_line_break_indices(cue, max_words_per_line=max_words_per_line)
        dialogue_lines.append(
            "Dialogue: 0,"
            f"{_format_ass_timestamp(cue.start_ms)},{_format_ass_timestamp(cue.end_ms)},{style_name},,"
            "0,0,0,,"
            f"{_build_karaoke_text(cue, preset, break_indices)}"
        )
    return dialogue_lines


def _build_karaoke_text(cue: SubtitleCue, preset: str, break_indices: list[int]) -> str:
    parts: list[str] = []
    break_set = {index for index in break_indices if 0 < index < len(cue.word_slices)}
    for index, word in enumerate(cue.word_slices):
        duration_cs = max(1, round((word.end_ms - word.start_ms) / 10))
        token = word.text.upper() if preset == "impact-caps" else word.text
        if index in break_set:
            token = r"\N" + token
        parts.append(rf"{{\k{duration_cs}}}{token}")
    return " ".join(parts)


def _build_reveal_dialogue_lines(
    cue: SubtitleCue,
    style_name: str,
    preset: str,
    max_words_per_line: int,
) -> list[str]:
    if not cue.word_slices:
        return []

    words = [item.text.upper() if preset == "impact-caps" else item.text for item in cue.word_slices]
    break_indices = _resolve_line_break_indices(cue, max_words_per_line=max_words_per_line)
    dialogue_lines: list[str] = []

    for index, word in enumerate(cue.word_slices):
        next_start = cue.word_slices[index + 1].start_ms if index + 1 < len(cue.word_slices) else cue.end_ms
        start_ms = word.start_ms
        end_ms = max(start_ms + 1, next_start)
        revealed = _join_words_with_breaks(words[: index + 1], break_indices)
        dialogue_lines.append(
            "Dialogue: 0,"
            f"{_format_ass_timestamp(start_ms)},{_format_ass_timestamp(end_ms)},{style_name},,"
            "0,0,0,,"
            f"{revealed}"
        )

    return dialogue_lines


def _resolve_line_break_indices(cue: SubtitleCue, max_words_per_line: int) -> list[int]:
    token_count = len(cue.word_slices)
    if token_count < 2:
        return []

    if len(cue.lines) > 1:
        breaks: list[int] = []
        cumulative_words = 0
        for line in cue.lines[:-1]:
            cumulative_words += len(line.split())
            if 0 < cumulative_words < token_count:
                breaks.append(cumulative_words)
        if breaks:
            return sorted(set(breaks))

    if max_words_per_line > 0 and token_count > max_words_per_line:
        return list(range(max_words_per_line, token_count, max_words_per_line))

    words = [token.text for token in cue.word_slices]
    joined = " ".join(words)
    if token_count < 5 and len(joined) <= 28:
        return []

    half = len(joined) / 2
    best_index = None
    best_delta = None
    for index in range(1, token_count):
        left_len = len(" ".join(words[:index]))
        delta = abs(left_len - half)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_index = index

    return [best_index] if best_index is not None else []


def _join_words_with_breaks(words: list[str], break_indices: list[int]) -> str:
    valid_breaks = sorted({index for index in break_indices if 0 < index < len(words)})
    if not valid_breaks:
        return " ".join(words)

    chunks: list[str] = []
    previous_index = 0
    for break_index in valid_breaks:
        chunk = " ".join(words[previous_index:break_index]).strip()
        if chunk:
            chunks.append(chunk)
        previous_index = break_index

    tail = " ".join(words[previous_index:]).strip()
    if tail:
        chunks.append(tail)
    return "\\N".join(chunks)


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


def _resolve_effective_font_size(
    requested_size: int,
    play_res_y: int,
    cues: list[SubtitleCue],
    auto_font_scale: bool,
) -> int:
    if not auto_font_scale:
        return max(24, requested_size)

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
