# Tu SketchUp Agent - MCP Bridge cho SketchUp 2026

Hệ thống kết nối AI (Antigravity IDE, Cursor, Claude Desktop) với **Trimble SketchUp 2026** thông qua kiến trúc **Model Context Protocol (MCP)** và **TCP Socket Bridge**.

```
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

## 1. Cấu trúc thư mục

```
c:\Users\thanh\AppData\Roaming\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent\
├── main.rb                    # Plugin Ruby chạy trong SketchUp (TCP Server + SketchUp API)
├── tu_sketchup_agent_loader.rb# File đăng ký Extension chuẩn SketchUp
├── mcp_server.py              # FastMCP Server (Python) giao tiếp với AI Client
├── test_client.py             # Script Python kiểm tra kết nối socket trực tiếp
└── README.md                  # Hướng dẫn sử dụng và cấu hình
```

---

## 2. Kích hoạt trong SketchUp 2026

### Cách 1: Tải trực tiếp từ Ruby Console
1. Mở SketchUp 2026.
2. Vào **Extensions -> Developer -> Ruby Console** (hoặc nhấn phím tắt).
3. Chạy lệnh:
   ```ruby
   load 'tu_sketchup_agent/main.rb'
   ```
4. Menu **Extensions -> Tu SketchUp Agent** sẽ xuất hiện. TCP Bridge được tự động bật sau 1 giây.

### Cách 2: Tự động tải khi mở SketchUp
- Copy file `tu_sketchup_agent_loader.rb` ra thư mục `Plugins` cha và đổi tên thành `tu_sketchup_agent.rb`:
  `c:\Users\thanh\AppData\Roaming\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent.rb`

---

## 3. Kiểm tra kết nối Socket (Standalone Test)

Trước khi cấu hình vào MCP Client, bạn có thể kiểm tra kết nối ngay bằng script test:

```powershell
cd "c:\Users\thanh\AppData\Roaming\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent"
python test_client.py
```

Nếu SketchUp đang mở và TCP Bridge đang chạy, bạn sẽ thấy:
- Lệnh `ping` trả về OK.
- Lệnh `model_summary` trả về thông số file đang mở.
- Khối hộp 500x500x800mm xuất hiện trực tiếp trong SketchUp.
- Chạy thử mã Ruby thành công.

---

## 4. Cấu hình MCP Client

### A. Dành cho Antigravity IDE
Mở file cấu hình MCP của Antigravity (hoặc thêm vào danh sách MCP Servers):

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

### B. Dành cho Cursor (`~/.cursor/mcp.json`)
Thêm vào file cấu hình MCP của Cursor:

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

### C. Dành cho Claude Desktop (`claude_desktop_config.json`)
Đường dẫn file: `%APPDATA%\Claude\claude_desktop_config.json`

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

## 5. Danh sách MCP Tools khả dụng

| Tool | Mô tả |
|------|-------|
| `sketchup_ping` | Kiểm tra trạng thái bridge TCP tới SketchUp |
| `sketchup_get_model_info` | Lấy kích thước mô hình, tags, materials, số lượng entity |
| `sketchup_get_selection` | Lấy chi tiết các đối tượng người dùng đang click chọn trong viewport |
| `sketchup_execute_ruby` | **Quyền năng tối thượng**: Thực thi bất kỳ đoạn mã Ruby nào trong SketchUp API với chế độ Undo an toàn |
| `sketchup_create_box` | Tạo khối hộp tham số (mm), vị trí x,y,z, gán tên và vật liệu |
| `sketchup_create_cylinder` | Tạo khối trụ tròn đứng (mm), bán kính, chiều cao, số phân đoạn |
| `sketchup_create_wall` | Dựng tường thẳng nối 2 điểm 2D với bề dày và chiều cao (mm) |
| `sketchup_capture_viewport` | Chụp ảnh màn hình 3D view hiện tại trả về ảnh cho Vision AI |
| `sketchup_zoom_extents` | Zoom toàn màn hình bao trọn mô hình |

---

## 6. Ví dụ câu lệnh ra lệnh cho AI

- *"Hãy kiểm tra xem SketchUp đã kết nối chưa và cho tôi biết model hiện tại có bao nhiêu đối tượng."*
- *"Vẽ một căn phòng 4 bức tường kích thước 4000x5000mm, cao 3000mm, độ dày tường 150mm."*
- *"Tạo một bàn gỗ kích thước 1200x600x750mm ở tọa độ gốc, sau đó zoom extents và chụp ảnh viewport lại cho tôi xem."*
- *"Chạy mã Ruby lặp qua toàn bộ model và đổi tất cả mặt phẳng có diện tích lớn hơn 2m2 sang màu đỏ."*
