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
  --max-words-per-line 3 `
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
- `Mode`:
  - `highlight` -> words change from base white to selected color while spoken.
  - `reveal` -> words appear progressively in selected color.
