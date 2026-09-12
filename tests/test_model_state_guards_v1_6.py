"""Live SketchUp integration coverage for optimistic model-state guards v1.6.

Run inside an environment where SketchUp 2026 and the Tu SketchUp Agent bridge are running.
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
            "request_id": "test_v1_6",
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
    state = request("get_model_state")
    assert_ok(state)
    current = state.get("model_state", state)
    revision = int(current["revision"])
    session_id = current["model_session_id"]

    created = request(
        "create_box",
        {
            "width": 10,
            "depth": 10,
            "height": 10,
            "name": "v1.6_guard_test",
            "expected_model_revision": revision,
            "expected_model_session_id": session_id,
        },
    )
    assert_ok(created)
    verification = created.get("verification", {})
    assert verification.get("verified") is True, created
    assert verification.get("entity_postcondition", {}).get("verified") is True, created
    assert verification.get("property_postcondition", {}).get("verified") is True, created

    created_state = request("get_model_state")
    assert_ok(created_state)
    after_create = created_state.get("model_state", created_state)
    assert int(after_create["revision"]) == revision + 1

    wrong_session = request(
        "create_box",
        {
            "width": 10,
            "depth": 10,
            "height": 10,
            "name": "v1.6_wrong_session",
            "expected_model_revision": int(after_create["revision"]),
            "expected_model_session_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert wrong_session.get("error", {}).get("code") == "STALE_MODEL_STATE", wrong_session

    stale = request(
        "create_box",
        {
            "width": 10,
            "depth": 10,
            "height": 10,
            "name": "v1.6_stale_revision",
            "expected_model_revision": revision,
            "expected_model_session_id": session_id,
        },
    )
    assert stale.get("error", {}).get("code") == "STALE_MODEL_STATE", stale

    final_state = request("get_model_state")
    assert_ok(final_state)
    final_curr = final_state.get("model_state", final_state)
    assert int(final_curr["revision"]) == int(after_create["revision"])

    persistent_id = created.get("persistent_id") or created.get("entity", {}).get("persistent_id") or created.get("result", {}).get("persistent_id")
    if persistent_id:
        request("delete", {"persistent_ids": [persistent_id]})

    print("MODEL STATE GUARD v1.6: PASS")


if __name__ == "__main__":
    main()
