# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Live test for optimistic model-state guards on mutation MCP tools."""

import json
import socket
import uuid

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def send(command: str, arguments: dict | None = None) -> dict:
    body = json.dumps({
        "token": TOKEN,
        "command": command,
        "request_id": f"ms15_{uuid.uuid4().hex[:8]}",
        "arguments": arguments or {},
    }, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=15) as s:
        s.sendall(f"{len(body)}\n".encode() + body)
        line = b""
        while not line.endswith(b"\n"):
            chunk = s.recv(1)
            if not chunk:
                raise ConnectionError("Bridge đóng kết nối")
            line += chunk
        length = int(line.decode().strip())
        data = bytearray()
        while len(data) < length:
            chunk = s.recv(min(8192, length - len(data)))
            if not chunk:
                raise ConnectionError("Bridge đóng kết nối khi đọc body")
            data.extend(chunk)
        return json.loads(data.decode("utf-8"))


def main() -> None:
    state = send("get_model_state")["model_state"]
    session_id = state["model_session_id"]
    revision = state["revision"]

    # Correct state must allow the mutation.
    created = send("create_box", {
        "width": 100, "depth": 100, "height": 100,
        "name": "ModelState_v1_5_Test",
        "expected_model_revision": revision,
        "expected_model_session_id": session_id,
    })
    assert created.get("ok") is True, created
    pid = created.get("persistent_id") or created.get("entity", {}).get("persistent_id")
    assert pid, created

    current = send("get_model_state")["model_state"]
    assert current["revision"] == revision + 1, current

    # Stale revision must be rejected before the handler mutates the model.
    stale = send("create_box", {
        "width": 100, "depth": 100, "height": 100,
        "name": "Should_Not_Be_Created",
        "expected_model_revision": revision,
        "expected_model_session_id": session_id,
    })
    assert stale.get("ok") is False, stale
    assert stale.get("error", {}).get("code") == "STALE_MODEL_STATE", stale

    after_stale = send("get_model_state")["model_state"]
    assert after_stale["revision"] == current["revision"], after_stale

    # Cleanup the successful mutation without a stale guard.
    deleted = send("delete", {"persistent_ids": [pid]})
    assert deleted.get("ok") is True, deleted
    print("MODEL STATE GUARD v1.5: PASS")


if __name__ == "__main__":
    main()
