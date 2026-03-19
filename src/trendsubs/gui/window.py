from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from trendsubs.core.models import RenderOptions
from trendsubs.core.presets import PRESETS
from trendsubs.core.render_service import render_subtitled_video


def build_preset_names() -> list[str]:
    return list(PRESETS.keys())


class TrendSubsWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TrendSubs")
        self.resize(760, 500)

        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Select input video")
        self.video_pick_button = QPushButton("Browse...")
        self.video_pick_button.clicked.connect(self.pick_video)

        self.srt_input = QLineEdit()
        self.srt_input.setPlaceholderText("Select subtitle file")
        self.srt_pick_button = QPushButton("Browse...")
        self.srt_pick_button.clicked.connect(self.pick_srt)

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Choose output video")
        self.output_pick_button = QPushButton("Browse...")
        self.output_pick_button.clicked.connect(self.pick_output)

        self.font_input = QLineEdit()
        self.font_input.setPlaceholderText("Select .ttf or .otf font")
        self.font_pick_button = QPushButton("Browse...")
        self.font_pick_button.clicked.connect(self.pick_font)

        self.accent_input = QLineEdit("#FFD84D")
        self.size_input = QLineEdit("40")
        self.margin_input = QLineEdit("120")

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(build_preset_names())

        self.render_button = QPushButton("Render")
        self.render_button.clicked.connect(self.run_render)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        form = QFormLayout()
        form.addRow("Video", _build_path_row(self.video_input, self.video_pick_button))
        form.addRow("SRT", _build_path_row(self.srt_input, self.srt_pick_button))
        form.addRow("Output", _build_path_row(self.output_input, self.output_pick_button))
        form.addRow("Font", _build_path_row(self.font_input, self.font_pick_button))
        form.addRow("Preset", self.preset_combo)
        form.addRow("Accent", self.accent_input)
        form.addRow("Size", self.size_input)
        form.addRow("Bottom Margin", self.margin_input)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.render_button)
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def pick_video(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select input video",
            _existing_parent_dir(self.video_input.text()),
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm);;All Files (*)",
        )
        if selected:
            self.video_input.setText(selected)
            if not self.output_input.text().strip():
                output_candidate = Path(selected).with_name(f"{Path(selected).stem}_subbed.mp4")
                self.output_input.setText(str(output_candidate))

    def pick_srt(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select subtitle file",
            _existing_parent_dir(self.srt_input.text()),
            "Subtitle Files (*.srt);;All Files (*)",
        )
        if selected:
            self.srt_input.setText(selected)

    def pick_output(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Choose output video",
            _default_output_path(self.output_input.text()),
            "Video Files (*.mp4)",
        )
        if selected:
            self.output_input.setText(selected)

    def pick_font(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select font file",
            _existing_parent_dir(self.font_input.text()),
            "Font Files (*.ttf *.otf);;All Files (*)",
        )
        if selected:
            self.font_input.setText(selected)

    def run_render(self) -> None:
        video_path = Path(_normalize_path_input(self.video_input.text()))
        srt_path = Path(_normalize_path_input(self.srt_input.text()))
        output_path = Path(_normalize_path_input(self.output_input.text()))
        font_path = Path(_normalize_path_input(self.font_input.text()))

        missing: list[str] = []
        if not video_path.exists():
            missing.append(f"Video not found: {video_path}")
        if not srt_path.exists():
            missing.append(f"SRT not found: {srt_path}")
        if not font_path.exists():
            missing.append(f"Font not found: {font_path}")
        if missing:
            for line in missing:
                self.log_output.append(line)
            return

        try:
            font_size = int(self.size_input.text().strip() or "40")
            bottom_margin = int(self.margin_input.text().strip() or "120")
        except ValueError:
            self.log_output.append("Size and Bottom Margin must be numbers.")
            return

        render_subtitled_video(
            video_path=video_path,
            srt_path=srt_path,
            output_path=output_path,
            options=RenderOptions(
                preset=self.preset_combo.currentText(),
                font_path=str(font_path),
                accent_color=self.accent_input.text().strip() or "#FFD84D",
                font_size=font_size,
                bottom_margin=bottom_margin,
                keep_ass=False,
            ),
        )
        self.log_output.append(f"Rendered video: {output_path}")


def _normalize_path_input(raw: str) -> str:
    value = raw.strip()
    # Normalize smart quotes often pasted from messengers/editors.
    value = (
        value.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def _existing_parent_dir(raw: str) -> str:
    normalized = _normalize_path_input(raw)
    if not normalized:
        return str(Path.home())
    candidate = Path(normalized)
    if candidate.exists() and candidate.is_dir():
        return str(candidate)
    if candidate.parent.exists():
        return str(candidate.parent)
    return str(Path.home())


def _default_output_path(raw: str) -> str:
    normalized = _normalize_path_input(raw)
    if normalized:
        return normalized
    return str(Path.home() / "result.mp4")


def _build_path_row(path_input: QLineEdit, browse_button: QPushButton) -> QWidget:
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(path_input)
    row.addWidget(browse_button)
    return container
