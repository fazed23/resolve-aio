"""MCP tools for DaVinci Resolve Deliver / Render operations."""

from __future__ import annotations

import json
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def register_render_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def list_render_presets() -> str:
        """List all available render presets."""
        try:
            presets = bridge.get_render_presets()
            return json.dumps({"presets": presets, "count": len(presets)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_render_preset(name: str) -> str:
        """Load a render preset by name.

        Args:
            name: Render preset name (e.g. "H.264 Master", "ProRes Master")
        """
        try:
            ok = bridge.set_render_preset(name)
            return json.dumps({"success": ok, "preset": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_render_settings(
        target_dir: str | None = None,
        filename: str | None = None,
        format: str | None = None,
        codec: str | None = None,
    ) -> str:
        """Configure render settings.

        Args:
            target_dir: Output directory path
            filename: Output filename (without extension)
            format: Container format (e.g. "mp4", "mov", "mxf")
            codec: Codec (e.g. "H.264", "H.265", "ProRes 422 HQ")
        """
        try:
            settings: dict = {}
            if target_dir:
                settings["TargetDir"] = target_dir
            if filename:
                settings["CustomName"] = filename
            if format:
                settings["FormatWidth"] = format
            if codec:
                settings["VideoCodec"] = codec
            if not settings:
                return json.dumps({"error": "No settings provided"})
            ok = bridge.set_render_settings(settings)
            return json.dumps({"success": ok, "settings": settings})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def add_render_job() -> str:
        """Add the current timeline as a render job to the render queue."""
        try:
            job_id = bridge.add_render_job()
            return json.dumps({"success": bool(job_id), "job_id": job_id})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def start_render() -> str:
        """Start rendering all jobs in the render queue."""
        try:
            ok = bridge.start_render()
            return json.dumps({"success": ok})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_render_status() -> str:
        """Get the current render status and job list."""
        try:
            status = bridge.get_render_status()
            jobs = []
            for job in status.get("jobs", []):
                if isinstance(job, dict):
                    jobs.append(job)
            return json.dumps({
                "is_rendering": status.get("is_rendering", False),
                "jobs": jobs,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def stop_render() -> str:
        """Stop the current render process."""
        try:
            bridge.stop_render()
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})
