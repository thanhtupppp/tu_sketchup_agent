# Layers/Tags & Scenes/Camera Management (Protocol v1.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai hoàn chỉnh 8 công cụ quản lý Layers/Tags (phân tầng hệ thống, màu sắc, ẩn/hiện) và Scenes/Camera (bản vẽ kỹ thuật 2D Top/Front/Iso, phối cảnh 3D, lưu/kích hoạt Scene) cho TuSketchupAgent nâng cấp lên Protocol v1.3.

**Architecture:** Bổ sung router và handlers trong Ruby bridge (`main.rb`), cung cấp helper `setup_camera_preset(view, preset, perspective, bounds)` tính toán chuẩn xác vector camera trực giao/phối cảnh, khai báo 8 công cụ FastMCP tương ứng trong `mcp_server.py`, đồng thời duy trì khả năng tương thích ngược hoàn hảo (Cách B) và bộ kiểm thử tự động 14 tests `tests/test_layers_scenes_v1_3.py`.

**Tech Stack:** SketchUp 2026 Ruby API, Python FastMCP (mcp >= 1.3.0), TCP Socket Bridge (Length-prefixed JSON), Git.

## Global Constraints
- Protocol Version: `1.3`, Min Compatible: `1.0` (Cách B).
- ID Specification: `persistent_ids` là chuẩn khuyến nghị chính thức.
- Mọi mutation bắt buộc đóng gói trong `with_operation(model, name)` để có thể hoàn tác nguyên tử (Undo).
- Bắt buộc gọi `bump_model_revision` sau mỗi thao tác mutation.
- Type Safety: Thao tác `set_entity_layer` chỉ áp dụng lên `Sketchup::Group` và `Sketchup::ComponentInstance`. Giữ các `Face` và `Edge` thuộc `Layer0`.

---

### Task 1: Thiết Lập Branch & Nâng Cấp Handshake Protocol v1.3

**Files:**
- Modify: `main.rb:14-15`
- Modify: `mcp_server.py:23-24`
- Modify: `tests/regression_suite_v1.py:23`

**Interfaces:**
- Consumes: Baseline Git tag `v1.2.0`.
- Produces: Branch `feature/v1.3-layers-scenes`, `PROTOCOL_VERSION = "1.3"`, `SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2", "1.3"}`.

- [ ] **Step 1: Tạo và chuyển sang branch mới**
```bash
git checkout -b feature/v1.3-layers-scenes
```

- [ ] **Step 2: Nâng cấp protocol version trong `main.rb`**
Cập nhật lines trong `main.rb`:
```ruby
  PROTOCOL_VERSION = "1.3"
  MIN_COMPATIBLE_PROTOCOL_VERSION = "1.0"
```

- [ ] **Step 3: Cập nhật protocol version trong `mcp_server.py`**
Cập nhật trong `mcp_server.py`:
```python
PROTOCOL_VERSION = "1.3"
SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2", "1.3"}
```

- [ ] **Step 4: Cập nhật danh sách protocol mong đợi trong regression test**
Trong `tests/regression_suite_v1.py`:
```python
EXPECTED_PROTOCOLS = ["1.0", "1.1", "1.2", "1.3"]
```

- [ ] **Step 5: Kiểm tra biên dịch và commit**
```bash
python -m py_compile mcp_server.py tests/regression_suite_v1.py
python scratch/check_ruby_blocks.py
git add main.rb mcp_server.py tests/regression_suite_v1.py
git commit -m "chore: bump protocol version to 1.3 with backward compatibility"
```

---

### Task 2: Triển Khai Helper Camera & Góc Nhìn Kỹ Thuật trong Ruby

**Files:**
- Modify: `main.rb` (sau phần `build_transformation`)

**Interfaces:**
- Consumes: `preset` (`"top"`, `"front"`, `"right"`, `"left"`, `"back"`, `"iso"`), `perspective` boolean, `model.bounds`.
- Produces: `setup_camera_preset(camera, preset, perspective, bounds) -> camera`.

- [ ] **Step 1: Thêm helper `setup_camera_preset` vào `main.rb`**
```ruby
  def setup_camera_preset(camera, preset, perspective = false, bounds = nil)
    bounds ||= Sketchup.active_model.bounds
    cx = bounds.center.x
    cy = bounds.center.y
    cz = bounds.center.z
    diag = [bounds.diagonal, 1000.mm].max
    dist = diag * 1.8

    camera.perspective = !!perspective

    case preset.to_s.downcase.strip
    when "top"
      eye = Geom::Point3d.new(cx, cy, cz + dist)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 1, 0)
    when "front"
      eye = Geom::Point3d.new(cx, cy - dist, cz)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 0, 1)
    when "right"
      eye = Geom::Point3d.new(cx + dist, cy, cz)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 0, 1)
    when "left"
      eye = Geom::Point3d.new(cx - dist, cy, cz)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 0, 1)
    when "back"
      eye = Geom::Point3d.new(cx, cy + dist, cz)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 0, 1)
    when "iso"
      offset = dist / Math.sqrt(3)
      eye = Geom::Point3d.new(cx + offset, cy - offset, cz + offset)
      target = Geom::Point3d.new(cx, cy, cz)
      up = Geom::Vector3d.new(0, 0, 1)
    else
      return camera
    end

    camera.set(eye, target, up)
    camera
  end
```

- [ ] **Step 2: Kiểm tra cân bằng cú pháp Ruby**
```bash
python scratch/check_ruby_blocks.py
```

- [ ] **Step 3: Commit**
```bash
git add main.rb
git commit -m "feat(ruby): add setup_camera_preset helper for standard engineering views"
```

---

### Task 3: Triển Khai 4 Handlers Quản Lý Layer / Tag Trong Ruby

**Files:**
- Modify: `main.rb` (Section `Dispatch API Handlers - Layers & Tags (v1.3)`)
- Modify: `main.rb` (Section `dispatch router`)

**Interfaces:**
- Consumes: `model.layers`, `entity.layer=`, `validate_group_or_component!`.
- Produces: Commands `"get_layers"`, `"create_layer"`, `"set_entity_layer"`, `"set_layer_visibility"`.

- [ ] **Step 1: Viết 4 methods Layer trong `main.rb`**
  1. `get_layers(args)`: Liệt kê các layer, tên, mã màu hex/rgb, trạng thái visible.
  2. `create_layer(args)`: Tạo hoặc cập nhật layer, đặt màu sắc và visible. Bọc `with_operation`.
  3. `set_entity_layer(args)`: Gán layer cho danh sách Group/ComponentInstance. Kiểm tra type safety guard. Bọc `with_operation`.
  4. `set_layer_visibility(args)`: Ẩn/hiện các layer được chỉ định. Bọc `with_operation`.

- [ ] **Step 2: Đăng ký router trong `dispatch`**
```ruby
    when "get_layers"
      get_layers(args)
    when "create_layer"
      create_layer(args)
    when "set_entity_layer"
      set_entity_layer(args)
    when "set_layer_visibility"
      set_layer_visibility(args)
```

- [ ] **Step 3: Kiểm tra cân bằng cú pháp Ruby và commit**
```bash
python scratch/check_ruby_blocks.py
git add main.rb
git commit -m "feat(ruby): implement 4 layer management handlers and routes"
```

---

### Task 4: Triển Khai 4 Handlers Quản Lý Scene & Camera Trong Ruby

**Files:**
- Modify: `main.rb` (Section `Dispatch API Handlers - Scenes & Camera (v1.3)`)
- Modify: `main.rb` (Section `dispatch router`)

**Interfaces:**
- Consumes: `model.pages`, `view.camera`, `setup_camera_preset`.
- Produces: Commands `"get_scenes"`, `"create_scene"`, `"activate_scene"`, `"set_camera_view"`.

- [ ] **Step 1: Viết 4 methods Scene & Camera trong `main.rb`**
  1. `get_scenes(args)`: Liệt kê scenes, page_id, tên, camera specs, hidden_layers.
  2. `create_scene(args)`: Tạo scene mới với preset hoặc camera specs tùy chọn; cấu hình hidden_layers. Bọc `with_operation`.
  3. `activate_scene(args)`: `model.pages.selected_page = page`.
  4. `set_camera_view(args)`: Cấu hình `view.camera` theo preset hoặc eye/target/up, hỗ trợ `zoom_extents`.

- [ ] **Step 2: Đăng ký router trong `dispatch`**
```ruby
    when "get_scenes"
      get_scenes(args)
    when "create_scene"
      create_scene(args)
    when "activate_scene"
      activate_scene(args)
    when "set_camera_view"
      set_camera_view(args)
```

- [ ] **Step 3: Kiểm tra cân bằng cú pháp Ruby và commit**
```bash
python scratch/check_ruby_blocks.py
git add main.rb
git commit -m "feat(ruby): implement 4 scene and camera handlers and routes"
```

---

### Task 5: Khai Báo 8 Tool FastMCP Trong Python (`mcp_server.py`)

**Files:**
- Modify: `mcp_server.py`

**Interfaces:**
- Consumes: TCP commands `"get_layers"`, `"create_layer"`, `"set_entity_layer"`, `"set_layer_visibility"`, `"get_scenes"`, `"create_scene"`, `"activate_scene"`, `"set_camera_view"`.
- Produces: 8 `@mcp.tool()` mới, nâng tổng số công cụ lên 41 tools.

- [ ] **Step 1: Viết 8 wrapper tools trong `mcp_server.py`**
  - `sketchup_get_layers(name_filter)`
  - `sketchup_create_layer(name, color, visible)`
  - `sketchup_set_entity_layer(layer_name, persistent_ids, entity_ids, ids)`
  - `sketchup_set_layer_visibility(layer_name, visible, layers)`
  - `sketchup_get_scenes(name_filter)`
  - `sketchup_create_scene(name, preset, camera, hidden_layers)`
  - `sketchup_activate_scene(name)`
  - `sketchup_set_camera_view(preset, perspective, eye, target, up, zoom_extents)`

- [ ] **Step 2: Kiểm tra biên dịch Python**
```bash
python -m py_compile mcp_server.py
```

- [ ] **Step 3: Commit**
```bash
git add mcp_server.py
git commit -m "feat(mcp): register 8 Layer and Scene tools in FastMCP server"
```

---

### Task 6: Xây Dựng Bộ Kiểm Thử Tự Động v1.3 & Chạy Hồi Quy Toàn Diện

**Files:**
- Create: `tests/test_layers_scenes_v1_3.py`
- Test: `tests/test_components_assembly_v1_2.py`
- Test: `tests/test_materials_attributes_v1_1.py`
- Test: `tests/regression_suite_v1.py`
- Test: `tests/test_all_27_tools.py`

- [ ] **Step 1: Tạo `tests/test_layers_scenes_v1_3.py` với 14 test case**
  1. Handshake Protocol v1.3 Check.
  2. Tạo 3 layer kiểm thử: `Tag_Chassis`, `Tag_Hydraulics`, `Tag_Sensors`.
  3. `get_layers` xác nhận tìm thấy các layer mới.
  4. Tạo 2 Group hình khối cơ sở.
  5. `set_entity_layer` gán đối tượng vào `Tag_Chassis` và `Tag_Hydraulics`.
  6. Type Safety Check: Chặn gán layer lên Face (INVALID_ENTITY_TYPE).
  7. `set_layer_visibility`: Ẩn `Tag_Hydraulics` $\to$ kiểm tra visible = false.
  8. `set_camera_view`: Chuyển góc nhìn trực giao Top View + zoom extents.
  9. `create_scene`: Tạo scene `Drawing_Top` từ preset `"top"`.
  10. `create_scene`: Tạo scene `View_Iso_3D` từ preset `"iso"` với `perspective: false`.
  11. `get_scenes`: Xác nhận 2 scene mới đã được lưu.
  12. `activate_scene`: Chuyển đổi viewport qua lại giữa các scene.
  13. Error Handling: Bắt lỗi khi gọi tên scene không tồn tại hoặc layer name trống.
  14. Cleanup: Xóa đối tượng test, xóa scene, phục hồi visibility của layer.

- [ ] **Step 2: Nạp lại Extension trong SketchUp 2026 và chạy test suite v1.3**
```powershell
python -X utf8 tests/test_layers_scenes_v1_3.py
```
*(Kỳ vọng: 14/14 PASS)*

- [ ] **Step 3: Chạy lại toàn bộ 4 bộ kiểm thử hồi quy trước đó**
```powershell
python -X utf8 tests/test_components_assembly_v1_2.py
python -X utf8 tests/test_materials_attributes_v1_1.py
python -X utf8 tests/regression_suite_v1.py
python -X utf8 tests/test_all_27_tools.py
```
*(Kỳ vọng: Toàn bộ 100% PASS)*

- [ ] **Step 4: Commit**
```bash
git add tests/test_layers_scenes_v1_3.py
git commit -m "test: add comprehensive 14 tests suite for layers and scenes tools"
```

---

### Task 7: Cập Nhật Tài Liệu README & Gắn Tag Release v1.3.0

**Files:**
- Modify: `README.md`
- Modify: `tests/README.md`

- [ ] **Step 1: Cập nhật danh sách 41 công cụ trong `README.md`**
Bổ sung bảng phân nhóm "Quản Lý Layers / Tags & Scenes / Camera (Protocol v1.3)".

- [ ] **Step 2: Cập nhật `tests/README.md`**

- [ ] **Step 3: Kiểm tra vệ sinh Git, commit, gắn tag và đẩy lên remote**
```powershell
git diff --check
git status --short
git add README.md tests/README.md
git commit -m "docs: document 41 MCP tools including layers and scenes management"
git tag -a v1.3.0 -m "SketchUp Agent protocol v1.3.0"
git push -u origin feature/v1.3-layers-scenes
git push origin v1.3.0
```
