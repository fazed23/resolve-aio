@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title ResolveAIO — Installer
color 1F

REM ══════════════════════════════════════════════════════════
REM  ResolveAIO — One-Click Installer for Windows
REM  Double-click this file to install. That's it.
REM ══════════════════════════════════════════════════════════

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "TOTAL_STEPS=6"

REM ── Welcome Screen ─────────────────────────────────────────

cls
echo.
echo     ╔═══════════════════════════════════════════════════╗
echo     ║                                                   ║
echo     ║      ██████  ███████ ███████  ██████  ██     ██   ║
echo     ║      ██   ██ ██      ██      ██    ██ ██     ██   ║
echo     ║      ██████  █████   ███████ ██    ██ ██     ██   ║
echo     ║      ██   ██ ██           ██ ██    ██ ██          ║
echo     ║      ██   ██ ███████ ███████  ██████  ███████ ██  ║
echo     ║                     A I O                         ║
echo     ║                                                   ║
echo     ╚═══════════════════════════════════════════════════╝
echo.
echo     All-in-One Plugin for DaVinci Resolve
echo     MCP Server / DCTL Tools / Automation / Chat UI
echo.
echo     ──────────────────────────────────────────
echo.
echo     The installer will:
echo       1. Check for Python
echo       2. Install required packages
echo       3. Install DCTL color tools for DaVinci Resolve
echo       4. Set up AI connection (Cursor / Claude Desktop)
echo       5. Create desktop shortcuts
echo.
echo     Make sure DaVinci Resolve is installed before continuing.
echo.
pause

REM ── Step 1: Check Python ───────────────────────────────────

cls
echo.
echo   [1/%TOTAL_STEPS%] Checking Python...
echo   ────────────────────────────────────────

set "PYTHON="

REM Check python3 first, then python
where python3 >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('python3 -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2^>nul') do set "PY_VER=%%i"
    for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
        if %%a geq 3 if %%b geq 10 set "PYTHON=python3"
    )
)

if not defined PYTHON (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2^>nul') do set "PY_VER=%%i"
        for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
            if %%a geq 3 if %%b geq 10 set "PYTHON=python"
        )
    )
)

if not defined PYTHON (
    echo.
    echo   ERROR: Python 3.10+ not found!
    echo.
    echo   To install:
    echo     1. Go to https://www.python.org/downloads/
    echo     2. Download Python 3.12
    echo     3. IMPORTANT: Check "Add Python to PATH" during install
    echo     4. Run this installer again
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do set "PY_FULL=%%i"
echo   [OK] Found %PY_FULL%

REM ── Step 2: Create Virtual Environment ─────────────────────

echo.
echo   [2/%TOTAL_STEPS%] Setting up environment...
echo   ────────────────────────────────────────

if not exist "%VENV_DIR%" (
    echo   Creating virtual environment...
    %PYTHON% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo   ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

call "%VENV_DIR%\Scripts\activate.bat"
cd /d "%PROJECT_DIR%"
echo   [OK] Virtual environment ready

echo   Installing packages... (this may take a minute)
pip install --upgrade pip -q 2>nul
pip install -r "%PROJECT_DIR%\requirements.txt" -q 2>nul
if !errorlevel! neq 0 (
    echo   ERROR: Failed to install packages
    pause
    exit /b 1
)
echo   [OK] All packages installed

REM ── Step 3: Install Resolve assets ────────────────────────

echo.
echo   [3/%TOTAL_STEPS%] Installing LUTs, DCTLs, and Fusion templates...
echo   ────────────────────────────────────────

"%VENV_DIR%\Scripts\python.exe" -m src.automation.preset_manager install-bundled --strict
if errorlevel 1 (
    echo   [!] Resolve asset install failed
    echo       If Resolve uses a custom LUT folder, set RESOLVE_LUT_DIR and run again
    exit /b 1
)
echo   [OK] All Resolve assets installed

REM ── Step 4: Configure MCP ──────────────────────────────────

echo.
echo   [4/%TOTAL_STEPS%] Setting up AI connection...
echo   ────────────────────────────────────────

set "RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
set "RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"

if exist "%RESOLVE_SCRIPT_API%" (
    echo   [OK] Resolve Script API found
) else (
    echo   [!] Resolve Script API not found
    echo       Make sure DaVinci Resolve (not just Player) is installed
)

set "CURSOR_CONFIG=%USERPROFILE%\.cursor\mcp.json"
if not exist "%USERPROFILE%\.cursor" mkdir "%USERPROFILE%\.cursor" 2>nul

if not exist "%CURSOR_CONFIG%" (
    (
        echo {
        echo   "mcpServers": {
        echo     "resolve-aio": {
        echo       "command": "%VENV_DIR:\=/%/Scripts/python.exe",
        echo       "args": ["-m", "src.mcp.server"],
        echo       "cwd": "%PROJECT_DIR:\=/%",
        echo       "env": {
        echo         "RESOLVE_SCRIPT_API": "%RESOLVE_SCRIPT_API:\=/%",
        echo         "RESOLVE_SCRIPT_LIB": "%RESOLVE_SCRIPT_LIB:\=/%",
        echo         "PYTHONPATH": "%RESOLVE_SCRIPT_API:\=/%/Modules/"
        echo       }
        echo     }
        echo   }
        echo }
    ) > "%CURSOR_CONFIG%"
    echo   [OK] Cursor MCP configured
) else (
    echo   [!] Cursor config already exists — not overwriting
)

REM ── Step 5: Create Desktop Shortcuts ───────────────────────

echo.
echo   [5/%TOTAL_STEPS%] Creating desktop shortcuts...
echo   ────────────────────────────────────────

set "DESKTOP=%USERPROFILE%\Desktop"

REM Server shortcut
(
    echo @echo off
    echo title ResolveAIO — MCP Server
    echo color 1F
    echo cd /d "%PROJECT_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo set "RESOLVE_SCRIPT_API=%RESOLVE_SCRIPT_API%"
    echo set "RESOLVE_SCRIPT_LIB=%RESOLVE_SCRIPT_LIB%"
    echo set "PYTHONPATH=%RESOLVE_SCRIPT_API%\Modules\;%%PYTHONPATH%%"
    echo echo.
    echo echo   ResolveAIO — MCP Server
    echo echo   ═══════════════════════
    echo echo   The server is running. Open Cursor and start chatting with Resolve.
    echo echo   To stop: close this window or press Ctrl+C
    echo echo.
    echo python -m src.mcp.server
    echo pause
) > "%DESKTOP%\ResolveAIO - Start Server.bat"
echo   [OK] Created: ResolveAIO - Start Server.bat

REM Chat shortcut
(
    echo @echo off
    echo title ResolveAIO — Chat
    echo color 1F
    echo cd /d "%PROJECT_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo set "RESOLVE_SCRIPT_API=%RESOLVE_SCRIPT_API%"
    echo set "RESOLVE_SCRIPT_LIB=%RESOLVE_SCRIPT_LIB%"
    echo set "PYTHONPATH=%RESOLVE_SCRIPT_API%\Modules\;%%PYTHONPATH%%"
    echo echo.
    echo echo   ResolveAIO — Chat UI
    echo echo   ════════════════════
    echo echo   Opening browser...
    echo echo   To stop: close this window
    echo echo.
    echo start http://127.0.0.1:9881
    echo python -m src.ui.chat_panel
) > "%DESKTOP%\ResolveAIO - Chat.bat"
echo   [OK] Created: ResolveAIO - Chat.bat

REM ── Step 6: Verify ────────────────────────────────────────

echo.
echo   [6/%TOTAL_STEPS%] Verifying installation...
echo   ────────────────────────────────────────

"%VENV_DIR%\Scripts\python.exe" -c "from src.mcp.resolve_bridge import ResolveBridge; print('ok')" 2>nul
if !errorlevel! equ 0 (
    echo   [OK] All modules load successfully
) else (
    echo   [!] Module import issue — Resolve may need to be running
)

echo   [OK] DCTL files: %DCTL_COUNT% installed

REM ── Done ───────────────────────────────────────────────────

echo.
echo.
echo   ╔═══════════════════════════════════════════════════╗
echo   ║                                                   ║
echo   ║          Installation Complete!                    ║
echo   ║                                                   ║
echo   ╚═══════════════════════════════════════════════════╝
echo.
echo   What now?
echo.
echo   Option 1: Double-click "ResolveAIO - Chat" on your Desktop
echo             A chat window will open in your browser
echo.
echo   Option 2: Double-click "ResolveAIO - Start Server" on your Desktop
echo             Then open Cursor and chat with AI
echo.
echo   Option 3: Open Resolve ^> Color Page ^> Effects ^> DCTL
echo             Look under ResolveAIO for color tools
echo.
echo   IMPORTANT: Make sure DaVinci Resolve is running first!
echo.
pause
