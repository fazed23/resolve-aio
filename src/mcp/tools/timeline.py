"""MCP tools for DaVinci Resolve timeline operations."""

from __future__ import annotations

import json
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def register_timeline_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def list_timelines() -> str:
        """List all timelines in the current project with their properties."""
        try:
            timelines = bridge.list_timelines()
            return json.dumps({"timelines": timelines, "count": len(timelines)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_current_timeline() -> str:
        """Get the name and info of the currently active timeline."""
        try:
            name = bridge.get_current_timeline_name()
            tl = bridge.get_current_timeline()
            if tl:
                info = {
                    "name": name,
                    "timecode": bridge.get_current_timecode(),
                    "frame_rate": tl.GetSetting("timelineFrameRate"),
                    "resolution": f"{tl.GetSetting('timelineResolutionWidth')}x{tl.GetSetting('timelineResolutionHeight')}",
                }
            else:
                info = {"name": None}
            return json.dumps(info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_current_timeline(name: str) -> str:
        """Switch to a timeline by name.

        Args:
            name: Timeline name to switch to
        """
        try:
            ok = bridge.set_current_timeline(name)
            return json.dumps({"success": ok, "timeline": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def create_timeline(name: str) -> str:
        """Create a new empty timeline.

        Args:
            name: Name for the new timeline
        """
        try:
            tl = bridge.create_timeline(name)
            return json.dumps({"success": tl is not None, "timeline": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def delete_timeline(name: str) -> str:
        """Delete a timeline by name. This action cannot be undone.

        Args:
            name: Timeline name to delete
        """
        try:
            ok = bridge.delete_timeline(name)
            return json.dumps({"success": ok, "timeline": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_current_timecode() -> str:
        """Get the current playhead timecode position."""
        try:
            tc = bridge.get_current_timecode()
            return json.dumps({"timecode": tc})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_markers() -> str:
        """Get all markers on the current timeline."""
        try:
            markers = bridge.get_markers()
            formatted = []
            for frame, data in markers.items():
                formatted.append({
                    "frame": frame,
                    "color": data.get("color", ""),
                    "name": data.get("name", ""),
                    "note": data.get("note", ""),
                    "duration": data.get("duration", 1),
                })
            return json.dumps({"markers": formatted, "count": len(formatted)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def add_marker(
        frame: int,
        color: str = "Blue",
        name: str = "",
        note: str = "",
        duration: int = 1,
    ) -> str:
        """Add a marker to the current timeline.

        Args:
            frame: Frame number to place the marker
            color: Marker color (Blue, Cyan, Green, Yellow, Red, Pink, Purple, Fuchsia, Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream)
            name: Marker name
            note: Marker note/comment
            duration: Marker duration in frames
        """
        try:
            ok = bridge.add_marker(frame, color, name, note, duration)
            return json.dumps({"success": ok, "frame": frame, "color": color})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def delete_marker(frame: int) -> str:
        """Delete a marker at a specific frame.

        Args:
            frame: Frame number of the marker to delete
        """
        try:
            ok = bridge.delete_marker(frame)
            return json.dumps({"success": ok, "frame": frame})
        except Exception as e:
            return json.dumps({"error": str(e)})
