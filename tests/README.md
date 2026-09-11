# TuSketchupAgent - Giao Thức & Tiêu Chuẩn Vận Hành v1.0.0

Tài liệu này định nghĩa cấu trúc chuẩn, quy ước giao thức và quy trình kiểm thử hồi quy (Regression Testing) cho **Tu SketchUp Agent**.

---

## 1. Khóa Giao Thức (Protocol Freeze: v1.0)

Giao thức truyền thông giữa Python MCP Server và Ruby TCP Bridge trong SketchUp được đóng băng tại mốc **Protocol Version 1.0**.

### 1.1. Cấu trúc Gói tin TCP
* **Transport**: TCP Socket qua `127.0.0.1:9876`.
* **Framing**: Length-prefixed JSON (`<payload_bytes_length>\n<json_payload>`).
* **Bảo mật**: Header chứa mã định danh bí mật `TOKEN: "tu-local-secret"`.
* **Traceability**: Mọi request đều mang `request_id` dạng `req_<uuid>`.

### 1.2. Quy ước Schema Định Danh Đối Tượng (ID Specification)
```text
persistent_ids : list[int | str]  => Định danh khuyến nghị chính thức (bền vững qua các phiên & Undo/Redo)
entity_ids     : list[int]        => Định danh tạm thời trong phiên làm việc hiện tại (Runtime Session)
ids            : list[int | str]  => [Legacy] Tham số cũ tương thích ngược, tự động ánh xạ sang persistent_ids
```

---

## 2. Cấu Trúc Thư Mục Kiểm Thử

```text
tests/
├── models/
│   └── regression_empty.skp       # Model SketchUp trắng dùng chuyên biệt cho regression
├── logs/                          # Lưu trữ nhật ký các lần chạy regression tự động
├── regression_suite_v1.py         # Bộ kiểm thử hồi quy 14 bài kiểm tra chuẩn v1.0
├── test_materials_attributes_v1_1.py # Bộ kiểm thử 14 bài chuyên sâu Materials & Attributes (v1.1)
├── test_components_assembly_v1_2.py  # Bộ kiểm thử 14 bài chuyên sâu Components & Assembly (v1.2)
├── test_layers_scenes_v1_3.py     # Bộ kiểm thử 14 bài chuyên sâu Layers & Scenes (v1.3)
├── test_all_27_tools.py           # Bộ kiểm thử toàn diện 27 tool nền tảng
└── README.md                      # Tài liệu chuẩn hóa giao thức & vận hành
```

---

## 3. Quy Trình Chạy Kiểm Thử Hồi Quy Có Ghi Log

Chạy lệnh PowerShell sau trước mỗi lần kiểm tra hoặc chuẩn bị phát hành:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = "tests/logs/regression_v1_$timestamp.log"

python -X utf8 tests/regression_suite_v1.py 2>&1 | Tee-Object -FilePath $log

if ($LASTEXITCODE -ne 0) {
  Write-Error "Regression failed. Không được phát hành bản mới."
  exit $LASTEXITCODE
}
```

Mỗi file log ghi lại:
- Thời điểm chạy (ISO-8601).
- Git revision / commit hash hiện tại.
- Phiên bản Protocol (`1.0`).
- Kết quả chi tiết từng bài test trong 14 bài kiểm tra.
- Xác nhận trạng thái dọn dẹp model.

---

## 4. Bộ Quy Tắc Tiến Hóa Phiên Bản (SemVer)

| Loại thay đổi | Định dạng phiên bản | Ví dụ |
|---|---|---|
| Sửa lỗi nội bộ, giữ nguyên response schema | `1.0.x` (Patch) | `1.0.1` |
| Bổ sung tool mới không phá vỡ tương thích cũ | `1.x.0` (Minor) | `1.1.0` |
| Thêm trường tùy chọn vào response | `1.x.0` (Minor) | `1.1.0` |
| Đổi tên trường, sửa đổi ý nghĩa ID, đổi framing TCP | `x.0.0` (Major) | `2.0.0` |

---

## 5. Danh Sách 14 Bài Test Chuẩn Trong `regression_suite_v1.py`

1. **TEST 01**: Handshake & kiểm tra `protocol_version: "1.0"`
2. **TEST 02**: `model_summary` & năng lực tra cứu `persistent_id`
3. **TEST 03**: Tạo khối hộp (`create_box`)
4. **TEST 04**: Tra cứu Bounding Box chuẩn xác (`get_bounding_box` với `persistent_ids`)
5. **TEST 05**: Tịnh tiến đối tượng (`move` với `persistent_ids`)
6. **TEST 06**: Nhân bản đối tượng (`copy` với `persistent_ids`)
7. **TEST 07**: Xoay quanh trục Z (`rotate` với `persistent_ids`)
8. **TEST 08**: Thu phóng kích thước (`scale` với `persistent_ids`)
9. **TEST 09**: Gom nhóm (`group` với `persistent_ids`)
10. **TEST 10**: Cơ chế an toàn Container (chặn gom nhóm xuyên container khác nhau)
11. **TEST 11**: Rã nhóm an toàn (`ungroup`)
12. **TEST 12**: Xóa dọn dẹp đối tượng (`delete` với `persistent_ids`)
13. **TEST 13**: Chụp ảnh Viewport chuẩn hóa (`capture_viewport`)
14. **TEST 14**: Cổng bảo mật TCP (chặn `reload_extension` qua mạng với mã `FORBIDDEN`)

---

## 6. Danh Sách 14 Bài Test Chuẩn Trong `test_components_assembly_v1_2.py`

1. **TEST 01**: Handshake & kiểm tra Protocol Version tương thích
2. **TEST 02**: Tạo đối tượng phôi chuẩn bị đóng gói component (`create_box`)
3. **TEST 03**: Tạo ComponentDefinition & Instance (`create_component`)
4. **TEST 04**: Tra cứu và lọc danh sách Component Definitions (`get_component_definitions`)
5. **TEST 05**: Chèn ComponentInstance theo tọa độ trực quan và góc xoay (`place_component_instance`)
6. **TEST 06**: Chèn ComponentInstance theo ma trận raw 4x4 OpenGL column-major
7. **TEST 07**: Chèn ComponentInstance lồng vào Sub-assembly qua `parent_id`
8. **TEST 08**: Tách nhánh definition độc lập cho instance (`make_component_unique`)
9. **TEST 09**: Xác nhận tính độc lập tuyệt đối giữa 2 definitions sau Make Unique
10. **TEST 10**: Xuất ComponentDefinition ra tệp `.skp` lưu trữ đĩa cứng (`save_component_to_skp`)
11. **TEST 11**: Nạp tệp `.skp` từ đĩa vào model dưới dạng definition mới (`load_component_from_skp`)
12. **TEST 12**: Chèn instance từ Component vừa nạp vào không gian mô hình
13. **TEST 13**: Xử lý ngoại lệ an toàn (definition không tồn tại, đường dẫn sai, sai đuôi file)
14. **TEST 14**: Dọn dẹp đối tượng thử nghiệm và file tạm trên đĩa cứng

---

## 7. Danh Sách 14 Bài Test Chuẩn Trong `test_layers_scenes_v1_3.py`

1. **TEST 01**: Handshake & kiểm tra Protocol Version tương thích `1.3`
2. **TEST 02**: Tạo mới các Layers/Tags (`create_layer`) kèm kiểm tra thuộc tính và mã màu hex
3. **TEST 03**: Lọc và liệt kê danh sách Layers (`get_layers`)
4. **TEST 04**: Dựng các khối hình học thử nghiệm (`create_box`)
5. **TEST 05**: Gán Layer cho các Group (`set_entity_layer`)
6. **TEST 06**: Type Safety Check: Chặn đúng việc gán layer lên Face/Edge để bảo toàn Layer0
7. **TEST 07**: Thay đổi trạng thái ẩn/hiện của Layer (`set_layer_visibility`)
8. **TEST 08**: Đặt camera theo góc chiếu chuẩn 2D Orthographic (`set_camera_view` preset Top)
9. **TEST 09**: Tạo Scene 2D chuẩn kèm góc camera và cờ thuộc tính (`create_scene`)
10. **TEST 10**: Tạo Scene 3D Isometric kèm cấu hình ẩn Tag (`create_scene` hidden_layer_names)
11. **TEST 11**: Liệt kê danh sách Scenes trong mô hình (`get_scenes`)
12. **TEST 12**: Chuyển đổi và kích hoạt qua lại giữa các Scenes (`activate_scene`)
13. **TEST 13**: Xử lý ngoại lệ an toàn (Scene không tồn tại, tên layer rỗng)
14. **TEST 14**: Dọn dẹp đối tượng thử nghiệm và phục hồi trạng thái visibility của layers
