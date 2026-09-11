"""
Inspection Tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_entities(
        parent_id: Optional[Union[int, str]] = None,
        persistent_id: Optional[int] = None,
        entity_id: Optional[int] = None,
        type_filter: Optional[str] = None,
        layer_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """
        Liệt kê danh sách đối tượng (entities) trong model hoặc trong một Group/Component cha.
        
        Args:
            parent_id: ID (persistent_id hoặc entity_id) của Group/Component cha. Mặc định None để lấy danh sách ở cấp cao nhất (active_entities).
            persistent_id: Chỉ định trực tiếp persistent_id của Group/Component cha.
            entity_id: Chỉ định trực tiếp entity_id của Group/Component cha.
            type_filter: Lọc theo loại đối tượng ("Group", "ComponentInstance", "Face", "Edge", ...).
            layer_filter: Lọc theo tên Tag/Layer.
            name_filter: Lọc theo tên đối tượng (tìm kiếm không phân biệt hoa thường).
            limit: Số lượng tối đa trả về (1..1000, mặc định 100).
            offset: Vị trí bắt đầu lấy (mặc định 0).
        """
        args: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if persistent_id is not None:
            args["persistent_id"] = persistent_id
        elif entity_id is not None:
            args["entity_id"] = entity_id
        elif parent_id is not None:
            args["parent_id"] = parent_id
        if type_filter:
            args["type_filter"] = type_filter
        if layer_filter:
            args["layer_filter"] = layer_filter
        if name_filter:
            args["name_filter"] = name_filter

        res = send_to_sketchup("get_entities", args)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_entity_info(
        persistent_id: Optional[int] = None,
        entity_id: Optional[int] = None,
        reference_id: Optional[Union[int, str]] = None,
    ) -> str:
        """
        Xem thông tin chi tiết chuyên sâu của một đối tượng cụ thể trong SketchUp bằng persistent_id hoặc entity_id.
        
        Args:
            persistent_id: ID bền vững duy nhất của đối tượng trong model (ưu tiên sử dụng).
            entity_id: ID phiên làm việc hiện tại của đối tượng.
            reference_id: ID định danh (tự động tra cứu theo persistent_id hoặc entity_id).
        """
        args: Dict[str, Any] = {}
        if persistent_id is not None:
            args["persistent_id"] = persistent_id
        elif entity_id is not None:
            args["entity_id"] = entity_id
        elif reference_id is not None:
            args["reference_id"] = reference_id
        else:
            raise ValueError("Phải cung cấp ít nhất một trong các tham số: persistent_id, entity_id hoặc reference_id")

        res = send_to_sketchup("get_entity_info", args)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_bounding_box(
        persistent_ids: Optional[Union[list[int], int]] = None,
        entity_ids: Optional[Union[list[int], int]] = None,
        reference_ids: Optional[Union[list[Union[int, str]], int, str]] = None,
    ) -> str:
        """
        Tính toán hộp bao không gian (Bounding Box) hợp nhất cho một hoặc nhiều đối tượng (đơn vị mm).
        
        Args:
            persistent_ids: Một ID hoặc danh sách các ID persistent_id.
            entity_ids: Một ID hoặc danh sách các ID entity_id.
            reference_ids: Một ID hoặc danh sách các ID reference_id.
        """
        args: Dict[str, Any] = {}
        if persistent_ids is not None:
            args["persistent_ids"] = persistent_ids if isinstance(persistent_ids, list) else [persistent_ids]
        elif entity_ids is not None:
            args["entity_ids"] = entity_ids if isinstance(entity_ids, list) else [entity_ids]
        elif reference_ids is not None:
            args["reference_ids"] = reference_ids if isinstance(reference_ids, list) else [reference_ids]
        else:
            raise ValueError("Phải cung cấp ít nhất một trong các tham số: persistent_ids, entity_ids hoặc reference_ids")

        res = send_to_sketchup("get_bounding_box", args)
        return json.dumps(res, indent=2, ensure_ascii=False)
