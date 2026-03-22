#!/usr/bin/env bash
# ResolveAIO — Uninstaller for macOS
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo -e "${RED}${BOLD}  ResolveAIO — Uninstaller${NC}"
echo -e "  ${DIM}════════════════════════${NC}"
echo ""
echo "  This will remove:"
echo "    1. DCTL files from Resolve LUT directory"
echo "    2. Desktop shortcuts"
echo "    3. Virtual environment (.venv)"
echo "    4. MCP configuration from Cursor/Claude"
echo ""
echo -e "  ${YELLOW}The project files themselves will NOT be deleted.${NC}"
echo ""
echo -ne "  Are you sure? (y/N): "
read -r CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "  Cancelled."
    exit 0
fi

echo ""

# Remove DCTLs
DCTL_DIR="/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/ResolveAIO"
if [ -d "$DCTL_DIR" ]; then
    if [ -w "$DCTL_DIR" ]; then
        rm -rf "$DCTL_DIR"
    else
        sudo rm -rf "$DCTL_DIR"
    fi
    echo -e "  ${GREEN}✓${NC} Removed DCTL files"
else
    echo -e "  ${DIM}—${NC} No DCTL files found"
fi

# Remove desktop shortcuts
DESKTOP="$HOME/Desktop"
for f in "ResolveAIO - Start Server.command" "ResolveAIO - Chat.command"; do
    if [ -f "$DESKTOP/$f" ]; then
        rm "$DESKTOP/$f"
        echo -e "  ${GREEN}✓${NC} Removed $f"
    fi
done

# Remove venv
if [ -d "$PROJECT_DIR/.venv" ]; then
    rm -rf "$PROJECT_DIR/.venv"
    echo -e "  ${GREEN}✓${NC} Removed virtual environment"
fi

# Clean Cursor config
CURSOR_CONFIG="$HOME/.cursor/mcp.json"
if [ -f "$CURSOR_CONFIG" ]; then
    if grep -q "resolve-aio" "$CURSOR_CONFIG" 2>/dev/null; then
        # If it's our config (only has resolve-aio), remove it
        if python3 -c "
import json, sys
with open('$CURSOR_CONFIG') as f:
    cfg = json.load(f)
servers = cfg.get('mcpServers', {})
if list(servers.keys()) == ['resolve-aio']:
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null; then
            rm "$CURSOR_CONFIG"
            echo -e "  ${GREEN}✓${NC} Removed Cursor MCP config"
        else
            echo -e "  ${YELLOW}⚠${NC} Cursor config has other servers — remove resolve-aio manually"
        fi
    fi
fi

# Clean Claude Desktop config
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_CONFIG" ]; then
    if grep -q "resolve-aio" "$CLAUDE_CONFIG" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Claude Desktop config contains resolve-aio — remove manually"
    fi
fi

echo ""
echo -e "  ${GREEN}${BOLD}Uninstall complete.${NC}"
echo -e "  ${DIM}Project files are still at: $PROJECT_DIR${NC}"
echo ""
echo -ne "  Press Enter to close... "
read -r
