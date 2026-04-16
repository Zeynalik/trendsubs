from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SubtitleCue:
    index: int
    start_ms: int
    end_ms: int
    text: str
    lines: list[str]
    word_slices: list["WordSlice"] = field(default_factory=list)


@dataclass(slots=True)
class WordSlice:
    text: str
    start_ms: int
    end_ms: int
    is_punctuation: bool


@dataclass(slots=True)
class MemeOverlay:
    gif_path: Path
    start_ms: int
    end_ms: int
    x: int = 24
    y: int = 24


@dataclass(slots=True)
class RenderOptions:
    preset: str
    font_path: str
    accent_color: str
    font_size: int
    bottom_margin: int
    keep_ass: bool
    mode: str = "highlight"
    animation: str = "none"
    max_words_per_line: int = 0
    max_words_per_caption: int = 0
    safe_area_offset: int = 0
    auto_font_scale: bool = True
    memes_enabled: bool = False
    max_memes: int = 2
    tenor_api_key: str = ""
