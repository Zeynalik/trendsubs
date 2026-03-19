import os

from PySide6.QtWidgets import QApplication

from trendsubs.gui.window import TrendSubsWindow, build_preset_names


def test_build_preset_names_exposes_all_default_presets():
    assert build_preset_names() == ["social-pop", "clean-pro", "impact-caps"]


def test_trendsubs_window_builds_expected_form_fields():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    window = TrendSubsWindow()

    assert window.video_input.placeholderText() == "Select input video"
    assert window.srt_input.placeholderText() == "Select subtitle file"
    assert window.font_input.placeholderText() == "Select .ttf or .otf font"
    assert window.preset_combo.count() == 3
    assert window.render_button.text() == "Render"
    assert window.size_input.text() == "40"
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
    window.video_input.setText(str(video_path))
    window.srt_input.setText(str(srt_path))
    window.output_input.setText(str(output_path))
    window.font_input.setText(str(font_path))
    window.run_render()

    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_path"] == output_path
    assert "Rendered video" in window.log_output.toPlainText()
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
    window.video_input.setText(f'"{video_path}"')
    window.srt_input.setText(f'"{srt_path}"')
    window.output_input.setText(f'"{output_path}"')
    window.font_input.setText(f'"{font_path}"')
    window.run_render()

    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_path"] == output_path
    app.quit()


def test_trendsubs_window_run_render_logs_missing_files():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    window = TrendSubsWindow()
    window.video_input.setText(r"C:\missing\video.mp4")
    window.srt_input.setText(r"C:\missing\subs.srt")
    window.font_input.setText(r"C:\missing\font.ttf")
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
