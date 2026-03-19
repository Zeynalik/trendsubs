from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
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
from trendsubs.core.render_service import render_preview_frame, render_subtitled_video


def build_preset_names() -> list[str]:
    return list(PRESETS.keys())


COLOR_OPTIONS: dict[str, str] = {
    "Yellow": "#FFD84D",
    "White": "#FFFFFF",
    "Red": "#FF4D4D",
}


def build_color_names() -> list[str]:
    return list(COLOR_OPTIONS.keys())


def discover_font_paths() -> list[str]:
    candidates: list[Path] = []
    project_root = Path(__file__).resolve().parents[3]
    for folder in (project_root / "fonts", project_root / "assets" / "fonts"):
        if folder.exists():
            candidates.extend(sorted(folder.glob("*.ttf")))
            candidates.extend(sorted(folder.glob("*.otf")))

    windows_fallbacks = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for fallback in windows_fallbacks:
        if fallback.exists():
            candidates.append(fallback)

    unique: list[str] = []
    seen: set[str] = set()
    for path in candidates:
        normalized = str(path.resolve())
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


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

        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Choose output folder")
        self.output_dir_pick_button = QPushButton("Browse...")
        self.output_dir_pick_button.clicked.connect(self.pick_output_dir)

        self.output_name_input = QLineEdit()
        self.output_name_input.setPlaceholderText("Output file name (without .mp4)")
        self.output_name_input.textChanged.connect(lambda _text: self._sync_output_path_from_video())

        self.font_combo = QComboBox()
        for font_path in discover_font_paths():
            self.font_combo.addItem(Path(font_path).stem, font_path)
        self.font_pick_button = QPushButton("Add Font...")
        self.font_pick_button.clicked.connect(self.pick_font)
        if self.font_combo.count() == 0:
            self.font_combo.addItem("No font selected", "")

        self.color_combo = QComboBox()
        for color_name in build_color_names():
            self.color_combo.addItem(color_name, COLOR_OPTIONS[color_name])
        self.size_input = QLineEdit("40")
        self.margin_input = QLineEdit("120")
        self.safe_area_input = QLineEdit("0")
        self.max_words_input = QLineEdit("0")
        self.preview_time_input = QLineEdit("10")
        self.auto_scale_check = QCheckBox("Auto scale font")
        self.auto_scale_check.setChecked(True)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(build_preset_names())
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["highlight", "reveal"])

        self.render_button = QPushButton("Render")
        self.render_button.clicked.connect(self.run_render)
        self.preview_button = QPushButton("Preview Frame")
        self.preview_button.clicked.connect(self.run_preview)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        form = QFormLayout()
        form.addRow("Video", _build_path_row(self.video_input, self.video_pick_button))
        form.addRow("SRT", _build_path_row(self.srt_input, self.srt_pick_button))
        form.addRow("Output", _build_path_row(self.output_input, self.output_pick_button))
        form.addRow("Output Folder", _build_path_row(self.output_dir_input, self.output_dir_pick_button))
        form.addRow("Output Name", self.output_name_input)
        form.addRow("Font", _build_path_row(self.font_combo, self.font_pick_button))
        form.addRow("Preset", self.preset_combo)
        form.addRow("Mode", self.mode_combo)
        form.addRow("Color", self.color_combo)
        form.addRow("Size", self.size_input)
        form.addRow("Bottom Margin", self.margin_input)
        form.addRow("Safe Area Offset", self.safe_area_input)
        form.addRow("Max Words/Line (0=auto)", self.max_words_input)
        form.addRow("Preview Time (sec)", self.preview_time_input)
        form.addRow("Auto Scale", self.auto_scale_check)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.preview_button)
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
            if not self.output_name_input.text().strip():
                self.output_name_input.setText(f"{Path(selected).stem}_subbed")
            self._sync_output_path_from_video()

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
            selected_path = Path(selected)
            self.output_dir_input.setText(str(selected_path.parent))
            self.output_name_input.setText(selected_path.stem)

    def pick_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose output folder",
            _existing_parent_dir(self.output_dir_input.text()),
        )
        if selected:
            self.output_dir_input.setText(selected)
            self._sync_output_path_from_video()

    def pick_font(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select font file",
            _existing_parent_dir(self._selected_font_text()),
            "Font Files (*.ttf *.otf);;All Files (*)",
        )
        if selected:
            normalized = str(Path(selected).resolve())
            existing_index = self.font_combo.findData(normalized)
            if existing_index < 0:
                self.font_combo.addItem(Path(normalized).stem, normalized)
                existing_index = self.font_combo.count() - 1
            self.font_combo.setCurrentIndex(existing_index)

    def run_render(self) -> None:
        video_path = Path(_normalize_path_input(self.video_input.text()))
        srt_path = Path(_normalize_path_input(self.srt_input.text()))
        output_path = self._resolve_output_path(video_path)
        font_path = Path(_normalize_path_input(self._selected_font_text()))

        missing: list[str] = []
        if not video_path.exists():
            missing.append(f"Video not found: {video_path}")
        if not srt_path.exists():
            missing.append(f"SRT not found: {srt_path}")
        if output_path is None:
            missing.append("Output path is missing. Pick output folder or output file.")
        if not font_path.exists():
            missing.append(f"Font not found: {font_path}")
        if missing:
            for line in missing:
                self.log_output.append(line)
            return

        self.output_input.setText(str(output_path))

        options = self._build_render_options()
        if options is None:
            return

        render_subtitled_video(
            video_path=video_path,
            srt_path=srt_path,
            output_path=output_path,
            options=options,
        )
        self.log_output.append(f"Rendered video: {output_path}")

    def run_preview(self) -> None:
        video_path = Path(_normalize_path_input(self.video_input.text()))
        srt_path = Path(_normalize_path_input(self.srt_input.text()))
        output_path = self._resolve_output_path(video_path)
        font_path = Path(_normalize_path_input(self._selected_font_text()))

        missing: list[str] = []
        if not video_path.exists():
            missing.append(f"Video not found: {video_path}")
        if not srt_path.exists():
            missing.append(f"SRT not found: {srt_path}")
        if output_path is None:
            missing.append("Output path is missing. Pick output folder or output file.")
        if not font_path.exists():
            missing.append(f"Font not found: {font_path}")
        if missing:
            for line in missing:
                self.log_output.append(line)
            return

        self.output_input.setText(str(output_path))

        options = self._build_render_options()
        if options is None:
            return

        try:
            preview_time = float(self.preview_time_input.text().strip() or "10")
        except ValueError:
            self.log_output.append("Preview Time must be a number.")
            return

        preview_path = output_path.with_suffix(".preview.png")
        render_preview_frame(
            video_path=video_path,
            srt_path=srt_path,
            output_image_path=preview_path,
            options=options,
            at_seconds=preview_time,
        )
        self.log_output.append(f"Preview saved: {preview_path}")

    def _build_render_options(self) -> RenderOptions | None:
        font_path = Path(_normalize_path_input(self._selected_font_text()))
        try:
            font_size = int(self.size_input.text().strip() or "40")
            bottom_margin = int(self.margin_input.text().strip() or "120")
            safe_area_offset = int(self.safe_area_input.text().strip() or "0")
            max_words = int(self.max_words_input.text().strip() or "0")
        except ValueError:
            self.log_output.append("Size, Bottom Margin, Safe Area, Max Words must be numbers.")
            return None

        return RenderOptions(
            preset=self.preset_combo.currentText(),
            font_path=str(font_path),
            accent_color=str(self.color_combo.currentData() or "#FFD84D"),
            font_size=font_size,
            bottom_margin=bottom_margin,
            keep_ass=False,
            mode=self.mode_combo.currentText(),
            max_words_per_line=max(0, max_words),
            safe_area_offset=max(0, safe_area_offset),
            auto_font_scale=self.auto_scale_check.isChecked(),
        )

    def _selected_font_text(self) -> str:
        return str(self.font_combo.currentData() or "").strip()

    def _sync_output_path_from_video(self) -> None:
        video_raw = _normalize_path_input(self.video_input.text())
        if not video_raw and not self.output_name_input.text().strip():
            return

        video_path = Path(video_raw) if video_raw else None

        folder_raw = _normalize_path_input(self.output_dir_input.text())
        if folder_raw:
            output_dir = Path(folder_raw)
        elif video_path is not None:
            output_dir = video_path.parent
        else:
            output_dir = Path.home()

        output_dir.mkdir(parents=True, exist_ok=True)
        output_name = self.output_name_input.text().strip()
        if not output_name and video_path is not None and video_path.stem:
            output_name = f"{video_path.stem}_subbed"
            self.output_name_input.setText(output_name)
            return

        if output_name:
            output_name = Path(output_name).stem
            self.output_input.setText(str(output_dir / f"{output_name}.mp4"))

    def _resolve_output_path(self, video_path: Path) -> Path | None:
        output_name = self.output_name_input.text().strip()
        if output_name:
            folder_raw = _normalize_path_input(self.output_dir_input.text())
            if folder_raw:
                output_dir = Path(folder_raw)
            elif video_path.name:
                output_dir = video_path.parent
                self.output_dir_input.setText(str(output_dir))
            else:
                output_dir = Path.home() / "trendsubs_output"
                self.output_dir_input.setText(str(output_dir))
            output_dir.mkdir(parents=True, exist_ok=True)
            normalized_name = Path(output_name).stem
            return output_dir / f"{normalized_name}.mp4"

        output_text = _normalize_path_input(self.output_input.text())
        if output_text:
            output_path = Path(output_text)
            if output_path.suffix.lower() != ".mp4":
                output_path = output_path.with_suffix(".mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path

        if not video_path.name:
            return None

        folder_raw = _normalize_path_input(self.output_dir_input.text())
        if folder_raw:
            output_dir = Path(folder_raw)
        else:
            output_dir = video_path.parent / "trendsubs_output"
            self.output_dir_input.setText(str(output_dir))

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{video_path.stem}_subbed.mp4"


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


def _build_path_row(path_input: QWidget, browse_button: QPushButton) -> QWidget:
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(path_input)
    row.addWidget(browse_button)
    return container
