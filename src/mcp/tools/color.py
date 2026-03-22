"""MCP tools for DaVinci Resolve Color page operations."""

from __future__ import annotations

import json
import os
import platform
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def _default_lut_dir() -> str:
    system = platform.system()
    if system == "Darwin":
        return "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"
    elif system == "Windows":
        prog = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return rf"{prog}\Blackmagic Design\DaVinci Resolve\Support\LUT"
    else:
        return "/opt/resolve/LUT"


def register_color_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def list_timeline_clips(track_index: int = 1) -> str:
        """List all clips on a video track of the current timeline.

        Args:
            track_index: Video track number (default: 1)
        """
        try:
            items = bridge.get_timeline_items(track_index)
            clips = []
            for item in items:
                info = bridge.get_clip_color_info(item)
                clips.append(info)
            return json.dumps({"clips": clips, "count": len(clips)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_clip_color(clip_index: int, color: str, track_index: int = 1) -> str:
        """Set the clip color tag for a clip on the timeline.

        Args:
            clip_index: Zero-based index of the clip on the track
            color: Color name (Orange, Apricot, Yellow, Lime, Olive, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate)
            track_index: Video track number (default: 1)
        """
        try:
            items = bridge.get_timeline_items(track_index)
            if clip_index >= len(items):
                return json.dumps({"error": f"Clip index {clip_index} out of range (0-{len(items)-1})"})
            ok = bridge.set_clip_color(items[clip_index], color)
            return json.dumps({"success": ok, "clip_index": clip_index, "color": color})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def add_color_node(clip_index: int, track_index: int = 1) -> str:
        """Add a new color correction node to a clip.

        Args:
            clip_index: Zero-based index of the clip on the track
            track_index: Video track number (default: 1)
        """
        try:
            items = bridge.get_timeline_items(track_index)
            if clip_index >= len(items):
                return json.dumps({"error": f"Clip index {clip_index} out of range"})
            ok = bridge.add_node(items[clip_index])
            return json.dumps({"success": ok, "clip_index": clip_index})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def apply_lut_to_clip(clip_index: int, lut_path: str, node_index: int = 1, track_index: int = 1) -> str:
        """Apply a LUT or DCTL to a specific node on a clip.

        Args:
            clip_index: Zero-based index of the clip on the track
            lut_path: Absolute path to the LUT/DCTL file
            node_index: Node number to apply the LUT to (default: 1)
            track_index: Video track number (default: 1)
        """
        try:
            items = bridge.get_timeline_items(track_index)
            if clip_index >= len(items):
                return json.dumps({"error": f"Clip index {clip_index} out of range"})
            ok = bridge.apply_lut(items[clip_index], lut_path, node_index)
            return json.dumps({"success": ok, "lut": lut_path, "node": node_index})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def list_installed_luts() -> str:
        """List all LUT and DCTL files installed in the Resolve LUT directory."""
        try:
            lut_dir = _default_lut_dir()
            luts = []
            if os.path.isdir(lut_dir):
                for root, _, files in os.walk(lut_dir):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in (".cube", ".3dl", ".lut", ".dctl", ".look"):
                            rel = os.path.relpath(os.path.join(root, f), lut_dir)
                            luts.append({"name": f, "path": rel, "type": ext.lstrip(".")})
            return json.dumps({"luts": luts, "count": len(luts), "lut_dir": lut_dir})
        except Exception as e:
            return json.dumps({"error": str(e)})
