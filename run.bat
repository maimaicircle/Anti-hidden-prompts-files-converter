@echo off
setlocal

cd /d "%~dp0"

echo === Checking Python ===
python --version >nul 2>nul
if errorlevel 1 (
    py --version >nul 2>nul
    if errorlevel 1 (
        echo Python was not found. Please install Python first.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

echo === Checking requirements.txt ===
if not exist requirements.txt (
    echo requirements.txt was not found in this folder.
    pause
    exit /b 1
)

echo === Installing dependencies ===
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo === Running program ===
%PY_CMD% pdf_png_rebuild_gui.py

pause
