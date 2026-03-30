# TrendSubs

Trend subtitle renderer that turns a video and corrected SRT into a burned-in MP4.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

## Render From CLI

```powershell
.\.venv\Scripts\trendsubs render `
  --video .\input.mp4 `
  --subs .\input.srt `
  --out .\output.mp4 `
  --font C:\Windows\Fonts\arial.ttf `
  --mode reveal `
  --animation pop-bounce `
  --max-words-per-line 3 `
  --max-words-per-caption 8 `
  --safe-area-offset 30 `
  --no-auto-font-scale
```

`mode`: `highlight` (word highlight) or `reveal` (words appear progressively).

## Launch Desktop App

```powershell
.\.venv\Scripts\trendsubs gui
```

Or double-click `start_trendsubs_gui.bat` in the project root.

## GUI Notes

- `Output Folder`: default location for rendered files.
- `Output`: exact output filename (optional, auto-generated if empty).
- `Font`: pick from dropdown or `Add Font...`.
- `Color`: choose subtitle highlight color (`Yellow`, `White`, `Red`).
- `Preset`:
  - `social-pop` -> bold viral baseline (shorts/reels default).
  - `clean-pro` -> cleaner low-noise look.
  - `impact-caps` -> punchy all-caps style.
  - `hook-pop` -> heavy hook style for high-contrast openers.
  - `neon-glow` -> bright modern style with soft glow/shadow.
  - `podcast-clean` -> minimal style for talking-head/podcast cuts.
- `Mode`:
  - `highlight` -> words change from base white to selected color while spoken.
  - `reveal` -> words appear progressively in selected color.
  - `word` -> each spoken word appears as a separate subtitle event.
- `Animation`:
  - `none` -> static subtitle appearance.
  - `pop-bounce` -> fade-in + zoom overshoot + settle (dynamic look).
- `Max Words/Caption`: split long subtitle chunks into smaller timed captions (e.g., `8` words per caption).
