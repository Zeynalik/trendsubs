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
  --font C:\Windows\Fonts\arial.ttf
```

## Launch Desktop App

```powershell
.\.venv\Scripts\trendsubs gui
```

Or double-click `start_trendsubs_gui.bat` in the project root.
