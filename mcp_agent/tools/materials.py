"""
Materials Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload, add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_materials(name_filter: Optional[str] = None, limit: int = 100, offset: int = 0) -> str:
        """Liệt kê các vật liệu hiện có trong mô hình SketchUp."""
        payload: Dict[str, Any] = {"limit": limit, "offset": offset}
        if name_filter:
            payload["name_filter"] = name_filter
        return json.dumps(send_to_sketchup("get_materials", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_material_info(material_name: str) -> str:
        """Lấy thông số chi tiết của một vật liệu trong SketchUp."""
        return json.dumps(send_to_sketchup("get_material_info", {"material_name": material_name}), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_material(
        name: str,
        color: Optional[Union[str, list[int]]] = None,
        alpha: float = 1.0,
        texture_path: Optional[str] = None,
        texture_width_mm: Optional[float] = None,
        texture_height_mm: Optional[float] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tạo mới hoặc cập nhật vật liệu trong SketchUp."""
        payload: Dict[str, Any] = {"name": name, "alpha": alpha}
        if color is not None:
            payload["color"] = color
        if texture_path is not None:
            payload["texture_path"] = texture_path
        if texture_width_mm is not None:
            payload["texture_width"] = texture_width_mm
        if texture_height_mm is not None:
            payload["texture_height"] = texture_height_mm
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("create_material", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_material(
        material_name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Gán vật liệu cho một hoặc nhiều Group hoặc ComponentInstance."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["material_name"] = material_name
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("set_entity_material", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_clear_entity_material(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Xóa lớp vật liệu gán đè trên Group hoặc ComponentInstance."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("clear_entity_material", payload), indent=2, ensure_ascii=False)
