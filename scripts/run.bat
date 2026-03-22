@echo off
REM ResolveAIO Runner — Windows
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%PROJECT_DIR%\.venv"

if not exist "%VENV_DIR%" (
    echo Virtual environment not found. Run scripts\install.bat first.
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

set "ENV_FILE=%PROJECT_DIR%\config\resolve_aio.env"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        if not "%%A"=="" if not "%%A:~0,1%%"=="#" set "%%A=%%B"
    )
)

set "RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
set "RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
set "PYTHONPATH=%RESOLVE_SCRIPT_API%\Modules\;%PYTHONPATH%"

cd /d "%PROJECT_DIR%"

if "%~1"=="--chat" (
    echo Starting ResolveAIO Chat UI on http://127.0.0.1:9881
    if "%OPENAI_API_KEY%"=="" echo GPT is disabled. Add OPENAI_API_KEY to config\resolve_aio.env to enable it.
    python -m src.ui.chat_panel %*
) else if "%~1"=="--sse" (
    echo Starting ResolveAIO MCP Server (SSE mode)
    python -m src.mcp.server --transport sse %*
) else (
    echo Starting ResolveAIO MCP Server (stdio mode)
    python -m src.mcp.server %*
)
