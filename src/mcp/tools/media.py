"""MCP tools for DaVinci Resolve Media Pool operations."""

from __future__ import annotations

import json
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def register_media_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def list_clips() -> str:
        """List all clips in the current Media Pool folder."""
        try:
            clips = bridge.list_clips()
            return json.dumps({"clips": clips, "count": len(clips)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def list_bins() -> str:
        """List all bins (sub-folders) in the Media Pool root."""
        try:
            bins = bridge.list_bins()
            return json.dumps({"bins": bins, "count": len(bins)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def create_bin(name: str) -> str:
        """Create a new bin in the Media Pool.

        Args:
            name: Name for the new bin
        """
        try:
            folder = bridge.create_bin(name)
            return json.dumps({"success": folder is not None, "bin": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_current_bin(name: str) -> str:
        """Set the active Media Pool bin.

        Args:
            name: Bin name to switch to
        """
        try:
            ok = bridge.set_current_bin(name)
            return json.dumps({"success": ok, "bin": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def import_media(file_paths: list[str]) -> str:
        """Import media files into the current Media Pool bin.

        Args:
            file_paths: List of absolute file paths to import
        """
        try:
            clips = bridge.import_media(file_paths)
            imported = [c.GetName() for c in clips] if clips else []
            return json.dumps({"imported": imported, "count": len(imported)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def append_clips_to_timeline(clip_names: list[str]) -> str:
        """Append clips from the Media Pool to the current timeline by name.

        Args:
            clip_names: List of clip names to append
        """
        try:
            all_clips = bridge.list_clips()
            pool_clips = bridge._media_pool().GetRootFolder().GetClipList()
            to_add = []
            for clip in pool_clips:
                if clip.GetName() in clip_names:
                    to_add.append(clip)
            if not to_add:
                return json.dumps({"error": "No matching clips found", "requested": clip_names})
            result = bridge.append_to_timeline(to_add)
            added = [c.GetName() for c in result] if result else []
            return json.dumps({"appended": added, "count": len(added)})
        except Exception as e:
            return json.dumps({"error": str(e)})
