# Component & Assembly Management (Protocol v1.2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai hoàn chỉnh 6 công cụ chuyên sâu quản lý Component Definitions, chèn Instance đa tọa độ/ma trận, Sub-assemblies và nạp/lưu thư viện tệp `.skp` cho TuSketchupAgent nâng cấp lên Protocol v1.2.

**Architecture:** Bổ sung router và handlers trong Ruby bridge (`main.rb`), cung cấp helper ma trận biến đổi affine `build_transformation(args)`, khai báo 6 công cụ FastMCP tương ứng trong `mcp_server.py`, đồng thời bảo đảm cơ chế tương thích ngược (Cách B) và bộ kiểm thử tự động toàn diện `tests/test_components_assembly_v1_2.py`.

**Tech Stack:** SketchUp 2026 Ruby API, Python FastMCP (mcp >= 1.3.0), TCP Socket Bridge (Length-prefixed JSON), Git.

## Global Constraints
- Protocol Version: `1.2`, Min Compatible: `1.0` (Cách B).
- ID Specification: Khuyên dùng `persistent_ids`, hỗ trợ `entity_ids`, legacy `ids`.
- Mọi mutation bắt buộc đóng gói trong `with_operation(model, name)` để có thể hoàn tác nguyên tử (Undo).
- Bắt buộc cập nhật `model_revision` và `mcp_revision` sau mỗi mutation.
- Type Safety: Thao tác component chỉ áp dụng lên `Sketchup::Group`, `Sketchup::ComponentInstance` hoặc `Sketchup::ComponentDefinition`.
- An toàn tệp tin: Kiểm tra phần mở rộng `.skp` và xác thực đường dẫn hợp lệ khi nạp/xuất file.

---

### Task 1: Thiết Lập Branch & Nâng Cấp Handshake Protocol v1.2

**Files:**
- Modify: `main.rb:14-15`
- Modify: `mcp_server.py:23-24`
- Test: `tests/regression_suite_v1.py`

**Interfaces:**
- Consumes: Baseline Git tag `v1.1.0`.
- Produces: Branch `feature/v1.2-components-assembly`, `PROTOCOL_VERSION = "1.2"`, `SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2"}`.

- [ ] **Step 1: Tạo và chuyển sang branch mới**
```bash
git checkout -b feature/v1.2-components-assembly
```

- [ ] **Step 2: Nâng cấp protocol version trong `main.rb`**
Cập nhật lines 14-15 trong `main.rb`:
```ruby
  PROTOCOL_VERSION = "1.2"
  MIN_COMPATIBLE_PROTOCOL_VERSION = "1.0"
```

- [ ] **Step 3: Cập nhật protocol version trong `mcp_server.py`**
Cập nhật lines 23-24 trong `mcp_server.py`:
```python
PROTOCOL_VERSION = "1.2"
SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1", "1.2"}
```

- [ ] **Step 4: Cập nhật danh sách protocol mong đợi trong regression suite**
Trong `tests/regression_suite_v1.py`:
```python
EXPECTED_PROTOCOLS = ["1.0", "1.1", "1.2"]
```

- [ ] **Step 5: Kiểm tra biên dịch và commit**
```bash
python -m py_compile mcp_server.py tests/regression_suite_v1.py
git diff --check
git add main.rb mcp_server.py tests/regression_suite_v1.py
git commit -m "chore: bump protocol version to 1.2 with backward compatibility"
```

---

### Task 2: Xây Dựng Helper Biến Đổi Affine `build_transformation` trong Ruby

**Files:**
- Modify: `main.rb` (sau phần `validate_group_or_component!`)

**Interfaces:**
- Consumes: Hash `args` chứa `position`, `rotation`, `scale`, hoặc `matrix`.
- Produces: `build_transformation(args) -> Geom::Transformation`.

- [ ] **Step 1: Thêm hàm `build_transformation` vào `main.rb`**
```ruby
  def build_transformation(args)
    # 1. Chế độ Raw Matrix 4x4 (16 số thực)
    if args["matrix"].is_a?(Array) && args["matrix"].length == 16
      raw_vals = args["matrix"].map { |v| Float(v) }
      return Geom::Transformation.new(raw_vals)
    end

    # 2. Chế độ tham số trực quan: Scale * Rotation * Translation
    # Scale
    t_scale = if args["scale"].is_a?(Array) && args["scale"].length == 3
      Geom::Transformation.scaling(Float(args["scale"][0]), Float(args["scale"][1]), Float(args["scale"][2]))
    elsif args["scale"] && Float(args["scale"]) != 1.0
      s = Float(args["scale"])
      Geom::Transformation.scaling(s, s, s)
    else
      Geom::Transformation.new
    end

    # Rotation
    t_rot = Geom::Transformation.new
    if args["rotation"].is_a?(Hash)
      axis_str = args["rotation"]["axis"].to_s.downcase
      axis_vec = case axis_str
      when "x" then Geom::Vector3d.new(1, 0, 0)
      when "y" then Geom::Vector3d.new(0, 1, 0)
      else Geom::Vector3d.new(0, 0, 1)
      end
      angle_deg = Float(args["rotation"]["angle"] || 0.0)
      t_rot = Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), axis_vec, angle_deg.degrees) if angle_deg != 0.0
    elsif args["rotation"].is_a?(Array) && args["rotation"].length == 3
      rx, ry, rz = args["rotation"].map { |v| Float(v) }
      tr_x = rx != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0,0,0), Geom::Vector3d.new(1,0,0), rx.degrees) : Geom::Transformation.new
      tr_y = ry != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0,0,0), Geom::Vector3d.new(0,1,0), ry.degrees) : Geom::Transformation.new
      tr_z = rz != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0,0,0), Geom::Vector3d.new(0,0,1), rz.degrees) : Geom::Transformation.new
      t_rot = tr_z * tr_y * tr_x
    end

    # Translation (Position mm)
    t_pos = Geom::Transformation.new
    if args["position"].is_a?(Array) && args["position"].length >= 3
      px = Float(args["position"][0]).mm
      py = Float(args["position"][1]).mm
      pz = Float(args["position"][2]).mm
      t_pos = Geom::Transformation.translation(Geom::Point3d.new(px, py, pz))
    end

    t_pos * t_rot * t_scale
  end
```

- [ ] **Step 2: Kiểm tra cân bằng cú pháp Ruby**
```bash
python scratch/check_ruby_blocks.py
```

- [ ] **Step 3: Commit**
```bash
git add main.rb
git commit -m "feat(ruby): add build_transformation helper for flexible assembly placement"
```

---

### Task 3: Triển Khai Handlers `create_component` và `get_component_definitions`

**Files:**
- Modify: `main.rb` (Section `Dispatch API Handlers - Components & Assembly`)
- Modify: `main.rb` (Section `dispatch router`)

**Interfaces:**
- Consumes: `model.definitions`, `group.to_component`.
- Produces: Commands `"create_component"`, `"get_component_definitions"`.

- [ ] **Step 1: Viết method `create_component`**
```ruby
  def create_component(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["name"] || args["component_name"]).to_s.strip
    raise ArgumentError, "Tên component không được để trống" if name.empty?

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để tạo component" if entities.empty?

    description = args["description"].to_s

    instance = nil
    definition = nil

    with_operation(model, "AI - Create Component") do
      if entities.length == 1 && entities.first.is_a?(Sketchup::Group)
        instance = entities.first.to_component
      else
        temp_group = model.active_entities.add_group(entities)
        instance = temp_group.to_component
      end
      definition = instance.definition
      definition.name = name
      definition.description = description unless description.empty?
      bump_model_revision
    end

    {
      ok: true,
      operation: "create_component",
      definition: {
        name: definition.name,
        guid: definition.guid,
        instances_count: definition.instances.length,
        description: definition.description
      },
      instance: entity_metadata(instance),
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 2: Viết method `get_component_definitions`**
```ruby
  def get_component_definitions(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    include_internal = args["include_internal"] == true
    name_filter = args["name_filter"].to_s.downcase.strip

    items = []
    model.definitions.each do |defn|
      next if !include_internal && defn.group?
      next if !name_filter.empty? && !defn.name.downcase.include?(name_filter)

      bbox = defn.bounds
      items << {
        name: defn.name,
        guid: defn.guid,
        instances_count: defn.instances.length,
        description: defn.description,
        is_group_internal: defn.group?,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1)
        } : nil
      }
    end

    {
      ok: true,
      total_count: items.length,
      definitions: items,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 3: Đăng ký vào `dispatch` router trong `main.rb`**
```ruby
    when "create_component"
      create_component(args)
    when "get_component_definitions"
      get_component_definitions(args)
```

- [ ] **Step 4: Kiểm tra cú pháp và commit**
```bash
python scratch/check_ruby_blocks.py
git add main.rb
git commit -m "feat(ruby): implement create_component and get_component_definitions handlers"
```

---

### Task 4: Triển Khai Handlers `place_component_instance` và `make_component_unique`

**Files:**
- Modify: `main.rb`

**Interfaces:**
- Consumes: `build_transformation(args)`, `model.definitions[name]`, `inst.make_unique`.
- Produces: Commands `"place_component_instance"`, `"make_component_unique"`.

- [ ] **Step 1: Viết method `place_component_instance`**
```ruby
  def place_component_instance(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["definition_name"] || args["name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

    defn = model.definitions[name]
    raise ArgumentError, "Không tìm thấy ComponentDefinition có tên '#{name}' trong model" unless defn

    # Xác định container (mặc định model.active_entities hoặc bên trong parent_id)
    container = model.active_entities
    if args["parent_id"]
      parent_entity = find_entity_by_persistent_id(model, args["parent_id"]) || find_entity_by_id(model, args["parent_id"])
      raise ArgumentError, "Không tìm thấy parent entity với ID #{args['parent_id']}" unless parent_entity
      if parent_entity.is_a?(Sketchup::Group)
        container = parent_entity.entities
      elsif parent_entity.is_a?(Sketchup::ComponentInstance)
        container = parent_entity.definition.entities
      else
        raise ArgumentError, "Parent entity phải là Group hoặc ComponentInstance"
      end
    end

    transform = build_transformation(args)
    inst_name = args["instance_name"].to_s.strip

    instance = nil
    with_operation(model, "AI - Place Component Instance") do
      instance = container.add_instance(defn, transform)
      instance.name = inst_name unless inst_name.empty?
      bump_model_revision
    end

    bbox = instance.bounds
    {
      ok: true,
      operation: "place_component_instance",
      definition_name: defn.name,
      instance: entity_metadata(instance),
      position_mm: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)],
      bounds_mm: {
        width: bbox.width.to_mm.round(1),
        depth: bbox.height.to_mm.round(1),
        height: bbox.depth.to_mm.round(1)
      },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 2: Viết method `make_component_unique`**
```ruby
  def make_component_unique(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy instance nào để make_unique" if entities.empty?

    components = entities.select { |e| e.is_a?(Sketchup::ComponentInstance) }
    raise ArgumentError, "Không có ComponentInstance nào trong danh sách được cung cấp" if components.empty?

    new_name = args["new_name"].to_s.strip

    with_operation(model, "AI - Make Component Unique") do
      components.each do |comp|
        comp.make_unique
        comp.definition.name = new_name if !new_name.empty? && components.length == 1
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "make_component_unique",
      updated_count: components.length,
      new_definition_name: components.first.definition.name,
      missing_ids: missing_ids,
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 3: Đăng ký router trong `dispatch`**
```ruby
    when "place_component_instance"
      place_component_instance(args)
    when "make_component_unique"
      make_component_unique(args)
```

- [ ] **Step 4: Kiểm tra cú pháp và commit**
```bash
python scratch/check_ruby_blocks.py
git add main.rb
git commit -m "feat(ruby): implement place_component_instance and make_component_unique handlers"
```

---

### Task 5: Triển Khai Handlers Nạp/Xuất File `.skp` (`save_component_to_skp`, `load_component_from_skp`)

**Files:**
- Modify: `main.rb`

**Interfaces:**
- Consumes: `defn.save_as(path)`, `model.definitions.load(path)`.
- Produces: Commands `"save_component_to_skp"`, `"load_component_from_skp"`.

- [ ] **Step 1: Viết method `save_component_to_skp`**
```ruby
  def save_component_to_skp(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["definition_name"] || args["name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

    defn = model.definitions[name]
    raise ArgumentError, "Không tìm thấy definition '#{name}' trong model" unless defn

    file_path = args["file_path"].to_s.strip
    raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
    raise ArgumentError, "Đường dẫn file phải có đuôi .skp" unless file_path.downcase.end_with?(".skp")

    dir = File.dirname(file_path)
    raise ArgumentError, "Thư mục không tồn tại: #{dir}" unless Dir.exist?(dir)

    overwrite = args["overwrite"] == true
    if File.exist?(file_path) && !overwrite
      raise ArgumentError, "File '#{file_path}' đã tồn tại (dùng overwrite: true nếu muốn ghi đè)"
    end

    success = defn.save_as(file_path)
    raise "Lỗi lưu definition ra file .skp" unless success

    {
      ok: true,
      operation: "save_component_to_skp",
      definition_name: defn.name,
      file_path: file_path,
      file_size_bytes: File.size(file_path),
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 2: Viết method `load_component_from_skp`**
```ruby
  def load_component_from_skp(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    file_path = args["file_path"].to_s.strip
    raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
    raise ArgumentError, "File không tồn tại: #{file_path}" unless File.exist?(file_path)
    raise ArgumentError, "File phải có định dạng .skp" unless file_path.downcase.end_with?(".skp")

    defn = nil
    with_operation(model, "AI - Load Component From SKP") do
      defn = model.definitions.load(file_path)
      if args["definition_name"] && !args["definition_name"].to_s.strip.empty?
        defn.name = args["definition_name"].to_s.strip
      end
      bump_model_revision
    end

    bbox = defn.bounds
    {
      ok: true,
      operation: "load_component_from_skp",
      definition: {
        name: defn.name,
        guid: defn.guid,
        instances_count: defn.instances.length,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1)
        } : nil
      },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end
```

- [ ] **Step 3: Đăng ký router trong `dispatch`**
```ruby
    when "save_component_to_skp"
      save_component_to_skp(args)
    when "load_component_from_skp"
      load_component_from_skp(args)
```

- [ ] **Step 4: Kiểm tra cú pháp và commit**
```bash
python scratch/check_ruby_blocks.py
git add main.rb
git commit -m "feat(ruby): implement save_component_to_skp and load_component_from_skp handlers"
```

---

### Task 6: Khai Báo 6 Tool FastMCP Trong Python (`mcp_server.py`)

**Files:**
- Modify: `mcp_server.py`

**Interfaces:**
- Consumes: TCP commands `"create_component"`, `"get_component_definitions"`, `"place_component_instance"`, `"make_component_unique"`, `"save_component_to_skp"`, `"load_component_from_skp"`.
- Produces: 6 `@mcp.tool()` tương ứng.

- [ ] **Step 1: Viết 6 wrapper tools trong `mcp_server.py`**
  - `sketchup_create_component(name, persistent_ids, description)`
  - `sketchup_get_component_definitions(name_filter, include_internal)`
  - `sketchup_place_component_instance(definition_name, position, rotation, scale, matrix, instance_name, parent_id)`
  - `sketchup_make_component_unique(persistent_ids, new_name)`
  - `sketchup_save_component_to_skp(definition_name, file_path, overwrite)`
  - `sketchup_load_component_from_skp(file_path, definition_name)`

- [ ] **Step 2: Kiểm tra biên dịch Python**
```bash
python -m py_compile mcp_server.py
```

- [ ] **Step 3: Commit**
```bash
git add mcp_server.py
git commit -m "feat(mcp): register 6 Component and Assembly tools in FastMCP server"
```

---

### Task 7: Xây Dựng Bộ Kiểm Thử Tự Động v1.2 & Chạy Hồi Quy Toàn Diện

**Files:**
- Create: `tests/test_components_assembly_v1_2.py`
- Test: `tests/test_all_27_tools.py`
- Test: `tests/regression_suite_v1.py`

- [ ] **Step 1: Tạo `tests/test_components_assembly_v1_2.py`**
Xây dựng 14 test case bao quát đầy đủ 6 tool mới:
1. `TEST 01`: Handshake Protocol v1.2.
2. `TEST 02`: Tạo Box cơ sở.
3. `TEST 03`: `create_component` biến Box thành Definition `"Comp_Test_Roller"`.
4. `TEST 04`: `get_component_definitions` xác nhận tìm thấy definition mới.
5. `TEST 05`: `place_component_instance` với tọa độ trực quan `position=[200, 300, 0]` và `rotation={"axis":"z", "angle":45}`.
6. `TEST 06`: `place_component_instance` với ma trận raw 4x4.
7. `TEST 07`: `place_component_instance` lồng vào Group cha (`parent_id`).
8. `TEST 08`: `make_component_unique` trên một instance, gán tên mới `"Comp_Test_Roller_Unique"`.
9. `TEST 09`: Kiểm tra tính độc lập của definition mới.
10. `TEST 10`: `save_component_to_skp` xuất ra file `tests/scratch/roller.skp`.
11. `TEST 11`: `load_component_from_skp` nạp lại file với tên `"Comp_Imported_Roller"`.
12. `TEST 12`: Chèn instance của component đã nạp.
13. `TEST 13`: Kiểm tra xử lý lỗi (tên không tồn tại, đường dẫn sai).
14. `TEST 14`: Dọn dẹp toàn bộ đối tượng thử nghiệm và file tạm.

- [ ] **Step 2: Nạp lại Extension trong SketchUp 2026 và chạy test**
```powershell
python -X utf8 tests/test_components_assembly_v1_2.py
```
*(Kỳ vọng: 14/14 PASS)*

- [ ] **Step 3: Chạy lại bộ hồi quy nền tảng**
```powershell
python -X utf8 tests/regression_suite_v1.py
python -X utf8 tests/test_materials_attributes_v1_1.py
python -X utf8 tests/test_all_27_tools.py
```
*(Kỳ vọng: Toàn bộ các suite đều 100% PASS)*

- [ ] **Step 4: Commit**
```bash
git add tests/test_components_assembly_v1_2.py
git commit -m "test: add comprehensive 14 tests suite for components and assembly tools"
```

---

### Task 8: Đồng Bộ Tài Liệu README & Gắn Tag Release v1.2.0

**Files:**
- Modify: `README.md`
- Modify: `tests/README.md`

- [ ] **Step 1: Cập nhật danh sách 33 công cụ trong `README.md`**
Bổ sung bảng phân nhóm "Quản Lý Component & Lắp Ráp (Assembly Management — Protocol v1.2)".

- [ ] **Step 2: Kiểm tra vệ sinh Git**
```powershell
git diff --check
git status --short
```

- [ ] **Step 3: Commit, gắn tag v1.2.0 và đẩy lên GitHub**
```powershell
git add README.md tests/README.md
git commit -m "docs: document 33 MCP tools including component and assembly management"
git tag -a v1.2.0 -m "SketchUp Agent protocol v1.2.0"
git push -u origin feature/v1.2-components-assembly
git push origin v1.2.0
```
