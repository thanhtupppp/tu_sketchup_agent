"""
Layers & Scenes MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_layers(
        name_filter: Optional[str] = None,
    ) -> str:
        """
        Liệt kê danh sách tất cả Layers/Tags trong model SketchUp.

        Args:
            name_filter: Bộ lọc theo tên layer (không phân biệt hoa thường).
        """
        payload: Dict[str, Any] = {}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_layers", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_layer(
        name: str,
        color: Optional[Union[str, list[int]]] = None,
        visible: bool = True,
    ) -> str:
        """
        Tạo mới hoặc cập nhật thuộc tính của một Layer/Tag theo tên.

        Args:
            name: Tên của layer (ví dụ: "Chassis_Frame", "Hydraulics", "Sensors").
            color: Màu hiển thị của layer (mã hex "#1E90FF" hoặc mảng RGB [30, 144, 255]).
            visible: Trạng thái hiển thị ban đầu (mặc định True).
        """
        payload: Dict[str, Any] = {"name": name, "visible": visible}
        if color is not None:
            payload["color"] = color
        res = send_to_sketchup("create_layer", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_layer(
        layer_name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
    ) -> str:
        """
        Gán các đối tượng vào Layer/Tag chỉ định. Tự động tạo layer nếu chưa tồn tại.
        Lưu ý an toàn: Chỉ hỗ trợ Sketchup::Group hoặc Sketchup::ComponentInstance (bảo toàn Face/Edge ở Layer0).

        Args:
            layer_name: Tên của layer cần gán.
            persistent_ids: Danh sách Persistent ID của các đối tượng (khuyên dùng).
            entity_ids: Danh sách Entity ID (tùy chọn).
            ids: (Legacy - chỉ để tương thích ngược).
        """
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["layer_name"] = layer_name
        res = send_to_sketchup("set_entity_layer", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_layer_visibility(
        layer_name: Optional[str] = None,
        visible: bool = True,
        layers: Optional[Dict[str, bool]] = None,
    ) -> str:
        """
        Bật hoặc tắt trạng thái hiển thị của một hoặc nhiều Layer/Tag (hỗ trợ bóc tách kết cấu, exploded view).

        Args:
            layer_name: Tên layer đơn lẻ cần bật/tắt (kèm tham số visible).
            visible: Trạng thái hiển thị (True: hiện, False: ẩn).
            layers: Dictionary bật/tắt nhiều layer cùng lúc (ví dụ: {"Chassis": true, "Pipes": false}).
        """
        payload: Dict[str, Any] = {}
        if layers is not None:
            payload["layers"] = layers
        elif layer_name is not None:
            payload["layer_name"] = layer_name
            payload["visible"] = visible
        else:
            raise ValueError("Cần cung cấp layer_name hoặc dictionary layers")
        res = send_to_sketchup("set_layer_visibility", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_scenes(
        name_filter: Optional[str] = None,
    ) -> str:
        """
        Liệt kê danh sách tất cả các Scene (Pages) hiện có trong model kèm thông số camera và hidden layers.

        Args:
            name_filter: Bộ lọc theo tên scene (tùy chọn).
        """
        payload: Dict[str, Any] = {}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_scenes", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_scene(
        name: str,
        preset: Optional[str] = None,
        camera: Optional[Dict[str, Any]] = None,
        perspective: bool = False,
        hidden_layers: Optional[list[str]] = None,
    ) -> str:
        """
        Tạo một Scene mới lưu lại góc nhìn camera và trạng thái layer.

        Args:
            name: Tên Scene (ví dụ: "Drawing_01_Front", "Scene_Iso_Exploded").
            preset: Preset kỹ thuật chuẩn ("top", "front", "right", "left", "back", "iso").
            camera: Cấu hình camera tùy biến {"eye": [x,y,z], "target": [x,y,z], "up": [x,y,z], "perspective": bool}.
            perspective: Chế độ phối cảnh (True: 3D perspective, False: 2D trực giao Orthographic cho bản vẽ kỹ thuật).
            hidden_layers: Danh sách tên các layer cần ẩn riêng trong scene này.
        """
        payload: Dict[str, Any] = {"name": name, "perspective": perspective}
        if preset:
            payload["preset"] = preset
        if camera:
            payload["camera"] = camera
        if hidden_layers:
            payload["hidden_layers"] = hidden_layers
        res = send_to_sketchup("create_scene", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_activate_scene(
        name: str,
    ) -> str:
        """
        Chuyển Viewport SketchUp sang góc nhìn và trạng thái của Scene chỉ định.

        Args:
            name: Tên Scene cần kích hoạt.
        """
        payload = {"name": name}
        res = send_to_sketchup("activate_scene", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_camera_view(
        preset: Optional[str] = None,
        perspective: bool = False,
        eye: Optional[list[float]] = None,
        target: Optional[list[float]] = None,
        up: Optional[list[float]] = None,
        zoom_extents: bool = True,
    ) -> str:
        """
        Điều khiển trực tiếp góc nhìn Camera của active view tức thời (không cần lưu thành scene).

        Args:
            preset: Preset góc nhìn kỹ thuật ("top", "front", "right", "left", "back", "iso").
            perspective: Chế độ chiếu (False: 2D Orthographic kỹ thuật, True: 3D Perspective).
            eye: Tọa độ mắt nhìn [x, y, z] tính theo mm (dùng khi không dùng preset).
            target: Tọa độ tâm ngắm [x, y, z] tính theo mm.
            up: Vector phương đứng [x, y, z] (mặc định [0, 0, 1]).
            zoom_extents: Tự động zoom extents bao trọn hình khối sau khi đặt góc nhìn (mặc định True).
        """
        payload: Dict[str, Any] = {
            "perspective": perspective,
            "zoom_extents": zoom_extents,
        }
        if preset:
            payload["preset"] = preset
        if eye is not None:
            payload["eye"] = eye
        if target is not None:
            payload["target"] = target
        if up is not None:
            payload["up"] = up
        res = send_to_sketchup("set_camera_view", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
