from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from trendsubs.core.models import SubtitleCue, WordSlice
from trendsubs.core.word_jump_overlay import (
    MascotSprite,
    _active_cue,
    _active_word_index,
    _clamp_mascot_center,
    _draw_active_word,
    _draw_image_mascot,
    _jump_position,
    _layout_words,
    _load_font,
    _load_mascot_sprite,
    _image_mascot_foot_anchor,
    _image_mascot_subject_bbox,
    _image_mascot_visible_extents,
    _image_mascot_visible_height,
    _image_mascot_size,
    _mascot_anchor,
    _mascot_action_index,
    _mascot_jump_duration_ms,
    _mascot_jump_height,
    _mascot_jump_progress,
    _separate_mascot_from_word,
    _select_mascot_frame,
)


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


def test_mascot_jump_is_short_enough_to_land_on_active_word():
    assert _mascot_jump_duration_ms(900) == 180
    assert _mascot_jump_duration_ms(240) == 90
    assert _mascot_jump_height(80) == 26


def test_mascot_does_not_jump_in_place_on_first_word():
    assert _mascot_jump_progress(
        previous_index=0,
        active_index=0,
        at_ms=80,
        word_start_ms=0,
        word_duration_ms=1000,
    ) == 1.0
    assert _mascot_jump_progress(
        previous_index=0,
        active_index=1,
        at_ms=45,
        word_start_ms=0,
        word_duration_ms=1000,
    ) == 0.25


def test_active_cue_stops_at_end_time():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=2000,
        text="one",
        lines=["one"],
        word_slices=[WordSlice(text="one", start_ms=1000, end_ms=2000, is_punctuation=False)],
    )

    assert _active_cue([cue], 1999) == cue
    assert _active_cue([cue], 2000) is None


def test_layout_words_wraps_by_max_words_per_line():
    cue = SubtitleCue(
        index=1,
        start_ms=1000,
        end_ms=3000,
        text="one two three four",
        lines=["one two three four"],
        word_slices=[
            WordSlice(text="one", start_ms=1000, end_ms=1500, is_punctuation=False),
            WordSlice(text="two", start_ms=1500, end_ms=2000, is_punctuation=False),
            WordSlice(text="three", start_ms=2000, end_ms=2500, is_punctuation=False),
            WordSlice(text="four", start_ms=2500, end_ms=3000, is_punctuation=False),
        ],
    )
    image = Image.new("RGBA", (420, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    boxes = _layout_words(
        draw=draw,
        cue=cue,
        play_res=(420, 240),
        font=ImageFont.load_default(),
        font_size=32,
        bottom_margin=40,
        safe_area_offset=0,
        max_words_per_line=2,
    )

    assert boxes[0][1][1] == boxes[1][1][1]
    assert boxes[2][1][1] > boxes[0][1][1]
    assert boxes[2][1][0] < boxes[1][1][0]


def test_load_font_rejects_invalid_font_file(tmp_path):
    font_path = tmp_path / "broken.ttf"
    font_path.write_bytes(b"not a font")

    try:
        _load_font(font_path=font_path, font_size=32)
    except OSError as error:
        assert str(font_path) in str(error)
    else:
        raise AssertionError("invalid font file was silently accepted")


def test_active_word_draws_red_reference_pill_without_white_inner_border():
    image = Image.new("RGBA", (220, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font_size = 36
    box = (62, 42, 150, 78)

    _draw_active_word(
        draw=draw,
        word="GUYS",
        box=box,
        origin=(62, 38),
        font=ImageFont.load_default(),
        font_size=font_size,
        active_fill_color=(220, 18, 50, 235),
        active_text_color=(255, 255, 255, 255),
        outline_color=(0, 0, 0, 230),
        outline_width=5,
    )

    assert image.getpixel((58, 38))[3] > 0
    assert image.getpixel((145, 47))[:3] == (220, 18, 50)
    assert image.getpixel((62, 42))[:3] != (255, 255, 255)


def test_word_pill_text_stroke_does_not_overpower_custom_font_shape():
    from trendsubs.core.word_jump_overlay import _text_stroke_width

    assert _text_stroke_width(font_size=80, outline_width=3) <= 3


def test_mascot_center_is_clamped_inside_frame_when_subtitles_are_high():
    clamped = _clamp_mascot_center(
        center=(120, -40),
        play_res=(320, 180),
        font_size=64,
        mascot_image=Image.new("RGBA", (100, 200), (255, 0, 0, 255)),
    )

    assert clamped[0] == 120
    assert 0 <= clamped[1] <= 180


def test_mascot_center_clamps_using_current_wide_frame():
    mascot_frame = Image.new("RGBA", (220, 120), (255, 0, 0, 255))
    clamped = _clamp_mascot_center(
        center=(315, 80),
        play_res=(320, 180),
        font_size=64,
        mascot_image=mascot_frame,
    )
    width, _height = _image_mascot_size(mascot_frame=mascot_frame, font_size=64)

    assert clamped[0] + width // 2 <= 316


def test_mascot_center_clamps_asymmetric_frame_from_visible_foot_anchor():
    mascot_frame = Image.new("RGBA", (240, 120), (0, 0, 0, 0))
    ImageDraw.Draw(mascot_frame).rectangle((110, 20, 235, 105), fill=(255, 0, 0, 255))
    left_extent, _top_extent, right_extent, _bottom_extent = _image_mascot_visible_extents(
        mascot_frame=mascot_frame,
        font_size=64,
    )

    clamped = _clamp_mascot_center(
        center=(300, 100),
        play_res=(320, 180),
        font_size=64,
        mascot_image=mascot_frame,
    )

    assert clamped[0] - left_extent >= 4
    assert clamped[0] + right_extent <= 316


def test_mascot_anchor_places_feet_on_word_pill_top():
    anchor = _mascot_anchor((80, 120, 180, 160), font_size=50)

    assert anchor == (130, 116)


def test_mascot_anchor_can_move_to_word_start_end_or_below():
    box = (80, 120, 180, 160)

    assert _mascot_anchor(box, font_size=50, position="left") == (68, 116)
    assert _mascot_anchor(box, font_size=50, position="right") == (192, 116)
    assert _mascot_anchor(box, font_size=50, position="below") == (130, 228)


def test_mascot_frame_selection_uses_one_six_frame_cycle_per_word():
    frames = [Image.new("RGBA", (2, 2), (index, 0, 0, 255)) for index in range(18)]
    sprite = MascotSprite(frames=frames)

    first_word_frame = _select_mascot_frame(mascot_sprite=sprite, progress=1.0, word_index=0)
    second_word_frame = _select_mascot_frame(mascot_sprite=sprite, progress=0.0, word_index=1)
    third_word_frame = _select_mascot_frame(mascot_sprite=sprite, progress=0.5, word_index=2)

    assert frames.index(first_word_frame) == 5
    assert frames.index(second_word_frame) == 6
    assert frames.index(third_word_frame) == 14


def test_mascot_frame_selection_supports_appended_six_frame_cycles():
    frames = [Image.new("RGBA", (2, 2), (index, 0, 0, 255)) for index in range(36)]
    sprite = MascotSprite(frames=frames)

    sixth_cycle_frame = _select_mascot_frame(mascot_sprite=sprite, progress=0.5, word_index=5)

    assert frames.index(sixth_cycle_frame) == 32


def test_default_mascot_sprite_includes_street_fighter_combo_cycles():
    mascot_path = Path("assets/mascot/manat_character.png")
    sprite = _load_mascot_sprite(mascot_path)

    assert sprite is not None
    assert len(sprite.frames) >= 84
    assert len(sprite.frames) % 6 == 0


def test_street_fighter_combo_key_frames_have_readable_special_actions():
    frames_dir = Path("assets/mascot/manat_character_frames")
    uppercut = Image.open(frames_dir / "46.png").convert("RGBA")
    stretched_arms = Image.open(frames_dir / "55.png").convert("RGBA")

    upper_pixels = [
        uppercut.getpixel((x, y))
        for x in range(120, 190)
        for y in range(8, 72)
    ]
    bright_uppercut_pixels = [
        pixel for pixel in upper_pixels if pixel[3] > 120 and pixel[0] > 220 and pixel[1] > 140
    ]

    stretched_bbox = stretched_arms.getchannel("A").getbbox()
    assert len(bright_uppercut_pixels) > 120
    assert stretched_bbox is not None
    assert stretched_bbox[2] - stretched_bbox[0] >= 210


def test_fatality_combo_key_frames_have_paper_and_portal_effects():
    frames_dir = Path("assets/mascot/manat_character_frames")
    paper_storm = Image.open(frames_dir / "64.png").convert("RGBA")
    portal = Image.open(frames_dir / "81.png").convert("RGBA")

    paper_pixels = [
        paper_storm.getpixel((x, y))
        for x in range(145, 235)
        for y in range(38, 150)
    ]
    portal_pixels = [
        portal.getpixel((x, y))
        for x in range(140, 235)
        for y in range(45, 155)
    ]

    bright_paper_pixels = [
        pixel for pixel in paper_pixels if pixel[3] > 100 and pixel[0] > 210 and pixel[1] > 180 and pixel[2] > 120
    ]
    purple_portal_pixels = [
        pixel for pixel in portal_pixels if pixel[3] > 100 and pixel[0] > 110 and pixel[2] > 150
    ]

    assert len(bright_paper_pixels) > 160
    assert len(purple_portal_pixels) > 220


def test_mascot_action_index_continues_across_caption_chunks():
    cue = SubtitleCue(
        index=3,
        start_ms=0,
        end_ms=1000,
        text="fire",
        lines=["fire"],
        word_slices=[WordSlice(text="fire", start_ms=0, end_ms=1000, is_punctuation=False)],
    )

    assert _mascot_action_index(cue=cue, active_index=0) == 2


def test_mascot_sprite_uses_consistent_scale_for_different_action_poses():
    short_pose = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    tall_pose = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    ImageDraw.Draw(short_pose).rectangle((40, 45, 80, 105), fill=(255, 0, 0, 255))
    ImageDraw.Draw(tall_pose).rectangle((20, 10, 100, 105), fill=(255, 0, 0, 255))
    reference_height = max(_image_mascot_visible_height(short_pose), _image_mascot_visible_height(tall_pose))

    short_size = _image_mascot_size(
        mascot_frame=short_pose,
        font_size=80,
        reference_visible_height=reference_height,
    )
    tall_size = _image_mascot_size(
        mascot_frame=tall_pose,
        font_size=80,
        reference_visible_height=reference_height,
    )

    assert short_size == tall_size


def test_image_mascot_visible_feet_land_on_requested_anchor_with_padded_frame():
    mascot_frame = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    ImageDraw.Draw(mascot_frame).rectangle((35, 20, 85, 95), fill=(255, 0, 0, 255))
    output = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
    sprite = MascotSprite(
        frames=[mascot_frame],
        reference_visible_height=_image_mascot_visible_height(mascot_frame),
    )

    _draw_image_mascot(
        frame=output,
        mascot_frame=mascot_frame,
        center=(120, 130),
        font_size=64,
        mascot_sprite=sprite,
    )

    alpha = output.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    bbox = alpha.getbbox()
    assert bbox is not None
    assert bbox[3] - 1 == 130


def test_mascot_foot_anchor_ignores_disconnected_action_effects():
    mascot_frame = Image.new("RGBA", (220, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mascot_frame)
    draw.rectangle((88, 38, 132, 142), fill=(40, 120, 230, 255))
    draw.line((5, 40, 70, 20), fill=(40, 120, 230, 255), width=3)
    draw.line((5, 50, 70, 30), fill=(40, 120, 230, 255), width=3)

    subject_bbox = _image_mascot_subject_bbox(mascot_frame)
    foot_x, foot_y = _image_mascot_foot_anchor(mascot_frame=mascot_frame, font_size=64)

    assert subject_bbox == (88, 38, 133, 143)
    assert 78 <= foot_x <= 84
    assert foot_y == 105


def test_mascot_side_positions_keep_current_frame_clear_of_word():
    mascot_frame = Image.new("RGBA", (160, 120), (0, 0, 0, 0))
    ImageDraw.Draw(mascot_frame).rectangle((20, 20, 150, 100), fill=(255, 0, 0, 255))
    word_box = (180, 90, 280, 130)
    sprite = MascotSprite(
        frames=[mascot_frame],
        reference_visible_height=_image_mascot_visible_height(mascot_frame),
    )

    left_center = _separate_mascot_from_word(
        center=_mascot_anchor(word_box, font_size=64, position="left"),
        word_box=word_box,
        font_size=64,
        position="left",
        mascot_sprite=sprite,
        mascot_frame=mascot_frame,
    )
    right_center = _separate_mascot_from_word(
        center=_mascot_anchor(word_box, font_size=64, position="right"),
        word_box=word_box,
        font_size=64,
        position="right",
        mascot_sprite=sprite,
        mascot_frame=mascot_frame,
    )
    below_center = _separate_mascot_from_word(
        center=_mascot_anchor(word_box, font_size=64, position="below"),
        word_box=word_box,
        font_size=64,
        position="below",
        mascot_sprite=sprite,
        mascot_frame=mascot_frame,
    )
    left_extent, top_extent, right_extent, _bottom_extent = _image_mascot_visible_extents(
        mascot_frame=mascot_frame,
        font_size=64,
        reference_visible_height=sprite.reference_visible_height,
    )
    gap = max(10, round(64 * 0.25))

    assert left_center[0] + right_extent <= word_box[0] - gap
    assert right_center[0] - left_extent >= word_box[2] + gap
    assert below_center[1] - top_extent >= word_box[3] + gap
