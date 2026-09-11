"""
BIM Attributes & Metadata MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload, add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_entity_attributes(persistent_id: Optional[Union[int, str]] = None, entity_id: Optional[int] = None,
                                       id: Optional[Union[int, str]] = None, dictionary_name: Optional[str] = None) -> str:
        """Đọc Attribute Dictionaries / metadata của một đối tượng."""
        payload: Dict[str, Any] = {}
        if persistent_id is not None:
            payload["persistent_id"] = persistent_id
        elif entity_id is not None:
            payload["entity_id"] = entity_id
        elif id is not None:
            payload["persistent_id"] = id
        else:
            raise ValueError("Phải cung cấp persistent_id hoặc entity_id của đối tượng")
        if dictionary_name:
            payload["dictionary_name"] = dictionary_name
        return json.dumps(send_to_sketchup("get_entity_attributes", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_attributes(
        dictionary_name: str,
        attributes: Dict[str, Any],
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Ghi metadata/BIM attributes vào Group hoặc ComponentInstance."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({"dictionary_name": dictionary_name, "attributes": attributes})
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("set_entity_attributes", payload), indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_delete_entity_attributes(
        dictionary_name: str,
        keys: Optional[list[str]] = None,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        """Xóa metadata/BIM attributes khỏi Group hoặc ComponentInstance."""
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["dictionary_name"] = dictionary_name
        if keys is not None:
            payload["keys"] = keys
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        return json.dumps(send_to_sketchup("delete_entity_attributes", payload), indent=2, ensure_ascii=False)
