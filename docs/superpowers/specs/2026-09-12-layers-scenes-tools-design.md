# Thiết Kế Kỹ Thuật: Nhóm Công Cụ Layers/Tags & Scenes/Camera Management (Protocol v1.3)

Tài liệu thiết kế chi tiết kiến trúc, giao thức và các quy chuẩn kỹ thuật cho bộ 8 công cụ chuyên sâu về **Quản lý Layer / Tag** và **Scene / Camera** cho `TuSketchupAgent` nâng cấp lên **Protocol v1.3.0**.

---

## 1. Mục Tiêu & Phạm Vi Kỹ Thuật

1. **Quản lý Tổ chức Mô hình (Layers / Tags)**:
   - Cho phép AI phân loại các thành phần vào các tầng/hệ thống kỹ thuật (ví dụ: `Chassis`, `Transmission`, `Hydraulics`, `Sensors`).
   - Quản lý trạng thái hiển thị (ẩn/hiện) theo từng layer hoặc nhóm layer để hỗ trợ các góc nhìn bóc tách kết cấu (exploded view).
   - **Type Safety**: Thao tác gán layer chỉ áp dụng lên `Sketchup::Group` và `Sketchup::ComponentInstance`. Giữ nguyên các hình học con `Face` và `Edge` ở `Layer0` theo đúng nguyên tắc chuẩn mực quốc tế của SketchUp.

2. **Thiết Lập Góc Nhìn Kỹ Thuật & Trình Diễn (Scenes & Camera)**:
   - Cung cấp các góc chiếu trực giao kỹ thuật 2D chuẩn (Orthographic Projection: Top, Front, Right, Left, Back, Isometric) phục vụ xuất bản vẽ gia công/sản xuất.
   - Cung cấp góc nhìn phối cảnh 3D (Perspective Projection) với đầy đủ thông số mắt nhìn (`eye`), tâm ngắm (`target`), vector phương đứng (`up`), và góc mở ống kính (`fov`).
   - Lưu trữ các cấu hình góc nhìn và trạng thái layer vào các `Sketchup::Page` (Scene) để người dùng hoặc AI có thể chuyển đổi linh hoạt.

3. **Chiến Lược Tương Thích Ngược (Cách B)**:
   - `PROTOCOL_VERSION = "1.3"`
   - `MIN_COMPATIBLE_PROTOCOL_VERSION = "1.0"`
   - `SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2", "1.3"}`
   - Bảo đảm 100% tương thích ngược với các client v1.0, v1.1, và v1.2.

---

## 2. Danh Sách 8 Công Cụ Đề Xuất (v1.3)

| STT | Tên Tool FastMCP | Lệnh Bridge | Loại Thao Tác | Phạm Vi | Mô Tả Chức Năng |
|:---:|---|---|:---:|:---:|---|
| **1** | `sketchup_get_layers` | `get_layers` | Read-only | Model | Liệt kê tất cả layers/tags trong model, trạng thái ẩn/hiện, mã màu RGB/Hex. |
| **2** | `sketchup_create_layer` | `create_layer` | Mutation | Model | Tạo mới hoặc cập nhật layer/tag theo tên, màu sắc hiển thị và trạng thái visible. |
| **3** | `sketchup_set_entity_layer` | `set_entity_layer` | Mutation | Group / Component | Gán danh sách Group hoặc ComponentInstance vào layer chỉ định. |
| **4** | `sketchup_set_layer_visibility` | `set_layer_visibility` | Mutation | Model | Bật/tắt hiển thị của một hoặc nhiều layer (ẩn/hiện hàng loạt theo dictionary). |
| **5** | `sketchup_get_scenes` | `get_scenes` | Read-only | Model | Liệt kê danh sách scenes hiện có, camera position, target, perspective, hidden layers. |
| **6** | `sketchup_create_scene` | `create_scene` | Mutation | Model | Tạo scene mới theo preset kỹ thuật (Top, Front, Iso, ...) hoặc camera tùy biến. |
| **7** | `sketchup_activate_scene` | `activate_scene` | Viewport Nav | Viewport | Chuyển góc nhìn và trạng thái hiển thị của viewport sang scene chỉ định. |
| **8** | `sketchup_set_camera_view` | `set_camera_view` | Viewport Nav | Viewport | Điều khiển trực tiếp camera của active view (hỗ trợ preset kỹ thuật + auto zoom extents). |

---

## 3. Quy Chuẩn Kỹ Thuật Chi Tiết

### 3.1. Nhóm Quản Lý Layers / Tags

#### 3.1.1. `get_layers(args)`
* **Mục đích**: Lấy danh sách toàn bộ layers/tags.
* **Payload Input**:
  ```json
  { "name_filter": "chassis" }
  ```
* **Response Payload**:
  ```json
  {
    "ok": true,
    "total_count": 4,
    "layers": [
      {
        "name": "Layer0",
        "visible": true,
        "color_hex": "#000000",
        "color_rgb": [0, 0, 0]
      },
      {
        "name": "Chassis_Frame",
        "visible": true,
        "color_hex": "#1E90FF",
        "color_rgb": [30, 144, 255]
      }
    ]
  }
  ```

#### 3.1.2. `create_layer(args)`
* **Mục đích**: Tạo mới hoặc cập nhật layer.
* **Payload Input**:
  ```json
  {
    "name": "Chassis_Frame",
    "color": "#1E90FF",
    "visible": true
  }
  ```
* **Hành vi Ruby**:
  - `layer = model.layers[name] || model.layers.add(name)`
  - Đặt màu nếu có: `layer.color = Sketchup::Color.new(color)`
  - `layer.visible = visible` nếu được chỉ định.
  - Bọc `with_operation(model, "AI - Create Layer")`, gọi `bump_model_revision`.

#### 3.1.3. `set_entity_layer(args)`
* **Mục đích**: Gán đối tượng vào layer chỉ định.
* **Payload Input**:
  ```json
  {
    "layer_name": "Chassis_Frame",
    "persistent_ids": [52523, 52554]
  }
  ```
* **Hành vi Ruby**:
  - Tự động nạp hoặc tạo layer nếu chưa có: `layer = model.layers[name] || model.layers.add(name)`.
  - Duyệt qua từng entity: kiểm tra `validate_group_or_component!(e)`. Nếu không hợp lệ $\to$ báo lỗi.
  - Gán `e.layer = layer`.
  - Bọc `with_operation(model, "AI - Set Entity Layer")`, gọi `bump_model_revision`.

#### 3.1.4. `set_layer_visibility(args)`
* **Mục đích**: Ẩn/hiện một hoặc nhiều layer cùng lúc.
* **Payload Input (Hỗ trợ 2 định dạng)**:
  - Dạng đơn: `{"layer_name": "Chassis_Frame", "visible": false}`
  - Dạng danh sách: `{"layers": {"Chassis_Frame": false, "Transmission": true}}`
* **Hành vi Ruby**:
  - Bọc trong `with_operation`, áp dụng visibility cho các layer tương ứng.
  - Gọi `bump_model_revision`.

---

### 3.2. Nhóm Quản Lý Scenes & Camera

#### 3.2.1. Thiết Lập Camera Preset Kỹ Thuật (Standard Engineering Presets)
Quy chuẩn hướng nhìn và vector camera chuẩn:
* **`top`**: `eye = [cx, cy, max_z + dist]`, `target = [cx, cy, cz]`, `up = [0, 1, 0]`, `perspective = false` (Chiếu bằng trực giao).
* **`front`**: `eye = [cx, min_y - dist, cz]`, `target = [cx, cy, cz]`, `up = [0, 0, 1]`, `perspective = false` (Chiếu đứng trực giao).
* **`right`**: `eye = [max_x + dist, cy, cz]`, `target = [cx, cy, cz]`, `up = [0, 0, 1]`, `perspective = false` (Chiếu cạnh phải trực giao).
* **`left`**: `eye = [min_x - dist, cy, cz]`, `target = [cx, cy, cz]`, `up = [0, 0, 1]`, `perspective = false` (Chiếu cạnh trái trực giao).
* **`back`**: `eye = [cx, max_y + dist, cz]`, `target = [cx, cy, cz]`, `up = [0, 0, 1]`, `perspective = false` (Chiếu sau trực giao).
* **`iso`**: `eye = [cx + dist, cy - dist, cz + dist]`, `target = [cx, cy, cz]`, `up = [0, 0, 1]`, `perspective = false` (Hình chiếu trục đo đẳng cự trực giao).
* **`perspective` / 3D tự do**: `perspective = true`, nhận các tọa độ `eye`, `target`, `up` (hoặc tính tự động góc nhìn chéo 45 độ phối cảnh).

#### 3.2.2. `get_scenes(args)`
* **Mục đích**: Đọc danh sách tất cả scenes trong model.
* **Response Payload**:
  ```json
  {
    "ok": true,
    "total_count": 2,
    "scenes": [
      {
        "name": "Scene_Top_View",
        "page_id": 102,
        "camera": {
          "eye_mm": [250.0, 250.0, 1500.0],
          "target_mm": [250.0, 250.0, 0.0],
          "up": [0.0, 1.0, 0.0],
          "perspective": false,
          "fov": 35.0
        },
        "hidden_layers": ["Annotation_Dims"]
      }
    ]
  }
  ```

#### 3.2.3. `create_scene(args)`
* **Mục đích**: Tạo scene mới lưu góc nhìn và trạng thái layer.
* **Payload Input**:
  ```json
  {
    "name": "Drawing_01_Front",
    "preset": "front",
    "hidden_layers": ["Draft_Helpers"]
  }
  ```
* **Hành vi Ruby**:
  - `page = model.pages.add(name)`
  - Cấu hình camera theo preset hoặc tọa độ chỉ định.
  - Cấu hình `page.set_visibility(layer, false)` cho danh sách `hidden_layers`.
  - Cập nhật `page.update(PAGE_USE_ALL)`.
  - Bọc trong `with_operation(model, "AI - Create Scene")`, gọi `bump_model_revision`.

#### 3.2.4. `activate_scene(args)`
* **Mục đích**: Kích hoạt scene trong Viewport.
* **Payload Input**:
  ```json
  { "name": "Drawing_01_Front" }
  ```
* **Hành vi Ruby**:
  - `page = model.pages[name]`
  - `model.pages.selected_page = page`
  - Viewport tự động chuyển góc nhìn và cập nhật trạng thái hiển thị.

#### 3.2.5. `set_camera_view(args)`
* **Mục đích**: Điều khiển camera active view tức thời không cần lưu scene.
* **Payload Input**:
  ```json
  {
    "preset": "iso",
    "perspective": false,
    "zoom_extents": true
  }
  ```
* **Hành vi Ruby**:
  - Thiết lập `view.camera` theo preset hoặc `eye`, `target`, `up`.
  - `view.zoom_extents` nếu `zoom_extents: true`.
  - Trả về thông số camera mới.

---

## 4. Kế Hoạch Xác Minh & Kiểm Thử E2E

### 4.1. File Kiểm Thử Mới: `tests/test_layers_scenes_v1_3.py`
Xây dựng 14 bài kiểm tra E2E tự động:
1. `TEST 01`: Handshake Protocol v1.3 & min_compatible v1.0.
2. `TEST 02`: Tạo các layer kiểm thử: `"Tag_Chassis"`, `"Tag_Hydraulics"`, `"Tag_Sensors"`.
3. `TEST 03`: `get_layers` xác nhận tìm thấy 3 layer mới kèm màu sắc.
4. `TEST 04`: Tạo 2 Group hình học mẫu.
5. `TEST 05`: `set_entity_layer` gán Group 1 vào `"Tag_Chassis"` và Group 2 vào `"Tag_Hydraulics"`.
6. `TEST 06`: Type Safety Guard: Cố tình gán layer cho Face $\to$ bắt đúng lỗi `INVALID_ENTITY_TYPE`.
7. `TEST 07`: `set_layer_visibility` ẩn `"Tag_Hydraulics"` $\to$ kiểm tra trạng thái visible = false.
8. `TEST 08`: `set_camera_view` chuyển góc nhìn trực giao Top View kèm `zoom_extents`.
9. `TEST 09`: `create_scene` tạo Scene `"View_Top_Drawing"` từ preset `"top"`.
10. `TEST 10`: `create_scene` tạo Scene `"View_Iso_3D"` từ preset `"iso"` với `perspective: false`.
11. `TEST 11`: `get_scenes` xác nhận sự hiện diện của 2 scene mới.
12. `TEST 12`: `activate_scene` chuyển viewport qua lại giữa `"View_Top_Drawing"` và `"View_Iso_3D"`.
13. `TEST 13`: Kiểm tra xử lý lỗi (tên scene không tồn tại, tên layer trống).
14. `TEST 14`: Dọn dẹp đối tượng thử nghiệm, xóa scene tạm, khôi phục visibility layer.

### 4.2. Kiểm Thử Hồi Quy Toàn Diện
Chạy liên tục:
- `tests/regression_suite_v1.py` (v1.0 baseline - 14 tests)
- `tests/test_materials_attributes_v1_1.py` (v1.1 - 14 tests)
- `tests/test_components_assembly_v1_2.py` (v1.2 - 14 tests)
- `tests/test_all_27_tools.py` (27 tools tổng thể)
Kỳ vọng: **100% PASS trên tất cả các bộ kiểm thử**.
