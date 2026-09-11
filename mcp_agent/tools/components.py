"""
Component Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_create_component(
        name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        description: str = "",
    ) -> str:
        """
        Tạo một ComponentDefinition mới từ một hoặc nhiều đối tượng hình học (Group, Face, Edge, ...).
        Nếu chỉ truyền 1 Group, Group đó sẽ được chuyển đổi trực tiếp thành ComponentInstance.
        Nếu truyền nhiều đối tượng, chúng sẽ được gom lại và chuyển thành ComponentInstance mới.

        Args:
            name: Tên của ComponentDefinition (ví dụ: "Bearing_6204", "Roller_Shaft").
            persistent_ids: Danh sách Persistent ID của các đối tượng tạo nên component (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            description: Mô tả chi tiết về component (tùy chọn).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["name"] = name
        if description:
            payload["description"] = description
        res = send_to_sketchup("create_component", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_component_definitions(
        name_filter: Optional[str] = None,
        include_internal: bool = False,
    ) -> str:
        """
        Liệt kê danh sách tất cả các ComponentDefinition trong model hiện tại.

        Args:
            name_filter: Bộ lọc theo tên định nghĩa (không phân biệt hoa thường).
            include_internal: Nếu True, bao gồm cả các definition nội bộ tự động của Group (mặc định False).
        """
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
    ) -> str:
        """
        Tách riêng một hoặc nhiều ComponentInstance khỏi definition gốc (Make Unique), tạo definition độc lập mới.
        Rất hữu ích khi cần chỉnh sửa hoặc tùy biến một chi tiết lắp ráp mà không ảnh hưởng đến các chi tiết khác cùng loại.

        Args:
            persistent_ids: Danh sách Persistent ID của các ComponentInstance cần make unique (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            new_name: Tên mới cho ComponentDefinition độc lập vừa tạo (áp dụng khi make unique 1 instance).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        if new_name:
            payload["new_name"] = new_name
        res = send_to_sketchup("make_component_unique", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_save_component_to_skp(
        definition_name: str,
        file_path: str,
        overwrite: bool = False,
    ) -> str:
        """
        Xuất một ComponentDefinition ra tệp mô hình SketchUp độc lập (.skp) để lưu trữ vào thư viện linh kiện.

        Args:
            definition_name: Tên ComponentDefinition cần xuất.
            file_path: Đường dẫn tệp đích đầy đủ (phải có đuôi .skp).
            overwrite: Nếu True, cho phép ghi đè nếu tệp đã tồn tại (mặc định False).
        """
        payload = {
            "definition_name": definition_name,
            "file_path": file_path,
            "overwrite": overwrite,
        }
        res = send_to_sketchup("save_component_to_skp", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_load_component_from_skp(
        file_path: str,
        definition_name: Optional[str] = None,
    ) -> str:
        """
        Nạp một tệp mô hình SketchUp (.skp) từ thư viện bên ngoài vào danh sách ComponentDefinition của model.

        Args:
            file_path: Đường dẫn tuyệt đối tới tệp .skp cần nạp.
            definition_name: Đặt lại tên cho ComponentDefinition sau khi nạp (tùy chọn).
        """
        payload: Dict[str, Any] = {"file_path": file_path}
        if definition_name:
            payload["definition_name"] = definition_name
        res = send_to_sketchup("load_component_from_skp", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
