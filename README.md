# Tu SketchUp Agent - MCP Bridge cho SketchUp 2026

Hệ thống cầu nối AI (Antigravity IDE, Cursor, Claude Desktop) với **Trimble SketchUp 2026** thông qua kiến trúc **Model Context Protocol (MCP)** và **TCP Socket Bridge**, hỗ trợ tự động hóa dựng hình, biến đổi hình học, quản lý vật liệu và siêu dữ liệu BIM.

```text
[ AI Assistant: Antigravity / Cursor / Claude ]
                     │  (stdio MCP Protocol)
                     ▼
       [ Python FastMCP Server ]
          (mcp_server.py chạy qua `uv run`)
                     │  (TCP Socket: 127.0.0.1:9876)
                     │  (Length-prefixed JSON)
                     ▼
    [ SketchUp Ruby Extension: TuSketchupAgent ]
          (main.rb - UI.start_timer thread-safe)
                     │
                     ▼
          [ SketchUp 2026 Ruby API ]
```

---

## 1. Cấu Trúc Thư Mục Dự Án

```text
tu_sketchup_agent/
├── main.rb                           # Extension Ruby chạy trong SketchUp (TCP Server + SketchUp API)
├── tu_sketchup_agent_loader.rb       # File đăng ký Extension chuẩn của SketchUp
├── mcp_server.py                     # FastMCP Server (Python) điều phối công cụ MCP
├── test_client.py                    # Script kiểm tra socket cơ bản
├── tests/                            # Bộ kiểm thử tự động & hồi quy
│   ├── models/
│   │   └── regression_empty.skp      # Model SketchUp trống dùng riêng cho kiểm thử
│   ├── logs/                         # Nhật ký lưu trữ các lần chạy test
│   ├── regression_suite_v1.py        # Bộ kiểm thử hồi quy 14 bài kiểm tra chuẩn Protocol v1.0
│   ├── test_materials_attributes_v1_1.py # Bộ kiểm thử 14 bài chuyên sâu cho Materials & Attributes
│   └── README.md                     # Tài liệu đặc tả giao thức & quy chuẩn kiểm thử
├── docs/                             # Bản thiết kế kỹ thuật & tài liệu hướng dẫn
└── README.md                         # Tài liệu hướng dẫn sử dụng chính thức
```

---

## 2. Kích Hoạt Trong SketchUp 2026

### Cách 1: Nạp trực tiếp từ Ruby Console
1. Mở SketchUp 2026.
2. Vào menu **Extensions -> Developer -> Ruby Console**.
3. Chạy lệnh:
   ```ruby
   load File.expand_path("~/AppData/Roaming/SketchUp/SketchUp 2026/SketchUp/Plugins/tu_sketchup_agent/main.rb")
   ```
4. Menu **Extensions -> Tu SketchUp Agent** sẽ xuất hiện và TCP Bridge tự động kích hoạt tại cổng `9876`.

### Cách 2: Tự động nạp khi khởi động SketchUp
Copy file `tu_sketchup_agent_loader.rb` ra thư mục cha `Plugins` và đổi tên thành `tu_sketchup_agent.rb`:
`%APPDATA%\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent.rb`

---

## 3. Cấu Hình MCP Client

### A. Antigravity IDE (`mcp_config.json`)
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

### B. Cursor (`~/.cursor/mcp.json`)
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

### C. Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
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

## 4. Danh Sách 27 MCP Tools Khả Dụng

### 4.1. Hệ Thống & Trạng Thái Kết Nối (System & Connection)
| Tool | Mô tả |
|---|---|
| `sketchup_ping` | Kiểm tra kết nối TCP bridge, phiên bản SketchUp, phiên bản giao thức và trạng thái Dev Mode |
| `sketchup_get_model_info` | Lấy tổng quan kích thước BoundingBox, tags/layers, scenes, materials và revision model |
| `sketchup_get_selection` | Lấy chi tiết các đối tượng đang được người dùng click chọn trong Viewport |
| `sketchup_zoom_extents` | Zoom toàn màn hình bao trọn tất cả hình khối trong mô hình |
| `sketchup_capture_viewport` | Chụp ảnh Viewport 3D góc nhìn hiện tại trả về ảnh cho AI quan sát (Vision) |

### 4.2. Truy Vấn Đối Tượng & Hình Học (Geometry Inspection)
| Tool | Mô tả |
|---|---|
| `sketchup_get_entities` | Liệt kê các đối tượng trong model hoặc bên trong một Group/Component, hỗ trợ lọc theo kiểu (`Face`, `Edge`, `Group`, ...) |
| `sketchup_get_entity_info` | Tra cứu chi tiết một đối tượng cụ thể (tên, kiểu, layer, vật liệu, tọa độ BoundingBox) |
| `sketchup_get_bounding_box` | Tính toán kích thước BoundingBox tổng hợp (mm) của một hoặc nhiều đối tượng |

### 4.3. Dựng Hình Học Tham Số (Parametric Geometry Creation)
| Tool | Mô tả |
|---|---|
| `sketchup_create_box` | Tạo khối hộp chữ nhật (mm) theo chiều rộng, sâu, cao, tọa độ x,y,z, tên và vật liệu |
| `sketchup_create_cylinder` | Tạo khối hình trụ đứng (mm) theo bán kính, chiều cao, số phân đoạn đáy, tên và vật liệu |
| `sketchup_create_wall` | Dựng bức tường kiến trúc nối 2 điểm 2D với độ dày và chiều cao chỉ định (mm) |

### 4.4. Biến Đổi Hình Học & Thứ Bậc (Transformation & Hierarchy)
| Tool | Mô tả |
|---|---|
| `sketchup_move` | Tịnh tiến đối tượng theo vector khoảng cách `[dx, dy, dz]` (mm) |
| `sketchup_copy` | Sao chép nhân bản đối tượng kèm vector dịch chuyển `[dx, dy, dz]` (mm) |
| `sketchup_rotate` | Xoay đối tượng quanh trục chỉ định (`"z"`, `"x"`, `"y"`) theo góc độ (degrees) và tâm xoay |
| `sketchup_scale` | Thu phóng kích thước đối tượng theo các trục `[x_scale, y_scale, z_scale]` quanh tâm |
| `sketchup_delete` | Xóa an toàn một hoặc nhiều đối tượng khỏi mô hình |
| `sketchup_group` | Gom các đối tượng cùng container cha thành một Group mới |
| `sketchup_ungroup` | Rã nhóm Group/Component trở về container chứa đối tượng |

### 4.5. Quản Lý Vật Liệu (Materials Management — Protocol v1.1)
| Tool | Mô tả |
|---|---|
| `sketchup_get_materials` | Liệt kê vật liệu trong model, hỗ trợ phân trang (`limit`, `offset`) và lọc tên (`name_filter`) |
| `sketchup_get_material_info` | Tra cứu thông số chi tiết của một vật liệu (mã Hex, RGB, độ trong suốt Alpha, texture) |
| `sketchup_create_material` | Tạo mới hoặc cập nhật vật liệu (hỗ trợ mã Hex `#RRGGBB`, mảng RGB, alpha, đường dẫn file texture) |
| `sketchup_set_entity_material` | Gán vật liệu cho Group/ComponentInstance. **Chặn gán trực tiếp lên Face/Edge** để bảo toàn hình học |
| `sketchup_clear_entity_material` | Xóa vật liệu gán đè trên Group/Component, đưa về màu mặc định |

### 4.6. Thuộc Tính Tùy Biến & BIM Metadata (Attributes — Protocol v1.1)
| Tool | Mô tả |
|---|---|
| `sketchup_get_entity_attributes` | Đọc toàn bộ hoặc lọc theo dictionary từ điển thuộc tính (BIM/specs metadata) của đối tượng |
| `sketchup_set_entity_attributes` | Ghi các cặp key/value (chuỗi, số thực, số nguyên, bool) vào Attribute Dictionary của Group/Component |
| `sketchup_delete_entity_attributes` | Xóa key cụ thể hoặc xóa toàn bộ từ điển thuộc tính khỏi đối tượng |

### 4.7. Thực Thi Mã Nhà Phát Triển (Developer Mode Execution)
| Tool | Mô tả |
|---|---|
| `sketchup_execute_ruby` | Thực thi đoạn mã Ruby tùy ý trực tiếp trong SketchUp 2026 |

> [!CAUTION]
> **CẢNH BÁO BẢO MẬT VỀ `sketchup_execute_ruby`:**
> `sketchup_execute_ruby` là API thực thi mã tùy ý (Arbitrary Code Execution). Công cụ này **mặc định bị vô hiệu hóa** với mã lỗi `DEV_MODE_REQUIRED`.
> - Chỉ được kích hoạt khi bật Dev Mode trực tiếp từ máy cục bộ qua menu **Extensions -> Tu SketchUp Agent -> Toggle Dev Mode** hoặc biến môi trường `TU_SKETCHUP_DEV_MODE=1`.
> - Tuyệt đối không bật Dev Mode trên các file mô hình production đang làm việc.
> - Lệnh reload extension qua TCP bị chặn vĩnh viễn với mã `FORBIDDEN` để tránh nguy cơ tấn công chiếm quyền qua socket cục bộ.

---

## 5. Quy Ước Định Danh Đối Tượng (Entity ID Specification)

Nhằm đảm bảo tính bền vững khi tương tác với SketchUp Ruby API, các công cụ mutation tuân thủ quy ước định danh:

```text
persistent_ids : list[int | str]  => [KHUYÊN DÙNG] Bền vững qua các lần lưu file, Undo/Redo và reload session
entity_ids     : list[int]        => Chỉ có giá trị trong phiên làm việc hiện tại (Runtime Session)
ids            : list[int | str]  => [LEGACY] Tham số cũ tương thích ngược, tự động ánh xạ sang persistent_ids
```

Mọi thao tác thay đổi hình khối đều được bọc trong một transaction `model.start_operation` có thể hoàn tác (`Undo`) nguyên tử, đồng thời cập nhật số hiệu `model_revision`.

---

## 6. Giao Thức & Khả Năng Tương Thích Ngược (Cách B)

Dự án áp dụng cơ chế tương thích ngược có kiểm soát giữa **Protocol v1.1** và **Protocol v1.0**:

* **Ruby Bridge**: Trả về `protocol_version: "1.1"` kèm `min_compatible_protocol_version: "1.0"` trên tất cả các endpoint.
* **Python FastMCP**: Hỗ trợ tập phiên bản `SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1"}`.
* Các client v1.0 tuân thủ kiểm tra tương thích đều có thể tiếp tục sử dụng các công cụ nền tảng mà không bị phá vỡ giao tiếp.

---

## 7. Quy Trình Kiểm Thử & An Toàn Vận Hành

### Quy Tắc Dùng Model Kiểm Thử Riêng
> [!IMPORTANT]
> **TUYỆT ĐỐI KHÔNG CHẠY TEST TRÊN FILE THIẾT KẾ THẬT.**
> Trước khi chạy kiểm thử, luôn mở file model trống dành riêng:
> `tests/models/regression_empty.skp`

### Chạy Bộ Kiểm Thử Tự Động

1. **Biên dịch & kiểm tra cú pháp**:
   ```powershell
   python -m py_compile mcp_server.py tests/test_materials_attributes_v1_1.py tests/regression_suite_v1.py
   python scratch/check_ruby_blocks.py
   git diff --check
   ```

2. **Chạy kiểm thử hồi quy nền tảng (Regression v1.0)**:
   ```powershell
   python -X utf8 tests/regression_suite_v1.py
   ```
   *(Kỳ vọng: 14/14 PASS 100%)*

3. **Chạy kiểm thử tính năng vật liệu & thuộc tính (Materials & Attributes v1.1)**:
   ```powershell
   python -X utf8 tests/test_materials_attributes_v1_1.py
   ```
   *(Kỳ vọng: 14/14 PASS 100%)*

---

## 8. Quy Trình Phát Triển & Đóng Góp (Git Workflow)

* **Nhánh cơ sở ổn định (Baseline)**: `master` (gắn tag `v1.0.0`).
* **Nhánh tính năng (Feature Branch)**: `feature/v1.1-materials-attributes` (gắn tag `v1.1.0`).
* **Quy chuẩn phát hành**:
  - Không sửa đổi hoặc ghi đè tag `v1.0.0` trên nhánh `master`.
  - Mọi tính năng mới được hoàn thiện, xác nhận 100% test pass trên branch riêng, sau đó tạo **Pull Request** về nhánh phát hành chính.
