"""Live SketchUp integration test for mutation idempotency v2.2."""

import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments=None, request_id="test_v2_2"):
    payload = json.dumps(
        {
            "token": TOKEN,
            "command": command,
            "request_id": request_id,
            "arguments": arguments or {},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.sendall(f"{len(payload)}\n".encode("utf-8") + payload)
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


def model_state(response):
    assert_ok(response)
    return response.get("model_state", response)


def main():
    before = model_state(request("get_model_state", request_id="v2_2_state_before"))
    before_revision = int(before["revision"])
    session_id = before["model_session_id"]

    args = {
        "width": 30,
        "depth": 30,
        "height": 30,
        "name": "v2.2_idempotency_box",
        "expected_model_revision": before_revision,
        "expected_model_session_id": session_id,
    }

    request_id = "v2_2_create_once"
    first = request("create_box", args, request_id=request_id)
    assert_ok(first)
    assert first.get("idempotency", {}).get("status") == "stored", first
    first_revision = int(first["model_revision"])
    assert first_revision == before_revision + 1, first

    first_pid = first.get("entity", {}).get("persistent_id")
    assert first_pid, first

    second = request("create_box", args, request_id=request_id)
    assert_ok(second)
    assert second.get("idempotency", {}).get("status") == "replayed", second
    assert second.get("entity", {}).get("persistent_id") == first_pid, second
    assert int(second["model_revision"]) == first_revision, second

    after_replay = model_state(request("get_model_state", request_id="v2_2_state_after_replay"))
    assert int(after_replay["revision"]) == first_revision, after_replay

    conflict_args = dict(args)
    conflict_args["width"] = 40
    conflict = request("create_box", conflict_args, request_id=request_id)
    assert conflict.get("error", {}).get("code") == "IDEMPOTENCY_KEY_REUSE", conflict
    assert conflict.get("retry_safe") is False, conflict

    cleanup = request(
        "delete",
        {
            "persistent_ids": [first_pid],
            "expected_model_revision": first_revision,
            "expected_model_session_id": session_id,
        },
        request_id="v2_2_cleanup_delete",
    )
    assert_ok(cleanup)
    assert cleanup.get("idempotency", {}).get("status") == "stored", cleanup

    print("IDEMPOTENCY v2.2: PASS")


if __name__ == "__main__":
    main()
