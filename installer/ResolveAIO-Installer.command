#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  ResolveAIO — One-Click Installer for macOS
#  Double-click this file to install. That's it.
# ══════════════════════════════════════════════════════════════
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Navigate to project root (installer/ is inside the project)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"
TOTAL_STEPS=6
CURRENT_STEP=0

# ── Helpers ──────────────────────────────────────────────────

progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    echo -e "  ${CYAN}[$CURRENT_STEP/$TOTAL_STEPS]${NC} ${BOLD}$1${NC}"
    echo -e "  ${DIM}────────────────────────────────────────${NC}"
}

success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

fail() {
    echo -e "  ${RED}✗ $1${NC}"
    echo ""
    echo -e "  ${RED}ההתקנה נכשלה. לחץ Enter לסגור.${NC}"
    read -r
    exit 1
}

# ── Welcome Screen ───────────────────────────────────────────

clear
echo ""
echo -e "${BLUE}"
cat << 'LOGO'
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║     ██████╗ ███████╗███████╗ ██████╗ ██╗    ██╗   ║
    ║     ██╔══██╗██╔════╝██╔════╝██╔═══██╗██║    ██║   ║
    ║     ██████╔╝█████╗  ███████╗██║   ██║██║    ██║   ║
    ║     ██╔══██╗██╔══╝  ╚════██║██║   ██║██║    ██║   ║
    ║     ██║  ██║███████╗███████║╚██████╔╝███████╗██║   ║
    ║     ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═════╝╚═╝   ║
    ║                    A I O                            ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
LOGO
echo -e "${NC}"
echo -e "  ${BOLD}All-in-One Plugin for DaVinci Resolve${NC}"
echo -e "  ${DIM}MCP Server · DCTL Tools · Automation · Chat UI${NC}"
echo ""
echo -e "  ${DIM}──────────────────────────────────────────${NC}"
echo ""
echo -e "  ההתקנה תבצע:"
echo -e "  ${DIM}1.${NC} בדיקת Python"
echo -e "  ${DIM}2.${NC} התקנת חבילות נדרשות"
echo -e "  ${DIM}3.${NC} התקנת כלי צבע (DCTL) ל-DaVinci Resolve"
echo -e "  ${DIM}4.${NC} הגדרת חיבור AI (Cursor / Claude Desktop)"
echo -e "  ${DIM}5.${NC} יצירת קיצורי דרך להפעלה"
echo ""
echo -e "  ${YELLOW}וודא ש-DaVinci Resolve מותקן לפני שממשיכים.${NC}"
echo ""
echo -ne "  ${BOLD}לחץ Enter להתחלת ההתקנה...${NC} "
read -r

# ── Step 1: Check Python ────────────────────────────────────

progress "בודק Python..."

PYTHON=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null; then
        PY_VER=$($py -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")' 2>/dev/null || echo "0.0")
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
            PYTHON="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.10+ לא נמצא.\n\n  להתקנה:\n  1. פתח https://www.python.org/downloads/\n  2. הורד והתקן Python 3.12\n  3. הרץ את ה-Installer הזה שוב"
fi

PY_VERSION=$($PYTHON --version 2>&1)
success "נמצא $PY_VERSION ($PYTHON)"

# ── Step 2: Create Virtual Environment ──────────────────────

progress "יוצר סביבת עבודה..."

if [ -d "$VENV_DIR" ]; then
    success "סביבה קיימת כבר — משתמש בה"
else
    $PYTHON -m venv "$VENV_DIR" 2>/dev/null || fail "לא הצלחתי ליצור virtual environment"
    success "נוצרה סביבת עבודה"
fi

source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"

echo -e "  ${DIM}מתקין חבילות... (זה יכול לקחת דקה)${NC}"
pip install --upgrade pip -q 2>/dev/null
pip install -r "$PROJECT_DIR/requirements.txt" -q 2>/dev/null || fail "התקנת חבילות נכשלה"
success "כל החבילות הותקנו"

# ── Step 3: Install Resolve Assets ──────────────────────────

progress "מתקין LUTs, DCTLs ותבניות Fusion ל-DaVinci Resolve..."

LUT_DIR="$("$VENV_DIR/bin/python" -m src.automation.preset_manager print-lut-dir)"
echo -e "  ${DIM}LUT target: $LUT_DIR${NC}"

if [[ "$LUT_DIR" == /Library/* || "$LUT_DIR" == /opt/* ]]; then
    echo -e "  ${YELLOW}נדרשת הרשאת מנהל להתקנת LUT/DCTL (הכנס סיסמה)${NC}"
    sudo "$VENV_DIR/bin/python" -m src.automation.preset_manager install-bundled --strict --asset-type LUT --asset-type DCTL \
        || fail "התקנת LUT/DCTL נכשלה"
    "$VENV_DIR/bin/python" -m src.automation.preset_manager install-bundled --strict --asset-type FusionTemplate \
        || fail "התקנת Fusion templates נכשלה"
else
    "$VENV_DIR/bin/python" -m src.automation.preset_manager install-bundled --strict \
        || fail "התקנת Resolve assets נכשלה"
fi
success "כל ה-assets הותקנו"

# ── Step 4: Detect Resolve Script API ───────────────────────

progress "מגדיר חיבור ל-DaVinci Resolve..."

RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"

if [ -d "$RESOLVE_SCRIPT_API" ]; then
    success "Resolve Script API נמצא"
else
    warning "Resolve Script API לא נמצא"
    warning "וודא ש-DaVinci Resolve (לא רק Player) מותקן"
fi

# Configure Cursor
CURSOR_CONFIG="$HOME/.cursor/mcp.json"
mkdir -p "$(dirname "$CURSOR_CONFIG")" 2>/dev/null || true

MCP_ENTRY=$(cat <<JSONEOF
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

if [ -f "$CURSOR_CONFIG" ]; then
    warning "קובץ Cursor MCP כבר קיים — לא דורס"
    echo -e "  ${DIM}הוסף ידנית את resolve-aio ל-$CURSOR_CONFIG${NC}"
else
    echo "$MCP_ENTRY" > "$CURSOR_CONFIG"
    success "Cursor MCP הוגדר אוטומטית"
fi

# Configure Claude Desktop
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -d "$(dirname "$CLAUDE_CONFIG")" ]; then
    if [ ! -f "$CLAUDE_CONFIG" ]; then
        echo "$MCP_ENTRY" > "$CLAUDE_CONFIG"
        success "Claude Desktop הוגדר אוטומטית"
    else
        warning "קובץ Claude Desktop כבר קיים — לא דורס"
    fi
fi

# ── Step 5: Create Desktop Shortcuts ───────────────────────

progress "יוצר קיצורי דרך..."

# Create launcher apps on Desktop
DESKTOP="$HOME/Desktop"

# MCP Server launcher
cat > "$DESKTOP/ResolveAIO - Start Server.command" << LAUNCHER
#!/usr/bin/env bash
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"
export RESOLVE_SCRIPT_API="$RESOLVE_SCRIPT_API"
export RESOLVE_SCRIPT_LIB="$RESOLVE_SCRIPT_LIB"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules/"
echo ""
echo "  ResolveAIO — MCP Server"
echo "  ═══════════════════════"
echo "  השרת רץ. אפשר לפתוח Cursor ולהתחיל לדבר עם Resolve."
echo "  לעצירה: Ctrl+C"
echo ""
python -m src.mcp.server
LAUNCHER
chmod +x "$DESKTOP/ResolveAIO - Start Server.command"
success "נוצר: ResolveAIO - Start Server (שולחן העבודה)"

# Chat UI launcher
cat > "$DESKTOP/ResolveAIO - Chat.command" << LAUNCHER
#!/usr/bin/env bash
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"
export RESOLVE_SCRIPT_API="$RESOLVE_SCRIPT_API"
export RESOLVE_SCRIPT_LIB="$RESOLVE_SCRIPT_LIB"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules/"
echo ""
echo "  ResolveAIO — Chat UI"
echo "  ════════════════════"
echo "  פותח דפדפן..."
echo "  לעצירה: Ctrl+C"
echo ""
sleep 1 && open "http://127.0.0.1:9881" &
python -m src.ui.chat_panel
LAUNCHER
chmod +x "$DESKTOP/ResolveAIO - Chat.command"
success "נוצר: ResolveAIO - Chat (שולחן העבודה)"

# ── Step 6: Verify ──────────────────────────────────────────

progress "בודק שהכל תקין..."

# Quick import test
IMPORT_OK=$("$VENV_DIR/bin/python" -c "from src.mcp.resolve_bridge import ResolveBridge; print('ok')" 2>/dev/null || echo "fail")
if [ "$IMPORT_OK" = "ok" ]; then
    success "כל המודולים נטענים בהצלחה"
else
    warning "בעיה בטעינת מודולים — ייתכן שצריך להפעיל Resolve"
fi

DCTL_CHECK=$(find "$DCTL_DEST" -name "*.dctl" 2>/dev/null | wc -l | tr -d ' ')
success "DCTL files: $DCTL_CHECK מותקנים"

# ── Done! ────────────────────────────────────────────────────

echo ""
echo ""
echo -e "${GREEN}"
cat << 'DONE'
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║           ✓  ההתקנה הושלמה בהצלחה!               ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
DONE
echo -e "${NC}"
echo -e "  ${BOLD}מה עכשיו?${NC}"
echo ""
echo -e "  ${CYAN}אפשרות 1:${NC} לחץ פעמיים על ${BOLD}ResolveAIO - Chat${NC} בשולחן העבודה"
echo -e "            → ייפתח ממשק צ'אט בדפדפן לשליטה ב-Resolve"
echo ""
echo -e "  ${CYAN}אפשרות 2:${NC} לחץ פעמיים על ${BOLD}ResolveAIO - Start Server${NC} בשולחן העבודה"
echo -e "            → ואז פתח Cursor ודבר עם ה-AI"
echo ""
echo -e "  ${CYAN}אפשרות 3:${NC} פתח Resolve → Color Page → Effects → DCTL"
echo -e "            → חפש תחת ResolveAIO לכלי צבע"
echo ""
echo -e "  ${YELLOW}חשוב: וודא ש-DaVinci Resolve רץ לפני שמפעילים!${NC}"
echo ""
echo -ne "  ${DIM}לחץ Enter לסגור...${NC} "
read -r
