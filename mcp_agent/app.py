"""
FastMCP Application instance for SketchUp Agent.
"""

from mcp.server.fastmcp import FastMCP
from .tools import register_all_tools

mcp = FastMCP("sketchup-agent")
register_all_tools(mcp)
