"""Live SketchUp integration coverage for optimistic model-state guards v1.6.

Run inside an environment where SketchUp 2026 and the Tu SketchUp Agent bridge are running.
"""

import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(method, params=None):
    payload = json.dumps({"token": TOKEN, "method": method, "params": params or {}}, ensure_ascii=False).encode("utf-8")
    packet = len(payload).to_bytes(4, "big") + payload
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.sendall(packet)
        header = sock.recv(4)
        if len(header) != 4:
            raise RuntimeError("Không nhận được response header")
        size = int.from_bytes(header, "big")
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
    current = state["result"]
    revision = int(current["revision"])
    session_id = current["model_session_id"]

    # Valid guard must allow mutation and advance revision exactly once.
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

    created_state = request("get_model_state")
    assert_ok(created_state)
    after_create = created_state["result"]
    assert int(after_create["revision"]) == revision + 1

    # Wrong session must be rejected before handler execution.
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

    # Stale revision must be rejected and must not bump revision.
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
    assert int(final_state["result"]["revision"]) == int(after_create["revision"])

    # Clean up the test object without a guard so cleanup cannot be blocked by the assertions above.
    created_result = created.get("result", {})
    ids = created_result.get("persistent_ids") or created_result.get("persistent_id")
    if ids:
        if not isinstance(ids, list):
            ids = [ids]
        request("delete", {"persistent_ids": ids})

    print("MODEL STATE GUARD v1.6: PASS")


if __name__ == "__main__":
    main()
