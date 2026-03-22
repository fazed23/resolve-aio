"""MCP tools for DaVinci Resolve Fusion page operations."""

from __future__ import annotations

import json
from mcp.server import Server
from ..resolve_bridge import ResolveBridge


def register_fusion_tools(server: Server, bridge: ResolveBridge) -> None:

    @server.tool()
    async def list_fusion_tools() -> str:
        """List all Fusion tools/nodes in the current composition."""
        try:
            tools = bridge.list_fusion_tools()
            return json.dumps({"tools": tools, "count": len(tools)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def get_fusion_comp_info() -> str:
        """Get information about the current Fusion composition."""
        try:
            comp = bridge.get_fusion_comp()
            if not comp:
                return json.dumps({"error": "No Fusion composition found. Select a clip with a Fusion comp."})
            attrs = comp.GetAttrs()
            info = {
                "name": attrs.get("COMPS_Name", "Unknown"),
                "filename": attrs.get("COMPS_FileName", ""),
                "tool_count": len(comp.GetToolList()),
            }
            return json.dumps(info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def add_fusion_tool(tool_id: str, x: float = 0, y: float = 0) -> str:
        """Add a Fusion tool/node to the current composition.

        Args:
            tool_id: Fusion tool ID (e.g. "Blur", "Transform", "Background", "MediaIn", "Merge")
            x: X position in the flow (default: 0)
            y: Y position in the flow (default: 0)
        """
        try:
            comp = bridge.get_fusion_comp()
            if not comp:
                return json.dumps({"error": "No Fusion composition found"})
            tool = comp.AddTool(tool_id, x, y)
            if tool:
                return json.dumps({"success": True, "tool": tool_id})
            return json.dumps({"success": False, "error": f"Could not add tool '{tool_id}'"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def set_fusion_tool_input(tool_name: str, input_name: str, value: float | str | bool) -> str:
        """Set an input value on a Fusion tool.

        Args:
            tool_name: Name of the tool in the composition
            input_name: Input parameter name (e.g. "Blend", "Size", "Center")
            value: Value to set
        """
        try:
            comp = bridge.get_fusion_comp()
            if not comp:
                return json.dumps({"error": "No Fusion composition found"})
            tool = comp.FindTool(tool_name)
            if not tool:
                return json.dumps({"error": f"Tool '{tool_name}' not found"})
            inp = tool.FindMainInput(1)  # fallback
            tool.SetInput(input_name, value)
            return json.dumps({"success": True, "tool": tool_name, "input": input_name, "value": value})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def connect_fusion_tools(output_tool: str, input_tool: str, input_name: str = "Input") -> str:
        """Connect one Fusion tool's output to another tool's input.

        Args:
            output_tool: Name of the tool providing the output
            input_tool: Name of the tool receiving the input
            input_name: Input name on the receiving tool (default: "Input")
        """
        try:
            comp = bridge.get_fusion_comp()
            if not comp:
                return json.dumps({"error": "No Fusion composition found"})
            out_t = comp.FindTool(output_tool)
            in_t = comp.FindTool(input_tool)
            if not out_t:
                return json.dumps({"error": f"Output tool '{output_tool}' not found"})
            if not in_t:
                return json.dumps({"error": f"Input tool '{input_tool}' not found"})
            in_t.SetInput(input_name, out_t.Output)
            return json.dumps({"success": True, "from": output_tool, "to": input_tool})
        except Exception as e:
            return json.dumps({"error": str(e)})
