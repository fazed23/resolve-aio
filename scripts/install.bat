@echo off
REM ResolveAIO Installer — Windows
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%PROJECT_DIR%\.venv"

echo ========================================
echo        ResolveAIO — Installer
echo ========================================
echo.

REM --- Detect Python ---
set "PYTHON="
where python3 >nul 2>&1 && set "PYTHON=python3"
if not defined PYTHON (
    where python >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
    echo ERROR: Python 3.10+ not found. Install it first.
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VERSION=%%i"
echo Found Python %PY_VERSION% (%PYTHON%)

REM --- Create virtual environment ---
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    %PYTHON% -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate.bat"
echo Virtual environment active

REM --- Install dependencies ---
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r "%PROJECT_DIR%\requirements.txt" -q
echo Dependencies installed

REM --- Detect Resolve paths ---
set "RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
set "RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
set "LUT_DIR=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\LUT"

if exist "%RESOLVE_SCRIPT_API%" (
    echo Resolve Script API found
) else (
    echo WARNING: Resolve Script API not found. Is DaVinci Resolve installed?
)

REM --- Install bundled assets ---
echo Installing bundled Resolve assets...
python -m src.automation.preset_manager install-bundled
if errorlevel 1 (
    echo WARNING: bundled asset install reported an error
) else (
    echo Bundled assets processed
)

echo.
echo ========================================
echo        Installation Complete!
echo ========================================
echo.
echo To start: scripts\run.bat
echo To enable GPT in the Chat UI, edit: config\resolve_aio.env
echo Make sure DaVinci Resolve is running!
pause
