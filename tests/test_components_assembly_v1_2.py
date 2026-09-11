# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Comprehensive Test Suite for Component & Assembly Management (Protocol v1.2).
Validates 6 new tools on live SketchUp 2026 instance.
"""

import json
import os
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
EXPECTED_PROTOCOL = "1.2"


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
        "request_id": f"comp_{uuid.uuid4().hex[:8]}",
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
    print("=" * 70)
    print("  TU SKETCHUP AGENT - COMPONENT & ASSEMBLY TEST SUITE (v1.2)")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Git commit: {git_revision()}")
    print("-" * 70)

    # 1. Handshake & Protocol v1.2 Check
    ping = send("ping")
    assert ping.get("ok") is True, f"Ping thất bại: {ping}"
    protocol = ping.get("protocol_version")
    min_compat = ping.get("min_compatible_protocol_version")
    if protocol != EXPECTED_PROTOCOL:
        print(f"[TEST 01] Protocol Version: {protocol} (Kỳ vọng: {EXPECTED_PROTOCOL})")
        print("         => CẦN RELOAD EXTENSION: Trong SketchUp, chọn menu 'Extensions -> Tu SketchUp Agent -> Reload Extension'")
        print("         => Hoặc trong Ruby Console: load File.expand_path('~/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/main.rb')")
        print("         (Sau khi reload, chạy lại lệnh này để hoàn tất 14 bài kiểm tra v1.2)")
        sys.exit(2)

    print(f"[TEST 01] Protocol Version: {protocol} (min_compat: {min_compat}) -> PASS")

    created_pids = []
    temp_files = []

    try:
        # 2. Tạo hình học nền tảng (Box 100x100x50 mm)
        box_res = send("create_box", {"width": 100, "depth": 100, "height": 50, "name": "Box_For_Component"})
        assert box_res.get("ok") is True, f"create_box thất bại: {box_res}"
        box_pid = box_res.get("persistent_id") or box_res.get("entity", {}).get("persistent_id")
        assert box_pid, f"Thiếu persistent_id cho Box: {box_res}"
        print(f"[TEST 02] create_box: Tạo Box (PID: {box_pid}) -> PASS")

        # 3. create_component biến Box thành Definition "Comp_Test_Roller"
        comp_res = send("create_component", {
            "persistent_ids": [box_pid],
            "name": "Comp_Test_Roller",
            "description": "Test Roller Bearing Part"
        })
        assert comp_res.get("ok") is True, f"create_component thất bại: {comp_res}"
        defn_info = comp_res.get("definition", {})
        assert defn_info.get("name") == "Comp_Test_Roller", f"Tên definition sai: {defn_info}"
        assert defn_info.get("guid"), "Thiếu definition GUID"
        inst_info = comp_res.get("instance", {})
        inst1_pid = inst_info.get("persistent_id")
        assert inst1_pid, "Thiếu instance persistent_id"
        created_pids.append(inst1_pid)
        print(f"[TEST 03] create_component: Đã tạo Definition '{defn_info['name']}' (Instance PID: {inst1_pid}) -> PASS")

        # 4. get_component_definitions xác nhận tìm thấy definition mới
        list_res = send("get_component_definitions", {"name_filter": "roller"})
        assert list_res.get("ok") is True, f"get_component_definitions thất bại: {list_res}"
        names = [d["name"] for d in list_res.get("definitions", [])]
        assert "Comp_Test_Roller" in names, f"Không tìm thấy Comp_Test_Roller trong {names}"
        print(f"[TEST 04] get_component_definitions: Tìm thấy {list_res.get('total_count')} definitions phù hợp -> PASS")

        # 5. place_component_instance với tham số trực quan (position & rotation)
        place_res1 = send("place_component_instance", {
            "definition_name": "Comp_Test_Roller",
            "position": [200, 300, 0],
            "rotation": {"axis": "z", "angle": 45.0},
            "scale": 1.0,
            "instance_name": "Roller_Inst_Visual"
        })
        assert place_res1.get("ok") is True, f"place_component_instance (visual) thất bại: {place_res1}"
        inst2_pid = place_res1.get("instance", {}).get("persistent_id")
        assert inst2_pid, "Thiếu instance persistent_id cho visual placement"
        created_pids.append(inst2_pid)
        print(f"[TEST 05] place_component_instance (Visual transform): Instance PID {inst2_pid} -> PASS")

        # 6. place_component_instance với ma trận 4x4 raw (OpenGL column-major)
        # Translation matrix at (400, 100, 0) mm => inches: 400/25.4 = 15.748...
        # But wait, in SketchUp transformation matrix constructor:
        # Geom::Transformation.new(array16) expects inches!
        # Let's test standard 16 floats identity with translation or let's use identity matrix:
        # [1,0,0,0, 0,1,0,0, 0,0,1,0, 400/25.4, 100/25.4, 0, 1]
        tx_in = 400.0 / 25.4
        ty_in = 100.0 / 25.4
        mat4x4 = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            tx_in, ty_in, 0.0, 1.0
        ]
        place_res2 = send("place_component_instance", {
            "definition_name": "Comp_Test_Roller",
            "matrix": mat4x4,
            "instance_name": "Roller_Inst_Matrix"
        })
        assert place_res2.get("ok") is True, f"place_component_instance (raw matrix) thất bại: {place_res2}"
        inst3_pid = place_res2.get("instance", {}).get("persistent_id")
        assert inst3_pid, "Thiếu instance persistent_id cho matrix placement"
        created_pids.append(inst3_pid)
        print(f"[TEST 06] place_component_instance (Raw 4x4 matrix): Instance PID {inst3_pid} -> PASS")

        # 7. place_component_instance lồng vào Sub-assembly (parent_id)
        chassis_res = send("create_box", {"width": 500, "depth": 500, "height": 30, "name": "Assembly_Chassis"})
        assert chassis_res.get("ok") is True, f"Tạo Chassis thất bại: {chassis_res}"
        chassis_pid = chassis_res.get("persistent_id") or chassis_res.get("entity", {}).get("persistent_id")
        assert chassis_pid, f"Thiếu persistent_id cho Chassis: {chassis_res}"
        created_pids.append(chassis_pid)

        sub_res = send("place_component_instance", {
            "definition_name": "Comp_Test_Roller",
            "parent_id": chassis_pid,
            "position": [50, 50, 30],
            "instance_name": "Chassis_Mounted_Roller"
        })
        assert sub_res.get("ok") is True, f"place_component_instance vào parent_id thất bại: {sub_res}"
        print(f"[TEST 07] place_component_instance (Sub-assembly in parent PID {chassis_pid}) -> PASS")

        # 8. make_component_unique trên inst2_pid
        unique_res = send("make_component_unique", {
            "persistent_ids": [inst2_pid],
            "new_name": "Comp_Test_Roller_Unique"
        })
        assert unique_res.get("ok") is True, f"make_component_unique thất bại: {unique_res}"
        assert unique_res.get("new_definition_name") == "Comp_Test_Roller_Unique", f"Tên definition mới sai: {unique_res}"
        print(f"[TEST 08] make_component_unique: Instance {inst2_pid} thành '{unique_res.get('new_definition_name')}' -> PASS")

        # 9. Kiểm tra tính độc lập của 2 definition
        defs_check = send("get_component_definitions", {"name_filter": "roller"})
        found_names = [d["name"] for d in defs_check.get("definitions", [])]
        assert "Comp_Test_Roller" in found_names, "Definition gốc bị mất"
        assert "Comp_Test_Roller_Unique" in found_names, "Definition unique mới không xuất hiện"
        print(f"[TEST 09] Verify definition independence: Cả 2 definitions đều tồn tại độc lập -> PASS")

        # 10. save_component_to_skp xuất ra tệp
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
        os.makedirs(test_dir, exist_ok=True)
        skp_path = os.path.abspath(os.path.join(test_dir, "test_roller_export.skp")).replace("\\", "/")
        temp_files.append(skp_path)

        if os.path.exists(skp_path):
            os.remove(skp_path)

        save_res = send("save_component_to_skp", {
            "definition_name": "Comp_Test_Roller",
            "file_path": skp_path,
            "overwrite": True
        })
        assert save_res.get("ok") is True, f"save_component_to_skp thất bại: {save_res}"
        assert os.path.exists(skp_path), f"Tệp .skp không tồn tại trên đĩa: {skp_path}"
        assert os.path.getsize(skp_path) > 0, "Tệp .skp có kích thước 0 byte"
        print(f"[TEST 10] save_component_to_skp: Xuất thành công '{skp_path}' ({os.path.getsize(skp_path)} bytes) -> PASS")

        # 11. load_component_from_skp nạp lại tệp thành definition mới
        load_res = send("load_component_from_skp", {
            "file_path": skp_path,
            "definition_name": "Comp_Imported_Roller"
        })
        assert load_res.get("ok") is True, f"load_component_from_skp thất bại: {load_res}"
        loaded_name = load_res.get("definition", {}).get("name")
        assert loaded_name == "Comp_Imported_Roller", f"Tên nạp vào sai: {loaded_name}"
        print(f"[TEST 11] load_component_from_skp: Nạp thành công definition '{loaded_name}' -> PASS")

        # 12. place_component_instance cho component vừa nạp
        place_imported = send("place_component_instance", {
            "definition_name": "Comp_Imported_Roller",
            "position": [600, 0, 0],
            "instance_name": "Imported_Roller_Inst"
        })
        assert place_imported.get("ok") is True, f"Chèn instance component nạp thất bại: {place_imported}"
        imported_inst_pid = place_imported.get("instance", {}).get("persistent_id")
        assert imported_inst_pid, "Thiếu persistent_id"
        created_pids.append(imported_inst_pid)
        print(f"[TEST 12] place_component_instance (Imported Definition): PID {imported_inst_pid} -> PASS")

        # 13. Error Handling
        err_place = send("place_component_instance", {"definition_name": "Non_Existent_Definition_XYZ"})
        assert err_place.get("ok") is False, "Kỳ vọng lỗi khi chèn definition không tồn tại"

        err_load = send("load_component_from_skp", {"file_path": "C:/invalid_file_path_12345.skp"})
        assert err_load.get("ok") is False, "Kỳ vọng lỗi khi nạp file không tồn tại"

        err_ext = send("load_component_from_skp", {"file_path": __file__})
        assert err_ext.get("ok") is False, "Kỳ vọng lỗi khi nạp file không phải đuôi .skp"
        print(f"[TEST 13] Error Handling (Non-existent definition, missing file, non-skp extension) -> PASS")

        # 14. Dọn dẹp đối tượng test
        del_res = send("delete", {"persistent_ids": created_pids})
        assert del_res.get("ok") is True, f"Dọn dẹp thất bại: {del_res}"
        print(f"[TEST 14] Cleanup: Đã xóa {del_res.get('deleted_count')} đối tượng thử nghiệm -> PASS")

    finally:
        for fpath in temp_files:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    print("-" * 70)
    print("KẾT QUẢ: 14/14 BÀI TEST COMPONENT & ASSEMBLY v1.2 ĐÃ VƯỢT QUA!")
    print("=" * 70)


if __name__ == "__main__":
    run_suite()
