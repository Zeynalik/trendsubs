from __future__ import annotations

from pathlib import Path
import math
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from trendsubs.core.models import SubtitleCue, WordSlice


FrameCenter = tuple[int, int]
WordBox = tuple[WordSlice, tuple[int, int, int, int]]


def render_word_jump_overlay(
    *,
    cues: list[SubtitleCue],
    output_path: Path,
    play_res: tuple[int, int],
    font_path: Path,
    font_size: int,
    bottom_margin: int,
    safe_area_offset: int = 0,
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
    except OSError:
        return ImageFont.load_default()


def _active_cue(cues: list[SubtitleCue], at_ms: int) -> SubtitleCue | None:
    for cue in cues:
        if cue.start_ms <= at_ms <= cue.end_ms:
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
) -> None:
    word_boxes = _layout_words(
        draw=draw,
        cue=cue,
        play_res=play_res,
        font=font,
        font_size=font_size,
        bottom_margin=bottom_margin,
        safe_area_offset=safe_area_offset,
    )
    if not word_boxes:
        return

    active_index = _active_word_index(cue, at_ms)
    for index, (word, box) in enumerate(word_boxes):
        if index == active_index:
            _draw_active_word(draw=draw, word=word.text, box=box, font=font)
        else:
            _draw_inactive_word(draw=draw, word=word.text, box=box, font=font)

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
) -> list[WordBox]:
    words = _display_words(cue)
    if not words:
        return []

    spacing = max(12, round(font_size * 0.28))
    measurements: list[tuple[WordSlice, int, int]] = []
    total_width = 0
    for word in words:
        bbox = draw.textbbox((0, 0), word.text, font=font, stroke_width=max(1, font_size // 18))
        word_width = bbox[2] - bbox[0]
        word_height = bbox[3] - bbox[1]
        measurements.append((word, word_width, word_height))
        total_width += word_width
    total_width += spacing * max(0, len(words) - 1)

    max_width = round(play_res[0] * 0.88)
    if total_width > max_width:
        spacing = max(6, round(spacing * max_width / total_width))

    x = max(24, round((play_res[0] - min(total_width, max_width)) / 2))
    baseline_y = play_res[1] - bottom_margin - safe_area_offset
    text_top = baseline_y - max(height for _, _, height in measurements)
    boxes: list[WordBox] = []
    for word, word_width, word_height in measurements:
        boxes.append((word, (x, text_top, x + word_width, text_top + word_height)))
        x += word_width + spacing
    return boxes


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
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    pad_x = 18
    pad_y = 10
    pill = (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y)
    draw.rounded_rectangle(pill, radius=18, fill=(0, 118, 255, 235), outline=(255, 255, 255, 215), width=3)
    _draw_word_text(draw=draw, word=word, box=box, font=font, fill=(255, 255, 255, 255))


def _draw_inactive_word(
    *,
    draw: ImageDraw.ImageDraw,
    word: str,
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    _draw_word_text(draw=draw, word=word, box=box, font=font, fill=(255, 255, 255, 230))


def _draw_word_text(
    *,
    draw: ImageDraw.ImageDraw,
    word: str,
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    stroke_width = max(2, (box[3] - box[1]) // 12)
    draw.text(
        (box[0], box[1]),
        word,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, 210),
    )


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
