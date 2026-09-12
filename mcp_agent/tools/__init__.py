"""
MCP Tools Registry for SketchUp Agent.
Registers all tool groups onto a FastMCP instance.
"""

from mcp.server.fastmcp import FastMCP

from . import (
    assembly,
    attributes,
    components,
    geometry,
    inspection,
    materials,
    planning,
    scenes,
    system,
    transform,
)


def register_all_tools(mcp: FastMCP) -> None:
    """Register all modular tool handlers on the given FastMCP instance."""
    system.register(mcp)
    inspection.register(mcp)
    geometry.register(mcp)
    transform.register(mcp)
    materials.register(mcp)
    attributes.register(mcp)
    components.register(mcp)
    assembly.register(mcp)
    scenes.register(mcp)
    planning.register(mcp)
