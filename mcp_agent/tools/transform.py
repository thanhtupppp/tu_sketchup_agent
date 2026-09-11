"""
Transformation & Hierarchy MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_move(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
    ) -> str:
        """
        Di chuyển (tịnh tiến) một hoặc nhiều đối tượng (Group, ComponentInstance, Face, ...) theo khoảng cách mm.
        
        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần di chuyển (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID trong phiên làm việc (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược; tự động map sang persistent_ids).
            dx: Khoảng cách dịch chuyển theo trục X (đơn vị mm, dương: sang phải, âm: sang trái).
            dy: Khoảng cách dịch chuyển theo trục Y (đơn vị mm, dương: ra sau/sâu, âm: ra trước).
            dz: Khoảng cách dịch chuyển theo trục Z (đơn vị mm, dương: lên trên, âm: xuống dưới).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({
            "dx": dx,
            "dy": dy,
            "dz": dz,
        })
        res = send_to_sketchup("move", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_copy(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
    ) -> str:
        """
        Sao chép (nhân bản) một hoặc nhiều đối tượng và tịnh tiến bản sao theo khoảng cách mm.
        
        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng gốc cần sao chép (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            dx: Độ lệch theo trục X cho bản sao mới (đơn vị mm).
            dy: Độ lệch theo trục Y cho bản sao mới (đơn vị mm).
            dz: Độ lệch theo trục Z cho bản sao mới (đơn vị mm).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({
            "dx": dx,
            "dy": dy,
            "dz": dz,
        })
        res = send_to_sketchup("copy", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_rotate(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        angle_degrees: float = 0.0,
        axis: Union[str, list[float]] = "z",
        origin: Optional[list[float]] = None,
    ) -> str:
        """
        Xoay một hoặc nhiều đối tượng quanh một trục và tâm quay chỉ định.
        
        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần xoay (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            angle_degrees: Góc xoay tính bằng độ (dương: ngược chiều kim đồng hồ nhìn từ đỉnh vector).
            axis: Trục xoay ("x", "y", "z" hoặc vector tuỳ chỉnh 3 phần tử [ax, ay, az], mặc định "z").
            origin: Tọa độ tâm xoay [x, y, z] tính bằng mm. Nếu bỏ trống, tự động lấy tâm bounding box của các đối tượng.
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({
            "angle_degrees": angle_degrees,
            "axis": axis,
        })
        if origin is not None:
            payload["origin"] = origin
        res = send_to_sketchup("rotate", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_scale(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        scale: Optional[float] = None,
        x_scale: float = 1.0,
        y_scale: float = 1.0,
        z_scale: float = 1.0,
        origin: Optional[list[float]] = None,
    ) -> str:
        """
        Thu phóng (scale) kích thước của một hoặc nhiều đối tượng theo các trục X, Y, Z.

        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần scale (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            scale: Hệ số thu phóng đồng đều cho cả 3 trục (tiện lợi).
            x_scale: Hệ số thu phóng theo trục X (mặc định 1.0).
            y_scale: Hệ số thu phóng theo trục Y (mặc định 1.0).
            z_scale: Hệ số thu phóng theo trục Z (mặc định 1.0).
            origin: Tọa độ gốc scale [x, y, z] tính bằng mm (mặc định lấy tâm bounding box).
        """
        if scale is not None:
            x_scale = scale
            y_scale = scale
            z_scale = scale

        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload.update({
            "x_scale": x_scale,
            "y_scale": y_scale,
            "z_scale": z_scale,
        })
        if origin is not None:
            payload["origin"] = origin
        res = send_to_sketchup("scale", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_delete(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Xóa an toàn một hoặc nhiều đối tượng khỏi model.
        
        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần xóa (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        res = send_to_sketchup("delete", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_group(
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        name: str = "",
    ) -> str:
        """
        Gom nhóm một hoặc nhiều đối tượng thành một Group mới.
        
        Args:
            persistent_ids: Danh sách Persistent ID của các đối tượng cần gom nhóm (chuẩn khuyến nghị chính thức).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
            name: Tên đặt cho Group mới (tùy chọn).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["name"] = name
        res = send_to_sketchup("group", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_ungroup(
        persistent_id: Optional[Union[int, str]] = None,
        entity_id: Optional[int] = None,
        id: Optional[Union[int, str]] = None,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Rã nhóm (explode) một hoặc nhiều Group/Component thành các đối tượng rời độc lập.

        Args:
            persistent_id: Persistent ID của Group cần rã nhóm (chuẩn khuyến nghị chính thức).
            entity_id: Entity ID của Group cần rã nhóm (tùy chọn).
            id: (Legacy - chỉ để tương thích ngược).
            persistent_ids: Danh sách Persistent ID của các Group cần rã nhóm (tùy chọn).
            entity_ids: Danh sách Entity ID của các Group cần rã nhóm (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
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

        res = send_to_sketchup("ungroup", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
