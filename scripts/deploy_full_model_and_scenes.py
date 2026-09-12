"""
Deployment script for Nha Cap 4 11.5x20.5m 3D Architectural Model and Presentation Scenes.
Executes complete automated modeling, tagging, and scene rendering:
- Modular House Body (Foundation, Walls, Columns, Doors, Windows, Pavement)
- Modular House Roof (Main Roof, Porch Roofs, Ridge Caps, Fascia Trims)
- 7 Architectural Presentation Scenes & High-Res Renders
"""

import os
import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))
from mcp_agent.transport import send_to_sketchup

ARTIFACTS_DIR = "C:/Users/thanh/.gemini/antigravity-ide/brain/c9f17fca-375e-456c-93f8-9a97124b8f65"

def deploy():
    print("=== Bước 1: Dọn dẹp các đối tượng nhà trước đó ===")
    res_root = send_to_sketchup("get_entities", {"limit": 100})
    for it in res_root.get("items", []):
        bb = it.get("bounds_mm")
        if bb and -6000 <= bb["center"][0] <= 25000 and it["persistent_id"] not in [41159, 649573]:
            print(f"Deleting previous instance: PID={it['persistent_id']}")
            send_to_sketchup("delete", {"persistent_ids": [it["persistent_id"]]})

    print("=== Bước 2: Nạp mô hình Thân Nhà (Body) ===")
    body_dae = os.path.abspath("tests/scratch/nha_cap_4_body.dae")
    res_body = send_to_sketchup("import_file", {
        "file_path": body_dae,
        "units": "m",
        "as_component": True,
        "name": "Nha_Cap_4_Than_Nha"
    })
    if not res_body.get("ok"):
        raise RuntimeError(f"Lỗi nạp Body DAE: {res_body}")
    body_pid = res_body.get("persistent_id")
    print(f"Đã nạp Thân Nhà: PID={body_pid}")

    print("=== Bước 3: Nạp mô hình Mái Nhà (Roof) ===")
    roof_dae = os.path.abspath("tests/scratch/nha_cap_4_roof.dae")
    res_roof = send_to_sketchup("import_file", {
        "file_path": roof_dae,
        "units": "m",
        "as_component": True,
        "name": "Nha_Cap_4_Mai_Nha"
    })
    if not res_roof.get("ok"):
        raise RuntimeError(f"Lỗi nạp Roof DAE: {res_roof}")
    roof_pid = res_roof.get("persistent_id")
    print(f"Đã nạp Mái Nhà: PID={roof_pid}")

    print("=== Bước 4: Thiết lập hệ thống Thẻ/Lớp (Tags/Layers) ===")
    send_to_sketchup("create_layer", {"name": "Tag_00_CAD_Drawing_DWG", "color": "#7F8C8D", "visible": False})
    send_to_sketchup("create_layer", {"name": "Tag_01_Architecture_House_Body", "color": "#2C3E50", "visible": True})
    send_to_sketchup("create_layer", {"name": "Tag_01_Architecture_House_Roof", "color": "#2980B9", "visible": True})
    send_to_sketchup("create_layer", {"name": "Tag_02_Human_Scale_Figure", "color": "#E67E22", "visible": True})

    # Assign entities to Tags
    send_to_sketchup("set_entity_layer", {"layer_name": "Tag_00_CAD_Drawing_DWG", "persistent_ids": [649573]})
    send_to_sketchup("set_entity_layer", {"layer_name": "Tag_01_Architecture_House_Body", "persistent_ids": [body_pid]})
    send_to_sketchup("set_entity_layer", {"layer_name": "Tag_01_Architecture_House_Roof", "persistent_ids": [roof_pid]})
    send_to_sketchup("set_entity_layer", {"layer_name": "Tag_02_Human_Scale_Figure", "persistent_ids": [41159]})

    # Ensure CAD layer is hidden
    send_to_sketchup("set_layer_visibility", {"layer_name": "Tag_00_CAD_Drawing_DWG", "visible": False})
    send_to_sketchup("set_layer_visibility", {"layer_name": "Tag_01_Architecture_House_Body", "visible": True})
    send_to_sketchup("set_layer_visibility", {"layer_name": "Tag_01_Architecture_House_Roof", "visible": True})

    print("=== Bước 5: Khởi tạo 7 Scenes trình diễn kiến trúc chuyên nghiệp ===")
    scenes = [
        {
            "name": "01_PhoiCanh_MatTien",
            "camera": {
                "eye": [-15000.0, -8000.0, 8500.0],
                "target": [8000.0, 5000.0, 2500.0],
                "up": [0.0, 0.0, 1.0],
                "perspective": True
            },
            "perspective": True,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG"],
            "filename": "render_01_phoi_canh_mat_tien.png"
        },
        {
            "name": "02_MatDung_Chinh",
            "camera": {
                "eye": [-18000.0, 5050.0, 3200.0],
                "target": [0.0, 5050.0, 3200.0],
                "up": [0.0, 0.0, 1.0],
                "perspective": False
            },
            "perspective": False,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG"],
            "filename": "render_02_mat_dung_chinh.png"
        },
        {
            "name": "03_MatDung_Ben_Phai",
            "camera": {
                "eye": [10300.0, -18000.0, 3200.0],
                "target": [10300.0, 0.0, 3200.0],
                "up": [0.0, 0.0, 1.0],
                "perspective": False
            },
            "perspective": False,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG"],
            "filename": "render_03_mat_dung_ben_phai.png"
        },
        {
            "name": "04_MatBang_TongThe",
            "camera": {
                "eye": [10300.0, 5050.0, 32000.0],
                "target": [10300.0, 5050.0, 0.0],
                "up": [0.0, 1.0, 0.0],
                "perspective": False
            },
            "perspective": False,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG"],
            "filename": "render_04_mat_bang_tong_the.png"
        },
        {
            "name": "05_PhoiCanh_ChimBay",
            "camera": {
                "eye": [-18000.0, 22000.0, 19000.0],
                "target": [10000.0, 5000.0, 2000.0],
                "up": [0.0, 0.0, 1.0],
                "perspective": True
            },
            "perspective": True,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG"],
            "filename": "render_05_phoi_canh_chim_bay.png"
        },
        {
            "name": "06_PhoiCanh_BocMai_NoiThat",
            "camera": {
                "eye": [-12000.0, -6000.0, 16000.0],
                "target": [8000.0, 5000.0, 1500.0],
                "up": [0.0, 0.0, 1.0],
                "perspective": True
            },
            "perspective": True,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG", "Tag_01_Architecture_House_Roof"],
            "filename": "render_06_phoi_canh_boc_mai_noi_that.png"
        },
        {
            "name": "07_MatBang_NoiThat_2D",
            "camera": {
                "eye": [8000.0, 5050.0, 28000.0],
                "target": [8000.0, 5050.0, 0.0],
                "up": [0.0, 1.0, 0.0],
                "perspective": False
            },
            "perspective": False,
            "hidden_layers": ["Tag_00_CAD_Drawing_DWG", "Tag_01_Architecture_House_Roof"],
            "filename": "render_07_mat_bang_noi_that_2d.png"
        }
    ]

    for sc in scenes:
        print(f"Creating scene: {sc['name']}...")
        send_to_sketchup("create_scene", {
            "name": sc["name"],
            "camera": sc["camera"],
            "perspective": sc["perspective"],
            "hidden_layers": sc["hidden_layers"]
        })
        # Set exact camera directly for immediate viewport capture
        send_to_sketchup("set_camera_view", {
            "eye": sc["camera"]["eye"],
            "target": sc["camera"]["target"],
            "up": sc["camera"]["up"],
            "perspective": sc["perspective"]
        })
        # Apply layer visibility for capture
        for hl in sc["hidden_layers"]:
            send_to_sketchup("set_layer_visibility", {"layer_name": hl, "visible": False})
        visible_layers = [l for l in ["Tag_01_Architecture_House_Body", "Tag_01_Architecture_House_Roof", "Tag_02_Human_Scale_Figure"] if l not in sc["hidden_layers"]]
        for vl in visible_layers:
            send_to_sketchup("set_layer_visibility", {"layer_name": vl, "visible": True})
            
        time.sleep(0.2)

        # Capture viewport
        img_out = os.path.join(ARTIFACTS_DIR, sc["filename"]).replace("\\", "/")
        res_cap = send_to_sketchup("capture_viewport", {
            "width": 1920,
            "height": 1080,
            "output_path": img_out
        })
        print(f"Captured {sc['filename']}: ok={res_cap.get('ok')}")

    # Restore roof visibility in model
    send_to_sketchup("set_layer_visibility", {"layer_name": "Tag_01_Architecture_House_Roof", "visible": True})
    # Activate Scene 1 by default
    send_to_sketchup("activate_scene", {"name": "01_PhoiCanh_MatTien"})
    print("=== HOÀN TẤT TRIỂN KHAI MÔ HÌNH VÀ RENDER 7 SCENES KIẾN TRÚC THÀNH CÔNG ===")

if __name__ == "__main__":
    deploy()

