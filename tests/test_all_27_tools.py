# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.3.0", "pillow>=10.0.0"]
# ///
"""
End-to-End Test Suite for All 27 MCP Tools of TuSketchupAgent.
Validates each individual tool against the live SketchUp 2026 instance.
"""

import sys
import os
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mcp_server


def test_group1_system():
    print("================== NHÓM 1: HỆ THỐNG & KẾT NỐI ==================")
    # 1. ping
    r1 = json.loads(mcp_server.sketchup_ping())
    print(f"[TOOL 01] sketchup_ping: ok={r1.get('ok')}, protocol={r1.get('protocol_version')}, su_ver={r1.get('sketchup_version')}")
    assert r1.get('ok') is True

    # 2. model_info
    r2 = json.loads(mcp_server.sketchup_get_model_info())
    print(f"[TOOL 02] sketchup_get_model_info: ok={r2.get('ok')}, revision={r2.get('model_revision')}, entities={r2.get('entity_count')}, bounds={r2.get('bounds_mm')}")
    assert r2.get('ok') is True

    # 3. selection
    r3 = json.loads(mcp_server.sketchup_get_selection())
    print(f"[TOOL 03] sketchup_get_selection: ok={r3.get('ok')}, count={r3.get('count')}")
    assert r3.get('ok') is True

    # 4. zoom_extents
    r4 = json.loads(mcp_server.sketchup_zoom_extents())
    print(f"[TOOL 04] sketchup_zoom_extents: ok={r4.get('ok')}, op={r4.get('operation')}")
    assert r4.get('ok') is True

    # 5. capture_viewport
    r5 = mcp_server.sketchup_capture_viewport(width=640, height=360)
    print(f"[TOOL 05] sketchup_capture_viewport: bytes={len(r5.data)} -> PNG generated successfully")
    assert len(r5.data) > 0
    print(">>> NHÓM 1 HOÀN TẤT 5/5 TOOLS: PASS <<<\n")


def test_group2_parametric_creation():
    print("================== NHÓM 2: DỰNG HÌNH CƠ BẢN ==================")
    # 6. create_box
    r6 = json.loads(mcp_server.sketchup_create_box(width=200, depth=300, height=400, name="Box_T06"))
    print(f"[TOOL 06] sketchup_create_box: ok={r6.get('ok')}, pid={r6.get('entity', {}).get('persistent_id')}, dims={r6.get('dimensions_mm')}")
    assert r6.get('ok') is True
    box_pid = r6.get('entity', {}).get('persistent_id')

    # 7. create_cylinder
    r7 = json.loads(mcp_server.sketchup_create_cylinder(radius=100, height=350, segments=24, x=500, y=0, z=0, name="Cyl_T07"))
    print(f"[TOOL 07] sketchup_create_cylinder: ok={r7.get('ok')}, pid={r7.get('entity', {}).get('persistent_id')}, radius={r7.get('radius_mm')}")
    assert r7.get('ok') is True
    cyl_pid = r7.get('entity', {}).get('persistent_id')

    # 8. create_wall
    r8 = json.loads(mcp_server.sketchup_create_wall(start_x=0, start_y=1000, end_x=1500, end_y=1000, thickness=120, height=2400, name="Wall_T08"))
    assert r8.get('ok') is True
    wall_pid = r8.get('entity', {}).get('persistent_id')
    print(f"[TOOL 08] sketchup_create_wall: ok={r8.get('ok')}, pid={wall_pid}, length={r8.get('length_mm')}")

    print(">>> NHÓM 2 HOÀN TẤT 3/3 TOOLS: PASS <<<\n")
    return box_pid, cyl_pid, wall_pid


def test_group3_geometry_inspection(box_pid, cyl_pid, wall_pid):
    print("================== NHÓM 3: TRUY VẤN HÌNH HỌC & ĐỐI TƯỢNG ==================")
    # 9. get_entities (model level)
    r9 = json.loads(mcp_server.sketchup_get_entities())
    print(f"[TOOL 09] sketchup_get_entities (model level): ok={r9.get('ok')}, total_count={r9.get('total_count')}")
    assert r9.get('ok') is True

    # 9b. get_entities inside box (children faces/edges)
    r9b = json.loads(mcp_server.sketchup_get_entities(persistent_id=box_pid, type_filter="Face"))
    print(f"[TOOL 09b] sketchup_get_entities (inside Box, filter=Face): ok={r9b.get('ok')}, faces={r9b.get('returned_count')}")
    assert r9b.get('ok') is True and r9b.get('returned_count') == 6

    # 10. get_entity_info
    r10 = json.loads(mcp_server.sketchup_get_entity_info(persistent_id=box_pid))
    print(f"[TOOL 10] sketchup_get_entity_info: ok={r10.get('ok')}, name='{r10.get('entity', {}).get('name')}', type={r10.get('entity', {}).get('type')}")
    assert r10.get('ok') is True

    # 11. get_bounding_box
    r11 = json.loads(mcp_server.sketchup_get_bounding_box(persistent_ids=[box_pid, cyl_pid]))
    print(f"[TOOL 11] sketchup_get_bounding_box: ok={r11.get('ok')}, combined_bounds={r11.get('bounds_mm')}")
    assert r11.get('ok') is True

    print(">>> NHÓM 3 HOÀN TẤT 3/3 TOOLS: PASS <<<\n")


def test_group4_transformation_hierarchy(box_pid, cyl_pid, wall_pid):
    print("================== NHÓM 4: BIẾN ĐỔI HÌNH HỌC & THỨ BẬC ==================")
    # 12. move
    r12 = json.loads(mcp_server.sketchup_move(dx=50, dy=50, dz=0, persistent_ids=[box_pid]))
    print(f"[TOOL 12] sketchup_move: ok={r12.get('ok')}, moved_count={r12.get('moved_count')}")
    assert r12.get('ok') is True and r12.get('moved_count') == 1

    # 13. copy
    r13 = json.loads(mcp_server.sketchup_copy(dx=0, dy=200, dz=0, persistent_ids=[cyl_pid]))
    copy_pid = r13.get('entities', [{}])[0].get('persistent_id')
    print(f"[TOOL 13] sketchup_copy: ok={r13.get('ok')}, new_copy_pid={copy_pid}")
    assert r13.get('ok') is True and copy_pid is not None

    # 14. rotate
    r14 = json.loads(mcp_server.sketchup_rotate(angle_degrees=45.0, axis="z", persistent_ids=[wall_pid]))
    print(f"[TOOL 14] sketchup_rotate: ok={r14.get('ok')}, rotated_count={r14.get('rotated_count')}")
    assert r14.get('ok') is True and r14.get('rotated_count') == 1

    # 15. scale
    r15 = json.loads(mcp_server.sketchup_scale(scale=1.5, persistent_ids=[box_pid]))
    print(f"[TOOL 15] sketchup_scale: ok={r15.get('ok')}, scaled_count={r15.get('scaled_count')}")
    assert r15.get('ok') is True and r15.get('scaled_count') == 1

    # 16. group
    r16 = json.loads(mcp_server.sketchup_group(name="Group_T16", persistent_ids=[cyl_pid, copy_pid]))
    grp_pid = r16.get('group', {}).get('persistent_id')
    print(f"[TOOL 16] sketchup_group: ok={r16.get('ok')}, grp_pid={grp_pid}, children={r16.get('children_count')}")
    assert r16.get('ok') is True and r16.get('children_count') == 2

    # 17. ungroup
    r17 = json.loads(mcp_server.sketchup_ungroup(persistent_ids=[grp_pid]))
    print(f"[TOOL 17] sketchup_ungroup: ok={r17.get('ok')}, exploded_count={r17.get('exploded_count')}")
    assert r17.get('ok') is True and r17.get('exploded_count') == 2

    # 18. delete
    r18 = json.loads(mcp_server.sketchup_delete(persistent_ids=[box_pid, cyl_pid, copy_pid, wall_pid]))
    print(f"[TOOL 18] sketchup_delete: ok={r18.get('ok')}, deleted_count={r18.get('deleted_count')}")
    assert r18.get('ok') is True and r18.get('deleted_count') == 4

    print(">>> NHÓM 4 HOÀN TẤT 7/7 TOOLS: PASS <<<\n")


def test_group5_materials():
    print("================== NHÓM 5: QUẢN LÝ VẬT LIỆU ==================")
    # 19. get_materials
    r19 = json.loads(mcp_server.sketchup_get_materials(limit=50))
    print(f"[TOOL 19] sketchup_get_materials: ok={r19.get('ok')}, total_count={r19.get('total_count')}")
    assert r19.get('ok') is True

    # 21. create_material
    mat_test_name = "LiveTest_RubyRed"
    r21 = json.loads(mcp_server.sketchup_create_material(name=mat_test_name, color="#E60000", alpha=0.95))
    print(f"[TOOL 21] sketchup_create_material: ok={r21.get('ok')}, created_new={r21.get('created_new')}, mat_name='{mat_test_name}'")
    assert r21.get('ok') is True

    # 20. get_material_info
    r20 = json.loads(mcp_server.sketchup_get_material_info(material_name=mat_test_name))
    print(f"[TOOL 20] sketchup_get_material_info: ok={r20.get('ok')}, hex={r20.get('material', {}).get('color_hex')}, alpha={r20.get('material', {}).get('alpha')}")
    assert r20.get('ok') is True

    # Tạo box tạm cho mutation vật liệu
    r_box = json.loads(mcp_server.sketchup_create_box(width=100, depth=100, height=100, name="MatTestBox"))
    mat_box_pid = r_box.get('entity', {}).get('persistent_id')

    # 22. set_entity_material
    r22 = json.loads(mcp_server.sketchup_set_entity_material(material_name=mat_test_name, persistent_ids=[mat_box_pid]))
    print(f"[TOOL 22] sketchup_set_entity_material: ok={r22.get('ok')}, updated_count={r22.get('updated_count')}")
    assert r22.get('ok') is True and r22.get('updated_count') == 1

    # 23. clear_entity_material
    r23 = json.loads(mcp_server.sketchup_clear_entity_material(persistent_ids=[mat_box_pid]))
    print(f"[TOOL 23] sketchup_clear_entity_material: ok={r23.get('ok')}, cleared_count={r23.get('cleared_count')}")
    assert r23.get('ok') is True and r23.get('cleared_count') == 1

    print(">>> NHÓM 5 HOÀN TẤT 5/5 TOOLS: PASS <<<\n")
    return mat_box_pid


def test_group6_attributes(mat_box_pid):
    print("================== NHÓM 6: THUỘC TÍNH TÙY BIẾN & BIM METADATA ==================")
    dict_test = "specs_live_test"
    attrs_test = {"supplier": "SteelVN", "spec_code": "SS400", "thickness_mm": 12.5, "verified": True}

    # 25. set_entity_attributes
    r25 = json.loads(mcp_server.sketchup_set_entity_attributes(dictionary_name=dict_test, attributes=attrs_test, persistent_ids=[mat_box_pid]))
    print(f"[TOOL 25] sketchup_set_entity_attributes: ok={r25.get('ok')}, written={r25.get('attributes_written')}")
    assert r25.get('ok') is True and len(r25.get('attributes_written', [])) == 4

    # 24. get_entity_attributes
    r24 = json.loads(mcp_server.sketchup_get_entity_attributes(persistent_id=mat_box_pid, dictionary_name=dict_test))
    read_dict = r24.get('dictionaries', {}).get(dict_test, {})
    print(f"[TOOL 24] sketchup_get_entity_attributes: ok={r24.get('ok')}, read_keys={list(read_dict.keys())}")
    assert r24.get('ok') is True and read_dict.get('spec_code') == "SS400"

    # 26. delete_entity_attributes (xóa toàn bộ dict)
    r26 = json.loads(mcp_server.sketchup_delete_entity_attributes(dictionary_name=dict_test, persistent_ids=[mat_box_pid]))
    print(f"[TOOL 26] sketchup_delete_entity_attributes: ok={r26.get('ok')}, deleted_dict={r26.get('deleted_entire_dictionary')}")
    assert r26.get('ok') is True

    # Dọn dẹp box tạm
    mcp_server.sketchup_delete(persistent_ids=[mat_box_pid])
    print(">>> NHÓM 6 HOÀN TẤT 3/3 TOOLS: PASS <<<\n")


def test_group7_developer_security():
    print("================== NHÓM 7: DEVELOPER MODE & BẢO MẬT ==================")
    # 27. execute_ruby (phải bị chặn DEV_MODE_REQUIRED khi chưa bật dev mode)
    r27 = json.loads(mcp_server.sketchup_execute_ruby(code="puts 123"))
    err_code = r27.get('error', {}).get('code')
    print(f"[TOOL 27] sketchup_execute_ruby: ok={r27.get('ok')}, blocked_code='{err_code}' -> An toàn bảo mật đạt chuẩn!")
    assert r27.get('ok') is False and err_code == "DEV_MODE_REQUIRED"
    print(">>> NHÓM 7 HOÀN TẤT 1/1 TOOL: PASS <<<\n")


def run_all():
    print("*" * 68)
    print("TU SKETCHUP AGENT - BỘ KIỂM THỬ TOÀN DIỆN 27 MCP TOOLS")
    print(f"Bắt đầu: {datetime.now().isoformat(timespec='seconds')}")
    print("*" * 68)
    test_group1_system()
    b_pid, c_pid, w_pid = test_group2_parametric_creation()
    test_group3_geometry_inspection(b_pid, c_pid, w_pid)
    test_group4_transformation_hierarchy(b_pid, c_pid, w_pid)
    m_box_pid = test_group5_materials()
    test_group6_attributes(m_box_pid)
    test_group7_developer_security()
    print("*" * 68)
    print(">>> TỔNG KẾT: 27/27 MCP TOOLS ĐÃ HOẠT ĐỘNG HOÀN HẢO 100%! <<<")
    print("*" * 68)


if __name__ == "__main__":
    run_all()
