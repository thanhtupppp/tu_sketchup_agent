# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Model State & Revision Contract Test Suite (v1.4).
Runs against a live SketchUp 2026 TCP bridge.
"""

import json
import socket
import sys
import uuid
import subprocess
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"
EXPECTED_PROTOCOL = "1.3"


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def send(command: str, arguments: dict | None = None, timeout: float = 15.0) -> dict:
    req = {
        "token": TOKEN,
        "command": command,
        "request_id": f"ms14_{uuid.uuid4().hex[:8]}",
        "arguments": arguments or {},
    }
    body = json.dumps(req, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall(f"{len(body)}\n".encode("utf-8") + body)
        line = b""
        while not line.endswith(b"\n"):
            chunk = s.recv(1)
            if not chunk:
                raise ConnectionError("Bridge đóng kết nối khi đọc response header")
            line += chunk
        length = int(line.decode("utf-8").strip())
        data = bytearray()
        while len(data) < length:
            chunk = s.recv(min(8192, length - len(data)))
            if not chunk:
                raise ConnectionError("Bridge đóng kết nối khi đọc response body")
            data.extend(chunk)
        return json.loads(data.decode("utf-8"))


def run_suite() -> None:
    print("=" * 72)
    print("  TU SKETCHUP AGENT - MODEL STATE & REVISION TEST SUITE (v1.4)")
    print("=" * 72)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Git commit: {git_revision()}")
    print("-" * 72)

    ping = send("ping")
    assert ping.get("ok") is True, f"Ping thất bại: {ping}"
    assert ping.get("protocol_version") == EXPECTED_PROTOCOL, f"Protocol sai: {ping}"
    print("[TEST 01] Ping + protocol compatibility -> PASS")

    state1 = send("get_model_state")
    assert state1.get("ok") is True, f"get_model_state thất bại: {state1}"
    model_state1 = state1.get("model_state", {})
    assert model_state1.get("state_version") == 1, f"Thiếu state_version=1: {state1}"
    session_id = model_state1.get("model_session_id")
    assert session_id, f"Thiếu model_session_id: {state1}"
    revision1 = model_state1.get("revision")
    assert isinstance(revision1, int) and revision1 >= 0, f"Revision không hợp lệ: {state1}"
    print(f"[TEST 02] Model state identity + revision={revision1} -> PASS")

    summary = send("model_summary")
    assert summary.get("ok") is True, f"model_summary thất bại: {summary}"
    summary_state = summary.get("model_state", {})
    assert summary_state.get("model_session_id") == session_id, "Summary không cùng model session"
    assert summary_state.get("revision") == revision1, "Summary revision lệch get_model_state"
    print("[TEST 03] model_summary/state consistency -> PASS")

    state2 = send("get_model_state")
    assert state2.get("model_state", {}).get("model_session_id") == session_id, "Session ID thay đổi khi chỉ đọc"
    assert state2.get("model_state", {}).get("revision") == revision1, "Revision thay đổi khi chỉ đọc"
    print("[TEST 04] Read-only calls preserve state -> PASS")

    box = send("create_box", {"width": 120, "depth": 80, "height": 50, "name": "ModelState_v1_4_Test"})
    assert box.get("ok") is True, f"create_box thất bại: {box}"
    pid = box.get("persistent_id") or box.get("entity", {}).get("persistent_id")
    assert pid, f"Không lấy được persistent_id: {box}"

    state3 = send("get_model_state")
    model_state3 = state3.get("model_state", {})
    assert model_state3.get("model_session_id") == session_id, "Mutation tạo model session mới"
    assert model_state3.get("revision") == revision1 + 1, (
        f"Revision phải tăng đúng 1 sau create_box: trước={revision1}, sau={model_state3.get('revision')}"
    )
    assert box.get("model_revision") == model_state3.get("revision"), "Response mutation revision không khớp state"
    print(f"[TEST 05] create_box increments revision exactly once ({revision1} -> {model_state3.get('revision')}) -> PASS")

    deleted = send("delete", {"persistent_ids": [pid]})
    assert deleted.get("ok") is True, f"delete thất bại: {deleted}"

    state4 = send("get_model_state")
    model_state4 = state4.get("model_state", {})
    assert model_state4.get("revision") == model_state3.get("revision") + 1, (
        f"Revision phải tăng đúng 1 sau delete: trước={model_state3.get('revision')}, sau={model_state4.get('revision')}"
    )
    print(f"[TEST 06] delete increments revision exactly once ({model_state3.get('revision')} -> {model_state4.get('revision')}) -> PASS")

    assert model_state4.get("model_session_id") == session_id, "Session ID đổi sau mutation"
    assert model_state4.get("model_guid") is not None, "Thiếu model_guid metadata"
    print("[TEST 07] Model session remains stable; GUID exposed as metadata -> PASS")

    stale = send("create_box", {
        "width": 40,
        "depth": 40,
        "height": 40,
        "name": "Should_Not_Be_Created",
        "expected_model_revision": model_state3.get("revision"),
        "expected_model_session_id": session_id,
    })
    assert stale.get("ok") is False, f"Stale request phải bị từ chối: {stale}"
    assert stale.get("error", {}).get("code") == "STALE_MODEL_STATE", f"Sai error code: {stale}"
    assert stale.get("actual_model_revision") == model_state4.get("revision"), f"Sai actual revision: {stale}"
    print("[TEST 08] Optimistic concurrency guard rejects stale revision -> PASS")

    guarded = send("create_box", {
        "width": 60,
        "depth": 60,
        "height": 30,
        "name": "Guarded_ModelState_v1_4",
        "expected_model_revision": model_state4.get("revision"),
        "expected_model_session_id": session_id,
    })
    assert guarded.get("ok") is True, f"Fresh guarded request thất bại: {guarded}"
    guarded_pid = guarded.get("persistent_id") or guarded.get("entity", {}).get("persistent_id")
    assert guarded_pid, f"Guarded create không trả PID: {guarded}"
    delete_guarded = send("delete", {
        "persistent_ids": [guarded_pid],
        "expected_model_revision": model_state4.get("revision") + 1,
        "expected_model_session_id": session_id,
    })
    assert delete_guarded.get("ok") is True, f"Guarded delete thất bại: {delete_guarded}"
    print("[TEST 09] Fresh revision + session guard accepts valid request -> PASS")

    print("-" * 72)
    print("KẾT QUẢ: 9/9 BÀI TEST MODEL STATE & REVISION v1.4 ĐÃ VƯỢT QUA!")
    print("=" * 72)


if __name__ == "__main__":
    run_suite()
