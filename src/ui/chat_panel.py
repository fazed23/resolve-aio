"""
Chat Panel v2 — Full AI Studio interface for ResolveAIO.

Routes natural language commands (English + Hebrew) to Resolve bridge methods.
Handles presets, text animations, rough cuts, color science, and tutorials.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ..env_config import load_project_env
from ..mcp.resolve_bridge import get_bridge
from ..automation.preset_manager import (
    find_bundled_asset,
    install_bundled_assets,
    install_preset,
    list_bundled_assets,
    list_installed_presets,
)
from ..automation.powergrade_tools import (
    apply_powergrade_to_all_clips,
    export_current_powergrade,
    export_timeline_powergrades,
    list_gallery_albums,
)

logger = logging.getLogger("resolve_aio.chat")

load_project_env()

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ResolveAIO Studio")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_openai_api_key() -> str | None:
    """Return a non-empty OpenAI API key from the environment, if configured."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    return api_key or None


def _create_ai_engine(bridge: Any):
    """Create the GPT-backed AI engine only when API credentials are available."""
    api_key = _get_openai_api_key()
    if not api_key:
        return None

    try:
        from .ai_engine import AIEngine
    except Exception as exc:
        logger.warning("AI engine unavailable: %s", exc)
        return None

    return AIEngine(bridge=bridge, api_key=api_key)


def _ai_mode_message() -> str:
    if _get_openai_api_key():
        return "GPT tools enabled."
    return "Built-in command mode. Add OPENAI_API_KEY to config/resolve_aio.env to enable GPT."


# ── Tutorial content ────────────────────────────────────────

TUTORIAL_CONTENT = {
    "getting started with resolveaio": (
        "Getting Started with ResolveAIO\n"
        "═══════════════════════════════\n\n"
        "1. Make sure DaVinci Resolve is open and running\n"
        "2. The status indicator (bottom-left) should show 'Connected'\n"
        "3. Try these commands:\n"
        "   • 'version' — check which Resolve version is running\n"
        "   • 'list projects' — see all your projects\n"
        "   • 'list timelines' — see timelines in current project\n"
        "   • 'go to color' — switch to the Color page\n\n"
        "4. Use the Quick Actions bar above for common commands\n"
        "5. Navigate the sidebar to explore Presets, Text Animations,\n"
        "   Automation tools, and more.\n\n"
        "Tip: You can type in English or Hebrew!"
    ),
    "ai chat commands": (
        "AI Chat Commands — Complete Reference\n"
        "══════════════════════════════════════\n\n"
        "PROJECT:\n"
        "  • list projects / show projects\n"
        "  • current project / project name\n"
        "  • open project \"Name\"\n"
        "  • create project \"Name\"\n"
        "  • save / save project\n\n"
        "TIMELINE:\n"
        "  • list timelines\n"
        "  • current timeline\n"
        "  • create timeline \"Name\" / create timeline called \"Name\"\n"
        "  • switch to timeline \"Name\"\n"
        "  • delete timeline \"Name\"\n\n"
        "NAVIGATION:\n"
        "  • go to edit / go to color / go to fusion / etc.\n"
        "  • current page / which page\n"
        "  • version\n\n"
        "MEDIA:\n"
        "  • list clips / show clips\n"
        "  • list bins\n"
        "  • create bin \"Name\"\n"
        "  • import media /path/to/file\n\n"
        "MARKERS:\n"
        "  • add marker at frame 100\n"
        "  • add marker at current position\n"
        "  • list markers / show markers\n"
        "  • timecode / current timecode\n\n"
        "COLOR:\n"
        "  • list timeline clips\n"
        "  • auto grade all clips\n"
        "  • apply film look\n"
        "  • export current powergrade \"Hero Look\"\n"
        "  • export timeline powergrades\n"
        "  • apply preset \"Name\"\n"
        "  • list installed luts\n\n"
        "FUSION TEMPLATES:\n"
        "  • install text animation \"Typewriter\"\n"
        "  • install transition \"Whip Slide\"\n\n"
        "RENDER:\n"
        "  • render presets / list render presets\n"
        "  • batch render all timelines\n"
        "  • start render / stop render\n"
        "  • render status\n\n"
        "AUTOMATION:\n"
        "  • remove silence / detect silence\n"
        "  • color tag clips by duration\n"
        "  • install all presets\n"
        "  • generate timeline report\n"
    ),
    "understanding node trees": (
        "Understanding Node Trees\n"
        "════════════════════════\n\n"
        "A node tree is the order of color corrections applied to each clip.\n"
        "Think of it like a recipe — the order of steps matters.\n\n"
        "PROFESSIONAL NODE TREE ORDER:\n"
        "─────────────────────────────\n"
        "Node 1: INPUT TRANSFORM\n"
        "  Convert from camera log to working space\n"
        "  (e.g., S-Log3 → DaVinci Wide Gamut)\n\n"
        "Node 2: BALANCE / EXPOSURE\n"
        "  Fix white balance, exposure, and basic levels\n\n"
        "Node 3: CONTRAST\n"
        "  S-curve or lift/gamma/gain for contrast shape\n\n"
        "Node 4: SKIN TONES (Parallel)\n"
        "  Isolate and protect skin with qualifier\n\n"
        "Node 5: SKY / SECONDARY\n"
        "  Secondary corrections for specific elements\n\n"
        "Node 6: CREATIVE LOOK\n"
        "  LUT, PowerGrade, or manual look development\n\n"
        "Node 7: FILM GRAIN / HALATION\n"
        "  Always last — grain responds to final luminosity\n\n"
        "Node 8: OUTPUT TRANSFORM\n"
        "  Convert to delivery space (Rec.709, HDR10, etc.)\n\n"
        "WHY ORDER MATTERS:\n"
        "  • Operations early in the tree affect everything after\n"
        "  • Color space transforms must bookend the creative work\n"
        "  • Grain/halation must be last (they depend on final luma)\n"
    ),
    "powergrades explained": (
        "PowerGrades Explained\n"
        "═════════════════════\n\n"
        "A PowerGrade is a saved node tree that you can apply to any clip.\n"
        "Unlike LUTs, PowerGrades are FULLY EDITABLE — you can tweak every node.\n\n"
        "HOW TO USE:\n"
        "  1. Go to Color Page\n"
        "  2. Open Gallery (top-left)\n"
        "  3. Right-click → 'PowerGrades' album\n"
        "  4. Drag a PowerGrade onto a clip\n"
        "  5. Adjust individual nodes as needed\n\n"
        "HOW TO CREATE YOUR OWN:\n"
        "  1. Grade a clip the way you want\n"
        "  2. Right-click the thumbnail → 'Grab Still'\n"
        "  3. In Gallery, drag the still to 'PowerGrades' album\n"
        "  4. Right-click → 'Rename' to give it a meaningful name\n\n"
        "POWERGRADE vs LUT:\n"
        "  • LUT: Baked, fixed transform. Can't see or edit the math.\n"
        "  • PowerGrade: Editable nodes. See and tweak everything.\n"
        "  • LUT: Works in any software. PowerGrade: Resolve only.\n"
        "  • Use LUTs for delivery. Use PowerGrades for grading.\n\n"
        "ResolveAIO ships real LUTs, DCTLs, and Fusion templates, and it can export real DRX files from Resolve.\n"
        "Try: export current powergrade \"Hero Look\" or export timeline powergrades.\n"
    ),
    "aces vs davinci wide gamut": (
        "ACES vs DaVinci Wide Gamut\n"
        "══════════════════════════\n\n"
        "Both are 'scene-referred' workflows that give you more control.\n\n"
        "ACES (Academy Color Encoding System):\n"
        "  • Industry standard for film & VFX\n"
        "  • Huge color space (covers all visible colors)\n"
        "  • Input Device Transforms (IDT) for each camera\n"
        "  • Output: RRT + ODT for each display\n"
        "  • Best for: VFX-heavy projects, multi-camera, archival\n"
        "  • Setup: Project Settings → Color Management → ACES\n\n"
        "DaVinci Wide Gamut (DWG):\n"
        "  • Resolve's native wide gamut space\n"
        "  • Slightly easier to set up than ACES\n"
        "  • Uses CST (Color Space Transform) nodes\n"
        "  • Best for: Projects staying inside Resolve\n"
        "  • Setup: Project Settings → Color Science → DaVinci YRGB Color Managed\n\n"
        "QUICK DECISION:\n"
        "  • Indie project, one camera? → DWG or even Rec.709\n"
        "  • Multi-camera, VFX? → ACES\n"
        "  • Client requires ACES? → ACES\n"
        "  • Quick turnaround? → DWG\n"
    ),
    "camera-specific color workflows": (
        "Camera-Specific Color Workflows\n"
        "════════════════════════════════\n\n"
        "SONY (S-Log3 / S-Gamut3.Cine):\n"
        "  CST: S-Log3/S-Gamut3.Cine → DWG/DWG-I\n"
        "  Tips: Expose +1.5 to +2 stops over. S-Log3 has great DR.\n\n"
        "ARRI (LogC3 / LogC4):\n"
        "  CST: ARRI LogC3 or LogC4 / Wide Gamut → DWG\n"
        "  Tips: ARRI has the best native color science. Minimal work needed.\n\n"
        "CANON (C-Log3 / Cinema Gamut):\n"
        "  CST: Canon Log 3/Cinema Gamut → DWG\n"
        "  Tips: Canon reds tend to be warm. May need slight hue shift.\n\n"
        "RED (Log3G10 / REDWideGamutRGB):\n"
        "  Use IPP2 pipeline in Resolve\n"
        "  Tips: Adjust ISO in RAW settings first, then grade.\n\n"
        "BLACKMAGIC (BMD Film Gen5):\n"
        "  CST: Blackmagic Design Film/Wide Gamut → DWG\n"
        "  Tips: Pocket cameras need NR. Good dynamic range.\n\n"
        "APPLE (Apple Log):\n"
        "  CST: Apple Log → DWG (Resolve 18.6+)\n"
        "  Tips: iPhone footage. Good for social media, limited DR.\n\n"
        "DJI (D-Log M):\n"
        "  CST: DJI D-Log M → DWG\n"
        "  Tips: Drone footage. Watch for banding in skies.\n"
    ),
    "dctls": (
        "DCTLs — What They Are & How to Use\n"
        "════════════════════════════════════\n\n"
        "DCTL = DaVinci Color Transform Language\n"
        "Think of it as 'mini plugins' for the Color page.\n\n"
        "WHAT THEY DO:\n"
        "  • Run custom math on every pixel\n"
        "  • Execute on GPU (fast!)\n"
        "  • Have adjustable sliders and controls\n"
        "  • Can do things standard tools can't\n\n"
        "HOW TO USE:\n"
        "  1. Color Page → Add a new node\n"
        "  2. Open Effects Library\n"
        "  3. Search for 'DCTL' or browse LUT folder\n"
        "  4. Drag onto the node\n"
        "  5. Open Settings to adjust parameters\n\n"
        "ResolveAIO DCTLs INCLUDED:\n"
        "  Curves: S-Curve, Inverse S-Curve, Power Knee\n"
        "  Limiters: Signal Limiter, Luma Limiter, Clamp\n"
        "  Analysis: False Color, Gray Chart, Mid-Select\n"
        "  Conversion: Full↔Legal, Quantize\n"
        "  Creative: Channel Sat, Film Emulation, Skin Tone, Grain, Halation\n\n"
        "NOTE: DCTLs require DaVinci Resolve Studio (paid version).\n"
    ),
    "creating text animations in fusion": (
        "Creating Text Animations in Fusion\n"
        "════════════════════════════════════\n\n"
        "ResolveAIO ships bundled Fusion title templates in the Text Animations panel.\n"
        "You can also build your own:\n\n"
        "BASIC ANIMATED TITLE:\n"
        "  1. Edit Page → Effects → Titles → 'Text+' → drag to timeline\n"
        "  2. Click the clip → open Inspector\n"
        "  3. Go to Fusion page (or click 'Fusion' tab in Inspector)\n"
        "  4. In Fusion: Text+ node → Animate 'Size' or 'Position'\n"
        "  5. Set keyframes at start and end\n\n"
        "LOWER THIRD:\n"
        "  1. Create a Background node (set to a colored bar)\n"
        "  2. Add a Text+ node\n"
        "  3. Merge them together\n"
        "  4. Animate Position: start off-screen, slide in\n"
        "  5. Save as Macro → available in Edit page\n\n"
        "TYPEWRITER EFFECT:\n"
        "  1. Text+ node → 'Styled Text' tab\n"
        "  2. Right-click 'Write On' → Animate\n"
        "  3. Frame 0: Write On = 0, Frame 30: Write On = 1\n\n"
        "SAVING AS TEMPLATE:\n"
        "  1. Select all nodes\n"
        "  2. Right-click → 'Create Macro'\n"
        "  3. Check the parameters you want exposed\n"
        "  4. Save to: Fusion/Templates/Edit/Titles/\n"
        "  5. Restart Resolve — appears in Edit page Effects!\n"
    ),
    "rough cut workflow with ai": (
        "Rough Cut Workflow with AI\n"
        "══════════════════════════\n\n"
        "Let AI create your first assembly edit:\n\n"
        "STEP 1: IMPORT\n"
        "  Tell AI: 'import media from /path/to/footage'\n"
        "  AI imports all supported media files into the Media Pool.\n\n"
        "STEP 2: ORGANIZE\n"
        "  Tell AI: 'create bin called Interviews'\n"
        "  Tell AI: 'color tag clips by duration'\n"
        "  Short clips get tagged as B-roll, long as interviews.\n\n"
        "STEP 3: ASSEMBLE\n"
        "  Use the Rough Cut panel (sidebar → Rough Cut AI)\n"
        "  Options:\n"
        "    • Remove silence — cuts out dead air\n"
        "    • Sort by timecode — chronological order\n"
        "    • Color tag — visual organization\n"
        "    • Scene markers — mark scene changes\n\n"
        "STEP 4: REFINE\n"
        "  Tell AI: 'add marker at frame 240 with note Review'\n"
        "  Tell AI: 'switch to timeline Rough Cut v1'\n"
        "  Fine-tune in the Edit page manually.\n\n"
        "STEP 5: GRADE\n"
        "  Tell AI: 'auto grade all clips'\n"
        "  Or apply a specific look: 'apply preset Cinematic Teal & Orange'\n"
    ),
    "batch rendering like a pro": (
        "Batch Rendering Like a Pro\n"
        "══════════════════════════\n\n"
        "Render multiple timelines or formats automatically:\n\n"
        "QUICK RENDER:\n"
        "  Tell AI: 'batch render all timelines'\n"
        "  Uses your default render preset for all timelines.\n\n"
        "CUSTOM RENDER:\n"
        "  1. Tell AI: 'list render presets'\n"
        "  2. Pick one: 'set render preset ProRes 422 HQ'\n"
        "  3. Set output: 'set render output to ~/Desktop/renders'\n"
        "  4. Start: 'start render'\n\n"
        "MONITOR:\n"
        "  Tell AI: 'render status' to check progress.\n"
        "  Tell AI: 'stop render' to abort.\n\n"
        "TIPS:\n"
        "  • Always render to a fast drive (SSD preferred)\n"
        "  • ProRes 422 HQ for editing/archive\n"
        "  • H.264/H.265 for final delivery\n"
        "  • Check 'Use Optimized Media' if available\n"
    ),
    "film emulation looks": (
        "Film Emulation Looks\n"
        "═════════════════════\n\n"
        "Recreate the look of classic film stocks digitally:\n\n"
        "KODAK VISION3 2383 (Print Film):\n"
        "  • Warm highlights, rich shadows\n"
        "  • The 'Hollywood' look\n"
        "  • Apply: 'apply preset Kodak 2383 Print'\n\n"
        "FUJI ETERNA 3513:\n"
        "  • Cooler tones, slightly green shadows\n"
        "  • More subtle than Kodak\n"
        "  • Apply: 'apply preset Fuji 3513 Print'\n\n"
        "KODAK PORTRA 400:\n"
        "  • Beautiful skin tones\n"
        "  • Slightly faded, pastel feel\n"
        "  • Apply: 'apply preset Faded Portra'\n\n"
        "DIY FILM LOOK RECIPE:\n"
        "  1. Lift the black point slightly (Data level 5-10)\n"
        "  2. Soft S-curve (not too aggressive)\n"
        "  3. Reduce saturation 10-20%\n"
        "  4. Add slight warmth to highlights\n"
        "  5. Cool the shadows (blue/teal shift)\n"
        "  6. Add halation (red glow from bright areas)\n"
        "  7. Add film grain (last node, always)\n\n"
        "Use the Film Emulation DCTL for a mathematical approach,\n"
        "or the Film Print Emulation PowerGrade for a node-based one.\n"
    ),
    "hdr grading fundamentals": (
        "HDR Grading Fundamentals\n"
        "═════════════════════════\n\n"
        "HDR = High Dynamic Range. More brightness, more colors.\n\n"
        "HDR FORMATS:\n"
        "  • HDR10: Static metadata, PQ curve, 1000-4000 nits\n"
        "  • HDR10+: Dynamic metadata (Samsung)\n"
        "  • Dolby Vision: Dynamic metadata, best quality\n"
        "  • HLG: Broadcast HDR, backward compatible\n\n"
        "SETUP IN RESOLVE:\n"
        "  1. Project Settings → Color Management\n"
        "  2. Timeline Color Space: Rec.2020/ST.2084 (for HDR10)\n"
        "  3. Output Color Space: match your target\n"
        "  4. Enable HDR grading tools in Color page\n\n"
        "GRADING TIPS:\n"
        "  • Grade SDR first, then trim for HDR\n"
        "  • Don't push highlights just because you can\n"
        "  • Specular highlights (sun, lights): 600-1000 nits\n"
        "  • Skin tones: 5-15 nits range\n"
        "  • Watch on a calibrated HDR monitor\n"
        "  • Use False Color DCTL to check levels\n\n"
        "DELIVERY:\n"
        "  • HDR10: HEVC 10-bit, MaxCLL/MaxFALL metadata\n"
        "  • Dolby Vision: Requires Resolve Studio + license\n"
        "  • YouTube HDR: VP9 or HEVC with HDR metadata\n"
    ),
}


# ── API Routes ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.get("/api/status")
async def api_status():
    bridge = get_bridge()
    c = bridge.connected
    return {
        "connected": c,
        "ai_enabled": _get_openai_api_key() is not None,
        "project": bridge.get_current_project_name() if c else "",
        "timeline": bridge.get_current_timeline_name() if c else "",
        "version": bridge.get_version() if c else "",
    }


@app.get("/api/presets")
async def api_presets():
    return {"presets": list_installed_presets()}


@app.get("/api/catalog")
async def api_catalog():
    assets = list_bundled_assets()
    presets = [asset for asset in assets if asset["type"] in {"DCTL", "LUT", "PowerGrade"}]
    text_animations = [
        asset
        for asset in assets
        if asset["type"] == "FusionTemplate" and asset["category"] == "Titles"
    ]
    transitions = [
        asset
        for asset in assets
        if asset["type"] == "FusionTemplate" and asset["category"] == "Transitions"
    ]
    counts = {
        "dctl": sum(1 for asset in assets if asset["type"] == "DCTL"),
        "lut": sum(1 for asset in assets if asset["type"] == "LUT"),
        "powergrade": sum(1 for asset in assets if asset["type"] == "PowerGrade"),
        "fusion_template": sum(1 for asset in assets if asset["type"] == "FusionTemplate"),
        "titles": len(text_animations),
        "transitions": len(transitions),
    }
    return {
        "presets": presets,
        "text_animations": text_animations,
        "transitions": transitions,
        "counts": counts,
    }


# ── WebSocket ───────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    bridge = get_bridge()
    ai_engine = _create_ai_engine(bridge)
    ai_mode = _ai_mode_message()
    await ws.send_json({
        "type": "system",
        "message": (
            "ResolveAIO Studio connected.\n"
            "Type any command in English or Hebrew to control DaVinci Resolve.\n"
            f"{ai_mode}"
        ),
    })
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            user_text = msg.get("message", "").strip()
            if not user_text:
                continue
            response = await process_command(bridge, user_text, ai_engine=ai_engine)
            await ws.send_json({"type": "assistant", "message": response})
    except WebSocketDisconnect:
        logger.info("Client disconnected")


# ── Command Engine ──────────────────────────────────────────

def _extract_quoted(text: str) -> str:
    """Extract text from quotes, or return last meaningful word."""
    m = re.search(r'["\'](.+?)["\']', text)
    if m:
        return m.group(1)
    # Try after keywords
    for kw in ["called", "named", "name", "to", "preset", "animation"]:
        if kw in text.lower():
            after = text.lower().split(kw)[-1].strip().strip("'\" ")
            if after:
                return after
    return ""


def _default_fallback_response(text: str) -> str:
    return (
        f"I'll try to help with: \"{text}\"\n\n"
        "Some things you can try:\n"
        "  • 'help' — see everything I can do\n"
        "  • 'version' — check connection to Resolve\n"
        "  • 'list projects' / 'list timelines' / 'list clips'\n"
        "  • 'go to color' / 'go to edit'\n"
        "  • 'teach me: node trees'\n"
        "  • 'apply preset Cinematic Teal & Orange'\n"
    )


def _format_asset_summary(asset: dict[str, str]) -> str:
    return (
        f"{asset['name']}\n"
        f"Type: {asset['type']}\n"
        f"Category: {asset['category']}\n"
        f"Source: {asset['relative']}\n"
        f"Action: {asset['action']}\n"
        f"{asset['description']}"
    )


def _parse_option_list(text: str) -> set[str]:
    marker = "with options:"
    lower = text.lower()
    if marker not in lower:
        return set()
    options_text = lower.split(marker, 1)[1]
    return {part.strip() for part in options_text.split(",") if part.strip()}


def _process_builtin_command(bridge, text: str) -> str | None:
    """Handle the built-in command set and return None when no rule matches."""
    lower = text.lower().strip()

    try:
        # ── Tutorials ──
        if lower.startswith("teach me"):
            topic = lower.replace("teach me:", "").replace("teach me", "").strip()
            for key, content in TUTORIAL_CONTENT.items():
                if any(w in topic for w in key.split()):
                    return content
            return "I have tutorials on:\n" + "\n".join(
                f"  • {k.title()}" for k in TUTORIAL_CONTENT.keys()
            ) + "\n\nTry: 'teach me: node trees'"

        # ── Version / Status ──
        if any(w in lower for w in ["version", "גרסה", "status", "סטטוס"]):
            try:
                v = bridge.get_version()
                proj = bridge.get_current_project_name()
                tl = bridge.get_current_timeline_name()
                page = bridge.get_current_page()
                return (
                    f"DaVinci Resolve {v}\n"
                    f"Project: {proj or 'None'}\n"
                    f"Timeline: {tl or 'None'}\n"
                    f"Page: {page or 'Unknown'}"
                )
            except Exception:
                return "Not connected to DaVinci Resolve. Make sure it's running."

        # ── Page Navigation ──
        if any(w in lower for w in ["current page", "which page", "איזה דף"]):
            return f"Current page: {bridge.get_current_page()}"

        for page in ["media", "cut", "edit", "fusion", "color", "fairlight", "deliver"]:
            if f"go to {page}" in lower or f"open {page}" in lower or f"switch to {page}" in lower or f"עבור ל{page}" in lower:
                ok = bridge.set_current_page(page)
                return f"Switched to {page.capitalize()} page" if ok else f"Failed to switch to {page}"

        # ── Projects ──
        if any(w in lower for w in ["list project", "show project", "הצג פרויקטים", "all projects"]):
            projects = bridge.list_projects()
            if not projects:
                return "No projects found in current database."
            return "Projects:\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(projects))

        if any(w in lower for w in ["current project", "project name", "פרויקט נוכחי"]):
            return f"Current project: {bridge.get_current_project_name() or 'None'}"

        if any(w in lower for w in ["open project", "load project", "פתח פרויקט"]):
            name = _extract_quoted(text)
            if name:
                ok = bridge.open_project(name)
                return f"Opened project: {name}" if ok else f"Could not open project '{name}'"
            return "Specify a project name: open project \"MyProject\""

        if any(w in lower for w in ["create project", "new project", "צור פרויקט"]):
            name = _extract_quoted(text)
            if name:
                p = bridge.create_project(name)
                return f"Created project: {name}" if p else f"Failed to create project '{name}'"
            return "Specify a name: create project \"MyProject\""

        if any(w in lower for w in ["save project", "save", "שמור"]):
            ok = bridge.save_project()
            return "Project saved successfully." if ok else "Failed to save project."

        # ── Timelines ──
        if any(w in lower for w in ["list timeline", "show timeline", "הצג טיימליינים", "all timelines"]) and "batch render" not in lower:
            tls = bridge.list_timelines()
            if not tls:
                return "No timelines in this project."
            lines = [f"  {t['index']}. {t['name']}  ({t['resolution']} @ {t['frame_rate']}fps)" for t in tls]
            return "Timelines:\n" + "\n".join(lines)

        if any(w in lower for w in ["current timeline", "טיימליין נוכחי", "active timeline"]):
            name = bridge.get_current_timeline_name()
            tc = bridge.get_current_timecode()
            return f"Current timeline: {name or 'None'}\nTimecode: {tc or 'N/A'}"

        if any(w in lower for w in ["create timeline", "new timeline", "צור טיימליין"]):
            name = _extract_quoted(text) or text.split("timeline")[-1].strip().strip("'\" ")
            if name and name not in ("", "called"):
                tl = bridge.create_timeline(name)
                return f"Created timeline: {name}" if tl else f"Failed to create timeline '{name}'"
            return "Specify a name: create timeline \"My Edit\""

        if "switch to timeline" in lower or "open timeline" in lower:
            name = _extract_quoted(text)
            if name:
                ok = bridge.set_current_timeline(name)
                return f"Switched to timeline: {name}" if ok else f"Timeline '{name}' not found"
            return "Specify a name: switch to timeline \"My Edit\""

        if "delete timeline" in lower:
            name = _extract_quoted(text)
            if name:
                ok = bridge.delete_timeline(name)
                return f"Deleted timeline: {name}" if ok else f"Could not delete timeline '{name}'"
            return "Specify a name: delete timeline \"Old Edit\""

        # ── Media Pool ──
        if any(w in lower for w in ["list clip", "show clip", "הצג קליפים", "all clips"]):
            clips = bridge.list_clips()
            if not clips:
                return "No clips in Media Pool."
            lines = [f"  • {c['name']}  ({c['duration']}, {c['resolution']})" for c in clips]
            return f"Clips ({len(clips)}):\n" + "\n".join(lines)

        if any(w in lower for w in ["list bin", "show bin", "folders"]):
            bins = bridge.list_bins()
            return "Bins:\n" + "\n".join(f"  • {b}" for b in bins) if bins else "No bins in root."

        if "create bin" in lower or "create folder" in lower:
            name = _extract_quoted(text)
            if name:
                f = bridge.create_bin(name)
                return f"Created bin: {name}" if f else f"Failed to create bin '{name}'"
            return "Specify a name: create bin \"B-Roll\""

        if "import media" in lower or "import file" in lower or "ייבא" in lower:
            path = text.split("import")[-1].strip().strip("'\" ")
            if path and path not in ("media", "file"):
                clips = bridge.import_media([path])
                return f"Imported {len(clips)} file(s)" if clips else "Import failed. Check the file path."
            return "Specify a path: import media /path/to/video.mp4"

        # ── Markers ──
        if any(w in lower for w in ["list marker", "show marker", "get marker"]):
            markers = bridge.get_markers()
            if not markers:
                return "No markers on current timeline."
            lines = []
            for frame, data in markers.items():
                lines.append(f"  Frame {frame}: [{data.get('color','')}] {data.get('name','')} — {data.get('note','')}")
            return f"Markers ({len(lines)}):\n" + "\n".join(lines)

        if "add marker" in lower or "הוסף מרקר" in lower:
            if "current" in lower:
                tc = bridge.get_current_timecode()
                # Try to get current frame
                tl = bridge.get_current_timeline()
                if tl:
                    frame = tl.GetCurrentVideoItem()
                    ok = bridge.add_marker(0, "Blue", "Marker", "Added by AI")
                    return f"Added marker at current position ({tc})" if ok else "Failed to add marker"
            # Extract frame number
            frame_match = re.search(r'frame\s*(\d+)', lower)
            if frame_match:
                frame = int(frame_match.group(1))
                ok = bridge.add_marker(frame, "Blue", "AI Marker", "Added by ResolveAIO")
                return f"Added marker at frame {frame}" if ok else "Failed to add marker"
            return "Specify position: add marker at frame 100"

        if any(w in lower for w in ["timecode", "position", "טיימקוד"]):
            return f"Current timecode: {bridge.get_current_timecode()}"

        # ── Color / Grading ──
        if "list timeline clip" in lower or "clips on timeline" in lower:
            items = bridge.get_timeline_items()
            if not items:
                return "No clips on video track 1."
            lines = [f"  {i}. {item.GetName()}" for i, item in enumerate(items)]
            return f"Timeline clips ({len(items)}):\n" + "\n".join(lines)

        if "auto grade" in lower or "auto-grade" in lower or "גריידינג אוטומטי" in lower:
            items = bridge.get_timeline_items()
            if not items:
                return "No clips to grade."
            count = 0
            for item in items:
                if bridge.add_node(item):
                    count += 1
            return f"Added a color node to {count}/{len(items)} clips.\nApply a LUT or PowerGrade for the look."

        if "film look" in lower or "apply film" in lower or "לוק פילם" in lower:
            return (
                "Film Look Options:\n"
                "  • 'apply preset Film Print Emulation' — Full node-tree film emulation\n"
                "  • 'apply preset Kodak 2383 Print' — Classic Hollywood print stock\n"
                "  • 'apply preset Vintage Film 70s' — Warm, faded retro look\n"
                "  • 'apply preset Faded Portra' — Kodak Portra pastel skin tones\n\n"
                "Or use the Presets panel (sidebar) to browse all looks."
            )

        if "preview preset" in lower or "show preset" in lower:
            name = _extract_quoted(text)
            if name:
                asset = find_bundled_asset(name)
                if asset:
                    return _format_asset_summary(asset)
                return f"Preset '{name}' is not bundled in this build."
            return "Specify a preset: preview preset \"Kodak 2383 Print\""

        if (
            "apply preset" in lower
            or "apply look" in lower
            or ("install preset" in lower and "install all presets" not in lower)
        ):
            name = _extract_quoted(text)
            if name:
                asset = find_bundled_asset(name)
                if asset:
                    if asset["type"] in {"DCTL", "LUT"}:
                        from ..automation.auto_grade import apply_lut_to_all_clips

                        results = apply_lut_to_all_clips(asset["path"])
                        ok_count = sum(1 for value in results.values() if value)
                        return (
                            f"Applied {asset['name']} to {ok_count}/{len(results)} clips.\n"
                            f"Type: {asset['type']}\n"
                            f"Source: {asset['relative']}"
                        )

                    if asset["type"] == "PowerGrade":
                        ok = apply_powergrade_to_all_clips(asset["path"])
                        return (
                            f"Applied PowerGrade {asset['name']}.\n"
                            f"Success: {'Yes' if ok else 'No'}\n"
                            f"Source: {asset['relative']}"
                        )

                    if asset["type"] == "FusionTemplate":
                        dest = install_preset(asset["path"], category=asset["category"])
                        return (
                            f"Installed Fusion template: {asset['name']}\n"
                            f"Destination: {dest}\n"
                            "Restart Resolve or refresh templates to see it in the Edit page."
                        )

                    return _format_asset_summary(asset)
                return f"Preset '{name}' is not bundled in this build."
            return "Specify a preset: apply preset \"Cinematic Teal & Orange\""

        if "list installed lut" in lower or "list lut" in lower or "installed dctl" in lower:
            presets = list_installed_presets()
            if not presets:
                return "No presets found. Run 'install all presets' first."
            lines = [f"  [{p['type']}] {p['name']}" for p in presets[:30]]
            result = f"Installed presets ({len(presets)}):\n" + "\n".join(lines)
            if len(presets) > 30:
                result += f"\n  ... and {len(presets) - 30} more"
            return result

        # ── Render ──
        if any(w in lower for w in ["render preset", "list render", "list preset"]):
            presets = bridge.get_render_presets()
            return "Render presets:\n" + "\n".join(f"  • {p}" for p in presets)

        if "batch render" in lower or "render all" in lower or "רנדר הכל" in lower:
            from ..automation.batch_render import render_all_timelines

            results = render_all_timelines()
            if not results:
                return "No timelines were queued for render."
            ok_count = sum(1 for ok in results.values() if ok)
            lines = "\n".join(f"  • {name}: {'OK' if ok else 'FAILED'}" for name, ok in results.items())
            return f"Queued/rendered {ok_count}/{len(results)} timelines.\n{lines}"

        if "start render" in lower or "התחל רנדר" in lower:
            ok = bridge.start_render()
            return "Render started!" if ok else "Failed to start render. Add a render job first."

        if "stop render" in lower or "עצור רנדר" in lower:
            bridge.stop_render()
            return "Render stopped."

        if "render status" in lower or "סטטוס רנדר" in lower:
            status = bridge.get_render_status()
            rendering = "Yes" if status.get("is_rendering") else "No"
            jobs = status.get("jobs", [])
            return f"Rendering: {rendering}\nJobs in queue: {len(jobs)}"

        # ── Rough Cut ──
        if "rough cut" in lower or "ראף קאט" in lower or "assembly" in lower:
            from ..automation.rough_cut import create_rough_cut

            name = _extract_quoted(text) or "Rough Cut v1"
            options = _parse_option_list(text)
            result = create_rough_cut(
                timeline_name=name,
                remove_silence=("remove silence" in options) or not options,
                sort_by_timecode=("sort by timecode" in options) or not options,
                color_tag="color tag clips" in options,
                add_markers="add scene markers" in options,
            )
            if "error" in result:
                return result["error"]
            return (
                f"Rough cut created: {result['timeline']}\n"
                f"Imported: {result['imported']}\n"
                f"Clips added: {result['clips_added']}\n"
                f"Markers: {result['markers_added']}\n"
                f"Tagged: {result['tagged']}\n"
                f"Silent segments: {result.get('silent_segments', 0)}"
            )

        # ── Automation ──
        if any(w in lower for w in ["remove silence", "detect silence", "mark silence", "הסר שתיקה"]):
            from ..automation.silence_remover import detect_silent_segments, mark_silent_segments

            segments = detect_silent_segments()
            if not segments:
                return "No potential silent segments found on the current audio track."
            marker_count = mark_silent_segments(segments)
            return (
                f"Detected {len(segments)} potential silent segments.\n"
                f"Added {marker_count} silence markers to the timeline."
            )

        if "color tag" in lower or "tag clips" in lower or "תייג קליפים" in lower:
            from ..automation.auto_grade import color_tag_by_duration

            results = color_tag_by_duration()
            if not results:
                return "No clips on timeline to tag."
            counts: dict[str, int] = {}
            for color in results.values():
                counts[color] = counts.get(color, 0) + 1
            parts = ", ".join(f"{color}={count}" for color, count in sorted(counts.items()))
            return f"Tagged {len(results)} clips by duration.\n{parts}"

        if "install text animation" in lower or "install template" in lower:
            name = _extract_quoted(text)
            if name:
                asset = find_bundled_asset(name, asset_type="FusionTemplate")
                if not asset:
                    return f"Text animation '{name}' is not bundled in this build."
                dest = install_preset(asset["path"], category=asset["category"])
                return (
                    f"Installed text animation: {asset['name']}\n"
                    f"Destination: {dest}\n"
                    "Open Edit > Titles after restarting Resolve to use it."
                )
            return "Specify a template: install text animation \"Typewriter\""

        if "install transition" in lower:
            name = _extract_quoted(text)
            if name:
                asset = find_bundled_asset(name, asset_type="FusionTemplate")
                if not asset or asset["category"] != "Transitions":
                    return f"Transition '{name}' is not bundled in this build."
                dest = install_preset(asset["path"], category=asset["category"])
                return (
                    f"Installed transition: {asset['name']}\n"
                    f"Destination: {dest}\n"
                    "Open Edit > Effects > Video Transitions after Resolve refreshes templates."
                )
            return "Specify a transition: install transition \"Whip Slide\""

        if "install" in lower and "preset" in lower:
            counts = install_bundled_assets()
            total = sum(counts.values())
            parts = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            return f"Installed {total} bundled assets.\n{parts}"

        if "gallery album" in lower or "still album" in lower:
            albums = list_gallery_albums()
            if not albums:
                return "No gallery albums available."
            return "Gallery albums:\n" + "\n".join(f"  • {album}" for album in albums)

        if "timeline report" in lower or "דוח טיימליין" in lower:
            tl_name = bridge.get_current_timeline_name()
            items = bridge.get_timeline_items()
            markers = bridge.get_markers()
            tc = bridge.get_current_timecode()
            timelines = bridge.list_timelines()
            tl_info = next((t for t in timelines if t["name"] == tl_name), {})
            return (
                f"Timeline Report: {tl_name}\n"
                f"{'═' * 40}\n"
                f"Resolution: {tl_info.get('resolution', 'N/A')}\n"
                f"Frame Rate: {tl_info.get('frame_rate', 'N/A')} fps\n"
                f"Clips: {len(items)}\n"
                f"Markers: {len(markers)}\n"
                f"Current Timecode: {tc}\n"
            )

        if "smart reframe" in lower or "reframe" in lower:
            return (
                "Smart Reframe to 9:16 (vertical):\n"
                "  1. Go to Edit page\n"
                "  2. Select clips to reframe\n"
                "  3. Inspector → 'Smart Reframe' (Resolve 18+)\n"
                "  4. Set target aspect ratio to 9:16\n"
                "  5. Enable 'Auto' framing\n\n"
                "Tip: For best results, use clips where subjects move slowly."
            )

        if "export timeline powergrade" in lower or "export powergrades" in lower or "export stills from all clips" in lower:
            exported = export_timeline_powergrades()
            if not exported:
                return "No PowerGrades were exported from the current timeline."
            lines = "\n".join(f"  • {path}" for path in exported[:12])
            extra = f"\n  ... and {len(exported) - 12} more" if len(exported) > 12 else ""
            return (
                f"Exported {len(exported)} timeline PowerGrades.\n"
                f"Destination folder: {Path(exported[0]).parent}\n"
                f"{lines}{extra}"
            )

        if "export current powergrade" in lower or "export powergrade" in lower or "grab still" in lower:
            name = _extract_quoted(text) or bridge.get_current_timeline_name() or "current-look"
            exported = export_current_powergrade(name)
            return f"Exported PowerGrade: {exported}"

        # ── Text Animations ──
        if "add text animation" in lower:
            name = _extract_quoted(text)
            if name:
                asset = find_bundled_asset(name, asset_type="FusionTemplate")
                if asset:
                    dest = install_preset(asset["path"], category=asset["category"])
                    return (
                        f"Installed text animation: {asset['name']}\n"
                        f"Destination: {dest}\n"
                        "Add it from Edit > Effects > Titles after Resolve refreshes templates."
                    )

        if "text animation" in lower or "add text" in lower or "אנימציית טקסט" in lower:
            name = _extract_quoted(text)
            return (
                f"Text Animation: {name or 'Browse available'}\n"
                f"  Check the Text Animations panel (sidebar) for the bundled Fusion templates.\n"
                f"  Click Install to copy a template into Resolve's Titles folder.\n\n"
                f"  After a Resolve refresh, the template appears in Edit > Effects > Titles."
            )

        if "transition" in lower or "מעבר" in lower:
            return (
                "Fusion Transitions:\n"
                "  Check the Transitions panel (sidebar) for bundled Edit-page transition templates.\n"
                "  Click Install to copy a transition into Resolve's Transitions folder.\n\n"
                "  Example: install transition \"Dip To Color\""
            )

        # ── Color Science ──
        if "color science" in lower or "workflow" in lower or "aces" in lower or "dwg" in lower:
            return (
                "Color Science Workflows:\n"
                "  Check the Color Science panel (sidebar) for setup guides.\n\n"
                "  Quick options:\n"
                "  • 'teach me: ACES vs DaVinci Wide Gamut'\n"
                "  • 'teach me: camera-specific color workflows'\n"
                "  • 'apply preset ACES Lite Workflow'\n"
                "  • 'apply preset S-Log3 to Rec709'\n"
            )

        # ── Fusion ──
        if "fusion tool" in lower or "fusion comp" in lower:
            tools = bridge.list_fusion_tools()
            if not tools:
                return "No Fusion composition found. Select a clip with Fusion effects."
            return f"Fusion tools ({len(tools)}):\n" + "\n".join(f"  • {t}" for t in tools)

        # ── Help ──
        if any(w in lower for w in ["help", "עזרה", "commands", "what can you do"]):
            return (
                "ResolveAIO — What I Can Do\n"
                "══════════════════════════\n\n"
                "CONTROL RESOLVE:\n"
                "  • Manage projects, timelines, media\n"
                "  • Navigate pages, add markers\n"
                "  • Apply presets and LUTs\n"
                "  • Export and apply DRX PowerGrades\n"
                "  • Batch render, auto-grade\n\n"
                "LEARN:\n"
                "  • 'teach me: node trees'\n"
                "  • 'teach me: ACES vs DWG'\n"
                "  • 'teach me: camera workflows'\n\n"
                "EXPLORE:\n"
                "  • Presets panel — real LUTs and DCTLs\n"
                "  • Text Animations — bundled Fusion templates\n"
                "  • Transitions — bundled Fusion transition templates\n"
                "  • Automation — batch tools\n"
                "  • Color Science — workflow guides\n"
                "  • Tutorials — 12 guides\n\n"
                "Type 'teach me: AI chat commands' for the full command list."
            )

        # ── Fallback ──
        return None

    except Exception as e:
        return f"Error: {e}\n\nMake sure DaVinci Resolve is running."


async def process_command(bridge, text: str, ai_engine: Any | None = None) -> str:
    """Run built-in commands first, then fall back to the GPT tool router when available."""
    builtin_response = _process_builtin_command(bridge, text)
    if builtin_response is not None:
        return builtin_response

    if ai_engine is None:
        return _default_fallback_response(text)

    ai_response = await ai_engine.chat(text)
    if not ai_response or ai_response.startswith("AI Error:"):
        logger.warning("AI fallback failed for %r: %s", text, ai_response)
        return _default_fallback_response(text)

    return ai_response


# ── Main ────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ResolveAIO Studio")
    parser.add_argument("--port", type=int, default=9881)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info("ResolveAIO Studio → http://%s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
