"""Planning Tools for Tu SketchUp Agent."""

import json
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_validate_plan(plan: Dict[str, Any]) -> str:
        """Validate a multi-step SketchUp execution plan without mutating the model."""
        if not isinstance(plan, dict):
            raise ValueError("plan phải là object/dict")
        res = send_to_sketchup("validate_plan", {"plan": plan})
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_execute_plan(plan: Dict[str, Any]) -> str:
        """Execute a plan sequentially; each step is pinned to the current model state and execution stops on failure."""
        if not isinstance(plan, dict):
            raise ValueError("plan phải là object/dict")
        res = send_to_sketchup("execute_plan", {"plan": plan}, timeout=120.0)
        return json.dumps(res, indent=2, ensure_ascii=False)
