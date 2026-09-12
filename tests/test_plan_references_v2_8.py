import json
import socket
import uuid

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"


def request(command, arguments, request_id):
    payload = json.dumps({"token": TOKEN, "command": command, "request_id": request_id, "arguments": arguments}).encode()
    with socket.create_connection((HOST, PORT), timeout=20) as sock:
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
    name = f"ReferenceTest_{suffix}"
    plan_id = f"plan_v2_8_{suffix}"

    plan = {
        "plan_id": plan_id,
        "steps": [
            {
                "step_id": "create",
                "command": "create_box",
                "arguments": {
                    "width": 10,
                    "depth": 20,
                    "height": 30,
                    "x": 100,
                    "y": 100,
                    "z": 0,
                    "name": name,
                },
            },
            {
                "step_id": "move",
                "command": "move",
                "arguments": {
                    "ids": ["$ref:create.entity.persistent_id"],
                    "dx": 50,
                    "dy": 0,
                    "dz": 0,
                },
            },
            {
                "step_id": "delete",
                "command": "delete",
                "arguments": {
                    "persistent_ids": ["$ref:create.entity.persistent_id"],
                },
            },
        ],
    }

    preflight = request("preflight_plan", {"plan": plan}, f"v2_8_preflight_{suffix}")
    assert preflight.get("ok") is True, preflight
    pf = preflight["plan_preflight"]
    assert pf["valid"] is True, preflight
    assert pf["contract_version"] == 2, preflight
    assert pf["reference_validation"]["valid"] is True, preflight

    executed = request("execute_plan", {"plan": plan}, f"v2_8_execute_{suffix}")
    assert executed.get("ok") is True, executed
    assert executed.get("status") == "completed", executed
    assert executed.get("step_count") == 3, executed
    assert all(item.get("ok") is True for item in executed.get("steps", [])), executed

    created = executed["steps"][0]["response"]["entity"]
    moved = executed["steps"][1]["response"]
    deleted = executed["steps"][2]["response"]
    pid = created.get("persistent_id")
    assert pid is not None, executed
    assert moved.get("moved_count") == 1, executed
    assert deleted.get("deleted_count") == 1, executed

    bad_plan = {
        "plan_id": f"bad_{suffix}",
        "steps": [
            {"step_id": "a", "command": "create_box", "arguments": {
                "width": 10, "depth": 10, "height": 10, "name": f"BadRef_{suffix}"
            }},
            {"step_id": "b", "command": "move", "arguments": {
                "ids": ["$ref:missing.entity.persistent_id"], "dx": 10, "dy": 0, "dz": 0
            }},
        ],
    }
    bad = request("preflight_plan", {"plan": bad_plan}, f"v2_8_bad_{suffix}")
    assert bad.get("ok") is False, bad
    assert bad["error"]["code"] == "PLAN_PREFLIGHT_FAILED", bad
    assert any("không tìm thấy step" in e for e in bad["plan_preflight"]["errors"]), bad

    print("PLAN REFERENCES v2.8: PASS")


if __name__ == "__main__":
    main()
