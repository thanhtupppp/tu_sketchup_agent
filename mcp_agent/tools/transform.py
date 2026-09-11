"""
Transformation & Hierarchy MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload, add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_move(persistent_ids=None, entity_ids=None, ids=None, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0,
                      expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Di chuyển một hoặc nhiều đối tượng theo khoảng cách mm."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({"dx": dx, "dy": dy, "dz": dz})
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("move", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_copy(persistent_ids=None, entity_ids=None, ids=None, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0,
                      expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Sao chép một hoặc nhiều đối tượng và tịnh tiến bản sao theo mm."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({"dx": dx, "dy": dy, "dz": dz})
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("copy", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_rotate(persistent_ids=None, entity_ids=None, ids=None, angle_degrees: float = 0.0,
                        axis: Union[str, list[float]] = "z", origin: Optional[list[float]] = None,
                        expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Xoay một hoặc nhiều đối tượng quanh trục và tâm chỉ định."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({"angle_degrees": angle_degrees, "axis": axis})
        if origin is not None:
            payload["origin"] = origin
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("rotate", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_scale(persistent_ids=None, entity_ids=None, ids=None, scale: Optional[float] = None,
                       x_scale: float = 1.0, y_scale: float = 1.0, z_scale: float = 1.0,
                       origin: Optional[list[float]] = None,
                       expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Thu phóng một hoặc nhiều đối tượng theo các trục X, Y, Z."""
        if scale is not None:
            x_scale = scale
            y_scale = scale
            z_scale = scale
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({"x_scale": x_scale, "y_scale": y_scale, "z_scale": z_scale})
        if origin is not None:
            payload["origin"] = origin
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("scale", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_delete(persistent_ids=None, entity_ids=None, ids=None,
                        expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Xóa an toàn một hoặc nhiều đối tượng khỏi model."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("delete", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_group(persistent_ids=None, entity_ids=None, ids=None, name: str = "",
                       expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Gom nhóm một hoặc nhiều đối tượng thành một Group mới."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["name"] = name
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("group", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_ungroup(persistent_id: Optional[Union[int, str]] = None, entity_id: Optional[int] = None,
                         id: Optional[Union[int, str]] = None, persistent_ids=None, entity_ids=None, ids=None,
                         expected_model_revision: Optional[int] = None, expected_model_session_id: Optional[str] = None) -> str:
        """Rã nhóm (explode) một hoặc nhiều Group/Component thành các đối tượng rời."""
        if persistent_id is not None:
            payload = {"persistent_id": persistent_id}
        elif entity_id is not None:
            payload = {"entity_id": entity_id}
        elif id is not None:
            payload = {"persistent_id": id}
        elif persistent_ids and len(persistent_ids) > 0:
            payload = {"persistent_id": persistent_ids[0]}
        elif entity_ids and len(entity_ids) > 0:
            payload = {"entity_id": entity_ids[0]}
        elif ids and len(ids) > 0:
            payload = {"persistent_id": ids[0]}
        else:
            raise ValueError("Phải cung cấp persistent_id hoặc entity_id của Group cần rã nhóm")
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("ungroup", payload), indent=2, ensure_ascii=False)
