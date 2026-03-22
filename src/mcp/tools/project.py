"""MCP tools for DaVinci Resolve project management."""

from __future__ import annotations

import json
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def register_project_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def get_resolve_version() -> str:
        """Get the version of DaVinci Resolve currently running."""
        try:
            version = bridge.get_version()
            return json.dumps({"version": version})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_current_page() -> str:
        """Get the currently active page in DaVinci Resolve (media, edit, color, etc.)."""
        try:
            page = bridge.get_current_page()
            return json.dumps({"page": page})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_current_page(page: str) -> str:
        """Switch to a specific page in DaVinci Resolve.

        Args:
            page: Page name — one of: media, cut, edit, fusion, color, fairlight, deliver
        """
        try:
            ok = bridge.set_current_page(page)
            return json.dumps({"success": ok, "page": page})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def list_projects() -> str:
        """List all projects in the current database folder."""
        try:
            projects = bridge.list_projects()
            return json.dumps({"projects": projects, "count": len(projects)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_current_project_name() -> str:
        """Get the name of the currently open project."""
        try:
            name = bridge.get_current_project_name()
            return json.dumps({"project": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def open_project(name: str) -> str:
        """Open a project by name.

        Args:
            name: The project name to open
        """
        try:
            ok = bridge.open_project(name)
            return json.dumps({"success": ok, "project": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def create_project(name: str) -> str:
        """Create a new project.

        Args:
            name: Name for the new project
        """
        try:
            proj = bridge.create_project(name)
            return json.dumps({"success": proj is not None, "project": name})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def save_project() -> str:
        """Save the current project."""
        try:
            ok = bridge.save_project()
            return json.dumps({"success": ok})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def list_databases() -> str:
        """List all available databases."""
        try:
            dbs = bridge.list_databases()
            return json.dumps({"databases": dbs})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def list_folders() -> str:
        """List folders in the current project manager folder."""
        try:
            folders = bridge.list_folders()
            return json.dumps({"folders": folders})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def open_folder(name: str) -> str:
        """Open a folder in the project manager.

        Args:
            name: Folder name to open
        """
        try:
            ok = bridge.open_folder(name)
            return json.dumps({"success": ok, "folder": name})
        except Exception as e:
            return json.dumps({"error": str(e)})
