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
    plan_id = f"compat_v2_6_{suffix}"
    plan = {
        "plan_id": plan_id,
        "steps": [
            {"step_id": "state_1", "command": "get_model_state", "arguments": {}},
        ],
    }

    executed = request("execute_plan", {"plan": plan, "resume": False}, f"compat_execute_{suffix}")
    assert executed.get("ok") is True, executed
    assert executed.get("status") == "completed", executed
    assert executed.get("checkpoint", {}).get("status") == "completed", executed

    resumed = request("execute_plan", {"plan": plan, "resume": True}, f"compat_resume_{suffix}")
    assert resumed.get("ok") is True, resumed
    assert resumed.get("status") == "completed", resumed
    assert resumed.get("resumed") is True, resumed
    assert resumed.get("resumed_from_step_index") == 1, resumed
    assert resumed.get("step_count") == 1, resumed
    assert resumed.get("checkpoint", {}).get("status") == "completed", resumed
    assert resumed.get("steps") == [], resumed

    print("PLAN EXECUTOR COMPAT v2.6: PASS")


if __name__ == "__main__":
    main()
