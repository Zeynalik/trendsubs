@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Creating .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. Make sure Python is installed.
        pause
        exit /b 1
    )
)

echo [INFO] Syncing TrendSubs dependencies...
call ".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo [INFO] Starting TrendSubs GUI...
call ".venv\Scripts\python.exe" -m trendsubs.cli gui

if errorlevel 1 (
    echo [ERROR] TrendSubs closed with an error.
    pause
    exit /b 1
)

endlocal
