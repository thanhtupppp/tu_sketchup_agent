# Scandinavian Sofa Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng hoàn chỉnh bộ sofa phòng khách Scandinavian (Sofa văng 3 chỗ, đệm ngồi, gối decor, đôn sofa, bàn trà lồng đôi, thảm sàn) với tỷ lệ kiến trúc chuẩn xác và phân cấp Group/Component trong SketchUp 2026 qua Ruby API.

**Architecture:** Sử dụng kiến trúc hướng mô-đun trong SketchUp Ruby API. Tạo một script Ruby tham số hóa hoàn chỉnh tạo ra hệ thống phân cấp Group, bảng vật liệu màu sắc tinh tế, bo vát hình khối mềm mại tự nhiên, và bọc trong single-operation transaction để an toàn tuyệt đối.

**Tech Stack:** SketchUp 2026 Ruby API, `tu-sketchup-agent` TCP server / MCP.

## Global Constraints
- Tất cả kích thước sử dụng đơn vị mm (`.mm` trong SketchUp Ruby API).
- Bọc toàn bộ trong `model.start_operation("Create Scandinavian Sofa Set", true)` và `model.commit_operation`.
- Tạo đầy đủ 6 vật liệu màu sắc phong cách Scandinavian (`Mat_Fabric_Grey`, `Mat_Oak_Wood`, `Mat_White_Marble`, `Mat_Pillow_Mustard`, `Mat_Pillow_Sage`, `Mat_Rug_Texture`).
- Tổ chức phân cấp Group cha - con rõ ràng, không tạo rời rạc trong Root.

---

### Task 1: Khởi tạo bảng vật liệu và thảm trải sàn (Materials & Rug)

**Files:**
- Create: `scratch/create_sofa_set.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: 6 đối tượng vật liệu chuẩn trong `model.materials` và Group `Area_Rug`.

- [ ] **Step 1: Định nghĩa script khởi tạo vật liệu màu sắc**
```ruby
model = Sketchup.active_model
materials = model.materials

palette = {
  "Mat_Fabric_Grey"     => [216, 219, 226],
  "Mat_Oak_Wood"        => [196, 154, 108],
  "Mat_White_Marble"   => [247, 249, 249],
  "Mat_Pillow_Mustard"  => [222, 155, 53],
  "Mat_Pillow_Sage"     => [108, 130, 118],
  "Mat_Rug_Texture"     => [176, 181, 179]
}

palette.each do |name, rgb|
  mat = materials[name] || materials.add(name)
  mat.color = Sketchup::Color.new(rgb[0], rgb[1], rgb[2])
end
```

- [ ] **Step 2: Dựng Group thảm sàn `Area_Rug` kích thước 2400x1600x8mm**
```ruby
rug_grp = root_group.entities.add_group
rug_grp.name = "Area_Rug"
r_pts = [
  [-1200.mm, -900.mm, 0],
  [1200.mm, -900.mm, 0],
  [1200.mm, 1100.mm, 0],
  [-1200.mm, 1100.mm, 0]
]
r_face = rug_grp.entities.add_face(r_pts)
r_face.pushpull(8.mm)
rug_grp.material = materials["Mat_Rug_Texture"]
```

---

### Task 2: Dựng Sofa văng 3 chỗ (`Sofa_3Seater`)

**Files:**
- Modify: `scratch/create_sofa_set.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Sofa_3Seater` gồm `Legs_and_Base`, `Backrest_Frame`, `Armrests`, `Seat_Cushions`, `Back_Cushions`, `Throw_Pillows`.

- [ ] **Step 1: Dựng khung đế và 4 chân gỗ sồi tiện thuôn choãi 10 độ**
- [ ] **Step 2: Dựng hai bên tay vịn bo góc mềm mại và thành tựa lưng**
- [ ] **Step 3: Dựng 3 khối đệm ngồi êm ái dày dặn cao độ 430mm**
- [ ] **Step 4: Dựng 3 khối đệm tựa lưng ngả thư giãn**
- [ ] **Step 5: Dựng 2 gối tựa decor màu mustard và sage đặt góc**

---

### Task 3: Dựng Bộ bàn trà lồng đôi & Đôn sofa (`Coffee_Table_Set` & `Sofa_Ottoman`)

**Files:**
- Modify: `scratch/create_sofa_set.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Coffee_Table_Nesting` và Group `Sofa_Ottoman`.

- [ ] **Step 1: Dựng bàn trà lớn Ø700mm, cao 420mm mặt đá marble trắng, chân kiềng gỗ**
- [ ] **Step 2: Dựng bàn trà nhỏ Ø500mm, cao 360mm mặt gỗ sồi tự nhiên**
- [ ] **Step 3: Dựng đôn sofa 650x500x430mm đồng bộ chân gỗ và đệm nỉ**

---

### Task 4: Kiểm tra trực quan & Chụp ảnh Viewport

**Files:**
- Test: `sketchup_zoom_extents`, `sketchup_capture_viewport`
- Verify: Kiểm tra hình ảnh thực tế và cấu trúc group trong model

- [ ] **Step 1: Thực thi tạo toàn bộ mô hình trong 1 transaction an toàn**
- [ ] **Step 2: Zoom extents và chụp ảnh viewport SketchUp**
- [ ] **Step 3: Báo cáo kết quả chi tiết kèm ảnh chụp**
