# Component Part Drawings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng khu vực bóc tách gia công chế tạo linh kiện (Component Parts Layout) và lập bản vẽ chi tiết cho 8 linh kiện cơ khí chính của máy uốn ống 3 trục lăn trong SketchUp 2026 kèm đường dóng kích thước gia công, 4 Scenes chi tiết và xuất bộ ảnh bản vẽ độ phân giải cao 1920x1080px.

**Architecture:** Sử dụng kiến trúc module tham số hóa trong SketchUp Ruby API, tuân thủ nghiêm ngặt chuẩn `sketchup-api` (bọc Undo `start_operation`, guard vector/normal, quản lý Group `Component_Parts_Layout`).

**Tech Stack:** SketchUp 2026 Ruby API, `tu-sketchup-agent` TCP server / MCP.

## Global Constraints
- Tất cả kích thước chế tạo theo đơn vị mm (Decimal mm).
- Bọc toàn bộ trong `model.start_operation("Create Component Part Drawings", true)` và `model.commit_operation`.
- Giữ nguyên máy lắp ráp hoàn chỉnh tại gốc tọa độ, bố trí bãi linh kiện gia công từ $X = 1200\text{mm}$ đến $3400\text{mm}$.

---

### Task 1: Dựng Bãi Gia Công & 8 Linh Kiện Bóc Tách (Component Parts Geometry)

**Files:**
- Create: `scratch/create_component_drawings.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Component_Parts_Layout` chứa 8 linh kiện cơ khí và bệ gá gia công.

- [ ] **Step 1: Dựng bệ gá phôi gia công bãi linh kiện**
- [ ] **Step 2: Dựng Con lăn uốn ống Ø110x90mm (rãnh uốn R13.5, lỗ trục Ø30)**
- [ ] **Step 3: Dựng Trục dẫn động con lăn Ø30x360mm kèm rãnh then**
- [ ] **Step 4: Dựng Má máy đứng đôi 320x440x16mm có rãnh phay trượt 60x180mm**
- [ ] **Step 5: Dựng Gối trượt chữ U 58x130x115mm**
- [ ] **Step 6: Dựng Trục vít me ren Tr28x5 dài 245mm & Tay vặn chữ T 340mm**
- [ ] **Step 7: Dựng Đĩa xích răng Z=16 & Tay quay cơ khí chữ Z bán kính 350mm**
- [ ] **Step 8: Dựng Khung chân đế bích sàn 420x480mm & Trụ hộp 100x100mm có 4 gân**

---

### Task 2: Ghi Kích Thước Chế Tạo Cho Từng Linh Kiện (Manufacturing Dimensions)

**Files:**
- Modify: `scratch/create_component_drawings.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Hệ thống kích thước dóng mm trên từng linh kiện trong `Component_Parts_Layout`.

- [ ] **Step 1: Ghi kích thước con lăn uốn (Ø110, Ø82, bề rộng 90, rãnh 32, lỗ Ø30)**
- [ ] **Step 2: Ghi kích thước trục dẫn động (Ø30, chiều dài 360, các đoạn lắp ghép)**
- [ ] **Step 3: Ghi kích thước má máy & gối trượt (320x440x16, rãnh 60x180, tâm lỗ 240)**
- [ ] **Step 4: Ghi kích thước vít me, tay quay và đĩa xích**

---

### Task 3: Thiết Lập 4 Scenes Chi Tiết & Xuất Bộ Ảnh Độ Nét Cao

**Files:**
- Modify: `scratch/create_component_drawings.rb`
- Outputs: 4 file ảnh 1920x1080px trong artifacts directory
- Update: `walkthrough.md`

- [ ] **Step 1: Tạo Scene `05_Tong_The_Linh_Kien` (Toàn cảnh bãi gia công)**
- [ ] **Step 2: Tạo Scene `06_Chi_Tiet_Con_Lan_Truc` (Bản vẽ con lăn & trục)**
- [ ] **Step 3: Tạo Scene `07_Chi_Tiet_Ma_May_Goi_Truot` (Bản vẽ má máy & gối trượt)**
- [ ] **Step 4: Tạo Scene `08_Chi_Tiet_VitMe_TayQuay_Xich` (Bản vẽ vít me, tay quay & xích)**
- [ ] **Step 5: Xuất trọn bộ ảnh và cập nhật walkthrough.md**
