"""
Materials Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_materials(
        name_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """
        Liệt kê danh sách các vật liệu (Materials) hiện có trong mô hình SketchUp.

        Args:
            name_filter: Lọc theo tên vật liệu (không phân biệt hoa thường).
            limit: Số lượng vật liệu tối đa trả về (mặc định 100).
            offset: Vị trí bắt đầu lấy (mặc định 0).
        """
        payload: Dict[str, Any] = {"limit": limit, "offset": offset}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_materials", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_material_info(material_name: str) -> str:
        """
        Lấy thông số chi tiết của một vật liệu trong SketchUp (màu RGB/Hex, alpha, texture).

        Args:
            material_name: Tên của vật liệu cần tra cứu.
        """
        res = send_to_sketchup("get_material_info", {"material_name": material_name})
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_material(
        name: str,
        color: Optional[Union[str, list[int]]] = None,
        alpha: float = 1.0,
        texture_path: Optional[str] = None,
        texture_width_mm: Optional[float] = None,
        texture_height_mm: Optional[float] = None,
    ) -> str:
        """
        Tạo mới hoặc cập nhật vật liệu (Material) trong SketchUp.

        Args:
            name: Tên định danh của vật liệu.
            color: Mã màu (dạng Hex "#RRGGBB", tên tiếng Anh "red", hoặc mảng [R, G, B] / [R, G, B, A] từ 0-255).
            alpha: Độ đậm/trong suốt từ 0.0 (hoàn toàn trong suốt) đến 1.0 (đục).
            texture_path: Đường dẫn tuyệt đối tới file ảnh texture (tùy chọn).
            texture_width_mm: Chiều rộng hoa văn texture tính bằng mm (tùy chọn).
            texture_height_mm: Chiều cao hoa văn texture tính bằng mm (tùy chọn).
        """
        payload: Dict[str, Any] = {"name": name, "alpha": alpha}
        if color is not None:
            payload["color"] = color
        if texture_path is not None:
            payload["texture_path"] = texture_path
        if texture_width_mm is not None:
            payload["texture_width"] = texture_width_mm
        if texture_height_mm is not None:
            payload["texture_height"] = texture_height_mm

        res = send_to_sketchup("create_material", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_material(
        material_name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Gán vật liệu cho một hoặc nhiều Group hoặc ComponentInstance trong SketchUp.
        Lưu ý an toàn: Chỉ hỗ trợ Sketchup::Group hoặc Sketchup::ComponentInstance (không gán trực tiếp lên Face/Edge).

        Args:
            material_name: Tên vật liệu cần gán (phải tồn tại trong model).
            persistent_ids: Danh sách Persistent ID của các đối tượng (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["material_name"] = material_name
        res = send_to_sketchup("set_entity_material", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_clear_entity_material(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Xóa lớp vật liệu gán đè trên Group hoặc ComponentInstance, trả về vật liệu mặc định.

        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần xóa vật liệu (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        res = send_to_sketchup("clear_entity_material", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
