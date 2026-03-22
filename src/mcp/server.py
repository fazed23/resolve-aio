"""
ResolveAIO MCP Server

Main entry point. Registers all tool modules and starts the MCP server
over stdio (for Cursor / Claude Desktop) or SSE (for the web chat UI).
"""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .resolve_bridge import get_bridge
from .tools import (
    register_project_tools,
    register_timeline_tools,
    register_media_tools,
    register_color_tools,
    register_render_tools,
    register_fusion_tools,
)

logger = logging.getLogger("resolve_aio")


def create_server() -> Server:
    """Build and return a fully configured MCP Server."""
    server = Server("resolve-aio")

    bridge = get_bridge()

    # Register every tool module
    register_project_tools(server, bridge)
    register_timeline_tools(server, bridge)
    register_media_tools(server, bridge)
    register_color_tools(server, bridge)
    register_render_tools(server, bridge)
    register_fusion_tools(server, bridge)

    return server


async def run_stdio(server: Server) -> None:
    """Run the MCP server over stdio (Cursor / Claude Desktop)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="ResolveAIO MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=9880, help="SSE port (default: 9880)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    server = create_server()

    if args.transport == "stdio":
        import asyncio
        asyncio.run(run_stdio(server))
    else:
        # SSE transport for the web chat UI
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await server.run(streams[0], streams[1], server.create_initialization_options())

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        logger.info("Starting SSE server on port %d", args.port)
        uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
