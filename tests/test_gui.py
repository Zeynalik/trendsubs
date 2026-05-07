import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from trendsubs.gui.window import (
    TrendSubsWindow,
    _font_display_name,
    build_color_names,
    build_preset_names,
    discover_font_paths,
)


@pytest.fixture(autouse=True)
def _isolate_gui_state_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "trendsubs.gui.window._settings_file_path",
        lambda: tmp_path / "gui_state.json",
    )


def test_build_preset_names_exposes_all_default_presets():
    assert build_preset_names() == [
        "social-pop",
        "clean-pro",
        "impact-caps",
        "hook-pop",
        "neon-glow",
        "podcast-clean",
    ]


def test_build_color_names_exposes_available_colors():
    assert build_color_names() == ["Yellow", "White", "Red", "Blue"]


def test_discover_font_paths_includes_bundled_caption_fonts():
    font_names = {Path(font_path).name for font_path in discover_font_paths()}

    assert {
        "Anton-Regular.ttf",
        "Bangers-Regular.ttf",
        "BebasNeue-Regular.ttf",
        "Montserrat-VariableFont_wght.ttf",
    }.issubset(font_names)


def test_font_display_name_uses_font_family_for_real_font():
    font_path = os.path.abspath("fonts/Caveat-VariableFont_wght.ttf")

    assert _font_display_name(font_path) == "Caveat (Caveat-VariableFont_wght.ttf)"


def test_trendsubs_window_resolves_font_path_from_visible_combo_text_when_data_is_missing():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    font_path = os.path.abspath("fonts/Caveat-VariableFont_wght.ttf")
    window = TrendSubsWindow()
    window.font_combo.addItem(_font_display_name(font_path))
    window.font_combo.setCurrentIndex(window.font_combo.count() - 1)

    assert window._selected_font_text() == font_path
    app.quit()


def test_trendsubs_window_builds_expected_form_fields():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    window = TrendSubsWindow()

    assert window.video_input.placeholderText() == "Select input video"
    assert window.srt_input.placeholderText() == "Select subtitle file"
    assert window.output_dir_input.placeholderText() == "Choose output folder"
    assert window.output_name_input.placeholderText() == "Output file name (without .mp4)"
    assert window.preset_combo.count() == 6
    assert window.color_combo.count() == 5
    assert window.stroke_check.isChecked() is True
    assert window.mode_combo.count() == 4
    assert window.animation_combo.count() == 6
    assert window.font_combo.count() >= 1
    assert window.auto_scale_check.isChecked() is True
    assert window.mascot_check.isChecked() is True
    assert window.mascot_position_combo.currentText() == "Center"
    assert window.render_button.text() == "Render"
    assert window.preview_button.text() == "Preview Frame"
    assert window.size_input.text() == "40"
    assert window.max_caption_words_input.text() == "0"
    app.quit()


def test_trendsubs_window_uses_preset_accent_color_when_color_is_preset():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    window = TrendSubsWindow()
    window.preset_combo.setCurrentText("hook-pop")
    window.color_combo.setCurrentText("Preset")
    options = window._build_render_options()

    assert options is not None
    assert options.accent_color == "#FFD24A"
    app.quit()


def test_trendsubs_window_preview_logs_animation_notice(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    preview_path = output_path.with_suffix(".preview.png")
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    monkeypatch.setattr(
        "trendsubs.gui.window.render_preview_frame",
        lambda **kwargs: preview_path.write_bytes(b"png"),
    )

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.output_dir_input.setText(str(tmp_path))
    window.font_combo.setCurrentIndex(font_index)
    window.animation_combo.setCurrentText("float")
    window.run_preview()

    assert "Preview Frame is static" in window.log_output.toPlainText()
    app.quit()


def test_trendsubs_window_persists_settings_except_video_and_srt(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    settings_file = tmp_path / "gui_state.json"
    monkeypatch.setattr(
        "trendsubs.gui.window._settings_file_path",
        lambda: settings_file,
    )

    first_window = TrendSubsWindow()
    first_window.video_input.setText(str(tmp_path / "video.mp4"))
    first_window.srt_input.setText(str(tmp_path / "subs.srt"))
    first_window.output_dir_input.setText(str(tmp_path / "renders"))
    first_window.output_name_input.setText("final_name")
    first_window.preset_combo.setCurrentText("hook-pop")
    first_window.mode_combo.setCurrentText("reveal")
    first_window.animation_combo.setCurrentText("pop-bounce")
    first_window.color_combo.setCurrentText("Red")
    first_window.stroke_check.setChecked(False)
    first_window.size_input.setText("56")
    first_window.margin_input.setText("220")
    first_window.safe_area_input.setText("30")
    first_window.max_words_input.setText("2")
    first_window.max_caption_words_input.setText("7")
    first_window.preview_time_input.setText("4.5")
    first_window.auto_scale_check.setChecked(False)
    first_window.mascot_check.setChecked(False)
    first_window.mascot_position_combo.setCurrentText("Below")
    first_window.close()

    second_window = TrendSubsWindow()
    assert second_window.video_input.text() == ""
    assert second_window.srt_input.text() == ""
    assert second_window.output_dir_input.text() == str(tmp_path / "renders")
    assert second_window.output_name_input.text() == "final_name"
    assert second_window.preset_combo.currentText() == "hook-pop"
    assert second_window.mode_combo.currentText() == "reveal"
    assert second_window.animation_combo.currentText() == "pop-bounce"
    assert second_window.color_combo.currentText() == "Red"
    assert second_window.stroke_check.isChecked() is False
    assert second_window.size_input.text() == "56"
    assert second_window.margin_input.text() == "220"
    assert second_window.safe_area_input.text() == "30"
    assert second_window.max_words_input.text() == "2"
    assert second_window.max_caption_words_input.text() == "7"
    assert second_window.preview_time_input.text() == "4.5"
    assert second_window.auto_scale_check.isChecked() is False
    assert second_window.mascot_check.isChecked() is False
    assert second_window.mascot_position_combo.currentText() == "Below"
    second_window.close()
    app.quit()


def test_trendsubs_window_run_render_uses_shared_service(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_render(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("trendsubs.gui.window.render_subtitled_video", fake_render)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.output_dir_input.setText(str(tmp_path))
    window.font_combo.setCurrentIndex(font_index)
    window.mode_combo.setCurrentText("reveal")
    window.animation_combo.setCurrentText("pop-bounce")
    window.max_words_input.setText("3")
    window.max_caption_words_input.setText("8")
    window.safe_area_input.setText("15")
    window.auto_scale_check.setChecked(False)
    window.stroke_check.setChecked(False)
    window.mascot_check.setChecked(False)
    window.mascot_position_combo.setCurrentText("Right")
    window.run_render()

    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_path"] == output_path
    assert called["options"].mode == "reveal"
    assert called["options"].animation == "pop-bounce"
    assert called["options"].max_words_per_line == 3
    assert called["options"].max_words_per_caption == 8
    assert called["options"].safe_area_offset == 15
    assert called["options"].auto_font_scale is False
    assert called["options"].stroke_enabled is False
    assert called["options"].mascot_enabled is False
    assert called["options"].mascot_position == "right"
    assert f"Font: {font_path.resolve()}" in window.log_output.toPlainText()
    assert "Rendered video" in window.log_output.toPlainText()
    app.quit()


def test_trendsubs_window_run_render_logs_renderer_errors(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    def fake_render(**kwargs):
        raise OSError("Unable to load font file: font.ttf")

    monkeypatch.setattr("trendsubs.gui.window.render_subtitled_video", fake_render)

    window = TrendSubsWindow()
    window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
    window.font_combo.setCurrentIndex(window.font_combo.count() - 1)
    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.output_dir_input.setText(str(tmp_path))
    window.run_render()

    assert "Render failed: Unable to load font file" in window.log_output.toPlainText()
    app.quit()


def test_trendsubs_window_run_render_accepts_wrapped_quotes(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_render(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("trendsubs.gui.window.render_subtitled_video", fake_render)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(f'"{video_path}"')
    window.srt_input.setText(f'"{srt_path}"')
    window.output_input.setText(f'"{output_path}"')
    window.font_combo.setCurrentIndex(font_index)
    window.run_render()

    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_path"] == output_path
    app.quit()


def test_trendsubs_window_run_render_logs_missing_files():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    window = TrendSubsWindow()
    window.font_combo.addItem("missing", r"C:\missing\font.ttf")
    window.font_combo.setCurrentIndex(window.font_combo.count() - 1)
    window.video_input.setText(r"C:\missing\video.mp4")
    window.srt_input.setText(r"C:\missing\subs.srt")
    window.output_input.setText(r"C:\missing\out.mp4")
    window.run_render()

    log = window.log_output.toPlainText()
    assert "Video not found" in log
    assert "SRT not found" in log
    assert "Font not found" in log
    app.quit()


def test_trendsubs_window_pick_video_updates_video_field(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    selected = tmp_path / "clip.mp4"
    selected.write_bytes(b"video")
    monkeypatch.setattr(
        "trendsubs.gui.window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(selected), "Video Files (*.mp4)"),
    )

    window = TrendSubsWindow()
    window.pick_video()

    assert window.video_input.text() == str(selected)
    app.quit()


def test_trendsubs_window_pick_output_updates_output_field(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    selected = tmp_path / "result.mp4"
    monkeypatch.setattr(
        "trendsubs.gui.window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(selected), "Video Files (*.mp4)"),
    )

    window = TrendSubsWindow()
    window.pick_output()

    assert window.output_input.text() == str(selected)
    app.quit()


def test_trendsubs_window_run_preview_uses_preview_service(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    preview_path = output_path.with_suffix(".preview.png")
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_preview(**kwargs):
        called.update(kwargs)
        preview_path.write_bytes(b"png")
        return preview_path

    monkeypatch.setattr("trendsubs.gui.window.render_preview_frame", fake_preview)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.output_dir_input.setText(str(tmp_path))
    window.font_combo.setCurrentIndex(font_index)
    window.preview_time_input.setText("2.0")
    window.run_preview()

    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_image_path"] == preview_path
    assert called["at_seconds"] == 2.0
    assert "Preview saved" in window.log_output.toPlainText()
    app.quit()


def test_trendsubs_window_word_pill_preview_passes_selected_font_path(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "video.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = Path(os.path.abspath("fonts/Caveat-VariableFont_wght.ttf"))
    output_path = tmp_path / "out.mp4"
    preview_path = output_path.with_suffix(".preview.png")
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")

    called = {}

    def fake_preview(**kwargs):
        called.update(kwargs)
        preview_path.write_bytes(b"png")
        return preview_path

    monkeypatch.setattr("trendsubs.gui.window.render_preview_frame", fake_preview)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    assert font_index >= 0

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.output_dir_input.setText(str(tmp_path))
    window.font_combo.setCurrentIndex(font_index)
    window.mode_combo.setCurrentText("word-pill")
    window.run_preview()

    assert called["options"].mode == "word-pill"
    assert called["options"].font_path == str(font_path.resolve())
    assert f"Font: {font_path.resolve()}" in window.log_output.toPlainText()
    app.quit()


def test_trendsubs_window_defaults_output_to_selected_folder(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "clip.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_dir = tmp_path / "renders"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_render(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("trendsubs.gui.window.render_subtitled_video", fake_render)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText("")
    window.output_dir_input.setText(str(output_dir))
    window.font_combo.setCurrentIndex(font_index)
    window.run_render()

    assert called["output_path"] == output_dir / "clip_subbed.mp4"
    app.quit()


def test_trendsubs_window_uses_custom_output_name(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    video_path = tmp_path / "clip.mp4"
    srt_path = tmp_path / "subs.srt"
    font_path = tmp_path / "font.ttf"
    output_dir = tmp_path / "renders"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_render(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("trendsubs.gui.window.render_subtitled_video", fake_render)

    window = TrendSubsWindow()
    font_index = window.font_combo.findData(str(font_path.resolve()))
    if font_index < 0:
        window.font_combo.addItem(font_path.stem, str(font_path.resolve()))
        font_index = window.font_combo.count() - 1

    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText("")
    window.output_dir_input.setText(str(output_dir))
    window.output_name_input.setText("my_final_short")
    window.font_combo.setCurrentIndex(font_index)
    window.run_render()

    assert called["output_path"] == output_dir / "my_final_short.mp4"
    app.quit()
