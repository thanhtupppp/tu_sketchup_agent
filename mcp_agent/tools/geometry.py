"""
Parametric Geometry Tools for Tu SketchUp Agent.
"""

import json
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_create_box(
        width: float,
        depth: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: str = "Box",
        material: str = "",
    ) -> str:
        """
        Tạo một khối hộp chữ nhật (3D Box) trong SketchUp với đơn vị mm.
        
        Args:
            width: Chiều rộng (theo trục X, đơn vị mm)
            depth: Chiều sâu (theo trục Y, đơn vị mm)
            height: Chiều cao (theo trục Z, đơn vị mm)
            x: Tọa độ gốc X (mm, mặc định 0.0)
            y: Tọa độ gốc Y (mm, mặc định 0.0)
            z: Tọa độ gốc Z (mm, mặc định 0.0)
            name: Tên của Group đối tượng
            material: Tên vật liệu áp dụng (tùy chọn)
        """
        res = send_to_sketchup(
            "create_box",
            {
                "width": width,
                "depth": depth,
                "height": height,
                "x": x,
                "y": y,
                "z": z,
                "name": name,
                "material": material,
            },
        )
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_cylinder(
        radius: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        segments: int = 24,
        name: str = "Cylinder",
        material: str = "",
    ) -> str:
        """
        Tạo một hình trụ đứng (Cylinder) trong SketchUp với đơn vị mm.
        
        Args:
            radius: Bán kính đáy (mm)
            height: Chiều cao hình trụ (mm)
            x: Tọa độ tâm đáy X (mm)
            y: Tọa độ tâm đáy Y (mm)
            z: Tọa độ đáy Z (mm)
            segments: Số cạnh của đường tròn (mặc định 24)
            name: Tên Group
            material: Tên vật liệu áp dụng
        """
        if not 3 <= segments <= 256:
            raise ValueError("segments phải trong khoảng 3..256")

        res = send_to_sketchup(
            "create_cylinder",
            {
                "radius": radius,
                "height": height,
                "x": x,
                "y": y,
                "z": z,
                "segments": segments,
                "name": name,
                "material": material,
            },
        )
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_wall(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        thickness: float = 100.0,
        height: float = 2800.0,
        z: float = 0.0,
        name: str = "Wall",
        material: str = "",
    ) -> str:
        """
        Tạo bức tường kiến trúc thẳng nối 2 điểm 2D với bề dày và chiều cao (đơn vị mm).
        
        Args:
            start_x: Tọa độ X điểm bắt đầu (mm)
            start_y: Tọa độ Y điểm bắt đầu (mm)
            end_x: Tọa độ X điểm kết thúc (mm)
            end_y: Tọa độ Y điểm kết thúc (mm)
            thickness: Độ dày tường (mm, mặc định 100mm)
            height: Chiều cao tường (mm, mặc định 2800mm)
            z: Độ cao sàn (mm, mặc định 0.0)
            name: Tên group tường
            material: Tên vật liệu áp dụng (tùy chọn)
        """
        res = send_to_sketchup(
            "create_wall",
            {
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "thickness": thickness,
                "height": height,
                "z": z,
                "name": name,
                "material": material,
            },
        )
        return json.dumps(res, indent=2, ensure_ascii=False)
