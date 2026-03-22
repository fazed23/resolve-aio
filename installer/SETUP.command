#!/bin/bash

# ──────────────────────────────────────────────────
#  ResolveAIO — Quick Setup
#  If the installer doesn't open, run this first:
#  Right-click → Open (or run in Terminal)
# ──────────────────────────────────────────────────

DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  Removing macOS security blocks..."
xattr -cr "$DIR" 2>/dev/null
xattr -cr "$DIR/ResolveAIO-Installer.command" 2>/dev/null
xattr -cr "$DIR/ResolveAIO Installer.app" 2>/dev/null
xattr -cr "$DIR/Uninstall-ResolveAIO.command" 2>/dev/null
chmod +x "$DIR/ResolveAIO-Installer.command" 2>/dev/null
chmod +x "$DIR/ResolveAIO Installer.app/Contents/MacOS/launch" 2>/dev/null
chmod +x "$DIR/Uninstall-ResolveAIO.command" 2>/dev/null
echo "  Done! Now launching installer..."
echo ""

# Launch the installer
exec "$DIR/ResolveAIO-Installer.command"
