# Tu SketchUp Agent - MCP Bridge cho Trimble SketchUp 2026

Hệ thống cầu nối AI thế hệ mới kết nối các trợ lý lập trình & thiết kế (**Antigravity IDE, Cursor, Claude Desktop**) với **Trimble SketchUp 2026** thông qua kiến trúc **Model Context Protocol (MCP)** và **TCP Socket Bridge đa phân lớp (Domain-Driven Modular Architecture)**.

Hỗ trợ tự động hóa toàn diện từ dựng hình tham số 3D, biến đổi ma trận, quản lý vật liệu/kết cấu, siêu dữ liệu BIM/Attribute Dictionaries, quản lý cụm linh kiện/lắp ráp (Component & Assembly), cho đến phân tầng hiển thị (Tags/Layers) và xuất bản vẽ 2D kỹ thuật (Scenes & Camera Presets).

---

## 1. Sơ Đồ Kiến Trúc Hệ Thống (Architecture)

```text
┌─────────────────────────────────────────────────────────────┐
│       AI Assistant (Antigravity IDE / Cursor / Claude)      │
└──────────────────────────────┬──────────────────────────────┘
                               │  stdio MCP Protocol (JSON-RPC)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Python FastMCP Server (mcp_agent)              │
│  ├── mcp_server.py (Entry point chuẩn PEP 723 `uv run`)     │
│  ├── mcp_agent/transport.py (Framing Socket độ dài tiền tố) │
│  └── mcp_agent/tools/ (9 nhóm công cụ chuyên biệt hóa)      │
└──────────────────────────────┬──────────────────────────────┘
                               │  TCP Socket: 127.0.0.1:9876
                               │  Length-prefixed UTF-8 JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          SketchUp Ruby Bridge (TuSketchupAgent)             │
│  ├── main.rb (Lifecycle loader & UI Extension Menu)         │
│  ├── core/ (Server non-blocking, Router, Auth, Response)    │
│  ├── services/ (EntityService, TransformService, Metadata)  │
│  └── handlers/ (9 bộ Dispatch Handlers cho 42 nghiệp vụ)    │
└──────────────────────────────┬──────────────────────────────┘
                               │  Main Thread Safe (UI.start_timer)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Trimble SketchUp 2026 API                  │
│       (Model, Entities, Layers, Pages, Materials, SKP, CAD) │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Cấu Trúc Thư Mục Module Hóa (Modular Structure)

Mã nguồn được phân rã thành các tầng chức năng độc lập (Separation of Concerns), loại bỏ mã nguyên khối, giúp việc mở rộng tính năng mới an toàn và trực quan:

```text
tu_sketchup_agent/
├── main.rb                             # Entry point mỏng (~90 dòng), menu UI & auto-start
├── tu_sketchup_agent_loader.rb         # File nạp đăng ký Extension chuẩn vào SketchUp
├── mcp_server.py                       # Proxy entry point mỏng (PEP 723) giữ tương thích tuyệt đối
│
├── core/                               # HẠ TẦNG & GIAO TIẾP HỆ THỐNG
│   ├── protocol.rb                     # Phiên bản giao thức (v1.3), hằng số, giới hạn kích thước
│   ├── errors.rb                       # Hệ thống chuẩn hóa Domain Errors & Error Codes
│   ├── auth.rb                         # Kiểm tra Token SHA256 & kiểm soát Dev Mode
│   ├── operation.rb                    # Giao dịch mô hình (start_operation/undo) & Revision
│   ├── response.rb                     # Chuẩn hóa cấu trúc phản hồi JSON, đo duration_ms
│   ├── router.rb                       # Bộ định tuyến trung tâm (Central Command Dispatcher)
│   └── server.rb                       # TCP Server non-blocking đa lớp bảo vệ chống crash timer
│
├── services/                           # DỊCH VỤ NGHIỆP VỤ LÕI (CAD BUSINESS LOGIC)
│   ├── entity_service.rb               # Tra cứu đối tượng (PID/EID/ref), validation, bounds
│   ├── transformation_service.rb       # Ma trận dịch chuyển, xoay, tỷ lệ, thiết lập camera
│   └── metadata_service.rb             # Xử lý thông số Layer, Material, Attribute Dictionaries
│
├── handlers/                           # BỘ XỬ LÝ LỆNH ĐỘC LẬP CHO 42 NGHIỆP VỤ
│   ├── system.rb                       # ping, model_summary, get_selection, capture, zoom
│   ├── inspection.rb                   # get_entities, get_entity_info, get_bounding_box
│   ├── geometry.rb                     # create_box, create_cylinder, create_wall
│   ├── transform.rb                    # move, copy, rotate, scale, group, ungroup, delete
│   ├── materials.rb                    # get_materials, get_material_info, create/set/clear material
│   ├── attributes.rb                   # get/set/delete entity attributes (BIM metadata)
│   ├── components.rb                   # create/get/place component, make unique, save to skp
│   ├── assembly.rb                     # load component from skp, import_file (Universal CAD/3D)
│   ├── scenes.rb                       # layers/tags & scenes/camera (8 công cụ)
│   └── init.rb                         # Khởi tạo & nạp toàn bộ 42 lệnh vào Router
│
├── mcp_agent/                          # PACKAGE PYTHON FASTMCP MODULE HÓA
│   ├── __init__.py                     # Export FastMCP instance & hàm send_to_sketchup
│   ├── app.py                          # Khởi tạo instance FastMCP("sketchup-agent")
│   ├── transport.py                    # Giao thức TCP length-prefixed & xác thực protocol version
│   └── tools/                          # Các module đăng ký MCP Tools theo Domain
│       ├── common.py                   # Tiện ích chung & xử lý dữ liệu JSON
│       ├── system.py                   # 6 tools hệ thống & quan sát viewport
│       ├── inspection.py               # 3 tools truy vấn đối tượng & bounding box
│       ├── geometry.py                 # 3 tools dựng hình cơ bản
│       ├── transform.py                # 7 tools biến đổi hình học & phân cấp
│       ├── materials.py                # 5 tools quản lý màu sắc & vật liệu
│       ├── attributes.py               # 3 tools siêu dữ liệu thuộc tính BIM
│       ├── components.py               # 5 tools định nghĩa & thực thể Component
│       ├── assembly.py                 # 2 tools nạp linh kiện SKP & CAD Universal Importer
│       ├── scenes.py                   # 8 tools quản lý layer & góc nhìn camera/scene
│       └── __init__.py                 # Đăng ký tự động 42 tools vào FastMCP
│
├── tests/                              # BỘ KIỂM THỬ TỰ ĐỘNG (84/84 TESTS PASS)
│   ├── test_all_27_tools.py            # Kiểm thử toàn diện 27 tools nền tảng
│   ├── regression_suite_v1.py          # Kiểm thử hồi quy 14 ca kiểm tra v1.0
│   ├── test_materials_attributes_v1_1.py # Kiểm thử 14 ca quản lý vật liệu & BIM v1.1
│   ├── test_components_assembly_v1_2.py  # Kiểm thử 14 ca Component & Lắp ráp v1.2
│   ├── test_layers_scenes_v1_3.py      # Kiểm thử 14 ca Layer/Tag & Scene/Camera v1.3
│   ├── models/regression_empty.skp     # File mẫu trống chuyên dụng cho chạy test
│   └── README.md                       # Đặc tả chi tiết các bộ test suite
│
├── docs/                               # Bản thiết kế kỹ thuật & kế hoạch phát triển
└── README.md                           # Tài liệu hướng dẫn sử dụng chính thức
```

---

## 3. Hướng Dẫn Cài Đặt & Kích Hoạt

### Bước 1: Nạp Extension Trong SketchUp 2026

#### Cách A (Khuyên dùng - Tự động nạp khi mở SketchUp):
Sao chép tệp `tu_sketchup_agent_loader.rb` ra thư mục cha `Plugins` và đổi tên thành `tu_sketchup_agent.rb`:
```powershell
# Đường dẫn thư mục plugins của SketchUp 2026:
%APPDATA%\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent.rb
```
Mỗi khi khởi động SketchUp 2026 và mở một file model, extension sẽ tự động tải và kích hoạt TCP Bridge tại cổng `9876`.

#### Cách B (Nạp thủ công qua Ruby Console):
1. Mở SketchUp 2026.
2. Mở menu **Extensions -> Developer -> Ruby Console**.
3. Chạy lệnh:
   ```ruby
   load File.expand_path("~/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/main.rb")
   ```
4. Menu **Extensions -> Tu SketchUp Agent** sẽ xuất hiện trên thanh công cụ.

---

### Bước 2: Cấu Hình MCP Client (AI Assistant)

FastMCP Server hỗ trợ chạy trực tiếp không cần cài đặt phức tạp thông qua công cụ quản lý package siêu tốc `uv`.

#### A. Antigravity IDE (`mcp_config.json`)
```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp>=1.3.0,<2.0",
        "--with", "pillow>=10.0.0",
        "python",
        "c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/mcp_server.py"
      ]
    }
  }
}
```

#### B. Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp>=1.3.0,<2.0",
        "--with", "pillow>=10.0.0",
        "python",
        "c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/mcp_server.py"
      ]
    }
  }
}
```

#### C. Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp>=1.3.0,<2.0",
        "--with", "pillow>=10.0.0",
        "python",
        "c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/mcp_server.py"
      ]
    }
  }
}
```

---

## 4. Danh Mục Đầy Đủ 42 MCP Tools (Theo Nhóm Nghiệp Vụ)

### 4.1. Hệ Thống & Quan Sát Viewport (System & Vision — 6 tools)
*Được triển khai tại: [handlers/system.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/system.rb) và [mcp_agent/tools/system.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/system.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_ping` | *(none)* | Kiểm tra trạng thái TCP bridge, phiên bản SketchUp, protocol và trạng thái Dev Mode |
| `sketchup_get_model_info` | *(none)* | Lấy tổng quan kích thước BoundingBox, số lượng tags, scenes, materials, revision của model |
| `sketchup_get_selection` | *(none)* | Trích xuất danh sách đối tượng người dùng đang click chọn trên màn hình Viewport |
| `sketchup_zoom_extents` | *(none)* | Tự động zoom vừa vặn toàn màn hình bao trọn toàn bộ hình khối trong không gian 3D |
| `sketchup_capture_viewport` | `width`, `height` | Chụp ảnh khung nhìn 3D hiện tại trả về dữ liệu hình ảnh trực tiếp cho AI phân tích thị giác |
| `sketchup_execute_ruby` | `code` | Thực thi mã Ruby tùy ý (*Bảo mật: Mặc định bị khóa `DEV_MODE_REQUIRED`*) |

---

### 4.2. Truy Vấn & Kiểm Tra Hình Học (Inspection — 3 tools)
*Được triển khai tại: [handlers/inspection.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/inspection.rb) và [mcp_agent/tools/inspection.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/inspection.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_get_entities` | `persistent_id`, `type_filter` | Liệt kê danh sách đối tượng trong model hoặc duyệt sâu vào một Group/Component |
| `sketchup_get_entity_info` | `persistent_id` | Lấy chi tiết thuộc tính một đối tượng: tên, phân loại, layer, vật liệu, diện tích/thể tích |
| `sketchup_get_bounding_box` | `persistent_ids` | Tính toán hộp bao giới hạn không gian tổng hợp (mm) của một hoặc nhiều đối tượng |

---

### 4.3. Dựng Hình Học Cơ Bản (Parametric Geometry — 3 tools)
*Được triển khai tại: [handlers/geometry.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/geometry.rb) và [mcp_agent/tools/geometry.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/geometry.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_create_box` | `width`, `depth`, `height`, `x,y,z`, `name`, `material` | Tạo khối hộp chữ nhật đặc 3D dạng Group khép kín |
| `sketchup_create_cylinder` | `radius`, `height`, `segments`, `x,y,z`, `name`, `material` | Tạo khối hình trụ tròn đứng với số phân đoạn đường tròn tùy chỉnh |
| `sketchup_create_wall` | `start_x,y`, `end_x,y`, `thickness`, `height`, `name` | Dựng bức tường thẳng kiến trúc theo 2 điểm mốc 2D sàn |

---

### 4.4. Biến Đổi Không Gian & Cấu Trúc (Transform & Hierarchy — 7 tools)
*Được triển khai tại: [handlers/transform.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/transform.rb) và [mcp_agent/tools/transform.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/transform.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_move` | `dx`, `dy`, `dz`, `persistent_ids` | Tịnh tiến đối tượng theo vector khoảng cách (mm) |
| `sketchup_copy` | `dx`, `dy`, `dz`, `persistent_ids` | Sao chép đối tượng sang vị trí mới, trả về PID mới độc lập |
| `sketchup_rotate` | `angle_degrees`, `axis` (`"z"|"x"|"y"`), `origin`, `persistent_ids` | Xoay đối tượng quanh trục chỉ định theo độ |
| `sketchup_scale` | `scale` / `scale_x,y,z`, `origin`, `persistent_ids` | Thu phóng kích thước đối tượng đồng nhất hoặc dị hướng |
| `sketchup_delete` | `persistent_ids` | Xóa an toàn các đối tượng khỏi mô hình |
| `sketchup_group` | `name`, `persistent_ids` | Gom các đối tượng cùng cấp chứa thành một Group mới (*Bảo vệ Container Safety*) |
| `sketchup_ungroup` | `persistent_ids` | Rã nhóm Group trở về container cha |

---

### 4.5. Quản Lý Vật Liệu & Bề Mặt (Materials — 5 tools)
*Được triển khai tại: [handlers/materials.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/materials.rb) và [mcp_agent/tools/materials.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/materials.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_get_materials` | `limit`, `offset`, `name_filter` | Liệt kê vật liệu trong thư viện mô hình, hỗ trợ phân trang và lọc tên |
| `sketchup_get_material_info` | `material_name` | Tra cứu mã màu Hex, RGB, độ mờ đục Alpha và đường dẫn texture |
| `sketchup_create_material` | `name`, `color` (`#RRGGBB` / `[r,g,b]`), `alpha`, `texture_path` | Tạo mới hoặc cập nhật thông số vật liệu |
| `sketchup_set_entity_material` | `material_name`, `persistent_ids` | Gán vật liệu lên Group/Component (*Chặn gán trực tiếp Face/Edge để bảo toàn hình học*) |
| `sketchup_clear_entity_material` | `persistent_ids` | Xóa lớp vật liệu gán đè, đưa đối tượng về màu vật liệu mặc định |

---

### 4.6. Siêu Dữ Liệu Thuộc Tính BIM (Attribute Dictionaries — 3 tools)
*Được triển khai tại: [handlers/attributes.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/attributes.rb) và [mcp_agent/tools/attributes.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/attributes.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_get_entity_attributes` | `persistent_id`, `dictionary_name` | Đọc toàn bộ các từ điển thuộc tính BIM/thông số kỹ thuật gắn trên đối tượng |
| `sketchup_set_entity_attributes` | `dictionary_name`, `attributes`, `persistent_ids` | Ghi cặp thuộc tính key/value (hỗ trợ String, Float, Integer, Boolean) vào đối tượng |
| `sketchup_delete_entity_attributes` | `dictionary_name`, `attribute_keys`, `persistent_ids` | Xóa các khóa thuộc tính chỉ định hoặc xóa trắng cả từ điển |

---

### 4.7. Quản Lý Component, Lắp Ráp & CAD Import (Components, Assembly & CAD — 7 tools)
*Được triển khai tại: [handlers/components.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/components.rb), [handlers/assembly.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/assembly.rb)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_create_component` | `name`, `description`, `persistent_ids` | Đóng gói Group hoặc các khối hình học thành ComponentDefinition tái sử dụng |
| `sketchup_get_component_definitions` | `name_filter`, `include_internal` | Lấy danh sách linh kiện trong mô hình (kèm số lượng instances đang đặt) |
| `sketchup_place_component_instance` | `definition_name`, `position`, `rotation`, `scale`, `parent_id` | Chèn thực thể linh kiện vào không gian tổng hoặc lồng vào cụm con (Sub-assembly) |
| `sketchup_make_component_unique` | `persistent_id`, `new_name` | Tách riêng một instance thành definition độc lập để tùy biến không ảnh hưởng bản gốc |
| `sketchup_save_component_to_skp` | `definition_name`, `file_path` | Xuất linh kiện ra tệp `.skp` độc lập lưu vào thư viện linh kiện dùng chung |
| `sketchup_load_component_from_skp` | `file_path` | Nạp linh kiện từ file `.skp` bên ngoài đĩa vào mô hình sẵn sàng lắp ráp |
| `sketchup_import_file` | `file_path`, `units`, `merge_coplanar_faces`, `orient_faces`, `preserve_origin`, `as_component`, `name` | Nạp trực tiếp tệp bản vẽ CAD 2D/3D (`.dwg`, `.dxf`, `.dae`, `.obj`, `.3ds`, `.ifc`, `.skp`) vào mô hình SketchUp |

---

### 4.8. Quản Lý Phân Tầng & Bản Vẽ Kỹ Thuật (Layers/Tags & Scenes — 8 tools)
*Được triển khai tại: [handlers/scenes.rb](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/handlers/scenes.rb) và [mcp_agent/tools/scenes.py](file:///c:/Users/thanh/AppData/Roaming/SketchUp/SketchUp%202026/SketchUp/Plugins/tu_sketchup_agent/mcp_agent/tools/scenes.py)*

| Tool Name | Tham Số Chính | Chức Năng & Đặc Điểm Nghiệp Vụ |
|---|---|---|
| `sketchup_get_layers` | `name_filter` | Liệt kê danh sách Tags/Layers trong mô hình kèm trạng thái ẩn/hiện và màu sắc |
| `sketchup_create_layer` | `name`, `color_hex` | Tạo Tag/Layer mới phục vụ phân loại quản lý hình khối |
| `sketchup_set_entity_layer` | `layer_name`, `persistent_ids` | Gán Tag cho Group/Component (*Chặn gán trực tiếp lên Face/Edge để giữ vững Layer0/Untagged*) |
| `sketchup_set_layer_visibility` | `layer_name`, `visible` / `layers` dictionary | Bật/tắt trạng thái ẩn/hiện của một hoặc nhiều Tags cùng lúc |
| `sketchup_get_scenes` | `name_filter` | Liệt kê danh sách các Scenes (Pages), metadata camera và danh sách tag bị ẩn |
| `sketchup_create_scene` | `name`, `hidden_layer_names`, `include_in_animation` | Tạo Scene mới lưu góc nhìn camera và cấu hình ẩn/hiện layer chuyên biệt |
| `sketchup_activate_scene` | `name` / `page_id` | Chuyển đổi mượt mà góc nhìn làm việc sang Scene chỉ định |
| `sketchup_set_camera_view` | `preset` (`"top"|"front"|"right"|"iso"...`), `perspective`, `zoom_extents` | Thiết lập camera góc chiếu 2D vuông góc (Orthographic) chuẩn bản vẽ kỹ thuật |

---

## 5. Các Tiêu Chuẩn Thiết Kế & An Toàn Vận Hành

### 5.1. Quy Ước Định Danh Đối Tượng (Persistent ID vs Entity ID)
- **`persistent_ids` (Khuyên dùng)**: Sử dụng mã định danh bền vững nguyên bản của SketchUp 64-bit (`persistent_id`). Định danh này không bao giờ thay đổi sau các thao tác Undo/Redo, lưu file hay mở lại session.
- **`entity_ids` (Runtime only)**: Chỉ có hiệu lực trong bộ nhớ tạm thời của phiên chạy hiện tại.
- **`ids` (Legacy)**: Hỗ trợ tương thích ngược, tự động phân tích và chuyển đổi thành persistent_ids.

### 5.2. Tính Toàn Vẹn Của Mô Hình & Transaction Atomic
Mọi thao tác thay đổi hình khối đều được bọc trong giao dịch `model.start_operation("AI Operation", true)` giúp người dùng có thể bấm `Ctrl + Z` để hoàn tác 1 bước duy nhất cho toàn bộ cụm biến đổi do AI thực hiện. Mỗi thao tác thành công đều tự động tăng số hiệu `model_revision`.

### 5.3. Bảo Vệ Phân Tầng Chuẩn SketchUp (Layer0 Protection)
Hệ thống tự động thực thi luật an toàn type-safety:
- **Tuyệt đối không gán Layer hoặc Material trực tiếp lên `Face` hoặc `Edge`**.
- Mọi hình học cơ bản luôn thuộc `Layer0` (`Untagged`). Việc gán Tag hoặc Material chỉ được phép thực hiện trên `Group` hoặc `ComponentInstance`.

### 5.4. Cơ Chế Hot-Reload Không Cần Khởi Động Lại SketchUp
Khi sửa đổi bất kỳ tệp nào trong `core/`, `services/`, hoặc `handlers/`:
- Chỉ cần vào menu **Extensions -> Tu SketchUp Agent -> Reload Extension** trong SketchUp.
- Vòng lặp TCP Bridge sẽ tự động dọn dẹp sạch sẽ socket cũ và nạp lại toàn bộ code mới trong **< 0.1 giây**.

---

## 6. Bộ Kiểm Thử Tự Động Toàn Diện (84/84 Tests PASS)

Dự án sở hữu 5 bộ kiểm thử tự động độc lập, xác thực trực tiếp trên phiên bản **SketchUp 2026**:

```powershell
# Chạy toàn bộ 5 bộ kiểm thử:
python -X utf8 tests/test_all_27_tools.py            # 27/27 PASS (100%)
python -X utf8 tests/regression_suite_v1.py          # 14/14 PASS (100%)
python -X utf8 tests/test_materials_attributes_v1_1.py # 14/14 PASS (100%)
python -X utf8 tests/test_components_assembly_v1_2.py  # 15/15 PASS (100% - bao gồm import_file)
python -X utf8 tests/test_layers_scenes_v1_3.py      # 14/14 PASS (100%)
```

> [!TIP]
> **Quy tắc an toàn khi chạy kiểm thử:** Trước khi chạy các test suites, vui lòng mở file mô hình trống `tests/models/regression_empty.skp` để tránh làm ảnh hưởng đến các bản vẽ thiết kế thật đang mở.

---

## 7. Showcase: Tự Động Hóa CAD-to-3D Nhà Cấp 4 (11.5m x 20.5m)

Tu SketchUp Agent đã ứng dụng thành công công cụ **`sketchup_import_file`** để chuyển hóa tự động bản vẽ thiết kế thi công AutoCAD DWG (`[BVTK] Nha cap 4, 11.5x20.5 _ KenhXayDung.vn.dwg`) thành mô hình kiến trúc 3D hoàn chỉnh trong SketchUp 2026:

### Quy Trình Xử Lý Tự Động:
1. **Nạp & Cách Ly Bản Vẽ CAD (`sketchup_import_file`)**:
   - Nạp tệp DWG hơn 124,000 thực thể vào SketchUp chỉ trong vài giây.
   - Phân loại toàn bộ các layer CAD sang Tag chuyên biệt `Tag_00_CAD_Drawing_DWG` để dễ dàng ẩn/hiện, không làm ảnh hưởng đến không gian dựng 3D.
2. **Giải Mã Thông Số Kiến Trúc (CAD Reverse Engineering)**:
   - **Lưới trục ngang (Trục 1 đến 7)**: Chiều dài 20.6m (khoảng cách 1-2: 2.5m sảnh chính; 2-3: 2.0m; 3-4: 4.1m; 4-5: 5.2m; 5-6: 3.5m; 6-7: 3.3m).
   - **Lưới trục dọc (Trục A đến D)**: Chiều rộng 10.1m + 1.4m sảnh phụ = 11.5m (A-B: 3.2m; B-C: 4.0m; C-D: 2.9m).
   - **Cao độ**: Cốt sàn +0.450m (3 bậc tam cấp), trần cao +4.35m (tường cao 3.9m), đỉnh mái +6.95m (độ dốc mái Thái 30°).
3. **Mô Hình Hóa 3D Đa Phân Lớp (BIM Architecture)**:
   - **Cốt nền & Tam cấp**: Nền móng +450mm ốp đá granit và hệ bậc tam cấp sảnh chính, sảnh phụ.
   - **Cột sảnh cổ điển**: 2 cột sảnh chính có đế vuông hoa văn và thân cột 400x400mm; 2 cột sảnh phụ có dầm đỡ mái dốc.
   - **Tường bao & Ngăn phòng**: Tường bao 220mm có chỉ nước ngang trang trí; tường ngăn 110mm hoàn thiện công năng 4 phòng ngủ, phòng khách, phòng thờ trang nghiêm, phòng sinh hoạt chung, bếp ăn và 2 cụm WC.
   - **Cửa đi & Cửa sổ**: Cửa đi chính 4 cánh pano gỗ kết hợp ô kính lấy sáng và tay nắm mạ vàng; các cửa sổ lùa đa cánh viền phào chỉ nổi.
   - **Mái Thái giật cấp**: Mái ngói đa tầng giật cấp, ngói bò đỉnh mái, diềm mái viền trắng, trán hồi tam giác có ô thoáng tròn và nan chớp trang trí.
4. **Kiến Trúc Module Thân & Mái (Cutaway Architecture)**:
   - Tách biệt thành 2 component độc lập: `Tag_01_Architecture_House_Body` và `Tag_01_Architecture_House_Roof`.
   - Cho phép bóc tách mái (Cutaway View) trong tích tắc để quan sát bố cục phân chia công năng nội thất bên trong.
5. **Hệ Thống 7 Góc Nhìn Bản Vẽ & Render Chuẩn Xuất Bản**:
   - `01_PhoiCanh_MatTien`: Phối cảnh góc 3D mặt tiền sảnh chính kết hợp nhân vật mẫu tỷ lệ kiến trúc.
   - `02_MatDung_Chinh`: Hình chiếu đứng 2D mặt tiền chính chuẩn bản vẽ kỹ thuật CAD (Orthographic).
   - `03_MatDung_Ben_Phai`: Hình chiếu đứng 2D mặt bên phải dài 20.6m.
   - `04_MatBang_TongThe`: Hình chiếu bằng 2D nhìn từ trên cao bao trọn toàn bộ mái và sân hè.
   - `05_PhoiCanh_ChimBay`: Phối cảnh góc chim bay (Bird's Eye View) từ trên cao 19m.
   - `06_PhoiCanh_BocMai_NoiThat`: Phối cảnh 3D góc cao bóc mái (Roof Hidden) nhìn rõ toàn bộ 4 phòng ngủ, phòng khách, phòng thờ và bếp ăn.
   - `07_MatBang_NoiThat_2D`: Mặt bằng 2D phân bổ công năng nội thất nhìn từ trên xuống trực giao.

---

## 8. Chính Sách Bảo Mật & Developer Mode

> [!CAUTION]
> Công cụ `sketchup_execute_ruby` cho phép thực thi mã lệnh Ruby trực tiếp trên máy cục bộ, vì vậy **mặc định luôn bị khóa** với mã lỗi `DEV_MODE_REQUIRED`.
> - Chỉ được kích hoạt có chủ đích khi người dùng bật menu **Extensions -> Tu SketchUp Agent -> Toggle Dev Mode** hoặc khởi chạy với biến môi trường `TU_SKETCHUP_DEV_MODE=1`.
> - Lệnh reload extension qua TCP bị chặn với mã `FORBIDDEN` nhằm triệt tiêu nguy cơ remote code injection qua socket cục bộ.

---

## 9. Lịch Sử Phiên Bản & Giao Thức (Changelog)

- **v1.3.1 (Hiện tại - Nhánh `master`)**:
  - Bổ sung công cụ thứ 42 **`sketchup_import_file`**: Nạp phổ quát các tệp bản vẽ CAD 2D/3D (`.dwg`, `.dxf`, `.dae`, `.obj`, `.3ds`, `.ifc`, `.skp`) vào SketchUp 2026.
  - Tự động hóa thành công toàn trình chuyển đổi CAD DWG thành mô hình 3D Nhà Cấp 4 (11.5m x 20.5m) với 7 scenes và renders độ phân giải cao 1920x1080.
  - Bộ kiểm thử mở rộng đạt **84/84 tests PASS (100%)**.
- **v1.3.0**:
  - Tái cấu trúc toàn diện kiến trúc sang Domain-Driven Modular Architecture (`core/`, `services/`, `handlers/`, `mcp_agent/`).
  - Bổ sung 8 công cụ quản lý Phân tầng (Layers/Tags) và Bản vẽ kỹ thuật 2D/3D (Scenes & Camera Presets).
  - Khắc phục triệt để vấn đề blocking socket, bổ sung vòng lặp thử lại `Errno::EADDRINUSE` và bảo vệ timer chống crash.
- **v1.2.0**: Bổ sung 6 công cụ quản lý Component Definitions, Sub-assembly lồng nhau, Make Unique, xuất/nhập tệp linh kiện `.skp`.
- **v1.1.0**: Bổ sung 8 công cụ quản lý vật liệu Hex/RGB/Alpha và siêu dữ liệu BIM Attribute Dictionaries.
- **v1.0.0**: Phiên bản phát hành đầu tiên với 27 công cụ dựng hình, biến đổi và quan sát viewport.

---

## 10. Giấy Phép (License)

Dự án phát triển bởi **Tu** phục vụ cộng đồng kiến trúc sư, kỹ sư thiết kế và lập trình viên tích hợp trí tuệ nhân tạo (AI-assisted CAD Design). Mọi quyền được bảo lưu © 2026.
