"""Live SketchUp integration test for standardized transaction metadata v2.1.

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
            "request_id": f"test_v2_1_{command}",
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


def assert_transaction(response, expected_operation, before_revision):
    assert_ok(response)
    tx = response.get("transaction")
    assert isinstance(tx, dict), response
    assert tx.get("status") == "committed", response
    assert tx.get("operation") == expected_operation, response
    assert tx.get("revision_requested") is True, response
    assert tx.get("revision_request_count") == 1, response
    assert tx.get("revision_bumped") is True, response
    assert int(tx.get("revision_before")) == before_revision, response
    assert int(tx.get("revision_after")) == before_revision + 1, response
    assert int(tx.get("revision_delta")) == 1, response


def main():
    before = model_state(request("get_model_state"))
    before_revision = int(before["revision"])
    session_id = before["model_session_id"]

    created = request(
        "create_box",
        {
            "width": 30,
            "depth": 30,
            "height": 30,
            "name": "v2.1_transaction_metadata",
            "expected_model_revision": before_revision,
            "expected_model_session_id": session_id,
        },
    )
    assert_transaction(created, "AI - Create Box", before_revision)
    verification = created.get("verification", {})
    assert verification.get("verified") is True, created

    created_revision = int(created["transaction"]["revision_after"])
    persistent_id = created.get("entity", {}).get("persistent_id")
    assert persistent_id, created

    deleted = request(
        "delete",
        {
            "persistent_ids": [persistent_id],
            "expected_model_revision": created_revision,
            "expected_model_session_id": session_id,
        },
    )
    assert_transaction(deleted, "AI - Delete Entities", created_revision)
    verification = deleted.get("verification", {})
    assert verification.get("verified") is True, deleted

    final = model_state(request("get_model_state"))
    assert int(final["revision"]) == before_revision + 2, final
    assert final["model_session_id"] == session_id, final

    # Read-only responses must not inherit transaction metadata.
    ping = request("ping")
    assert_ok(ping)
    assert "transaction" not in ping, ping

    print("TRANSACTION METADATA v2.1: PASS")


if __name__ == "__main__":
    main()
