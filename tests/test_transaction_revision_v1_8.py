"""Live SketchUp coverage for transaction-safe model revision semantics v1.8.

Run with SketchUp 2026 and the Tu SketchUp Agent bridge running.
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
            "request_id": f"test_v1_8_{command}",
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


def model_state(response):
    assert_ok(response)
    return response.get("model_state", response)


def main():
    before = model_state(request("get_model_state"))
    before_revision = int(before["revision"])
    session_id = before["model_session_id"]

    created = request(
        "create_box",
        {
            "width": 20,
            "depth": 20,
            "height": 20,
            "name": "v1.8_transaction_revision",
            "expected_model_revision": before_revision,
            "expected_model_session_id": session_id,
        },
    )
    assert_ok(created)
    verification = created.get("verification", {})
    assert verification.get("verified") is True, created
    transition = verification.get("model_state_transition", {})
    assert transition.get("revision_delta") == 1, created
    assert transition.get("session_id_unchanged") is True, created

    after = model_state(request("get_model_state"))
    after_revision = int(after["revision"])
    assert after_revision == before_revision + 1, (before, created, after)

    # A rejected stale request must not advance the revision because no
    # transaction is allowed to start for the guarded mutation.
    stale = request(
        "create_box",
        {
            "width": 20,
            "depth": 20,
            "height": 20,
            "name": "v1.8_should_not_exist",
            "expected_model_revision": before_revision,
            "expected_model_session_id": session_id,
        },
    )
    assert stale.get("error", {}).get("code") == "STALE_MODEL_STATE", stale

    unchanged = model_state(request("get_model_state"))
    assert int(unchanged["revision"]) == after_revision, unchanged

    persistent_id = (
        created.get("persistent_id")
        or created.get("entity", {}).get("persistent_id")
        or created.get("result", {}).get("persistent_id")
    )
    if persistent_id:
        cleanup = request(
            "delete",
            {
                "persistent_ids": [persistent_id],
                "expected_model_revision": after_revision,
                "expected_model_session_id": session_id,
            },
        )
        assert_ok(cleanup)
        cleanup_verification = cleanup.get("verification", {})
        assert cleanup_verification.get("verified") is True, cleanup
        cleanup_transition = cleanup_verification.get("model_state_transition", {})
        assert cleanup_transition.get("revision_delta") == 1, cleanup

    print("TRANSACTION REVISION v1.8: PASS")


if __name__ == "__main__":
    main()
