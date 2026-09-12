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
    name = f"PlanExecutorTest_{suffix}"

    plan = {
        "plan_id": f"plan_v2_5_{suffix}",
        "steps": [
            {"step_id": "state_1", "command": "get_model_state", "arguments": {}},
            {"step_id": "create_1", "command": "create_box", "arguments": {
                "width": 10, "depth": 20, "height": 30,
                "x": 100, "y": 100, "z": 0, "name": name
            }},
            {"step_id": "state_2", "command": "get_model_state", "arguments": {}},
        ],
    }

    valid = request("validate_plan", {"plan": plan}, f"v2_5_validate_{suffix}")
    assert valid.get("ok") is True, valid

    executed = request("execute_plan", {"plan": plan}, f"v2_5_execute_{suffix}")
    assert executed.get("ok") is True, executed
    assert executed.get("status") == "completed", executed
    assert executed.get("step_count") == 3, executed
    assert all(step.get("ok") is True for step in executed.get("steps", [])), executed

    created = executed["steps"][1]["response"]
    entity = created.get("entity", {})
    persistent_id = entity.get("persistent_id")
    assert persistent_id is not None, executed

    # A failing step must stop the plan and prevent later steps from running.
    fail_plan = {
        "plan_id": f"plan_v2_5_fail_{suffix}",
        "steps": [
            {"step_id": "fail_1", "command": "create_box", "arguments": {
                "width": 10, "depth": 10, "height": 10,
                "name": f"PlanExecutorFail_{suffix}"
            }},
            {"step_id": "fail_2", "command": "create_box", "arguments": {
                "width": 0, "depth": 10, "height": 10,
                "name": f"MustNotRun_{suffix}"
            }},
            {"step_id": "fail_3", "command": "create_box", "arguments": {
                "width": 10, "depth": 10, "height": 10,
                "name": f"MustAlsoNotRun_{suffix}"
            }},
        ],
    }
    failed = request("execute_plan", {"plan": fail_plan}, f"v2_5_fail_{suffix}")
    assert failed.get("ok") is False, failed
    assert failed.get("error", {}).get("code") == "PLAN_STEP_FAILED", failed
    assert failed.get("failed_step_index") == 1, failed
    assert len(failed.get("steps", [])) == 2, failed
    assert failed["steps"][0]["ok"] is True, failed
    assert failed["steps"][1]["ok"] is False, failed
    assert failed["recovery"]["retry_safe"] is False, failed

    # Cleanup the successful test object and the first failed-plan object.
    for step_index in (1,):
        step_response = failed["steps"][step_index]["response"] if failed["steps"][step_index]["ok"] else failed["steps"][0]["response"]
        cleanup_entity = step_response.get("entity", {})
        cleanup_pid = cleanup_entity.get("persistent_id")
        if cleanup_pid is not None:
            cleanup = request(
                "delete",
                {"persistent_ids": [cleanup_pid]},
                f"v2_5_cleanup_{suffix}_{step_index}",
            )
            assert cleanup.get("ok") is True, cleanup

    cleanup = request(
        "delete",
        {"persistent_ids": [persistent_id]},
        f"v2_5_cleanup_created_{suffix}",
    )
    assert cleanup.get("ok") is True, cleanup

    print("PLAN EXECUTOR v2.5: PASS")


if __name__ == "__main__":
    main()
