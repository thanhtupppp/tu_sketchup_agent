# Technical Drawings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lập trọn bộ bản vẽ kỹ thuật cơ khí cho máy uốn ống 3 trục lăn trong SketchUp 2026 gồm hệ thống kích thước (Dimensions), 4 Scenes trực giao chuẩn (Đứng, Cạnh, Bằng, Trục đo) với camera Parallel Projection, Khung tên tiêu chuẩn & Bảng kê BOM, và xuất trọn bộ ảnh kỹ thuật 1920x1080px.

**Architecture:** Sử dụng SketchUp Ruby API (`add_dimension_linear`, `pages.add`, `write_image`), tuân thủ chuẩn `sketchup-api` (bọc Undo `start_operation`, tổ chức Group `Technical_Drawing_Annotations`).

**Tech Stack:** SketchUp 2026 Ruby API, `tu-sketchup-agent` TCP server / MCP.

## Global Constraints
- Kích thước đo đạc chính xác bằng đơn vị mm.
- Sử dụng camera Parallel Projection cho các hình chiếu phẳng trực giao.
- Bọc toàn bộ trong `model.start_operation("Create Technical Drawings", true)` và `model.commit_operation`.

---

### Task 1: Thiết Lập Hệ Thống Kích Thước Kỹ Thuật (Mechanical Dimensions)

**Files:**
- Create: `scratch/create_technical_drawings.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Technical_Drawing_Annotations` chứa toàn bộ kích thước dóng mm và bảng khung tên.

- [ ] **Step 1: Định nghĩa các đường dóng kích thước hình chiếu đứng**
  - Chiều cao tổng thể ($1355\text{mm}$)
  - Chiều cao tâm trục con lăn ($860\text{mm}$)
  - Khoảng cách 2 tâm trục dưới ($240\text{mm}$)
  - Chiều dài tay vặn chữ T ($340\text{mm}$)
  - Chiều rộng mặt bích đế sàn ($420\text{mm}$)
- [ ] **Step 2: Định nghĩa các đường dóng kích thước hình chiếu cạnh & bằng**
  - Chiều sâu bích đế sàn ($480\text{mm}$)
  - Khoảng cách 2 má máy ($140\text{mm}$)
  - Kích thước thân trụ đứng ($100\text{mm}$)
  - Khoảng cách tâm 4 bu-lông neo ($340 \times 400\text{mm}$)
- [ ] **Step 3: Dựng Khung tên kỹ thuật (Title Block) và Bảng kê danh mục chi tiết (BOM)**

---

### Task 2: Thiết Lập 4 Scenes Trực Giao Tiêu Chuẩn (Standard Orthographic Scenes)

**Files:**
- Modify: `scratch/create_technical_drawings.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: 4 Pages/Scenes trong `model.pages`.

- [ ] **Step 1: Tạo Scene `01_Hinh_Chieu_Dung` (Front Orthographic View)**
- [ ] **Step 2: Tạo Scene `02_Hinh_Chieu_Canh` (Right Side Orthographic View)**
- [ ] **Step 3: Tạo Scene `03_Hinh_Chieu_Bang` (Top Orthographic View)**
- [ ] **Step 4: Tạo Scene `04_Phoi_Canh_Truc_Do` (Isometric Technical View)**

---

### Task 3: Xuất Trọn Bộ Ảnh Bản Vẽ Kỹ Thuật & Báo Cáo Kết Quả

**Files:**
- Modify: `scratch/create_technical_drawings.rb`
- Outputs: 4 file ảnh 1920x1080px trong artifacts directory
- Update: `walkthrough.md`

- [ ] **Step 1: Chuyển qua từng Scene và xuất ảnh độ phân giải cao**
- [ ] **Step 2: Xác minh các file ảnh xuất thành công**
- [ ] **Step 3: Cập nhật walkthrough.md kèm đầy đủ các hình chiếu và bảng kê BOM**
