"""
System & Connection Tools for Tu SketchUp Agent.
"""

import json
import base64
from typing import Optional
from mcp.server.fastmcp import FastMCP, Image
from ..transport import send_to_sketchup


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_ping() -> str:
        """Kiểm tra trạng thái kết nối tới SketchUp 2026."""
        res = send_to_sketchup("ping")
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_model_info() -> str:
        """Lấy thông tin tổng quan của mô hình SketchUp đang mở (kích thước, layers/tags, materials, scenes, số lượng entity)."""
        res = send_to_sketchup("model_summary")
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_selection() -> str:
        """Xem danh sách và chi tiết các đối tượng (entity) đang được chọn trong SketchUp."""
        res = send_to_sketchup("get_selection")
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_zoom_extents() -> str:
        """Zoom toàn cảnh viewport để bao trọn tất cả các hình khối trong model."""
        res = send_to_sketchup("zoom_extents")
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_capture_viewport(width: int = 1280, height: int = 720) -> Image:
        """
        Chụp ảnh góc nhìn 3D hiện tại trong SketchUp Viewport và trả về ảnh để AI quan sát kết quả.
        
        Args:
            width: Chiều rộng ảnh (mặc định 1280px)
            height: Chiều cao ảnh (mặc định 720px)
        """
        if not 64 <= width <= 4096:
            raise ValueError("width phải trong khoảng 64..4096")

        if not 64 <= height <= 4096:
            raise ValueError("height phải trong khoảng 64..4096")

        res = send_to_sketchup("capture_viewport", {"width": width, "height": height, "include_base64": True})
        if not res.get("ok"):
            err = res.get("error", {})
            err_msg = err.get("message") if isinstance(err, dict) else str(err)
            raise RuntimeError(f"Lỗi chụp viewport SketchUp: {err_msg}")

        b64_data = res.get("image_base64")
        if not b64_data:
            raise RuntimeError(f"Không nhận được dữ liệu hình ảnh từ SketchUp: {res}")

        img_bytes = base64.b64decode(b64_data)
        return Image(data=img_bytes, format="png")

    @mcp.tool()
    def sketchup_execute_ruby(code: str, auto_operation: bool = False) -> str:
        """
        Thực thi mã Ruby trong SketchUp Ruby API.
        
        Lưu ý bảo mật:
        - Yêu cầu Dev Mode phải được BẬT trực tiếp trong SketchUp (qua menu Extensions -> Tu SketchUp Agent -> Toggle Dev Mode hoặc biến môi trường TU_SKETCHUP_DEV_MODE=1).
        - Không thể tự bật Dev Mode qua mạng để đảm bảo an toàn tuyệt đối cho người dùng.
        - Mặc định auto_operation=False để script tự quyết định transaction hoặc chạy lệnh tra cứu read-only mà không tạo Undo rác.
        - Giới hạn kích thước code: 100 KB.
        """
        res = send_to_sketchup("execute_ruby", {"code": code, "auto_operation": auto_operation}, timeout=30.0)
        return json.dumps(res, indent=2, ensure_ascii=False)
