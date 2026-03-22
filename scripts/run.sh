#!/usr/bin/env bash
# ResolveAIO Runner — macOS / Linux
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Run ./scripts/install.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

ENV_FILE="$PROJECT_DIR/config/resolve_aio.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Set Resolve environment
if [ "$(uname)" = "Darwin" ]; then
    export RESOLVE_SCRIPT_API="${RESOLVE_SCRIPT_API:-/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting}"
    export RESOLVE_SCRIPT_LIB="${RESOLVE_SCRIPT_LIB:-/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so}"
else
    export RESOLVE_SCRIPT_API="${RESOLVE_SCRIPT_API:-/opt/resolve/Developer/Scripting}"
    export RESOLVE_SCRIPT_LIB="${RESOLVE_SCRIPT_LIB:-/opt/resolve/libs/Fusion/fusionscript.so}"
fi
export PYTHONPATH="${RESOLVE_SCRIPT_API}/Modules/:${PYTHONPATH:-}"

cd "$PROJECT_DIR"

if [ "${1:-}" = "--chat" ]; then
    echo "Starting ResolveAIO Chat UI on http://127.0.0.1:9881"
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        echo "GPT is disabled. Add OPENAI_API_KEY to config/resolve_aio.env to enable it."
    fi
    python -m src.ui.chat_panel "$@"
elif [ "${1:-}" = "--sse" ]; then
    echo "Starting ResolveAIO MCP Server (SSE mode) on port 9880"
    python -m src.mcp.server --transport sse "$@"
else
    echo "Starting ResolveAIO MCP Server (stdio mode)"
    python -m src.mcp.server "$@"
fi
