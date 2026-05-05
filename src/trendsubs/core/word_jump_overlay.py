from __future__ import annotations

from pathlib import Path
import math
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from trendsubs.core.models import SubtitleCue, WordSlice


FrameCenter = tuple[int, int]
WordBox = tuple[WordSlice, tuple[int, int, int, int], tuple[int, int]]
WordMeasurement = tuple[WordSlice, tuple[int, int, int, int], int, int]
RgbaColor = tuple[int, int, int, int]


def render_word_jump_overlay(
    *,
    cues: list[SubtitleCue],
    output_path: Path,
    play_res: tuple[int, int],
    font_path: Path,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int = 0,
    max_words_per_line: int = 0,
    active_fill_color: RgbaColor = (0, 118, 255, 235),
    active_text_color: RgbaColor = (255, 255, 255, 255),
    inactive_text_color: RgbaColor = (255, 255, 255, 230),
    outline_color: RgbaColor = (0, 0, 0, 210),
    outline_width: int = 3,
    fps: int = 30,
    command_runner=None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = play_res
    total_ms = max((cue.end_ms for cue in cues), default=0)
    frame_count = max(1, math.ceil(total_ms / 1000 * fps) + 1)
    font = _load_font(font_path=font_path, font_size=font_size)

    with tempfile.TemporaryDirectory(prefix="trendsubs_word_jump_") as temp_dir:
        frames_dir = Path(temp_dir)
        for frame_index in range(frame_count):
            at_ms = round(frame_index * 1000 / fps)
            frame = _build_word_jump_frame(
                cues=cues,
                at_ms=at_ms,
                play_res=(width, height),
                font=font,
                font_size=font_size,
                bottom_margin=bottom_margin,
                safe_area_offset=safe_area_offset,
                max_words_per_line=max_words_per_line,
                active_fill_color=active_fill_color,
                active_text_color=active_text_color,
                inactive_text_color=inactive_text_color,
                outline_color=outline_color,
                outline_width=outline_width,
            )
            frame.save(frames_dir / f"{frame_index:06d}.png")

        command = [
            _resolve_ffmpeg_executable(),
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "%06d.png"),
            "-c:v",
            "qtrle",
            "-pix_fmt",
            "argb",
            str(output_path),
        ]
        runner = command_runner or _run_command
        runner(command)

    return output_path


def render_word_jump_frame(
    *,
    cues: list[SubtitleCue],
    output_path: Path,
    at_ms: int,
    play_res: tuple[int, int],
    font_path: Path,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int = 0,
    max_words_per_line: int = 0,
    active_fill_color: RgbaColor = (0, 118, 255, 235),
    active_text_color: RgbaColor = (255, 255, 255, 255),
    inactive_text_color: RgbaColor = (255, 255, 255, 230),
    outline_color: RgbaColor = (0, 0, 0, 210),
    outline_width: int = 3,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font = _load_font(font_path=font_path, font_size=font_size)
    frame = _build_word_jump_frame(
        cues=cues,
        at_ms=at_ms,
        play_res=play_res,
        font=font,
        font_size=font_size,
        bottom_margin=bottom_margin,
        safe_area_offset=safe_area_offset,
        max_words_per_line=max_words_per_line,
        active_fill_color=active_fill_color,
        active_text_color=active_text_color,
        inactive_text_color=inactive_text_color,
        outline_color=outline_color,
        outline_width=outline_width,
    )
    frame.save(output_path)
    return output_path


def _active_word_index(cue: SubtitleCue, at_ms: int) -> int:
    words = _display_words(cue)
    if not words:
        return 0

    for index, word in enumerate(words):
        if word.start_ms <= at_ms < word.end_ms:
            return index

    if at_ms < words[0].start_ms:
        return 0
    return len(words) - 1


def _jump_position(
    *,
    previous_center: FrameCenter,
    target_center: FrameCenter,
    progress: float,
    jump_height: int,
) -> FrameCenter:
    normalized = max(0.0, min(1.0, progress))
    x = previous_center[0] + (target_center[0] - previous_center[0]) * normalized
    y = previous_center[1] + (target_center[1] - previous_center[1]) * normalized
    arc = 4 * normalized * (1 - normalized)
    return round(x), round(y - jump_height * arc)


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _resolve_ffmpeg_executable() -> str:
    local_ffmpeg = shutil.which("ffmpeg")
    return local_ffmpeg or "ffmpeg"


def _load_font(*, font_path: Path, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(font_path), font_size)
    except OSError as error:
        raise OSError(f"Unable to load font file: {font_path}") from error


def _active_cue(cues: list[SubtitleCue], at_ms: int) -> SubtitleCue | None:
    for cue in cues:
        if cue.start_ms <= at_ms < cue.end_ms:
            return cue
    return None


def _build_word_jump_frame(
    *,
    cues: list[SubtitleCue],
    at_ms: int,
    play_res: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int,
    max_words_per_line: int,
    active_fill_color: RgbaColor,
    active_text_color: RgbaColor,
    inactive_text_color: RgbaColor,
    outline_color: RgbaColor,
    outline_width: int,
) -> Image.Image:
    frame = Image.new("RGBA", play_res, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    cue = _active_cue(cues, at_ms)
    if cue is not None:
        _draw_cue_frame(
            draw=draw,
            cue=cue,
            at_ms=at_ms,
            play_res=play_res,
            font=font,
            font_size=font_size,
            bottom_margin=bottom_margin,
            safe_area_offset=safe_area_offset,
            max_words_per_line=max_words_per_line,
            active_fill_color=active_fill_color,
            active_text_color=active_text_color,
            inactive_text_color=inactive_text_color,
            outline_color=outline_color,
            outline_width=outline_width,
        )
    return frame


def _draw_cue_frame(
    *,
    draw: ImageDraw.ImageDraw,
    cue: SubtitleCue,
    at_ms: int,
    play_res: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int,
    max_words_per_line: int,
    active_fill_color: RgbaColor,
    active_text_color: RgbaColor,
    inactive_text_color: RgbaColor,
    outline_color: RgbaColor,
    outline_width: int,
) -> None:
    word_boxes = _layout_words(
        draw=draw,
        cue=cue,
        play_res=play_res,
        font=font,
        font_size=font_size,
        bottom_margin=bottom_margin,
        safe_area_offset=safe_area_offset,
        max_words_per_line=max_words_per_line,
        outline_width=outline_width,
    )
    if not word_boxes:
        return

    active_index = _active_word_index(cue, at_ms)
    for index, (word, box, origin) in enumerate(word_boxes):
        if index == active_index:
            _draw_active_word(
                draw=draw,
                word=word.text,
                box=box,
                origin=origin,
                font=font,
                font_size=font_size,
                active_fill_color=active_fill_color,
                active_text_color=active_text_color,
                outline_color=outline_color,
                outline_width=outline_width,
            )
        else:
            _draw_inactive_word(
                draw=draw,
                word=word.text,
                origin=origin,
                font=font,
                font_size=font_size,
                inactive_text_color=inactive_text_color,
                outline_color=outline_color,
                outline_width=outline_width,
            )

    previous_index = max(0, active_index - 1)
    current_word = word_boxes[active_index][0]
    previous_center = _mascot_anchor(word_boxes[previous_index][1])
    target_center = _mascot_anchor(word_boxes[active_index][1])
    word_duration = max(1, current_word.end_ms - current_word.start_ms)
    jump_ms = min(420, word_duration)
    progress = (at_ms - current_word.start_ms) / jump_ms
    mascot_center = _jump_position(
        previous_center=previous_center,
        target_center=target_center,
        progress=progress,
        jump_height=max(42, round(font_size * 0.85)),
    )
    _draw_retro_plumber(draw=draw, center=mascot_center, scale=max(0.7, font_size / 72))


def _layout_words(
    *,
    draw: ImageDraw.ImageDraw,
    cue: SubtitleCue,
    play_res: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int,
    max_words_per_line: int = 0,
    outline_width: int = 3,
) -> list[WordBox]:
    words = _display_words(cue)
    if not words:
        return []

    spacing = max(12, round(font_size * 0.28))
    stroke_width = _text_stroke_width(font_size, outline_width)
    measurements: list[WordMeasurement] = []
    for word in words:
        bbox = draw.textbbox((0, 0), word.text, font=font, stroke_width=stroke_width)
        word_width = bbox[2] - bbox[0]
        word_height = bbox[3] - bbox[1]
        measurements.append((word, bbox, word_width, word_height))
    max_width = round(play_res[0] * 0.88)
    rows = _wrap_measurements(
        measurements=measurements,
        spacing=spacing,
        max_width=max_width,
        max_words_per_line=max_words_per_line,
    )

    baseline_y = play_res[1] - bottom_margin - safe_area_offset
    line_gap = max(8, round(font_size * 0.18))
    total_height = sum(max(height for _, _, _, height in row) for row in rows)
    total_height += line_gap * max(0, len(rows) - 1)
    text_top = max(8, baseline_y - total_height)

    boxes: list[WordBox] = []
    y = text_top
    for row in rows:
        row_width = _row_width(row=row, spacing=spacing)
        row_height = max(height for _, _, _, height in row)
        x = max(24, round((play_res[0] - row_width) / 2))
        for word, bbox, word_width, word_height in row:
            visual_box = (x, y, x + word_width, y + word_height)
            origin = (x - bbox[0], y - bbox[1])
            boxes.append((word, visual_box, origin))
            x += word_width + spacing
        y += row_height + line_gap
    return boxes


def _wrap_measurements(
    *,
    measurements: list[WordMeasurement],
    spacing: int,
    max_width: int,
    max_words_per_line: int,
) -> list[list[WordMeasurement]]:
    rows: list[list[WordMeasurement]] = []
    current: list[WordMeasurement] = []
    current_width = 0

    for measurement in measurements:
        word_width = measurement[2]
        next_width = word_width if not current else current_width + spacing + word_width
        explicit_break = max_words_per_line > 0 and len(current) >= max_words_per_line
        width_break = bool(current) and next_width > max_width
        if explicit_break or width_break:
            rows.append(current)
            current = []
            current_width = 0

        current.append(measurement)
        current_width = word_width if current_width == 0 else current_width + spacing + word_width

    if current:
        rows.append(current)
    return rows


def _row_width(*, row: list[WordMeasurement], spacing: int) -> int:
    return sum(measurement[2] for measurement in row) + spacing * max(0, len(row) - 1)


def _display_words(cue: SubtitleCue) -> list[WordSlice]:
    if cue.word_slices:
        return [word for word in cue.word_slices if not word.is_punctuation]
    text = cue.text.replace("\n", " ").strip()
    if not text:
        return []
    pieces = text.split()
    duration = max(1, cue.end_ms - cue.start_ms)
    step = max(1, duration // len(pieces))
    words: list[WordSlice] = []
    for index, piece in enumerate(pieces):
        start_ms = cue.start_ms + index * step
        end_ms = cue.end_ms if index == len(pieces) - 1 else cue.start_ms + (index + 1) * step
        words.append(WordSlice(text=piece, start_ms=start_ms, end_ms=end_ms, is_punctuation=False))
    return words


def _draw_active_word(
    *,
    draw: ImageDraw.ImageDraw,
    word: str,
    box: tuple[int, int, int, int],
    origin: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    active_fill_color: RgbaColor,
    active_text_color: RgbaColor,
    outline_color: RgbaColor,
    outline_width: int,
) -> None:
    pad_x = max(10, round(font_size * 0.28))
    pad_y = max(6, round(font_size * 0.18))
    pill = (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y)
    draw.rounded_rectangle(
        pill,
        radius=max(10, round(font_size * 0.24)),
        fill=active_fill_color,
        outline=(255, 255, 255, 215),
        width=max(2, round(font_size * 0.04)),
    )
    _draw_word_text(
        draw=draw,
        word=word,
        origin=origin,
        font=font,
        font_size=font_size,
        fill=active_text_color,
        outline_color=outline_color,
        outline_width=outline_width,
    )


def _draw_inactive_word(
    *,
    draw: ImageDraw.ImageDraw,
    word: str,
    origin: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    inactive_text_color: RgbaColor,
    outline_color: RgbaColor,
    outline_width: int,
) -> None:
    _draw_word_text(
        draw=draw,
        word=word,
        origin=origin,
        font=font,
        font_size=font_size,
        fill=inactive_text_color,
        outline_color=outline_color,
        outline_width=outline_width,
    )


def _draw_word_text(
    *,
    draw: ImageDraw.ImageDraw,
    word: str,
    origin: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    fill: tuple[int, int, int, int],
    outline_color: RgbaColor,
    outline_width: int,
) -> None:
    draw.text(
        origin,
        word,
        font=font,
        fill=fill,
        stroke_width=_text_stroke_width(font_size, outline_width),
        stroke_fill=outline_color,
    )


def _text_stroke_width(font_size: int, outline_width: int) -> int:
    return max(1, round(outline_width * max(0.8, font_size / 48)))


def _mascot_anchor(box: tuple[int, int, int, int]) -> FrameCenter:
    return round((box[0] + box[2]) / 2), box[1] - 34


def _draw_retro_plumber(
    *,
    draw: ImageDraw.ImageDraw,
    center: FrameCenter,
    scale: float,
) -> None:
    size = round(54 * scale)
    x = center[0] - size // 2
    y = center[1] - size
    s = scale

    def r(value: float) -> int:
        return round(value * s)

    outline = (42, 24, 18, 255)
    skin = (255, 197, 143, 255)
    red = (224, 35, 35, 255)
    blue = (32, 102, 218, 255)
    yellow = (255, 214, 72, 255)
    brown = (96, 55, 30, 255)
    white = (255, 255, 255, 255)

    draw.ellipse((x + r(12), y + r(14), x + r(42), y + r(42)), fill=skin, outline=outline, width=max(1, r(3)))
    draw.rounded_rectangle((x + r(8), y + r(8), x + r(46), y + r(22)), radius=r(8), fill=red, outline=outline, width=max(1, r(3)))
    draw.rectangle((x + r(22), y + r(4), x + r(36), y + r(14)), fill=red, outline=outline, width=max(1, r(2)))
    draw.ellipse((x + r(19), y + r(18), x + r(25), y + r(25)), fill=white, outline=outline, width=max(1, r(1)))
    draw.ellipse((x + r(32), y + r(18), x + r(38), y + r(25)), fill=white, outline=outline, width=max(1, r(1)))
    draw.rectangle((x + r(25), y + r(26), x + r(35), y + r(30)), fill=brown)
    draw.rounded_rectangle((x + r(15), y + r(40), x + r(39), y + r(66)), radius=r(8), fill=blue, outline=outline, width=max(1, r(3)))
    draw.rectangle((x + r(14), y + r(38), x + r(24), y + r(49)), fill=red, outline=outline, width=max(1, r(2)))
    draw.rectangle((x + r(30), y + r(38), x + r(40), y + r(49)), fill=red, outline=outline, width=max(1, r(2)))
    draw.ellipse((x + r(20), y + r(48), x + r(25), y + r(54)), fill=yellow, outline=outline, width=max(1, r(1)))
    draw.ellipse((x + r(31), y + r(48), x + r(36), y + r(54)), fill=yellow, outline=outline, width=max(1, r(1)))
    draw.line((x + r(14), y + r(45), x + r(5), y + r(35)), fill=outline, width=max(2, r(5)))
    draw.line((x + r(40), y + r(45), x + r(49), y + r(35)), fill=outline, width=max(2, r(5)))
    draw.rectangle((x + r(13), y + r(64), x + r(25), y + r(74)), fill=brown, outline=outline, width=max(1, r(2)))
    draw.rectangle((x + r(31), y + r(64), x + r(43), y + r(74)), fill=brown, outline=outline, width=max(1, r(2)))
