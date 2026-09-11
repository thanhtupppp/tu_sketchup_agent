"""
TCP Socket Transport & Protocol Verification for Tu SketchUp Agent.
"""

import json
import socket
import uuid
from typing import Optional, Dict, Any

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"
PROTOCOL_VERSION = "1.3"
SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2", "1.3"}

# Backward compatibility aliases
SKETCHUP_HOST = HOST
SKETCHUP_PORT = PORT
SHARED_SECRET = TOKEN


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
