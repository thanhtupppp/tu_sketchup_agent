"""
BIM Attributes & Metadata MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_entity_attributes(
        persistent_id: Optional[Union[int, str]] = None,
        entity_id: Optional[int] = None,
        id: Optional[Union[int, str]] = None,
        dictionary_name: Optional[str] = None,
    ) -> str:
        """
        Đọc các từ điển thuộc tính (Attribute Dictionaries / metadata / BIM) của một đối tượng trong SketchUp.

        Args:
            persistent_id: Persistent ID của đối tượng cần đọc thuộc tính (khuyên dùng).
            entity_id: Entity ID của đối tượng (tùy chọn).
            id: (Legacy - chỉ để tương thích ngược).
            dictionary_name: Tên dictionary cụ thể cần đọc. Nếu bỏ trống, trả về tất cả dictionaries của đối tượng.
        """
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

        res = send_to_sketchup("get_entity_attributes", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_attributes(
        dictionary_name: str,
        attributes: Dict[str, Any],
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Ghi các cặp thuộc tính (key-value / metadata / BIM) vào Attribute Dictionary của Group hoặc ComponentInstance.
        Lưu ý an toàn: Chỉ hỗ trợ Sketchup::Group hoặc Sketchup::ComponentInstance.

        Args:
            dictionary_name: Tên của từ điển thuộc tính (ví dụ: "bim_data", "specs", "pricing").
            attributes: Dictionary chứa các cặp key/value cần lưu trữ (ví dụ: {"part_no": "P-01", "cost": 150.0}).
            persistent_ids: Danh sách Persistent ID của các đối tượng (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["dictionary_name"] = dictionary_name
        payload["attributes"] = attributes
        res = send_to_sketchup("set_entity_attributes", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_delete_entity_attributes(
        dictionary_name: str,
        keys: Optional[list[str]] = None,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Xóa thuộc tính trong Attribute Dictionary của Group hoặc ComponentInstance.

        Args:
            dictionary_name: Tên của từ điển thuộc tính.
            keys: Danh sách các key cụ thể cần xóa. Nếu bỏ trống, toàn bộ dictionary này sẽ bị xóa khỏi đối tượng.
            persistent_ids: Danh sách Persistent ID của các đối tượng (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["dictionary_name"] = dictionary_name
        if keys is not None:
            payload["keys"] = keys
        res = send_to_sketchup("delete_entity_attributes", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
