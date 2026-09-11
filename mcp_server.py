# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.3.0,<2.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
FastMCP Server for SketchUp 2026.
Bridges AI assistants (Antigravity, Claude Desktop, Cursor) to SketchUp Ruby API via TCP.
Modular architecture refactored under `mcp_agent/`.
"""

import sys
from pathlib import Path

# Ensure plugin directory is on sys.path for direct script execution
_pkg_root = Path(__file__).resolve().parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from mcp_agent.app import mcp
from mcp_agent.transport import (
    HOST,
    PORT,
    TOKEN,
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    SKETCHUP_HOST,
    SKETCHUP_PORT,
    SHARED_SECRET,
    require_protocol_version,
    send_to_sketchup,
)

# Export all registered tool functions onto mcp_server module namespace
# for direct script / test compatibility (e.g., mcp_server.sketchup_ping())
for _tool_name, _tool_obj in mcp._tool_manager._tools.items():
    globals()[_tool_name] = _tool_obj.fn


def __getattr__(name: str):
    if name in mcp._tool_manager._tools:
        return mcp._tool_manager._tools[name].fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    mcp.run()
