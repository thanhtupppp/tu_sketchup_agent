# Kế Hoạch Thiết Kế & Triển Khai: CAD Import Tool (`sketchup_import_file`) & Dựng 3D Nhà Cấp 4

## 1. Mục Tiêu Tổng Quan
Phát triển công cụ MCP mới **`sketchup_import_file`** cho Tu SketchUp Agent, cho phép nạp trực tiếp các tệp bản vẽ kỹ thuật CAD (`.dwg`, `.dxf`, `.dae`, `.obj`, `.ifc`, `.3ds`) và mô hình 3D vào Trimble SketchUp 2026. Sau đó, nạp bản vẽ kiến trúc thực tế `[BVTK] Nha cap 4, 11.5x20.5 _ KenhXayDung.vn.dwg` và tiến hành các bước mô hình hóa 3D cho ngôi nhà.

---

## 2. Thiết Kế Công Cụ `sketchup_import_file`

### 2.1. Chữ Ký Công Cụ MCP (Python FastMCP)
```python
@mcp.tool()
def sketchup_import_file(
    file_path: str,
    units: str = "mm",
    merge_coplanar_faces: bool = True,
    orient_faces: bool = True,
    preserve_origin: bool = True,
    as_component: bool = True,
    name: Optional[str] = None
) -> str:
    """
    Nạp (Import) tệp bản vẽ CAD hoặc mô hình 3D ngoài đĩa vào SketchUp 2026.
    
    Định dạng hỗ trợ: .dwg, .dxf, .dae, .obj, .3ds, .skp, .ifc.
    
    Args:
        file_path: Đường dẫn tuyệt đối hoặc tương đối đến tệp cần nạp
        units: Đơn vị kích thước bản vẽ ("mm", "cm", "m", "in", "ft" - mặc định "mm")
        merge_coplanar_faces: Tự động hợp nhất các mặt phẳng đồng phẳng trong bản vẽ CAD
        orient_faces: Tự động định hướng đồng nhất mặt pháp tuyến (Front/Back face)
        preserve_origin: Bảo toàn tọa độ gốc (Origin) từ file CAD
        as_component: Nạp thành ComponentDefinition và đặt instance vào mô hình
        name: Tên đặt cho Component hoặc Group được nạp (tùy chọn)
    """
```

### 2.2. Xử Lý Phía Ruby Bridge (`handlers/assembly.rb`)
- Xác thực đường dẫn `file_path`, kiểm tra `File.exist?(path)` và phần mở rộng `.dwg`, `.dxf`, v.v.
- Xây dựng tùy chọn Importer Options tương thích SketchUp Ruby API:
  ```ruby
  options = {
    units: units_code,
    merge_coplanar_faces: merge_coplanar,
    orient_faces: orient_faces,
    preserve_origin: preserve_origin,
    show_summary: false
  }
  ```
- Sử dụng `model.definitions.import(file_path, options)` (hoặc fallback `model.import(file_path, false)` bọc trong `Operation.with_operation`).
- Tự động đặt Instance tại gốc tọa độ nếu `as_component: true`.
- Trích xuất metadata hộp bao BoundingBox (chiều rộng, sâu, cao, tâm), danh sách các Layers/Tags mới được nhập vào từ CAD, số lượng entities.

---

## 3. Các Bước Triển Khai

1. **Ruby Bridge**:
   - Thêm phương thức `import_file(args)` vào `TuSketchupAgent::Handlers::Assembly` (`handlers/assembly.rb`).
   - Đăng ký command `"import_file"` trong `Router.register("import_file")`.

2. **Python FastMCP**:
   - Thêm tool `sketchup_import_file` vào `mcp_agent/tools/assembly.py`.
   - Cập nhật ánh xạ proxy trong `mcp_server.py`.

3. **Kiểm Thử Tự Động**:
   - Viết test case nạp file CAD/SKP trong bộ kiểm thử.

4. **Thực Thi Nghiệp Vụ Với Bản Vẽ `[BVTK] Nha cap 4, 11.5x20.5 _ KenhXayDung.vn.dwg`**:
   - Mở SketchUp 2026.
   - Nạp file DWG vào SketchUp bằng `sketchup_import_file`.
   - Phân tích BoundingBox, các Layer (Tường, Cửa, Trục, Kích thước).
   - Chụp viewport để AI nắm bắt mặt bằng tổng thể ngôi nhà cấp 4.
   - Bắt đầu quy trình dựng 3D (sàn, tường, cửa, mái thái).
