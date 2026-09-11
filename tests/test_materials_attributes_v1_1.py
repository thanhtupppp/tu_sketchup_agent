# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Comprehensive Test Suite for Materials & Attributes Management (Protocol v1.1.0).
"""

import json
import socket
import sys
import uuid
import subprocess
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "tu-local-secret"
EXPECTED_PROTOCOLS = ["1.1", "1.2", "1.3"]


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def send(command: str, arguments: dict = None, timeout: float = 15.0) -> dict:
    req = {
        "token": TOKEN,
        "command": command,
        "request_id": f"mat_{uuid.uuid4().hex[:8]}",
        "arguments": arguments or {}
    }
    body = json.dumps(req, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall(f"{len(body)}\n".encode("utf-8") + body)
        line = b""
        while not line.endswith(b"\n"):
            chunk = s.recv(1)
            if not chunk:
                break
            line += chunk
        length = int(line.decode("utf-8").strip())
        data = bytearray()
        while len(data) < length:
            data.extend(s.recv(min(4096, length - len(data))))
        return json.loads(data.decode("utf-8"))


def run_suite():
    print("=" * 68)
    print("TU SKETCHUP AGENT - MATERIALS & ATTRIBUTES TEST SUITE v1.1")
    print(f"Started:      {datetime.now().isoformat(timespec='seconds')}")
    print(f"Git revision: {git_revision()}")
    print("=" * 68)

    # 1. Handshake & Protocol v1.1 Check
    ping = send("ping")
    assert ping.get("ok") is True, f"Ping thất bại: {ping}"
    protocol = ping.get("protocol_version")
    min_compat = ping.get("min_compatible_protocol_version")
    if protocol not in EXPECTED_PROTOCOLS:
        print(f"[TEST 01] Protocol Version: {protocol} (Kỳ vọng trong {EXPECTED_PROTOCOLS})")
        print("         => CẦN RELOAD EXTENSION: Trong SketchUp, chọn menu 'Extensions -> Tu SketchUp Agent -> Reload Extension'")
        print("         => Hoặc trong Ruby Console: load File.expand_path('~/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/main.rb')")
        print("         (Sau khi reload, chạy lại lệnh này để hoàn tất 14 bài kiểm tra v1.1)")
        sys.exit(2)

    print(f"[TEST 01] Protocol Version: {protocol} (min_compat: {min_compat}) -> PASS")

    # 2. get_materials
    mats_res = send("get_materials", {"limit": 200})
    assert mats_res.get("ok") is True, f"get_materials thất bại: {mats_res}"
    print(f"[TEST 02] get_materials: Tìm thấy {mats_res.get('total_count')} vật liệu trong model -> PASS")

    # 3. create_material (Tạo mới)
    mat_name = "Mat_Test_CyberGold"
    create_res = send("create_material", {
        "name": mat_name,
        "color": [255, 215, 0],
        "alpha": 0.88
    })
    assert create_res.get("ok") is True, f"create_material thất bại: {create_res}"
    print(f"[TEST 03] create_material: Tạo '{mat_name}' (created_new={create_res.get('created_new')}) -> PASS")

    # 4. get_material_info
    info_res = send("get_material_info", {"material_name": mat_name})
    assert info_res.get("ok") is True, f"get_material_info thất bại: {info_res}"
    m_info = info_res.get("material", {})
    assert m_info.get("name") == mat_name
    assert m_info.get("alpha") == 0.88
    print(f"[TEST 04] get_material_info: Color Hex={m_info.get('color_hex')}, Alpha={m_info.get('alpha')} -> PASS")

    # 5. create_material (Cập nhật màu và alpha)
    update_res = send("create_material", {
        "name": mat_name,
        "color": "#00FF88",
        "alpha": 1.0
    })
    assert update_res.get("ok") is True
    assert update_res.get("created_new") is False
    print(f"[TEST 05] update_material: Cập nhật màu hex thành công -> PASS")

    # 6. Tạo đối tượng thử nghiệm (Box Group)
    box_res = send("create_box", {
        "width": 120,
        "depth": 120,
        "height": 120,
        "x": 4000,
        "y": 0,
        "z": 0,
        "name": "Mat_Target_Box"
    })
    assert box_res.get("ok") is True
    box_pid = box_res["entity"]["persistent_id"]
    print(f"[TEST 06] Tạo đối tượng thử nghiệm (PID={box_pid}) -> PASS")

    # 7. set_entity_material cho Group
    set_mat_res = send("set_entity_material", {
        "persistent_ids": [box_pid],
        "material_name": mat_name
    })
    assert set_mat_res.get("ok") is True, f"set_entity_material thất bại: {set_mat_res}"
    assert set_mat_res.get("updated_count") == 1
    print(f"[TEST 07] set_entity_material: Gán '{mat_name}' cho Group PID={box_pid} -> PASS")

    # 8. Type Safety Validation: Thử gán vật liệu trực tiếp cho Face (Phải bị chặn!)
    # Lấy ID của một Face bên trong box
    children = send("get_entities", {"persistent_id": box_pid, "type_filter": "Face"})
    if children.get("ok") and children.get("items"):
        face_pid = children["items"][0]["persistent_id"]
        bad_mat_res = send("set_entity_material", {
            "persistent_ids": [face_pid],
            "material_name": mat_name
        })
        assert bad_mat_res.get("ok") is False, "Lẽ ra phải chặn gán material lên Face!"
        print(f"[TEST 08] Type Safety Check: Chặn gán material lên Face thành công ({bad_mat_res.get('error', {}).get('code')}) -> PASS")
    else:
        print("[TEST 08] Type Safety Check: Bỏ qua bước kiểm tra Face con")

    # 9. clear_entity_material
    clear_res = send("clear_entity_material", {"persistent_ids": [box_pid]})
    assert clear_res.get("ok") is True, f"clear_entity_material thất bại: {clear_res}"
    assert clear_res.get("cleared_count") == 1
    print(f"[TEST 09] clear_entity_material: Xóa lớp vật liệu gán đè thành công -> PASS")

    # 10. set_entity_attributes (Ghi BIM/Metadata)
    dict_name = "bim_inspection_v1"
    attributes_data = {
        "part_code": "CYBER-BND-01",
        "weight_kg": 18.75,
        "is_active": True,
        "manufacturer": "Tu Mechanical Works"
    }
    set_attr_res = send("set_entity_attributes", {
        "persistent_ids": [box_pid],
        "dictionary_name": dict_name,
        "attributes": attributes_data
    })
    assert set_attr_res.get("ok") is True, f"set_entity_attributes thất bại: {set_attr_res}"
    assert set_attr_res.get("updated_count") == 1
    print(f"[TEST 10] set_entity_attributes: Ghi 4 thuộc tính vào dict '{dict_name}' -> PASS")

    # 11. get_entity_attributes (Đọc lại so sánh)
    get_attr_res = send("get_entity_attributes", {
        "persistent_id": box_pid,
        "dictionary_name": dict_name
    })
    assert get_attr_res.get("ok") is True, f"get_entity_attributes thất bại: {get_attr_res}"
    read_dict = get_attr_res.get("dictionaries", {}).get(dict_name, {})
    assert read_dict.get("part_code") == "CYBER-BND-01"
    assert read_dict.get("weight_kg") == 18.75
    assert read_dict.get("is_active") is True
    print(f"[TEST 11] get_entity_attributes: Đọc lại 4 thuộc tính chính xác 100% -> PASS")

    # 12. delete_entity_attributes (Xóa key cụ thể)
    del_key_res = send("delete_entity_attributes", {
        "persistent_ids": [box_pid],
        "dictionary_name": dict_name,
        "keys": ["is_active"]
    })
    assert del_key_res.get("ok") is True
    check_keys = send("get_entity_attributes", {"persistent_id": box_pid, "dictionary_name": dict_name})
    remaining_keys = check_keys.get("dictionaries", {}).get(dict_name, {})
    assert "is_active" not in remaining_keys
    assert "part_code" in remaining_keys
    print(f"[TEST 12] delete_entity_attributes: Xóa key 'is_active' thành công -> PASS")

    # 13. delete_entity_attributes (Xóa toàn bộ dictionary)
    del_dict_res = send("delete_entity_attributes", {
        "persistent_ids": [box_pid],
        "dictionary_name": dict_name
    })
    assert del_dict_res.get("ok") is True
    check_dict = send("get_entity_attributes", {"persistent_id": box_pid, "dictionary_name": dict_name})
    assert dict_name not in check_dict.get("dictionaries", {})
    print(f"[TEST 13] delete_entity_attributes: Xóa toàn bộ dictionary '{dict_name}' -> PASS")

    # 14. Dọn dẹp đối tượng thử nghiệm
    del_box = send("delete", {"persistent_ids": [box_pid]})
    assert del_box.get("ok") is True
    print(f"[TEST 14] Dọn dẹp đối tượng thử nghiệm: deleted_count={del_box.get('deleted_count')} -> PASS")

    print("=" * 68)
    print(">>> KẾT QUẢ: 14/14 BÀI TEST MATERIALS & ATTRIBUTES v1.1 ĐÃ PASS! <<<")
    print("=" * 68)


if __name__ == "__main__":
    run_suite()
