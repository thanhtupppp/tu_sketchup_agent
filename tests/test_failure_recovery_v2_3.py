"""Live SketchUp coverage for failure classification/recovery contract v2.3."""

import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments=None, token=TOKEN, request_id="test_v2_3"):
    payload = json.dumps(
        {
            "token": token,
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


def assert_recovery(response, code, action):
    assert response.get("ok") is False, response
    assert response.get("error", {}).get("code") == code, response
    recovery = response.get("recovery", {})
    assert recovery.get("contract_version") == 1, response
    assert recovery.get("action") == action, response
    assert recovery.get("retry_safe") is False, response
    return recovery


def main():
    state = request("get_model_state", request_id="test_v2_3_state")
    assert state.get("ok") is True, state
    model_state = state.get("model_state", state)
    revision = int(model_state["revision"])
    session_id = model_state["model_session_id"]

    stale = request(
        "create_box",
        {
            "width": 10,
            "depth": 10,
            "height": 10,
            "expected_model_revision": revision - 1,
            "expected_model_session_id": session_id,
        },
        request_id="test_v2_3_stale",
    )
    recovery = assert_recovery(stale, "STALE_MODEL_STATE", "REFRESH_MODEL_STATE")
    assert recovery.get("mutation_committed") is False, stale
    assert recovery.get("retry_after") == "refresh_model_state", stale

    unauthorized = request(
        "ping",
        token="wrong-token",
        request_id="test_v2_3_unauthorized",
    )
    assert_recovery(unauthorized, "UNAUTHORIZED", "CHECK_AUTHENTICATION")

    unknown = request(
        "definitely_unknown_command",
        request_id="test_v2_3_unknown",
    )
    assert_recovery(unknown, "UNKNOWN_COMMAND", "USE_SUPPORTED_COMMAND")

    print("FAILURE RECOVERY v2.3: PASS")


if __name__ == "__main__":
    main()
