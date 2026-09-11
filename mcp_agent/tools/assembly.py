"""
Assembly Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_place_component_instance(
        definition_name: str,
        position: Optional[list[float]] = None,
        rotation: Optional[Union[Dict[str, Any], list[float]]] = None,
        scale: Optional[Union[float, list[float]]] = None,
        matrix: Optional[list[float]] = None,
        instance_name: Optional[str] = None,
        parent_id: Optional[Union[int, str]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Chèn một ComponentInstance mới vào model hoặc sub-assembly."""
        payload: Dict[str, Any] = {"definition_name": definition_name}
        if position is not None:
            payload["position"] = position
        if rotation is not None:
            payload["rotation"] = rotation
        if scale is not None:
            payload["scale"] = scale
        if matrix is not None:
            payload["matrix"] = matrix
        if instance_name:
            payload["instance_name"] = instance_name
        if parent_id is not None:
            payload["parent_id"] = parent_id
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("place_component_instance", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
