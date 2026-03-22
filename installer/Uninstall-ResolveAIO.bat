@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title ResolveAIO — Uninstaller
color 4F

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

echo.
echo   ResolveAIO — Uninstaller
echo   ════════════════════════
echo.
echo   This will remove:
echo     1. DCTL files from Resolve LUT directory
echo     2. Desktop shortcuts
echo     3. Virtual environment (.venv)
echo     4. MCP configuration from Cursor
echo.
echo   The project files themselves will NOT be deleted.
echo.
set /p "CONFIRM=  Are you sure? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo   Cancelled.
    pause
    exit /b 0
)

echo.

REM Remove DCTLs
set "DCTL_DIR=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\LUT\ResolveAIO"
if exist "%DCTL_DIR%" (
    rmdir /s /q "%DCTL_DIR%"
    echo   [OK] Removed DCTL files
) else (
    echo   [--] No DCTL files found
)

REM Remove desktop shortcuts
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%\ResolveAIO - Start Server.bat" (
    del "%DESKTOP%\ResolveAIO - Start Server.bat"
    echo   [OK] Removed Start Server shortcut
)
if exist "%DESKTOP%\ResolveAIO - Chat.bat" (
    del "%DESKTOP%\ResolveAIO - Chat.bat"
    echo   [OK] Removed Chat shortcut
)

REM Remove venv
if exist "%PROJECT_DIR%\.venv" (
    rmdir /s /q "%PROJECT_DIR%\.venv"
    echo   [OK] Removed virtual environment
)

REM Clean Cursor config
set "CURSOR_CONFIG=%USERPROFILE%\.cursor\mcp.json"
if exist "%CURSOR_CONFIG%" (
    findstr /c:"resolve-aio" "%CURSOR_CONFIG%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [!] Cursor config contains resolve-aio — remove manually
        echo       File: %CURSOR_CONFIG%
    )
)

echo.
echo   Uninstall complete.
echo   Project files are still at: %PROJECT_DIR%
echo.
pause
