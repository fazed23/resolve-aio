#!/usr/bin/env bash
# ResolveAIO Installer — macOS / Linux
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

echo "╔══════════════════════════════════════╗"
echo "║       ResolveAIO — Installer         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# --- Detect Python ---
PYTHON=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null; then
        PYTHON="$py"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python 3.10+ not found. Install it first."
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Found Python $PY_VERSION ($PYTHON)"

# --- Create virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"
echo "✓ Virtual environment active"

# --- Install dependencies ---
echo "→ Installing dependencies..."
pip install --upgrade pip -q
pip install -r "$PROJECT_DIR/requirements.txt" -q
echo "✓ Dependencies installed"

# --- Detect Resolve paths ---
RESOLVE_SCRIPT_API=""
RESOLVE_SCRIPT_LIB=""

if [ "$(uname)" = "Darwin" ]; then
    RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
    RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    LUT_DIR="/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"
else
    RESOLVE_SCRIPT_API="/opt/resolve/Developer/Scripting"
    RESOLVE_SCRIPT_LIB="/opt/resolve/libs/Fusion/fusionscript.so"
    LUT_DIR="/opt/resolve/LUT"
fi

if [ -d "$RESOLVE_SCRIPT_API" ]; then
    echo "✓ Resolve Script API found: $RESOLVE_SCRIPT_API"
else
    echo "⚠ Resolve Script API not found at: $RESOLVE_SCRIPT_API"
    echo "  Make sure DaVinci Resolve is installed."
fi

# --- Install bundled assets ---
echo "→ Installing bundled Resolve assets..."
LUT_TARGET="$($VENV_PYTHON -m src.automation.preset_manager print-lut-dir)"
echo "  LUT target: $LUT_TARGET"
if [[ "$LUT_TARGET" == /Library/* || "$LUT_TARGET" == /opt/* ]]; then
    echo "  Administrator access is required for LUT and DCTL files."
    sudo "$VENV_PYTHON" -m src.automation.preset_manager install-bundled --strict --asset-type LUT --asset-type DCTL
    "$VENV_PYTHON" -m src.automation.preset_manager install-bundled --strict --asset-type FusionTemplate
else
    "$VENV_PYTHON" -m src.automation.preset_manager install-bundled --strict
fi
echo "✓ Bundled assets installed"

# --- Configure Cursor MCP ---
CURSOR_CONFIG="$HOME/.cursor/mcp.json"
echo ""
echo "→ Configuring Cursor MCP integration..."

CURSOR_MCP_JSON=$(cat <<JSONEOF
{
  "mcpServers": {
    "resolve-aio": {
      "command": "$VENV_DIR/bin/python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "$PROJECT_DIR",
      "env": {
        "RESOLVE_SCRIPT_API": "$RESOLVE_SCRIPT_API",
        "RESOLVE_SCRIPT_LIB": "$RESOLVE_SCRIPT_LIB",
        "PYTHONPATH": "$RESOLVE_SCRIPT_API/Modules/"
      }
    }
  }
}
JSONEOF
)

mkdir -p "$(dirname "$CURSOR_CONFIG")"
if [ -f "$CURSOR_CONFIG" ]; then
    echo "  ⚠ $CURSOR_CONFIG already exists."
    echo "  Add the following to your mcpServers:"
    echo "$CURSOR_MCP_JSON"
else
    echo "$CURSOR_MCP_JSON" > "$CURSOR_CONFIG"
    echo "  ✓ Created $CURSOR_CONFIG"
fi

# --- Done ---
echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Installation Complete!         ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "To start the MCP server (for Cursor/Claude Desktop):"
echo "  ./scripts/run.sh"
echo ""
echo "To start the Chat UI:"
echo "  ./scripts/run.sh --chat"
echo ""
echo "To enable GPT in the Chat UI, edit:"
echo "  config/resolve_aio.env"
echo ""
echo "Make sure DaVinci Resolve is running before starting!"
