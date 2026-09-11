# Kế Hoạch Tái Cấu Trúc Kiến Trúc Module Hóa: Tu SketchUp Agent (Modular Architecture Refactor)

Tái cấu trúc kiến trúc toàn diện cho cả hai phía **SketchUp Ruby Bridge** và **Python FastMCP Server** từ cấu trúc nguyên khối (monolithic `main.rb` và `mcp_server.py`) sang kiến trúc module hóa hướng miền (**Domain-Driven Modular Architecture**) với **Bộ Điều Phối & Đăng Ký Trung Tâm (Central Router / Registry)**.

---

## 1. Mục Tiêu & Lợi Ích Cốt Lõi

1. **Phân rã đơn trách nhiệm (Single Responsibility Principle)**:
   - `main.rb` đóng vai trò là điểm khởi nhập (Entry Point) tải cấu hình, đăng ký handler và khởi động server.
   - Tách biệt hoàn toàn tầng mạng/giao thức (`core/`), tầng dịch vụ xử lý dữ liệu chung (`services/`), và tầng nghiệp vụ của từng nhóm công cụ (`handlers/`).
2. **Loại bỏ khối điều phối khổng lồ (Decoupled Registry / Router)**:
   - Thay thế `case op` / `if/elsif` dài hàng trăm dòng bằng cơ chế **Central Registry**: mỗi handler tự đăng ký năng lực của mình với `Router.register("op_name") { |args| ... }`. Khi thêm tool mới, chỉ cần viết handler mới mà không phải chạm vào file điều phối.
3. **Module hóa FastMCP Server (Python)**:
   - Tách `mcp_server.py` thành gói `mcp_agent/` chứa `transport.py`, `app.py` và các module theo nhóm chức năng (`tools/geometry.py`, `tools/transform.py`, `tools/components.py`, ...).
   - Duy trì `mcp_server.py` ở thư mục gốc làm bridge chuyển tiếp để đảm bảo 100% tương thích với cấu hình hiện hữu của Antigravity IDE, Cursor và Claude Desktop.
4. **Bảo đảm tính toàn vẹn & 0 Regression**:
   - Toàn bộ 41 công cụ hiện tại hoạt động giữ nguyên 100% interface, schema và semantics.
   - Cả 5 bộ test suites (`test_layers_scenes_v1_3.py`, `test_components_assembly_v1_2.py`, `test_materials_attributes_v1_1.py`, `regression_suite_v1.py`, `test_all_27_tools.py`) phải đạt **100% PASS** trên runtime SketchUp 2026.

---

## 2. Cấu Trúc Thư Mục Mới Sau Tái Cấu Trúc

```text
tu_sketchup_agent/
│
├── main.rb                             # Entry point: loader nạp core, services, handlers và kích hoạt UI/Server
├── tu_sketchup_agent_loader.rb         # Extension registration loader
├── mcp_server.py                       # Python MCP entry point (giữ nguyên tương thích với IDE config)
│
├── core/                               # Nền tảng hạ tầng & giao thức Ruby
│   ├── protocol.rb                     # Constants: PROTOCOL_VERSION, status codes, error codes
│   ├── errors.rb                       # Lớp ngoại lệ chuẩn hóa (ValidationError, EntityNotFoundError, etc.)
│   ├── auth.rb                         # Token verification, Dev Mode flags & toggle
│   ├── operation.rb                    # with_operation, bump_model_revision, revision tracking
│   ├── response.rb                     # Format response chuẩn (ok, error, framing length-prefixed)
│   ├── router.rb                       # Central Registry & Dispatcher (register/dispatch)
│   └── server.rb                       # TCP Server lifecycle, socket polling, UI.start_timer thread-safe loop
│
├── services/                           # Logic hạ tầng trợ giúp hình học & đối tượng
│   ├── entity_service.rb               # resolve_entity, resolve_entities, kiểm tra an toàn container
│   ├── transformation_service.rb       # build_transformation (trực quan + raw 4x4 OpenGL), setup_camera_preset
│   └── metadata_service.rb             # Trích xuất metadata cho entity, layer, camera, scene, material
│
├── handlers/                           # Business logic theo từng domain/capability
│   ├── system.rb                       # ping, get_model_info, get_selection, zoom_extents, capture_viewport, execute_ruby
│   ├── geometry.rb                     # create_box, create_cylinder, create_wall
│   ├── inspection.rb                   # get_entities, get_entity_info, get_bounding_box
│   ├── transform.rb                    # move, copy, rotate, scale, group, ungroup, delete
│   ├── materials.rb                    # get_materials, get_material_info, create_material, set_entity_material, clear_entity_material
│   ├── attributes.rb                   # get_entity_attributes, set_entity_attributes, delete_entity_attributes
│   ├── components.rb                   # create_component, get_component_definitions, make_component_unique, save_component_to_skp, load_component_from_skp
│   ├── assembly.rb                     # place_component_instance
│   └── scenes.rb                       # get_layers, create_layer, set_entity_layer, set_layer_visibility, get_scenes, create_scene, activate_scene, set_camera_view
│
├── mcp_agent/                          # Python FastMCP Modular Architecture
│   ├── __init__.py
│   ├── app.py                          # Khởi tạo FastMCP("sketchup")
│   ├── transport.py                    # TCP socket client, framing, auth, error handlers
│   └── tools/                          # Đăng ký MCP tool theo domain
│       ├── __init__.py                 # register_all_tools(mcp)
│       ├── system.py                   # 6 tools: ping, model_info, selection, zoom, capture, execute_ruby
│       ├── inspection.py               # 3 tools: get_entities, entity_info, bounding_box
│       ├── geometry.py                 # 3 tools: create_box, cylinder, wall
│       ├── transform.py                # 7 tools: move, copy, rotate, scale, group, ungroup, delete
│       ├── materials.py                # 5 tools: get/info/create/set/clear material
│       ├── attributes.py               # 3 tools: get/set/delete attributes
│       ├── components.py               # 5 tools: create, get_defs, make_unique, save_skp, load_skp
│       ├── assembly.py                 # 1 tool:  place_component_instance
│       └── scenes.py                   # 8 tools: layers & scenes management
│
└── tests/                              # Bộ kiểm thử chuẩn hóa (giữ nguyên không đổi interface)
```

---

## 3. User Review Required

> [!IMPORTANT]
> **Về việc nạp lại mã nguồn trong SketchUp 2026 (Live Hot-Reload):**
> Trong SketchUp Ruby API, lệnh `require` tiêu chuẩn chỉ nạp file 1 lần duy nhất (lưu trong `$LOADED_FEATURES`).
> Để hỗ trợ phát triển nhanh và tính năng **Reload Extension** trong UI SketchUp, `main.rb` sẽ cung cấp cơ chế `TuSketchupAgent.reload!` chủ động làm rỗng cache hoặc sử dụng `load` đối với các tệp nội bộ trong plugin, giúp nạp toàn bộ cấu trúc module mới tức thì mà không cần khởi động lại SketchUp.

> [!NOTE]
> **Tương thích hoàn toàn với cấu hình IDE hiện hữu:**
> Tệp `mcp_server.py` ở thư mục gốc vẫn được duy trì dưới dạng entry point chuyển tiếp:
> ```python
> from mcp_agent.app import mcp
> if __name__ == "__main__":
>     mcp.run(transport="stdio")
> ```
> Do đó mọi cấu hình trong `mcp_config.json` (Antigravity), `mcp.json` (Cursor), và Claude Desktop hoàn toàn không cần sửa đổi!

---

## 4. Chi Tiết Các Bước Triển Khai (Tasks & Phân Kỳ)

### Giai đoạn 1: Chuẩn bị Nhánh & Scaffolding
- Tạo nhánh riêng: `refactor/modular-architecture` từ `feature/v1.3-layers-scenes`.
- Tạo cấu trúc thư mục `core/`, `services/`, `handlers/` (Ruby) và `mcp_agent/`, `mcp_agent/tools/` (Python).

### Giai đoạn 2: Triển Khai Lớp Core & Services (Ruby)
- [NEW] `core/protocol.rb`: Định nghĩa hằng số giao thức, mã lỗi, cổng mặc định.
- [NEW] `core/errors.rb`: Các ngoại lệ chuẩn.
- [NEW] `core/auth.rb`: Quản lý token, kiểm tra Dev Mode.
- [NEW] `core/operation.rb`: Quản lý `with_operation` và `bump_model_revision`.
- [NEW] `core/response.rb`: Tạo response JSON chuẩn và length-prefixed framing.
- [NEW] `core/router.rb`: Central Registry & Dispatcher (`register`, `dispatch`, `registered_ops`).
- [NEW] `core/server.rb`: Quản lý TCP server socket, connection loop qua `UI.start_timer`.
- [NEW] `services/entity_service.rb`: Resolve persistent_id / entity_id, container containment validation.
- [NEW] `services/transformation_service.rb`: `build_transformation`, `setup_camera_preset`.
- [NEW] `services/metadata_service.rb`: Trích xuất thông số layers, camera, materials.

### Giai đoạn 3: Triển Khai Lớp Handlers (Ruby)
- [NEW] `handlers/system.rb`: `ping`, `get_model_info`, `get_selection`, `zoom_extents`, `capture_viewport`, `execute_ruby`.
- [NEW] `handlers/inspection.rb`: `get_entities`, `get_entity_info`, `get_bounding_box`.
- [NEW] `handlers/geometry.rb`: `create_box`, `create_cylinder`, `create_wall`.
- [NEW] `handlers/transform.rb`: `move`, `copy`, `rotate`, `scale`, `group`, `ungroup`, `delete`.
- [NEW] `handlers/materials.rb`: `get_materials`, `get_material_info`, `create_material`, `set_entity_material`, `clear_entity_material`.
- [NEW] `handlers/attributes.rb`: `get_entity_attributes`, `set_entity_attributes`, `delete_entity_attributes`.
- [NEW] `handlers/components.rb`: `create_component`, `get_component_definitions`, `make_component_unique`, `save_component_to_skp`, `load_component_from_skp`.
- [NEW] `handlers/assembly.rb`: `place_component_instance`.
- [NEW] `handlers/scenes.rb`: `get_layers`, `create_layer`, `set_entity_layer`, `set_layer_visibility`, `get_scenes`, `create_scene`, `activate_scene`, `set_camera_view`.

### Giai đoạn 4: Thu Gọn `main.rb`
- [MODIFY] `main.rb`:
  - Nạp tuần tự `core/`, `services/`, `handlers/`.
  - Gọi đăng ký handler: `TuSketchupAgent::Handlers.register_all`.
  - Thiết lập UI Menu trong SketchUp với chức năng **Start/Stop Server**, **Toggle Dev Mode**, và **Reload Plugin** (hỗ trợ hot-reload toàn bộ module).
  - Tự động gọi `TuSketchupAgent::Server.start`.

### Giai đoạn 5: Triển Khai Gói `mcp_agent/` (Python)
- [NEW] `mcp_agent/transport.py`: Đóng gói socket TCP, length-prefixed framing, auth token, request_id.
- [NEW] `mcp_agent/app.py`: Khởi tạo instance `FastMCP("sketchup")`.
- [NEW] `mcp_agent/tools/` (9 modules tách biệt cho từng domain):
  - `system.py`, `inspection.py`, `geometry.py`, `transform.py`, `materials.py`, `attributes.py`, `components.py`, `assembly.py`, `scenes.py`.
- [NEW] `mcp_agent/tools/__init__.py`: Hàm `register_all_tools(mcp)`.
- [MODIFY] `mcp_server.py`: Giữ làm entry point gọn gàng nạp `mcp_agent.app.mcp`.

---

## 5. Kế Hoạch Xác Minh & Đo Lường (Verification Plan)

### Automated Syntax & Static Checks:
```powershell
python -m py_compile mcp_server.py mcp_agent/*.py mcp_agent/tools/*.py
ruby -c main.rb
git diff --check
```

### Live Runtime Verification trên SketchUp 2026:
Nạp lại extension trong SketchUp 2026 và chạy tuần tự tất cả các bộ test suites:
1. `python -X utf8 tests/test_layers_scenes_v1_3.py` *(Kỳ vọng: 14/14 PASS)*
2. `python -X utf8 tests/test_components_assembly_v1_2.py` *(Kỳ vọng: 14/14 PASS)*
3. `python -X utf8 tests/test_materials_attributes_v1_1.py` *(Kỳ vọng: 14/14 PASS)*
4. `python -X utf8 tests/regression_suite_v1.py` *(Kỳ vọng: 14/14 PASS)*
5. `python -X utf8 tests/test_all_27_tools.py` *(Kỳ vọng: 27/27 PASS)*

Sau khi toàn bộ test pass 100%, commit, tag và cập nhật tài liệu kiến trúc.
