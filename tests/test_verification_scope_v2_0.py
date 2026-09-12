"""Live SketchUp integration test for verification scope v2.0."""

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
            "request_id": "test_v2_0_scope",
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


def main():
    state = request("get_model_state")
    assert_ok(state)
    current = state.get("model_state", state)

    guarded_ping = request(
        "ping",
        {
            "expected_model_revision": int(current["revision"]),
            "expected_model_session_id": current["model_session_id"],
        },
    )
    assert_ok(guarded_ping)
    assert "verification" not in guarded_ping, guarded_ping

    guarded_summary = request(
        "model_summary",
        {
            "expected_model_revision": int(current["revision"]),
            "expected_model_session_id": current["model_session_id"],
        },
    )
    assert_ok(guarded_summary)
    assert "verification" not in guarded_summary, guarded_summary

    final = request("get_model_state")
    assert_ok(final)
    final_state = final.get("model_state", final)
    assert int(final_state["revision"]) == int(current["revision"])

    print("VERIFICATION SCOPE v2.0: PASS")


if __name__ == "__main__":
    main()
