"""Live SketchUp integration test for transaction abort revision invariant v1.9.

Requires SketchUp 2026 and the Tu SketchUp Agent bridge to be running.
The test intentionally aborts a transaction after requesting a revision bump.
"""

import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments=None):
    payload = json.dumps(
        {
            "token": TOKEN,
            "command": command,
            "request_id": "test_v1_9",
            "arguments": arguments or {},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    header = f"{len(payload)}\n".encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.sendall(header + payload)
        line = b""
        while not line.endswith(b"\n"):
            chunk = sock.recv(1)
            if not chunk:
                raise RuntimeError("Không nhận được response header")
            line += chunk
        size = int(line.decode("utf-8").strip())
        body = b""
        while len(body) < size:
            chunk = sock.recv(size - len(body))
            if not chunk:
                raise RuntimeError("Kết nối đóng trước khi nhận đủ response")
            body += chunk
    return json.loads(body.decode("utf-8"))


def assert_ok(response):
    if response.get("ok") is False:
        raise AssertionError(response)


def main():
    before = request("get_model_state")
    assert_ok(before)
    before_state = before.get("model_state", before)
    revision = int(before_state["revision"])

    # A mutation that fails validation before entering the transaction must not
    # advance the revision. This is the public MCP-level abort/failure guard.
    failed = request(
        "create_box",
        {
            "width": 0,
            "depth": 100,
            "height": 100,
            "name": "v1.9_should_not_exist",
            "expected_model_revision": revision,
            "expected_model_session_id": before_state["model_session_id"],
        },
    )
    if failed.get("ok") is True:
        raise AssertionError("Expected create_box to fail validation")

    after = request("get_model_state")
    assert_ok(after)
    after_state = after.get("model_state", after)
    assert int(after_state["revision"]) == revision, {
        "before": before_state,
        "failed": failed,
        "after": after_state,
    }

    print("TRANSACTION ABORT REVISION v1.9: PASS")


if __name__ == "__main__":
    main()
