import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments, request_id):
    payload = json.dumps({"token": TOKEN, "command": command, "request_id": request_id, "arguments": arguments}).encode()
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.sendall(f"{len(payload)}\n".encode() + payload)
        line = b""
        while not line.endswith(b"\n"):
            chunk = sock.recv(1)
            if not chunk:
                raise RuntimeError("missing response header")
            line += chunk
        size = int(line.decode().strip())
        body = b""
        while len(body) < size:
            chunk = sock.recv(size - len(body))
            if not chunk:
                raise RuntimeError("short response")
            body += chunk
    return json.loads(body.decode())


def main():
    valid_plan = {
        "plan_id": "plan_v2_4_valid",
        "steps": [
            {"step_id": "step_1", "command": "get_model_state", "arguments": {}},
            {"step_id": "step_2", "command": "get_entities", "arguments": {"limit": 5}},
        ],
    }
    valid = request("validate_plan", {"plan": valid_plan}, "test_v2_4_valid")
    assert valid["ok"] is True, valid
    assert valid["plan_validation"]["valid"] is True, valid
    assert valid["plan_validation"]["contract_version"] == 1, valid
    assert valid["plan_validation"]["step_count"] == 2, valid

    invalid_plan = {
        "plan_id": "plan_v2_4_invalid",
        "steps": [{"step_id": "step_1", "command": "not_a_real_command", "arguments": {}}],
    }
    invalid = request("validate_plan", {"plan": invalid_plan}, "test_v2_4_invalid")
    assert invalid["ok"] is False, invalid
    assert invalid["error"]["code"] == "PLAN_INVALID", invalid
    assert invalid["plan_validation"]["valid"] is False, invalid
    assert any("không được đăng ký" in e for e in invalid["plan_validation"]["errors"]), invalid

    print("PLAN CONTRACT v2.4: PASS")


if __name__ == "__main__":
    main()
