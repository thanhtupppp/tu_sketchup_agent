# Bản Thiết Kế Kỹ Thuật: Nhóm Công Cụ Chuyên Sâu Component & Assembly (Protocol v1.2)

Tài liệu này đặc tả thiết kế kỹ thuật cho nhóm công cụ chuyên sâu **Component & Assembly Management** dành cho `TuSketchupAgent`, chuẩn bị cho phiên bản nâng cấp giao thức **Protocol v1.2**.

---

## 1. Mục Tiêu & Bối Cảnh

### 1.1. Bối cảnh
Phiên bản v1.0 đã hoàn thiện các thao tác hình học thô và biến đổi cơ bản (`create_box`, `move`, `rotate`, `group`, `delete`...). Phiên bản v1.1 đã bổ sung quản lý vật liệu và thuộc tính BIM (`materials`, `attributes`).

Tuy nhiên, trong thiết kế cơ khí chính xác (máy uốn ống, chi tiết truyền động, bu-lông, bạc đạn) cũng như kiến trúc nội thất mô-đun:
* Việc chỉ dùng `Group` khiến dữ liệu hình học bị nhân bản tốn dung lượng RAM, không thể quản lý vòng đời linh kiện tái sử dụng.
* Thiếu khả năng nạp các thư viện linh kiện tiêu chuẩn (`.skp`) từ ổ đĩa và xuất các cụm chi tiết đã hoàn thiện ra catalog.
* Thiếu khả năng chèn một linh kiện vào nhiều vị trí khác nhau theo ma trận tọa độ/góc xoay (Assembly Placement).

### 1.2. Mục tiêu kỹ thuật
1. Cung cấp đầy đủ chu trình sống của **Component Definition** và **Component Instance**.
2. Hỗ trợ chèn linh kiện theo 2 phương thức tọa độ: tham số trực quan (`position`, `rotation`, `scale`) và ma trận thuần 16 phần tử (`matrix` 4x4).
3. Hỗ trợ lắp ráp cụm lồng nhau (Sub-assemblies) thông qua `parent_id`.
4. Hỗ trợ lưu trữ và tái sử dụng linh kiện thông qua file `.skp` trên ổ đĩa.
5. Duy trì 100% nguyên tắc an toàn: mọi mutation nằm trong `with_operation` có thể Undo nguyên tử, kiểm tra hợp lệ đường dẫn tệp và kiểu đối tượng.

---

## 2. Danh Sách 6 Công Cụ Component & Assembly (v1.2)

### 2.1. `sketchup_create_component`
* **Mục đích**: Đóng gói một Group hoặc tập hợp đối tượng hiện hữu thành một `ComponentDefinition` có tên định danh, đồng thời thay thế vị trí đó bằng một `ComponentInstance`.
* **Request Arguments**:
  * `persistent_id` (hoặc `persistent_ids`): ID của Group hoặc các đối tượng cần đóng gói.
  * `name`: Tên định danh cho Component Definition (ví dụ: `"Roller_Shaft_D35"`).
  * `description`: Mô tả chi tiết kỹ thuật / thông số linh kiện (tùy chọn).
* **Response Schema**:
  ```json
  {
    "ok": true,
    "operation": "create_component",
    "definition": {
      "name": "Roller_Shaft_D35",
      "guid": "...",
      "instances_count": 1,
      "description": "Trục con lăn máy uốn ống"
    },
    "instance": {
      "persistent_id": 52100,
      "entity_id": 1205,
      "type": "ComponentInstance",
      "name": ""
    },
    "model_revision": 250,
    "protocol_version": "1.2",
    "min_compatible_protocol_version": "1.0"
  }
  ```

### 2.2. `sketchup_place_component_instance`
* **Mục đích**: Chèn một thể hiện linh kiện (Instance) của một Definition đã có vào không gian 3D với vị trí, góc xoay và tỷ lệ chỉ định.
* **Request Arguments**:
  * `definition_name`: Tên Definition cần chèn (phải tồn tại trong model).
  * `position`: Mảng tọa độ `[x, y, z]` tính bằng mm (mặc định `[0, 0, 0]`).
  * `rotation`: Góc xoay quanh trục, ví dụ `{"axis": "z", "angle": 45.0}` hoặc mảng `[rot_x, rot_y, rot_z]` (độ).
  * `scale`: Hệ số thu phóng đồng đều `scale` (float) hoặc mảng `[sx, sy, sz]`.
  * `matrix`: (Nâng cao) Mảng 16 số thực đại diện cho ma trận affine 4x4.
  * `name`: Tên riêng gán cho instance này (ví dụ: `"Roller_Left"`).
  * `parent_id`: Persistent ID của Group/Component cha nếu muốn lắp ráp lồng bên trong cụm con (Sub-assembly).
* **Response Schema**:
  ```json
  {
    "ok": true,
    "operation": "place_component_instance",
    "definition_name": "Roller_Shaft_D35",
    "instance": {
      "persistent_id": 52150,
      "entity_id": 1210,
      "type": "ComponentInstance",
      "name": "Roller_Left"
    },
    "position_mm": [150.0, 0.0, 200.0],
    "bounds_mm": { "width": 70.0, "depth": 70.0, "height": 180.0 },
    "model_revision": 251,
    "protocol_version": "1.2",
    "min_compatible_protocol_version": "1.0"
  }
  ```

### 2.3. `sketchup_get_component_definitions`
* **Mục đích**: Liệt kê danh mục các Component Definition hiện có trong mô hình.
* **Request Arguments**:
  * `include_internal`: Boolean (mặc định `false`, bỏ qua các definition ẩn tự sinh của group).
  * `name_filter`: Lọc tên definition theo chuỗi ký tự.
* **Response Schema**:
  ```json
  {
    "ok": true,
    "total_count": 12,
    "definitions": [
      {
        "name": "Roller_Shaft_D35",
        "guid": "...",
        "instances_count": 2,
        "description": "Trục con lăn",
        "bounds_mm": { "width": 70.0, "depth": 70.0, "height": 180.0 }
      }
    ],
    "protocol_version": "1.2",
    "min_compatible_protocol_version": "1.0"
  }
  ```

### 2.4. `sketchup_make_component_unique`
* **Mục đích**: Tách riêng một ComponentInstance thành một Definition độc lập (`make_unique`), cho phép chỉnh sửa chi tiết mà không gây ảnh hưởng đến các instance khác cùng loại.
* **Request Arguments**:
  * `persistent_id` (hoặc `persistent_ids`): ID của instance cần tách unique.
  * `new_name`: Tên đặt cho definition mới sau khi tách (tùy chọn).
* **Response Schema**:
  ```json
  {
    "ok": true,
    "operation": "make_component_unique",
    "updated_count": 1,
    "new_definition_name": "Roller_Shaft_D35_Modified",
    "model_revision": 252,
    "protocol_version": "1.2",
    "min_compatible_protocol_version": "1.0"
  }
  ```

### 2.5. `sketchup_save_component_to_skp`
* **Mục đích**: Xuất một ComponentDefinition ra file `.skp` độc lập trên ổ đĩa để tích lũy vào thư viện linh kiện chuẩn (catalog).
* **Request Arguments**:
  * `definition_name`: Tên definition cần xuất.
  * `file_path`: Đường dẫn tuyệt đối file `.skp` cần lưu (ví dụ: `"C:/CAD_Library/Bearings/6204.skp"`).
* **Kiểm tra an toàn**:
  * Bắt buộc đuôi `.skp`.
  * Kiểm tra thư mục cha tồn tại.
  * Trả lỗi `FILE_ALREADY_EXISTS` nếu file đã có và không có cờ `overwrite: true`.

### 2.6. `sketchup_load_component_from_skp`
* **Mục đích**: Nạp một file `.skp` từ thư viện linh kiện ổ đĩa vào model hiện tại thành một ComponentDefinition.
* **Request Arguments**:
  * `file_path`: Đường dẫn tuyệt đối tới file `.skp`.
  * `definition_name`: Tên gán cho definition trong model (tùy chọn, mặc định lấy tên file).
* **Kiểm tra an toàn**:
  * Xác thực file tồn tại và có đuôi `.skp`.
  * Nếu definition cùng tên đã có trong model, hỗ trợ tái sử dụng hoặc đổi tên tự động tránh xung đột.

---

## 3. Kiến Trúc & Luồng Dữ Liệu

```text
[ AI Client ]
      │
      │ 1. sketchup_place_component_instance(definition_name="Bolt", position=[100,0,50], rotation={axis:"z", angle:90})
      ▼
[ FastMCP Server: mcp_server.py ]
      │ Chuyển đổi tham số position/rotation -> payload JSON
      │ (hoặc truyền ma trận matrix 16 số nếu được cấp)
      ▼ (TCP 127.0.0.1:9876)
[ Ruby Bridge: main.rb ]
      │ 1. Tra cứu Definition: defn = model.definitions[name]
      │ 2. Xây dựng Geom::Transformation:
      │      t_pos = Geom::Transformation.translation(Point3d.new(x.mm, y.mm, z.mm))
      │      t_rot = Geom::Transformation.rotation(origin, axis, angle.degrees)
      │      t_total = t_pos * t_rot
      │ 3. Wrap: with_operation(model, "AI - Place Component")
      │ 4. Chèn: inst = container.add_instance(defn, t_total)
      │ 5. Tăng model_revision
      ▼
[ Phản hồi JSON ] -> FastMCP -> AI quan sát & điều phối bước tiếp theo
```

---

## 4. Chiến Lược Giao Thức & Tương Thích Ngược (Protocol v1.2)

* **Protocol Version**: Nâng lên `1.2`.
* **Cơ chế tương thích ngược (Cách B tiếp tục phát huy)**:
  - Ruby Bridge trả về:
    ```ruby
    protocol_version: "1.2",
    min_compatible_protocol_version: "1.0"
    ```
  - FastMCP Server chấp nhận:
    ```python
    SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2"}
    ```
  - Toàn bộ client v1.0 và v1.1 cũ vẫn kết nối và hoạt động hoàn toàn bình thường.

---

## 5. Kế Hoạch Triển Khai & Kiểm Thử

1. **Phân nhánh Git**: Tạo branch riêng `feature/v1.2-components-assembly` từ `v1.1.0`.
2. **Triển khai Ruby Bridge**: Thêm 6 handler trong `main.rb`, bổ sung helper biến đổi affine `build_transformation(args)`.
3. **Triển khai FastMCP Server**: Khai báo 6 tool mới với docstrings và schema type hints đầy đủ.
4. **Bộ kiểm thử chuyên sâu v1.2 (`tests/test_components_assembly_v1_2.py`)**:
   - Test tạo component từ group.
   - Test chèn instance tại tọa độ và góc xoay chỉ định.
   - Test chèn instance với ma trận raw 4x4.
   - Test make unique và kiểm tra tính độc lập của 2 definition.
   - Test xuất file `.skp` ra thư mục tạm.
   - Test nạp lại file `.skp` vào một definition mới.
   - Test dọn dẹp và hoàn tác (Undo).
5. **Chạy hồi quy toàn bộ**: `tests/regression_suite_v1.py` và `tests/test_all_27_tools.py` để đảm bảo 0 lỗi hồi quy.
