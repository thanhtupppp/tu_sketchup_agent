"""
Component Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload, add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_create_component(
        name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        description: str = "",
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tạo ComponentDefinition mới từ các đối tượng hình học."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["name"] = name
        if description:
            payload["description"] = description
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_component", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_component_definitions(
        name_filter: Optional[str] = None,
        include_internal: bool = False,
    ) -> str:
        """Liệt kê các ComponentDefinition trong model hiện tại."""
        payload: Dict[str, Any] = {"include_internal": include_internal}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_component_definitions", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_make_component_unique(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        new_name: Optional[str] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Tách ComponentInstance khỏi definition gốc bằng Make Unique."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        if new_name:
            payload["new_name"] = new_name
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("make_component_unique", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_save_component_to_skp(
        definition_name: str,
        file_path: str,
        overwrite: bool = False,
    ) -> str:
        """Xuất ComponentDefinition ra tệp .skp."""
        payload = {"definition_name": definition_name, "file_path": file_path, "overwrite": overwrite}
        res = send_to_sketchup("save_component_to_skp", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_load_component_from_skp(
        file_path: str,
        definition_name: Optional[str] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Nạp ComponentDefinition từ tệp .skp vào model."""
        payload: Dict[str, Any] = {"file_path": file_path}
        if definition_name:
            payload["definition_name"] = definition_name
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("load_component_from_skp", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
