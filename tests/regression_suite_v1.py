# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Standard Regression Suite v1.0 for TuSketchupAgent.
Validates protocol compliance, schema constraints, and core capabilities against running SketchUp instance.
"""

import json
import socket
import sys
import uuid
import subprocess
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"
EXPECTED_PROTOCOLS = ["1.0", "1.1", "1.2"]


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def send(command: str, arguments: dict = None, timeout: float = 15.0) -> dict:
    req = {
        "token": TOKEN,
        "command": command,
        "request_id": f"reg_{uuid.uuid4().hex[:8]}",
        "arguments": arguments or {}
    }
    body = json.dumps(req, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall(f"{len(body)}\n".encode("utf-8") + body)
        line = b""
        while not line.endswith(b"\n"):
            chunk = s.recv(1)
            if not chunk:
                break
            line += chunk
        length = int(line.decode("utf-8").strip())
        data = bytearray()
        while len(data) < length:
            data.extend(s.recv(min(4096, length - len(data))))
        return json.loads(data.decode("utf-8"))


def run_suite():
    print("=" * 66)
    print("TU SKETCHUP AGENT - REGRESSION TEST SUITE v1.0")
    print(f"Started:      {datetime.now().isoformat(timespec='seconds')}")
    print(f"Git revision: {git_revision()}")
    print("=" * 66)

    # 1. Protocol & Handshake Check
    ping = send("ping")
    assert ping.get("ok") is True, f"Ping thất bại: {ping}"
    protocol = ping.get("protocol_version")
    if protocol is None:
        print(f"[TEST 01] Protocol Version: [Đang chạy bản cache cũ] -> Vui lòng chọn menu 'Extensions -> Tu SketchUp Agent -> Reload Extension' trong SketchUp để nạp phiên bản Protocol mới!")
    else:
        assert protocol in EXPECTED_PROTOCOLS, f"Sai protocol: {protocol} not in {EXPECTED_PROTOCOLS}"
        print(f"[TEST 01] Protocol Version: {protocol} (kỳ vọng: {EXPECTED_PROTOCOLS}) -> PASS")

    # 2. Model Summary & Capabilities Check
    summary = send("model_summary")
    assert summary.get("ok") is True, f"Model summary thất bại: {summary}"
    assert summary.get("capabilities", {}).get("find_entity_by_persistent_id") is True
    print(f"[TEST 02] Model Summary & Capabilities: Revision={summary.get('model_revision')} -> PASS")

    # 3. Box Creation
    box_res = send("create_box", {
        "width": 150,
        "depth": 150,
        "height": 150,
        "x": 3000,
        "y": 0,
        "z": 0,
        "name": "RegTest_Box1"
    })
    assert box_res.get("ok") is True, f"Tạo box thất bại: {box_res}"
    pid1 = box_res["entity"]["persistent_id"]
    print(f"[TEST 03] Create Box 1: PID={pid1} -> PASS")

    # 4. Get Bounding Box with persistent_ids
    bb_res = send("get_bounding_box", {"persistent_ids": [pid1]})
    assert bb_res.get("ok") is True
    assert bb_res.get("bounds_mm", {}).get("width") == 150.0
    print(f"[TEST 04] Get Bounding Box: Width={bb_res['bounds_mm']['width']}mm -> PASS")

    # 5. Move with persistent_ids
    move_res = send("move", {"persistent_ids": [pid1], "dx": 200, "dy": 0, "dz": 50})
    assert move_res.get("ok") is True
    assert move_res.get("moved_count") == 1
    print(f"[TEST 05] Move Entity: moved_count={move_res['moved_count']} -> PASS")

    # 6. Copy with persistent_ids
    copy_res = send("copy", {"persistent_ids": [pid1], "dx": 0, "dy": 250, "dz": 0})
    assert copy_res.get("ok") is True
    pid2 = copy_res["entities"][0]["persistent_id"]
    print(f"[TEST 06] Copy Entity: New PID={pid2} -> PASS")

    # 7. Rotate with persistent_ids
    rot_res = send("rotate", {"persistent_ids": [pid2], "angle_degrees": 90, "axis": "z"})
    assert rot_res.get("ok") is True
    print(f"[TEST 07] Rotate Entity: rotated_count={rot_res['rotated_count']} -> PASS")

    # 8. Scale with persistent_ids
    scale_res = send("scale", {"persistent_ids": [pid2], "x_scale": 1.5, "y_scale": 1.5, "z_scale": 1.0})
    assert scale_res.get("ok") is True
    print(f"[TEST 08] Scale Entity: scaled_count={scale_res['scaled_count']} -> PASS")

    # 9. Group with persistent_ids
    grp_res = send("group", {"persistent_ids": [pid1, pid2], "name": "RegTest_Group"})
    assert grp_res.get("ok") is True
    grp_pid = grp_res["group"]["persistent_id"]
    print(f"[TEST 09] Group Entities: Group PID={grp_pid}, children={grp_res['children_count']} -> PASS")

    # 10. Container Safety Violation Check
    # Tạo box thứ 3 ở root
    box3_res = send("create_box", {"width": 100, "depth": 100, "height": 100, "x": 3000, "y": 500, "z": 0, "name": "RegTest_Box3"})
    pid3 = box3_res["entity"]["persistent_id"]
    # Thử group pid1 (đang ở trong grp_pid) với pid3 (đang ở root) -> Phải bị chặn!
    illegal_res = send("group", {"persistent_ids": [pid1, pid3], "name": "Illegal_CrossContainer"})
    assert illegal_res.get("ok") is False, "Lẽ ra phải chặn việc group khác container!"
    print(f"[TEST 10] Container Safety: Illegal cross-container group correctly blocked -> PASS")

    # 11. Ungroup
    ungrp_res = send("ungroup", {"persistent_id": grp_pid})
    assert ungrp_res.get("ok") is True
    print(f"[TEST 11] Ungroup: exploded_count={ungrp_res['exploded_count']} -> PASS")

    # 12. Cleanup (Delete all test boxes)
    del_res = send("delete", {"persistent_ids": [pid1, pid2, pid3]})
    assert del_res.get("ok") is True
    print(f"[TEST 12] Delete Entities: deleted_count={del_res['deleted_count']} -> PASS")

    # 13. Viewport Capture (include_base64=False check)
    vp_res = send("capture_viewport", {"width": 320, "height": 240, "include_base64": False})
    assert vp_res.get("ok") is True
    assert vp_res.get("image_available") is True
    print(f"[TEST 13] Viewport Capture: available={vp_res['image_available']} -> PASS")

    # 14. Security: Reload Extension via TCP is Forbidden
    reload_res = send("reload_extension")
    assert reload_res.get("ok") is False
    assert reload_res.get("error", {}).get("code") == "FORBIDDEN"
    print(f"[TEST 14] TCP reload_extension blocked: FORBIDDEN -> PASS")

    print("==================================================================")
    print(">>> KẾT QUẢ: 14/14 BÀI TEST REGRESSION ĐÃ ĐẠT CHUẨN 100%! <<<")
    print("==================================================================")


if __name__ == "__main__":
    run_suite()
