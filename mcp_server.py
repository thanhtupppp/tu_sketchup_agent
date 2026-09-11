# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.3.0,<2.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
FastMCP Server for SketchUp 2026.
Bridges AI assistants (Antigravity, Claude Desktop, Cursor) to SketchUp Ruby API via TCP.
"""

import json
import socket
import base64
import uuid
from typing import Optional, Dict, Any, Union
from mcp.server.fastmcp import FastMCP, Image

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"
PROTOCOL_VERSION = "1.1"
SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1"}

mcp = FastMCP("sketchup-agent")


def require_protocol_version(res: dict, supported: Optional[set[str]] = None) -> None:
    """Xác nhận tính tương thích phiên bản giao thức giữa MCP Server và Ruby Bridge."""
    if supported is None:
        supported = SUPPORTED_PROTOCOL_VERSIONS
    actual = res.get("protocol_version")
    min_compat = res.get("min_compatible_protocol_version")
    if actual and actual not in supported:
        if min_compat is None or min_compat not in supported:
            raise RuntimeError(
                f"Không tương thích protocol: hỗ trợ {supported}, nhưng nhận được {actual} (min_compat: {min_compat})"
            )


def send_to_sketchup(command: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> dict:
    """Send length-prefixed JSON request to SketchUp TCP bridge."""
    if arguments is None:
        arguments = {}

    request_id = f"req_{uuid.uuid4().hex[:8]}"
    payload = {
        "token": TOKEN,
        "command": command,
        "request_id": request_id,
        "arguments": arguments,
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"{len(body)}\n".encode("utf-8")

    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as s:
            s.sendall(header + body)

            # Read response length line
            line = b""
            while not line.endswith(b"\n"):
                chunk = s.recv(1)
                if not chunk:
                    raise ConnectionError("Kết nối bị đóng khi nhận header phản hồi từ SketchUp.")
                line += chunk

            length = int(line.decode("utf-8").strip())

            # Read full body
            data = bytearray()
            while len(data) < length:
                chunk = s.recv(min(8192, length - len(data)))
                if not chunk:
                    raise ConnectionError("Kết nối bị đóng khi nhận body dữ liệu từ SketchUp.")
                data.extend(chunk)

            res = json.loads(data.decode("utf-8"))
            if isinstance(res, dict):
                require_protocol_version(res)
            return res
    except ConnectionRefusedError:
        return {
            "ok": False,
            "error": (
                f"Không thể kết nối đến SketchUp tại {HOST}:{PORT}. "
                "Vui lòng đảm bảo SketchUp 2026 đang mở và TCP Bridge đã được bật "
                "(Extensions -> Tu SketchUp Agent -> Start TCP Bridge)."
            ),
        }
    except Exception as e:
        return {"ok": False, "error": f"Lỗi giao tiếp TCP Bridge: {str(e)}"}


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


def _build_ids_payload(
    persistent_ids: Optional[list[Union[int, str]]] = None,
    entity_ids: Optional[list[Union[int, str]]] = None,
    ids: Optional[list[Union[int, str]]] = None,
) -> Dict[str, Any]:
    if persistent_ids is not None:
        pids = persistent_ids if isinstance(persistent_ids, list) else [persistent_ids]
        return {"persistent_ids": pids}
    if entity_ids is not None:
        eids = entity_ids if isinstance(entity_ids, list) else [entity_ids]
        return {"entity_ids": eids}
    if ids is not None:
        id_list = ids if isinstance(ids, list) else [ids]
        return {"persistent_ids": id_list}
    raise ValueError("Cần cung cấp ít nhất một danh sách ID đối tượng: persistent_ids hoặc entity_ids")


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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
        x_scale: Hệ số thu phóng theo trục X (mặc định 1.0).
        y_scale: Hệ số thu phóng theo trục Y (mặc định 1.0).
        z_scale: Hệ số thu phóng theo trục Z (mặc định 1.0).
        origin: Tọa độ gốc scale [x, y, z] tính bằng mm (mặc định lấy tâm bounding box).
    """
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
    payload["name"] = name
    res = send_to_sketchup("group", payload)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def sketchup_ungroup(
    persistent_id: Optional[Union[int, str]] = None,
    entity_id: Optional[int] = None,
    id: Optional[Union[int, str]] = None,
) -> str:
    """
    Rã nhóm (explode) một Group thành các đối tượng rời độc lập.
    
    Args:
        persistent_id: Persistent ID của Group cần rã nhóm (chuẩn khuyến nghị chính thức).
        entity_id: Entity ID của Group cần rã nhóm (tùy chọn).
        id: (Legacy - chỉ để tương thích ngược).
    """
    if persistent_id is not None:
        payload = {"persistent_id": persistent_id}
    elif entity_id is not None:
        payload = {"entity_id": entity_id}
    elif id is not None:
        payload = {"persistent_id": id}
    else:
        raise ValueError("Phải cung cấp persistent_id hoặc entity_id của Group cần rã")
    res = send_to_sketchup("ungroup", payload)
    return json.dumps(res, indent=2, ensure_ascii=False)


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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
    res = send_to_sketchup("clear_entity_material", payload)
    return json.dumps(res, indent=2, ensure_ascii=False)


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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
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
    payload = _build_ids_payload(persistent_ids, entity_ids, ids)
    payload["dictionary_name"] = dictionary_name
    if keys is not None:
        payload["keys"] = keys
    res = send_to_sketchup("delete_entity_attributes", payload)
    return json.dumps(res, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
