# ResolveAIO

All-in-one DaVinci Resolve plugin: MCP server for AI control, DCTL color tools, automation scripts, and a web chat interface.

## What's Inside

| Module | Description |
|--------|-------------|
| **MCP Server** | Control Resolve from Cursor, Claude Desktop, or any MCP client via natural language |
| **DCTL Library** | 20 GPU color transforms — curves, limiters, analysis, conversion, creative |
| **Automation** | Batch render, auto-grade, silence detection, preset manager |
| **Chat UI** | Local web interface for chatting with Resolve |
| **OFX Scaffold** | Minimal OpenFX build scaffold for future compiled Resolve effects |

## Quick Start

### Prerequisites
- macOS or Windows
- DaVinci Resolve 18+ installed and running
- Python 3.10+

### Install

```bash
git clone <repo-url> resolve-aio
cd resolve-aio

# macOS / Linux:
./scripts/install.sh

# Windows:
scripts\install.bat
```

The installer will:
1. Create a Python virtual environment
2. Install dependencies
3. Install bundled Resolve assets: DCTLs, LUTs, and Fusion templates
4. Configure Cursor MCP integration

### Run

```bash
# MCP Server (for Cursor / Claude Desktop):
./scripts/run.sh

# Chat UI (opens web interface):
./scripts/run.sh --chat

# SSE mode (for custom MCP clients):
./scripts/run.sh --sse
```

## MCP Tools

### Project Management
- `get_resolve_version` — Get Resolve version
- `list_projects` / `open_project` / `create_project` / `save_project`
- `get_current_page` / `set_current_page`

### Timeline
- `list_timelines` / `create_timeline` / `delete_timeline`
- `get_current_timeline` / `set_current_timeline`
- `get_markers` / `add_marker` / `delete_marker`
- `get_current_timecode`

### Media Pool
- `list_clips` / `list_bins` / `create_bin`
- `import_media` / `append_clips_to_timeline`

### Color
- `list_timeline_clips` / `set_clip_color`
- `add_color_node` / `apply_lut_to_clip`
- `list_installed_luts`

### Render
- `list_render_presets` / `set_render_preset` / `set_render_settings`
- `add_render_job` / `start_render` / `stop_render` / `get_render_status`

### Fusion
- `list_fusion_tools` / `get_fusion_comp_info`
- `add_fusion_tool` / `set_fusion_tool_input` / `connect_fusion_tools`

## DCTL Library

Installed to `<Resolve LUT Dir>/ResolveAIO/`. Available in the Color page under DCTL effects.

| Category | Tools |
|----------|-------|
| **Curves** | S-Curve, Inverse S-Curve, Power Knee |
| **Limiters** | Signal Limiter, Luma Limiter, Clamp |
| **Analysis** | False Color, Gray Chart, Mid-Select |
| **Conversion** | Full→Legal, Legal→Full, Quantize |
| **Creative** | Channel Saturation, Film Emulation, Skin Tone Indicator, Step Ramp |

## Automation Scripts

```bash
# Batch render all timelines
python -m src.automation.batch_render --all-timelines --preset "H.264 Master" --output /path/to/output

# Auto-grade: apply a LUT to all clips
python -m src.automation.auto_grade apply-lut /path/to/look.cube

# Color-tag clips by duration
python -m src.automation.auto_grade color-tag --short-sec 5 --long-sec 30

# Detect silent segments
python -m src.automation.silence_remover --action mark

# Install bundled presets
python -m src.automation.preset_manager install-bundled

# List installed presets
python -m src.automation.preset_manager list

# Export the current clip grade as a real DRX PowerGrade
python -m src.automation.powergrade_tools export-current "Hero Look"

# Export DRX PowerGrades for every clip on the current timeline
python -m src.automation.powergrade_tools export-timeline

# Apply a DRX PowerGrade file to all clips on the current timeline
python -m src.automation.powergrade_tools apply presets/powergrades/hero-look.drx
```

PowerGrade export/import requires DaVinci Resolve to be open, because `.drx` files are created through Resolve's Gallery API rather than copied into the LUT directory.

## Chat UI

The web chat runs on `http://127.0.0.1:9881` and provides:
- Quick action buttons for common commands
- WebSocket-based real-time communication
- Hebrew and English support
- Connection status monitoring

The presets and text-animation panels are backed by real bundled files on disk:
- 20 DCTLs in [`src/dctl`](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/dctl)
- 6 LUTs in [`presets/luts`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/luts)
- 20 Fusion title templates in [`presets/fusion_templates/Titles`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/fusion_templates/Titles)
- 6 Fusion transition templates in [`presets/fusion_templates/Transitions`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/fusion_templates/Transitions)
- Exported DRX PowerGrades appear in [`presets/powergrades`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/powergrades)
- OpenFX scaffold sources live in [`src/ofx`](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/ofx)

If `OPENAI_API_KEY` is set, the chat UI also enables GPT-powered tool calling for free-form requests that are not covered by the built-in command router.

```bash
echo 'OPENAI_API_KEY=your-key-here' >> config/resolve_aio.env
./scripts/run.sh --chat
```

Preferred location for the key: [config/resolve_aio.env](/Volumes/Transcend/resolve plugin aio/resolve-aio/config/resolve_aio.env)

Extra setup notes: [docs/GPT_SETUP.md](/Volumes/Transcend/resolve plugin aio/resolve-aio/docs/GPT_SETUP.md)

## Cursor / Claude Desktop Setup

The installer auto-generates the MCP config. To set up manually:

**Cursor** — edit `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "resolve-aio": {
      "command": "/path/to/resolve-aio/.venv/bin/python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/resolve-aio"
    }
  }
}
```

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json` with the same structure.

## Project Structure

```
resolve-aio/
├── src/
│   ├── mcp/                    # MCP Server
│   │   ├── server.py           # Entry point (stdio + SSE)
│   │   ├── resolve_bridge.py   # Resolve API wrapper
│   │   ├── system_prompt.py    # AI system prompt
│   │   └── tools/              # Tool modules
│   ├── dctl/                   # DCTL color transforms
│   ├── automation/             # Automation scripts
│   └── ui/                     # Chat web interface
├── presets/                    # Bundled presets
├── config/                    # MCP config templates
├── scripts/                   # Install & run scripts
└── tests/                     # Test suite
```

## License

MIT
