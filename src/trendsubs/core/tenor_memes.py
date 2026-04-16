from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trendsubs.core.models import MemeOverlay, SubtitleCue

_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "funny": ("lol", "haha", "laugh", "смешно", "рж", "ха", "прикол"),
    "wow": ("wow", "omg", "шок", "вау", "невероят"),
    "fail": ("fail", "oops", "wtf", "фейл", "провал", "капец"),
    "money": ("money", "cash", "rich", "деньги", "бабки"),
    "bro": ("bro", "bruh", "dude", "бро", "брат"),
}


def resolve_tenor_memes(
    cues: list[SubtitleCue],
    output_dir: Path,
    api_key: str,
    max_memes: int = 2,
) -> list[MemeOverlay]:
    if not api_key.strip() or max_memes <= 0:
        return []

    planned = _plan_meme_slots(cues, max_memes=max_memes)
    if not planned:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    overlays: list[MemeOverlay] = []
    for index, slot in enumerate(planned, start=1):
        gif_url = _fetch_tenor_gif_url(query=slot["query"], api_key=api_key)
        if not gif_url:
            continue
        gif_path = output_dir / f"meme_{index}.gif"
        try:
            _download_file(gif_url, gif_path)
        except OSError:
            continue
        overlays.append(
            MemeOverlay(
                gif_path=gif_path,
                start_ms=int(slot["start_ms"]),
                end_ms=int(slot["end_ms"]),
            )
        )
    return overlays


def _plan_meme_slots(cues: list[SubtitleCue], max_memes: int) -> list[dict[str, str | int]]:
    slots: list[dict[str, str | int]] = []
    min_gap_ms = 7000
    duration_ms = 2200
    last_start_ms = -min_gap_ms

    for cue in cues:
        if len(slots) >= max_memes:
            break
        query = _pick_query(cue.text)
        if not query:
            continue
        start_ms = max(cue.start_ms, 0)
        if start_ms - last_start_ms < min_gap_ms:
            continue
        end_ms = min(cue.end_ms, start_ms + duration_ms)
        if end_ms <= start_ms:
            continue
        slots.append({"query": query, "start_ms": start_ms, "end_ms": end_ms})
        last_start_ms = start_ms
    return slots


def _pick_query(text: str) -> str | None:
    normalized = text.lower()
    for query, keywords in _THEME_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return query
    return None


def _fetch_tenor_gif_url(query: str, api_key: str) -> str | None:
    params = urlencode(
        {
            "q": query,
            "key": api_key,
            "client_key": "trendsubs",
            "limit": 1,
            "media_filter": "tinygif,gif",
            "contentfilter": "medium",
        }
    )
    request = Request(f"https://tenor.googleapis.com/v2/search?{params}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None
    media_formats = results[0].get("media_formats", {})
    if not isinstance(media_formats, dict):
        return None
    for key in ("tinygif", "gif"):
        data = media_formats.get(key, {})
        if isinstance(data, dict):
            url = data.get("url")
            if isinstance(url, str) and url:
                return url
    return None


def _download_file(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "TrendSubs/1.0"})
    with urlopen(request, timeout=10) as response:
        destination.write_bytes(response.read())
