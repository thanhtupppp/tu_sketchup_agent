import json
import socket
import uuid

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments, request_id):
    payload = json.dumps({"token": TOKEN, "command": command, "request_id": request_id, "arguments": arguments}).encode()
    with socket.create_connection((HOST, PORT), timeout=15) as sock:
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
    suffix = uuid.uuid4().hex[:8]

    valid_plan = {
        "plan_id": f"preflight_valid_{suffix}",
        "steps": [
            {"step_id": "create", "command": "create_box", "arguments": {"width": 10, "depth": 20, "height": 30, "name": f"Preflight_{suffix}"}},
        ],
    }
    preflight = request("preflight_plan", {"plan": valid_plan}, f"v2_7_preflight_{suffix}")
    assert preflight.get("ok") is True, preflight
    assert preflight["plan_preflight"]["valid"] is True, preflight
    assert preflight["plan_preflight"]["contract_version"] == 1, preflight

    bad_args = {
        "plan_id": f"preflight_bad_{suffix}",
        "steps": [
            {"step_id": "create", "command": "create_box", "arguments": {"width": 10, "depth": 20}},
        ],
    }
    bad = request("preflight_plan", {"plan": bad_args}, f"v2_7_bad_{suffix}")
    assert bad.get("ok") is False, bad
    assert bad["error"]["code"] == "PLAN_PREFLIGHT_FAILED", bad
    assert any("height" in e for e in bad["plan_preflight"]["errors"]), bad

    missing_entity = {
        "plan_id": f"preflight_missing_{suffix}",
        "steps": [
            {"step_id": "move_missing", "command": "move", "arguments": {"ids": [999999999], "dx": 10, "dy": 0, "dz": 0}},
        ],
    }
    missing = request("preflight_plan", {"plan": missing_entity}, f"v2_7_missing_{suffix}")
    assert missing.get("ok") is False, missing
    assert missing["error"]["code"] == "PLAN_PREFLIGHT_FAILED", missing
    assert any("entity dependency" in e for e in missing["plan_preflight"]["errors"]), missing

    print("PLAN PREFLIGHT v2.7: PASS")


if __name__ == "__main__":
    main()
