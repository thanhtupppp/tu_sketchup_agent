"""
Assembly Management MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_place_component_instance(
        definition_name: str,
        position: Optional[list[float]] = None,
        rotation: Optional[Union[Dict[str, Any], list[float]]] = None,
        scale: Optional[Union[float, list[float]]] = None,
        matrix: Optional[list[float]] = None,
        instance_name: Optional[str] = None,
        parent_id: Optional[Union[int, str]] = None,
    ) -> str:
        """
        Chèn một instance mới của ComponentDefinition vào không gian vẽ hoặc cụm lắp ráp cha (sub-assembly).
        Hỗ trợ 2 chế độ biến đổi:
        1. Trực quan: position [x, y, z] (mm), rotation {"axis": "x"|"y"|"z", "angle": độ} hoặc [rx, ry, rz], scale (hệ số).
        2. Ma trận 4x4 raw: matrix (16 số thực column-major).

        Args:
            definition_name: Tên ComponentDefinition cần chèn.
            position: Tọa độ chèn [x, y, z] tính theo milimet (mm).
            rotation: Góc quay, ví dụ {"axis": "z", "angle": 45.0} hoặc Euler angles [rx, ry, rz] theo độ.
            scale: Tỷ lệ co dãn (float đơn hoặc [sx, sy, sz]).
            matrix: Mảng 16 số thực ma trận 4x4 biến đổi affine.
            instance_name: Tên gán riêng cho instance vừa tạo (tùy chọn).
            parent_id: Persistent ID hoặc Entity ID của Group/Component cha nếu muốn lồng vào sub-assembly (tùy chọn).
        """
        payload: Dict[str, Any] = {"definition_name": definition_name}
        if position is not None:
            payload["position"] = position
        if rotation is not None:
            payload["rotation"] = rotation
        if scale is not None:
            payload["scale"] = scale
        if matrix is not None:
            payload["matrix"] = matrix
        if instance_name:
            payload["instance_name"] = instance_name
        if parent_id is not None:
            payload["parent_id"] = parent_id
        res = send_to_sketchup("place_component_instance", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_import_file(
        file_path: str,
        units: str = "mm",
        merge_coplanar_faces: bool = True,
        orient_faces: bool = True,
        preserve_origin: bool = True,
        as_component: bool = True,
        name: Optional[str] = None,
    ) -> str:
        """
        Nạp (Import) tệp bản vẽ CAD hoặc mô hình 3D ngoài đĩa vào SketchUp 2026.
        Định dạng hỗ trợ: .dwg, .dxf, .dae, .obj, .3ds, .skp, .ifc, .dem.

        Args:
            file_path: Đường dẫn tuyệt đối hoặc tương đối đến tệp cần nạp.
            units: Đơn vị kích thước bản vẽ ("mm", "cm", "m", "in", "ft" - mặc định "mm").
            merge_coplanar_faces: Tự động hợp nhất các mặt phẳng đồng phẳng trong bản vẽ CAD.
            orient_faces: Tự động định hướng đồng nhất mặt pháp tuyến (Front/Back face).
            preserve_origin: Bảo toàn tọa độ gốc (Origin) từ file CAD.
            as_component: Nạp thành ComponentDefinition và chèn instance vào mô hình.
            name: Tên đặt cho Component hoặc Group được nạp (tùy chọn).
        """
        payload: Dict[str, Any] = {
            "file_path": file_path,
            "units": units,
            "merge_coplanar_faces": merge_coplanar_faces,
            "orient_faces": orient_faces,
            "preserve_origin": preserve_origin,
            "as_component": as_component,
        }
        if name:
            payload["name"] = name
        res = send_to_sketchup("import_file", payload, timeout=180.0)
        return json.dumps(res, indent=2, ensure_ascii=False)
