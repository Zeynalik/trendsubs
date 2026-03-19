from __future__ import annotations

from pathlib import Path


def resolve_ass_font_name(font_path: str) -> str:
    path = Path(font_path)
    fallback = path.stem
    try:
        from fontTools.ttLib import TTFont  # type: ignore[import-not-found]

        with TTFont(path) as font:
            names = font["name"].names
            preferred = _find_font_name(names, name_id=16) or _find_font_name(names, name_id=1)
            if preferred:
                return preferred
    except Exception:
        pass

    return fallback


def _find_font_name(names: list[object], name_id: int) -> str | None:
    for record in names:
        if getattr(record, "nameID", None) != name_id:
            continue
        try:
            text = record.toUnicode().strip()
        except Exception:
            continue
        if text:
            return text
    return None
