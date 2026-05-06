from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(slots=True)
class MascotSprite:
    frames: list[Image.Image]
    reference_visible_height: int | None = None


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
    mascot_enabled: bool = True,
    mascot_image_path: Path | None = None,
    draw_subtitles: bool = True,
    mascot_anchor_offset_y: int = 0,
    mascot_position: str = "center",
    fps: int = 30,
    command_runner=None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = play_res
    total_ms = max((cue.end_ms for cue in cues), default=0)
    frame_count = max(1, math.ceil(total_ms / 1000 * fps) + 1)
    font = _load_font(font_path=font_path, font_size=font_size)
    mascot_sprite = _load_mascot_sprite(mascot_image_path) if mascot_enabled else None

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
                mascot_enabled=mascot_enabled,
                mascot_sprite=mascot_sprite,
                draw_subtitles=draw_subtitles,
                mascot_anchor_offset_y=mascot_anchor_offset_y,
                mascot_position=mascot_position,
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
    mascot_enabled: bool = True,
    mascot_image_path: Path | None = None,
    draw_subtitles: bool = True,
    mascot_anchor_offset_y: int = 0,
    mascot_position: str = "center",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font = _load_font(font_path=font_path, font_size=font_size)
    mascot_sprite = _load_mascot_sprite(mascot_image_path) if mascot_enabled else None
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
        mascot_enabled=mascot_enabled,
        mascot_sprite=mascot_sprite,
        draw_subtitles=draw_subtitles,
        mascot_anchor_offset_y=mascot_anchor_offset_y,
        mascot_position=mascot_position,
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


def _mascot_jump_duration_ms(word_duration_ms: int) -> int:
    return min(180, max(90, round(word_duration_ms * 0.35)))


def _mascot_jump_height(font_size: int) -> int:
    return max(18, round(font_size * 0.32))


def _mascot_jump_progress(
    *,
    previous_index: int,
    active_index: int,
    at_ms: int,
    word_start_ms: int,
    word_duration_ms: int,
) -> float:
    if previous_index == active_index:
        return 1.0
    return (at_ms - word_start_ms) / _mascot_jump_duration_ms(word_duration_ms)


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


def _load_mascot_image(mascot_image_path: Path | None) -> Image.Image | None:
    if mascot_image_path is None:
        return None
    if not mascot_image_path.exists():
        return None
    try:
        image = Image.open(mascot_image_path).convert("RGBA")
    except OSError:
        return None
    return image


def _load_mascot_sprite(mascot_image_path: Path | None) -> MascotSprite | None:
    base_image = _load_mascot_image(mascot_image_path)
    if base_image is None:
        return None

    if mascot_image_path is None:
        return MascotSprite(frames=[base_image])

    frames_dir = mascot_image_path.with_name(f"{mascot_image_path.stem}_frames")
    frames: list[Image.Image] = []
    if frames_dir.exists() and frames_dir.is_dir():
        for frame_path in sorted(frames_dir.glob("*.png")):
            try:
                frames.append(Image.open(frame_path).convert("RGBA"))
            except OSError:
                continue

    if not frames:
        frames = [base_image]
    reference_visible_height = max((_image_mascot_subject_height(frame) for frame in frames), default=None)
    return MascotSprite(frames=frames, reference_visible_height=reference_visible_height)


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
    mascot_enabled: bool,
    mascot_sprite: MascotSprite | None,
    draw_subtitles: bool,
    mascot_anchor_offset_y: int,
    mascot_position: str,
) -> Image.Image:
    frame = Image.new("RGBA", play_res, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    cue = _active_cue(cues, at_ms)
    if cue is not None:
        _draw_cue_frame(
            frame=frame,
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
            mascot_enabled=mascot_enabled,
            mascot_sprite=mascot_sprite,
            draw_subtitles=draw_subtitles,
            mascot_anchor_offset_y=mascot_anchor_offset_y,
            mascot_position=mascot_position,
        )
    return frame


def _draw_cue_frame(
    *,
    frame: Image.Image,
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
    mascot_enabled: bool,
    mascot_sprite: MascotSprite | None,
    draw_subtitles: bool,
    mascot_anchor_offset_y: int,
    mascot_position: str,
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
    if draw_subtitles:
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

    if mascot_enabled:
        previous_index = max(0, active_index - 1)
        current_word = word_boxes[active_index][0]
        word_duration = max(1, current_word.end_ms - current_word.start_ms)
        action_progress = (at_ms - current_word.start_ms) / word_duration
        mascot_frame = (
            _select_mascot_frame(
                mascot_sprite=mascot_sprite,
                progress=action_progress,
                word_index=_mascot_action_index(cue=cue, active_index=active_index),
            )
            if mascot_sprite is not None
            else None
        )
        previous_center = _mascot_anchor(
            word_boxes[previous_index][1],
            font_size=font_size,
            offset_y=mascot_anchor_offset_y,
            position=mascot_position,
        )
        target_center = _mascot_anchor(
            word_boxes[active_index][1],
            font_size=font_size,
            offset_y=mascot_anchor_offset_y,
            position=mascot_position,
        )
        previous_center = _separate_mascot_from_word(
            center=previous_center,
            word_box=word_boxes[previous_index][1],
            font_size=font_size,
            position=mascot_position,
            mascot_sprite=mascot_sprite,
            mascot_frame=mascot_frame,
        )
        target_center = _separate_mascot_from_word(
            center=target_center,
            word_box=word_boxes[active_index][1],
            font_size=font_size,
            position=mascot_position,
            mascot_sprite=mascot_sprite,
            mascot_frame=mascot_frame,
        )
        jump_progress = _mascot_jump_progress(
            previous_index=previous_index,
            active_index=active_index,
            at_ms=at_ms,
            word_start_ms=current_word.start_ms,
            word_duration_ms=word_duration,
        )
        mascot_center = _jump_position(
            previous_center=previous_center,
            target_center=target_center,
            progress=jump_progress,
            jump_height=_mascot_jump_height(font_size),
        )
        if mascot_sprite is None:
            mascot_center = _clamp_mascot_center(
                center=mascot_center,
                play_res=play_res,
                font_size=font_size,
            )
            _draw_retro_plumber(draw=draw, center=mascot_center, scale=max(0.7, font_size / 72))
        else:
            mascot_center = _clamp_mascot_center(
                center=mascot_center,
                play_res=play_res,
                font_size=font_size,
                mascot_sprite=mascot_sprite,
                mascot_image=mascot_frame,
            )
            _draw_image_mascot(
                frame=frame,
                mascot_frame=mascot_frame,
                center=mascot_center,
                font_size=font_size,
                mascot_sprite=mascot_sprite,
            )


def _select_mascot_frame(*, mascot_sprite: MascotSprite, progress: float, word_index: int = 0) -> Image.Image:
    if not mascot_sprite.frames:
        raise ValueError("Mascot sprite has no frames.")
    if len(mascot_sprite.frames) == 1:
        return mascot_sprite.frames[0]
    normalized = max(0.0, min(1.0, progress))

    if len(mascot_sprite.frames) >= 18 and len(mascot_sprite.frames) % 6 == 0:
        cycle_size = 6
        cycle_count = len(mascot_sprite.frames) // cycle_size
        cycle_start = (word_index % cycle_count) * cycle_size
        index = cycle_start + round(normalized * (cycle_size - 1))
        return mascot_sprite.frames[index]

    index = round(normalized * (len(mascot_sprite.frames) - 1))
    return mascot_sprite.frames[index]


def _mascot_action_index(*, cue: SubtitleCue, active_index: int) -> int:
    return max(0, cue.index - 1) + max(0, active_index)


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
    pad_x = max(8, round(font_size * 0.22))
    pad_y = max(5, round(font_size * 0.14))
    pill = (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y)
    radius = max(8, round(font_size * 0.20))
    shadow_offset = max(3, round(font_size * 0.06))
    shadow = (
        pill[0] - shadow_offset,
        pill[1] + shadow_offset,
        pill[2] + shadow_offset,
        pill[3] + shadow_offset,
    )
    draw.rounded_rectangle(shadow, radius=radius + shadow_offset, fill=(0, 0, 0, 115))
    draw.rounded_rectangle(
        pill,
        radius=radius,
        fill=active_fill_color,
        outline=_darken_color(active_fill_color, alpha=230),
        width=max(2, round(font_size * 0.045)),
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
    if outline_width <= 0:
        return 0
    return max(2, min(outline_width, round(font_size * 0.06)))


def _darken_color(color: RgbaColor, *, alpha: int) -> RgbaColor:
    red, green, blue, _original_alpha = color
    return (round(red * 0.55), round(green * 0.20), round(blue * 0.25), alpha)


def _mascot_anchor(
    box: tuple[int, int, int, int],
    *,
    font_size: int,
    offset_y: int = 0,
    position: str = "center",
) -> FrameCenter:
    normalized_position = position if position in {"center", "left", "right", "below"} else "center"
    pad_x = max(8, round(font_size * 0.25))
    pill_top = box[1] - max(5, round(font_size * 0.14))
    if normalized_position == "left":
        x = box[0] - pad_x
        y = pill_top + 3
    elif normalized_position == "right":
        x = box[2] + pad_x
        y = pill_top + 3
    elif normalized_position == "below":
        x = round((box[0] + box[2]) / 2)
        y = box[3] + max(34, round(font_size * 1.36))
    else:
        x = round((box[0] + box[2]) / 2)
        y = pill_top + 3
    return round(x), round(y + offset_y)


def _separate_mascot_from_word(
    *,
    center: FrameCenter,
    word_box: tuple[int, int, int, int],
    font_size: int,
    position: str,
    mascot_sprite: MascotSprite | None = None,
    mascot_frame: Image.Image | None = None,
) -> FrameCenter:
    normalized_position = position if position in {"left", "right", "below"} else "center"
    if normalized_position == "center":
        return center

    if mascot_frame is None:
        scale = max(0.7, font_size / 72)
        left_extent = round(27 * scale)
        top_extent = round(54 * scale)
        right_extent = round(27 * scale)
    else:
        left_extent, top_extent, right_extent, _bottom_extent = _image_mascot_visible_extents(
            mascot_frame=mascot_frame,
            font_size=font_size,
            reference_visible_height=(
                mascot_sprite.reference_visible_height if mascot_sprite is not None else None
            ),
        )

    gap = max(10, round(font_size * 0.25))
    x, y = center
    if normalized_position == "left":
        x = min(x, word_box[0] - gap - right_extent)
    elif normalized_position == "right":
        x = max(x, word_box[2] + gap + left_extent)
    elif normalized_position == "below":
        y = max(y, word_box[3] + gap + top_extent)
    return round(x), round(y)


def _clamp_mascot_center(
    *,
    center: FrameCenter,
    play_res: tuple[int, int],
    font_size: int,
    mascot_sprite: MascotSprite | None = None,
    mascot_image: Image.Image | None = None,
) -> FrameCenter:
    selected_frame = mascot_image
    if selected_frame is None and mascot_sprite is not None and mascot_sprite.frames:
        selected_frame = mascot_sprite.frames[0]

    if selected_frame is None:
        scale = max(0.7, font_size / 72)
        left_extent = round(27 * scale)
        top_extent = round(54 * scale)
        right_extent = round(27 * scale)
        bottom_extent = round(20 * scale)
    else:
        left_extent, top_extent, right_extent, bottom_extent = _image_mascot_visible_extents(
            mascot_frame=selected_frame,
            font_size=font_size,
            reference_visible_height=(
                mascot_sprite.reference_visible_height if mascot_sprite is not None else None
            ),
        )

    x = max(left_extent + 4, min(play_res[0] - right_extent - 4, center[0]))
    y = max(top_extent + 4, min(play_res[1] - bottom_extent - 4, center[1]))
    return round(x), round(y)


def _draw_image_mascot(
    *,
    frame: Image.Image,
    mascot_frame: Image.Image,
    center: FrameCenter,
    font_size: int,
    mascot_sprite: MascotSprite | None = None,
) -> None:
    reference_visible_height = mascot_sprite.reference_visible_height if mascot_sprite is not None else None
    target_width, target_height = _image_mascot_size(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    foot_x, foot_y = _image_mascot_foot_anchor(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    resampling = getattr(Image.Resampling, "LANCZOS", Image.BICUBIC)
    sprite = mascot_frame.resize((target_width, target_height), resampling)
    x = round(center[0] - foot_x)
    y = round(center[1] - foot_y)
    frame.alpha_composite(sprite, (x, y))


def _image_mascot_size(
    *,
    mascot_frame: Image.Image,
    font_size: int,
    reference_visible_height: int | None = None,
) -> tuple[int, int]:
    ratio = _image_mascot_scale(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    return max(1, round(mascot_frame.width * ratio)), max(1, round(mascot_frame.height * ratio))


def _image_mascot_scale(
    *,
    mascot_frame: Image.Image,
    font_size: int,
    reference_visible_height: int | None = None,
) -> float:
    visible_height = max(1, reference_visible_height or _image_mascot_subject_height(mascot_frame))
    target_visible_height = max(58, round(font_size * 1.20))
    return target_visible_height / visible_height


def _image_mascot_visible_bbox(mascot_frame: Image.Image) -> tuple[int, int, int, int]:
    bbox = mascot_frame.getchannel("A").getbbox()
    if bbox is None:
        return (0, 0, mascot_frame.width, mascot_frame.height)
    return bbox


def _image_mascot_visible_height(mascot_frame: Image.Image) -> int:
    bbox = _image_mascot_visible_bbox(mascot_frame)
    return max(1, bbox[3] - bbox[1])


def _image_mascot_subject_bbox(mascot_frame: Image.Image) -> tuple[int, int, int, int]:
    alpha = mascot_frame.getchannel("A")
    width, height = alpha.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    best_bbox: tuple[int, int, int, int] | None = None
    best_count = 0
    threshold = 48

    for start_y in range(height):
        row_offset = start_y * width
        for start_x in range(width):
            start_index = row_offset + start_x
            if visited[start_index] or pixels[start_x, start_y] < threshold:
                continue

            stack = [(start_x, start_y)]
            visited[start_index] = 1
            left = right = start_x
            top = bottom = start_y
            count = 0

            while stack:
                x, y = stack.pop()
                count += 1
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

                for next_y in range(max(0, y - 1), min(height, y + 2)):
                    next_row_offset = next_y * width
                    for next_x in range(max(0, x - 1), min(width, x + 2)):
                        next_index = next_row_offset + next_x
                        if visited[next_index] or pixels[next_x, next_y] < threshold:
                            continue
                        visited[next_index] = 1
                        stack.append((next_x, next_y))

            if count > best_count:
                best_count = count
                best_bbox = (left, top, right + 1, bottom + 1)

    return best_bbox or _image_mascot_visible_bbox(mascot_frame)


def _image_mascot_subject_height(mascot_frame: Image.Image) -> int:
    bbox = _image_mascot_subject_bbox(mascot_frame)
    return max(1, bbox[3] - bbox[1])


def _image_mascot_foot_anchor(
    *,
    mascot_frame: Image.Image,
    font_size: int,
    reference_visible_height: int | None = None,
) -> tuple[int, int]:
    bbox = _image_mascot_subject_bbox(mascot_frame)
    scale = _image_mascot_scale(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    left = bbox[0] * scale
    right = bbox[2] * scale
    bottom = bbox[3] * scale
    return round((left + right) / 2), round(bottom)


def _image_mascot_visible_extents(
    *,
    mascot_frame: Image.Image,
    font_size: int,
    reference_visible_height: int | None = None,
) -> tuple[int, int, int, int]:
    bbox = _image_mascot_visible_bbox(mascot_frame)
    scale = _image_mascot_scale(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    foot_x, foot_y = _image_mascot_foot_anchor(
        mascot_frame=mascot_frame,
        font_size=font_size,
        reference_visible_height=reference_visible_height,
    )
    left_extent = max(0, round(foot_x - bbox[0] * scale))
    top_extent = max(0, round(foot_y - bbox[1] * scale))
    right_extent = max(0, round(bbox[2] * scale - foot_x))
    bottom_extent = max(0, round(bbox[3] * scale - foot_y))
    return left_extent, top_extent, right_extent, bottom_extent


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
