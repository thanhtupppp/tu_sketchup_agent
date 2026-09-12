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
    plan_id = f"plan_v2_6_{suffix}"
    name = f"CheckpointTest_{suffix}"

    # First execution creates one object and records a checkpoint for every step.
    plan = {
        "plan_id": plan_id,
        "steps": [
            {"step_id": "create_1", "command": "create_box", "arguments": {
                "width": 10, "depth": 20, "height": 30,
                "x": 200, "y": 200, "z": 0, "name": name
            }},
        ],
    }
    executed = request("execute_plan", {"plan": plan}, f"v2_6_execute_{suffix}")
    assert executed.get("ok") is True, executed
    assert executed.get("checkpoint", {}).get("status") == "completed", executed
    assert executed["checkpoint"]["completed_count"] == 1, executed

    # Resume a completed plan: no step should execute again.
    resumed = request("execute_plan", {"plan": plan, "resume": True}, f"v2_6_resume_{suffix}")
    assert resumed.get("ok") is True, resumed
    assert resumed.get("status") == "completed", resumed
    assert resumed.get("resumed") is True, resumed
    assert resumed.get("resumed_from_step_index") == 1, resumed
    assert resumed.get("steps") == [], resumed

    # A changed model revision invalidates the checkpoint and blocks blind resume.
    state = request("get_model_state", {}, f"v2_6_state_{suffix}")
    assert state.get("ok") is True, state
    state_obj = state.get("model_state", state)
    assert int(state_obj["revision"]) >= int(executed["checkpoint"]["model_revision"]), state

    mutate = request("create_box", {
        "width": 5, "depth": 5, "height": 5,
        "x": 500, "y": 500, "z": 0, "name": f"CheckpointMutation_{suffix}"
    }, f"v2_6_mutate_{suffix}")
    assert mutate.get("ok") is True, mutate

    stale_resume = request("execute_plan", {"plan": plan, "resume": True}, f"v2_6_stale_resume_{suffix}")
    assert stale_resume.get("ok") is False, stale_resume
    assert stale_resume.get("error", {}).get("code") == "PLAN_CHECKPOINT_STALE", stale_resume
    assert stale_resume.get("recovery", {}).get("retry_safe") is False, stale_resume

    # Clean up the test-created entities.
    ids = []
    first_entity = executed["steps"][0]["response"].get("entity", {})
    if first_entity.get("persistent_id") is not None:
        ids.append(first_entity["persistent_id"])
    mutation_entity = mutate.get("entity", {})
    if mutation_entity.get("persistent_id") is not None:
        ids.append(mutation_entity["persistent_id"])
    for i, pid in enumerate(ids):
        cleanup = request("delete", {"persistent_ids": [pid]}, f"v2_6_cleanup_{suffix}_{i}")
        assert cleanup.get("ok") is True, cleanup

    print("PLAN CHECKPOINT v2.6: PASS")


if __name__ == "__main__":
    main()
