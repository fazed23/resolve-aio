"""
AI Engine — Real GPT-powered command execution for DaVinci Resolve.

Uses OpenAI GPT API with function calling to understand natural language
and execute actual Resolve commands through the bridge.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

from ..env_config import load_project_env
from ..mcp.resolve_bridge import ResolveBridge

logger = logging.getLogger("resolve_aio.ai_engine")

load_project_env()

# ── Tool Definitions for GPT Function Calling ──────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_resolve_version",
            "description": "Get the version of DaVinci Resolve currently running",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_page",
            "description": "Get the currently active page in Resolve (media, cut, edit, fusion, color, fairlight, deliver)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_current_page",
            "description": "Switch to a specific page in DaVinci Resolve",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": ["media", "cut", "edit", "fusion", "color", "fairlight", "deliver"],
                        "description": "The page to switch to",
                    }
                },
                "required": ["page"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List all projects in the current database folder",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_project_name",
            "description": "Get the name of the currently open project",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_project",
            "description": "Open a project by name",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Project name to open"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_project",
            "description": "Create a new project",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Name for the new project"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_project",
            "description": "Save the current project",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timelines",
            "description": "List all timelines in the current project with resolution and fps",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_timeline_name",
            "description": "Get the name of the currently active timeline",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_current_timeline",
            "description": "Switch to a timeline by name",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Timeline name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_timeline",
            "description": "Create a new empty timeline",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Timeline name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_timeline",
            "description": "Delete a timeline by name",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Timeline name to delete"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_timecode",
            "description": "Get the current playhead timecode position",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_markers",
            "description": "Get all markers on the current timeline",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_marker",
            "description": "Add a marker to the current timeline",
            "parameters": {
                "type": "object",
                "properties": {
                    "frame": {"type": "integer", "description": "Frame number"},
                    "color": {"type": "string", "default": "Blue", "description": "Marker color"},
                    "name": {"type": "string", "default": "", "description": "Marker name"},
                    "note": {"type": "string", "default": "", "description": "Marker note"},
                },
                "required": ["frame"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_clips",
            "description": "List all clips in the Media Pool with name, duration, resolution",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bins",
            "description": "List all bins (sub-folders) in the Media Pool",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_bin",
            "description": "Create a new bin in the Media Pool",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Bin name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_media",
            "description": "Import media files into the Media Pool",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute file paths",
                    }
                },
                "required": ["file_paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline_items",
            "description": "List all clips on video track 1 of the current timeline",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_render_presets",
            "description": "List all available render presets",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_render_preset",
            "description": "Load a render preset by name",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Preset name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_render",
            "description": "Start rendering all jobs in the queue",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_render",
            "description": "Stop the current render",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_render_status",
            "description": "Get current render progress and job list",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_installed_luts",
            "description": "List all installed LUT and DCTL files",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bundled_assets",
            "description": "List bundled ResolveAIO assets that ship with the project, including DCTLs, LUTs, PowerGrades, and Fusion templates",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_type": {
                        "type": "string",
                        "enum": ["DCTL", "LUT", "PowerGrade", "FusionTemplate"],
                        "description": "Optional asset type filter",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_bundled_preset",
            "description": "Apply a bundled LUT, DCTL, or PowerGrade by its display name to all clips on the current timeline",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Bundled preset display name"},
                    "node_index": {"type": "integer", "default": 1, "description": "Node index to apply to"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_text_template",
            "description": "Install a bundled Fusion text template into Resolve's Titles folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Bundled Fusion template display name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_fusion_template",
            "description": "Install a bundled Fusion template by name into Resolve's Edit Templates folder, including titles and transitions",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Bundled Fusion template display name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_gallery_albums",
            "description": "List Resolve Gallery still albums that are currently available in the open project",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_current_powergrade",
            "description": "Grab the current clip grade in Resolve and export it as a real DRX PowerGrade file inside the ResolveAIO bundle",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Output PowerGrade name"},
                    "album_name": {"type": "string", "description": "Optional gallery album to export from"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_timeline_powergrades",
            "description": "Grab stills from all clips on the current timeline and export them as DRX PowerGrade files inside the ResolveAIO bundle",
            "parameters": {
                "type": "object",
                "properties": {
                    "prefix": {"type": "string", "description": "Optional DRX file prefix"},
                    "album_name": {"type": "string", "description": "Optional gallery album to export from"},
                    "frame_source": {
                        "type": "string",
                        "enum": ["first", "middle"],
                        "description": "Which frame to grab from each clip",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_lut_to_all_clips",
            "description": "Apply a LUT or DCTL file to all clips on the timeline",
            "parameters": {
                "type": "object",
                "properties": {
                    "lut_path": {"type": "string", "description": "Absolute path to .cube, .dctl, or .3dl file"},
                    "node_index": {"type": "integer", "default": 1, "description": "Node index to apply to"},
                },
                "required": ["lut_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_node_to_all_clips",
            "description": "Add a new color correction node to every clip on the timeline",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "color_tag_by_duration",
            "description": "Color-tag clips by duration: short=Teal(B-roll), medium=Blue, long=Purple(interviews)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# ── System Prompt ───────────────────────────────────────────

SYSTEM_PROMPT = """\
You are ResolveAIO — an AI assistant that controls DaVinci Resolve through function calls.
You speak English and Hebrew fluently.

## Your capabilities
You have direct control over DaVinci Resolve through tools. When the user asks you to do something,
USE THE TOOLS — don't just describe steps. Actually execute the actions.

## Available tools
- Project management: list/open/create/save projects
- Timeline: list/create/switch/delete timelines, get timecode, add markers
- Media Pool: list clips/bins, create bins, import media
- Color: list timeline clips, apply LUTs/DCTLs, add nodes, color-tag clips
- Bundled assets: list packaged LUTs/DCTLs/PowerGrades/Fusion templates, apply looks, install titles/transitions
- Gallery: list still albums, export real DRX PowerGrades from Resolve
- Render: list presets, set preset, start/stop render, get status
- Analysis: list installed LUTs/DCTLs

## Guidelines
- Be concise. Post-production professionals value speed.
- When listing items, format them clearly.
- For destructive actions (delete, overwrite), confirm first.
- If Resolve is not connected, tell the user clearly.
- Always call the relevant tool — never just describe what to do.
- After executing a tool, summarize what happened in a short, clear response.
"""


# ── AI Engine Class ─────────────────────────────────────────

class AIEngine:
    def __init__(self, bridge: ResolveBridge, api_key: str | None = None):
        self.bridge = bridge
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY", ""))
        self.conversation: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # Keep conversation manageable
        self.max_history = 40

    def _trim_history(self):
        """Keep system prompt + last N messages."""
        if len(self.conversation) > self.max_history:
            self.conversation = [self.conversation[0]] + self.conversation[-(self.max_history - 1):]

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool call against the Resolve bridge and return JSON result."""
        try:
            b = self.bridge

            if name == "get_resolve_version":
                return json.dumps({"version": b.get_version()})

            elif name == "get_current_page":
                return json.dumps({"page": b.get_current_page()})

            elif name == "set_current_page":
                ok = b.set_current_page(args["page"])
                return json.dumps({"success": ok, "page": args["page"]})

            elif name == "list_projects":
                projects = b.list_projects()
                return json.dumps({"projects": projects, "count": len(projects)})

            elif name == "get_current_project_name":
                return json.dumps({"project": b.get_current_project_name()})

            elif name == "open_project":
                ok = b.open_project(args["name"])
                return json.dumps({"success": ok, "project": args["name"]})

            elif name == "create_project":
                p = b.create_project(args["name"])
                return json.dumps({"success": p is not None, "project": args["name"]})

            elif name == "save_project":
                ok = b.save_project()
                return json.dumps({"success": ok})

            elif name == "list_timelines":
                tls = b.list_timelines()
                return json.dumps({"timelines": tls, "count": len(tls)})

            elif name == "get_current_timeline_name":
                return json.dumps({"timeline": b.get_current_timeline_name()})

            elif name == "set_current_timeline":
                ok = b.set_current_timeline(args["name"])
                return json.dumps({"success": ok, "timeline": args["name"]})

            elif name == "create_timeline":
                tl = b.create_timeline(args["name"])
                return json.dumps({"success": tl is not None, "timeline": args["name"]})

            elif name == "delete_timeline":
                ok = b.delete_timeline(args["name"])
                return json.dumps({"success": ok, "timeline": args["name"]})

            elif name == "get_current_timecode":
                return json.dumps({"timecode": b.get_current_timecode()})

            elif name == "get_markers":
                markers = b.get_markers()
                formatted = []
                for frame, data in markers.items():
                    formatted.append({"frame": frame, **data})
                return json.dumps({"markers": formatted, "count": len(formatted)})

            elif name == "add_marker":
                ok = b.add_marker(
                    args["frame"],
                    args.get("color", "Blue"),
                    args.get("name", ""),
                    args.get("note", ""),
                )
                return json.dumps({"success": ok, "frame": args["frame"]})

            elif name == "list_clips":
                clips = b.list_clips()
                return json.dumps({"clips": clips, "count": len(clips)})

            elif name == "list_bins":
                bins = b.list_bins()
                return json.dumps({"bins": bins})

            elif name == "create_bin":
                f = b.create_bin(args["name"])
                return json.dumps({"success": f is not None, "bin": args["name"]})

            elif name == "import_media":
                clips = b.import_media(args["file_paths"])
                names = [c.GetName() for c in clips] if clips else []
                return json.dumps({"imported": names, "count": len(names)})

            elif name == "get_timeline_items":
                items = b.get_timeline_items()
                clips = [{"index": i, "name": item.GetName()} for i, item in enumerate(items)]
                return json.dumps({"clips": clips, "count": len(clips)})

            elif name == "get_render_presets":
                presets = b.get_render_presets()
                return json.dumps({"presets": presets})

            elif name == "set_render_preset":
                ok = b.set_render_preset(args["name"])
                return json.dumps({"success": ok, "preset": args["name"]})

            elif name == "start_render":
                ok = b.start_render()
                return json.dumps({"success": ok})

            elif name == "stop_render":
                b.stop_render()
                return json.dumps({"success": True})

            elif name == "get_render_status":
                status = b.get_render_status()
                return json.dumps({"is_rendering": status.get("is_rendering", False), "jobs": len(status.get("jobs", []))})

            elif name == "list_installed_luts":
                from ..automation.preset_manager import list_installed_presets
                presets = list_installed_presets()
                return json.dumps({"presets": presets[:50], "total": len(presets)})

            elif name == "list_bundled_assets":
                from ..automation.preset_manager import list_bundled_assets
                assets = list_bundled_assets(args.get("asset_type"))
                return json.dumps({"assets": assets[:100], "total": len(assets)})

            elif name == "apply_bundled_preset":
                from ..automation.auto_grade import apply_lut_to_all_clips
                from ..automation.preset_manager import find_bundled_asset
                from ..automation.powergrade_tools import apply_powergrade_to_all_clips

                asset = find_bundled_asset(args["name"])
                if not asset:
                    return json.dumps({"error": f"Bundled preset not found: {args['name']}"})
                if asset["type"] not in {"DCTL", "LUT", "PowerGrade"}:
                    return json.dumps({
                        "error": f"{asset['name']} is a {asset['type']} asset, not a directly applicable look asset"
                    })

                if asset["type"] == "PowerGrade":
                    ok = apply_powergrade_to_all_clips(asset["path"])
                    return json.dumps({
                        "preset": asset["name"],
                        "type": asset["type"],
                        "success": ok,
                    })

                results = apply_lut_to_all_clips(asset["path"], args.get("node_index", 1))
                ok_count = sum(1 for value in results.values() if value)
                return json.dumps({
                    "preset": asset["name"],
                    "type": asset["type"],
                    "applied": ok_count,
                    "total": len(results),
                })

            elif name == "list_gallery_albums":
                from ..automation.powergrade_tools import list_gallery_albums

                albums = list_gallery_albums()
                return json.dumps({"albums": albums, "total": len(albums)})

            elif name == "export_current_powergrade":
                from ..automation.powergrade_tools import export_current_powergrade

                path = export_current_powergrade(
                    args["name"],
                    album_name=args.get("album_name"),
                )
                return json.dumps({"path": path})

            elif name == "export_timeline_powergrades":
                from ..automation.powergrade_tools import export_timeline_powergrades

                paths = export_timeline_powergrades(
                    prefix=args.get("prefix"),
                    album_name=args.get("album_name"),
                    frame_source=args.get("frame_source", "middle"),
                )
                return json.dumps({"paths": paths, "total": len(paths)})

            elif name == "install_text_template":
                from ..automation.preset_manager import find_bundled_asset, install_preset

                asset = find_bundled_asset(args["name"], asset_type="FusionTemplate")
                if not asset:
                    return json.dumps({"error": f"Fusion template not found: {args['name']}"})

                dest = install_preset(asset["path"], category=asset["category"])
                return json.dumps({
                    "template": asset["name"],
                    "installed_to": dest,
                })

            elif name == "install_fusion_template":
                from ..automation.preset_manager import find_bundled_asset, install_preset

                asset = find_bundled_asset(args["name"], asset_type="FusionTemplate")
                if not asset:
                    return json.dumps({"error": f"Fusion template not found: {args['name']}"})

                dest = install_preset(asset["path"], category=asset["category"])
                return json.dumps({
                    "template": asset["name"],
                    "category": asset["category"],
                    "installed_to": dest,
                })

            elif name == "apply_lut_to_all_clips":
                from ..automation.auto_grade import apply_lut_to_all_clips
                results = apply_lut_to_all_clips(args["lut_path"], args.get("node_index", 1))
                ok_count = sum(1 for v in results.values() if v)
                return json.dumps({"applied": ok_count, "total": len(results)})

            elif name == "add_node_to_all_clips":
                from ..automation.auto_grade import add_node_to_all_clips
                count = add_node_to_all_clips()
                return json.dumps({"nodes_added": count})

            elif name == "color_tag_by_duration":
                from ..automation.auto_grade import color_tag_by_duration
                results = color_tag_by_duration()
                return json.dumps({"tagged": len(results), "clips": results})

            else:
                return json.dumps({"error": f"Unknown tool: {name}"})

        except Exception as e:
            return json.dumps({"error": str(e)})

    async def chat(self, user_message: str) -> str:
        """Process a user message through GPT with function calling."""
        self.conversation.append({"role": "user", "content": user_message})
        self._trim_history()

        try:
            # Call GPT
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )

            message = response.choices[0].message

            # Handle tool calls (possibly multiple)
            while message.tool_calls:
                self.conversation.append(message.model_dump())

                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    logger.info("Tool call: %s(%s)", fn_name, fn_args)

                    result = self._execute_tool(fn_name, fn_args)
                    logger.info("Tool result: %s", result[:200])

                    self.conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

                # Get GPT's response after tool execution
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=self.conversation,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=1024,
                )
                message = response.choices[0].message

            # Final text response
            assistant_text = message.content or "Done."
            self.conversation.append({"role": "assistant", "content": assistant_text})
            return assistant_text

        except Exception as e:
            error_msg = f"AI Error: {e}"
            logger.error(error_msg)
            # Fall back to a helpful message
            if "api_key" in str(e).lower() or "auth" in str(e).lower():
                return "OpenAI API key not set. Set OPENAI_API_KEY environment variable or enter it in settings."
            return error_msg
