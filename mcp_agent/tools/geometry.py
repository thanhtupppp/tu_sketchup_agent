"""
Parametric Geometry Tools for Tu SketchUp Agent.
"""

import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup


def _guard(payload: dict, expected_model_revision: Optional[int], expected_model_session_id: Optional[str]) -> dict:
    if expected_model_revision is not None:
        payload["expected_model_revision"] = expected_model_revision
    if expected_model_session_id is not None:
        payload["expected_model_session_id"] = expected_model_session_id
    return payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_create_box(
        width: float, depth: float, height: float,
        x: float = 0.0, y: float = 0.0, z: float = 0.0,
        name: str = "Box", material: str = "",
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tạo khối hộp chữ nhật với đơn vị mm.

        expected_model_revision/session_id là guard tùy chọn để tránh thao tác trên model state cũ.
        """
        payload = _guard({"width": width, "depth": depth, "height": height, "x": x, "y": y, "z": z, "name": name, "material": material}, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_box", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_cylinder(
        radius: float, height: float,
        x: float = 0.0, y: float = 0.0, z: float = 0.0,
        segments: int = 24, name: str = "Cylinder", material: str = "",
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tạo hình trụ đứng với đơn vị mm và guard model state tùy chọn."""
        if not 3 <= segments <= 256:
            raise ValueError("segments phải trong khoảng 3..256")
        payload = _guard({"radius": radius, "height": height, "x": x, "y": y, "z": z, "segments": segments, "name": name, "material": material}, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_cylinder", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_wall(
        start_x: float, start_y: float, end_x: float, end_y: float,
        thickness: float = 100.0, height: float = 2800.0, z: float = 0.0,
        name: str = "Wall", material: str = "",
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tạo tường kiến trúc thẳng với đơn vị mm và guard model state tùy chọn."""
        payload = _guard({"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y, "thickness": thickness, "height": height, "z": z, "name": name, "material": material}, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_wall", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
