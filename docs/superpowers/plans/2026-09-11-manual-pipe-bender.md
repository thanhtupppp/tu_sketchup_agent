# Manual 3-Roller Pipe Bender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng hoàn chỉnh mô hình 3D máy uốn ống 3 trục lăn bằng tay chân đứng có bộ truyền xích đôi (Pedestal Stand, Bending Head, 3 Rollers, Top Lead Screw, Rear Dual Sprocket Chain Drive, Front Crank, Bent Pipe Specimen) trong SketchUp 2026.

**Architecture:** Sử dụng kiến trúc module tham số hóa trong SketchUp Ruby API, tuân thủ nghiêm ngặt chuẩn `sketchup-api` (bọc Undo `start_operation`, guard vector/normal, cấu trúc Group phân cấp chi tiết).

**Tech Stack:** SketchUp 2026 Ruby API, `tu-sketchup-agent` TCP server / MCP.

## Global Constraints
- Tất cả kích thước sử dụng đơn vị mm (`.mm` trong SketchUp Ruby API).
- Bọc toàn bộ trong `model.start_operation("Create Manual Pipe Bender", true)` và `model.commit_operation`.
- Không sử dụng `entities.clear!`, dùng `erase_entities` an toàn.
- Đầy đủ 6 vật liệu cơ khí công nghiệp (`Mat_Machine_Blue`, `Mat_Steel_Machined`, `Mat_Thread_LeadScrew`, `Mat_Sprocket_Chain`, `Mat_Black_Hardware`, `Mat_Steel_Pipe`).

---

### Task 1: Dựng Cụm Khung Chân Trụ Đứng (Pedestal and Stand)

**Files:**
- Create: `scratch/create_pipe_bender.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Pedestal_and_Stand` gồm `Base_Plate_Bolts`, `Square_Column`, `Gusset_Plates`, `Top_Flange`.

- [ ] **Step 1: Định nghĩa palette vật liệu và helper vẽ hình học an toàn**
- [ ] **Step 2: Dựng mặt bích đế sàn 420x480x12mm và 4 bu-lông neo M14**
- [ ] **Step 3: Dựng trụ đứng thép hộp 100x100x720mm kèm 4 bản mã gân tam giác**
- [ ] **Step 4: Dựng mặt bích đỉnh 220x280x12mm kết nối đầu uốn**

---

### Task 2: Dựng Cụm Đầu Uốn 3 Trục & Vít Me Ép (Bending Head & Lead Screw)

**Files:**
- Modify: `scratch/create_pipe_bender.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Bending_Head_Chassis`, `Rollers_and_Bearings`, `LeadScrew_Mechanism`.

- [ ] **Step 1: Dựng 2 má thép đứng dày 16mm có rãnh phay dẫn hướng 60x180mm**
- [ ] **Step 2: Dựng xà ngang đỉnh dày 25mm và gối đỡ ren vít me**
- [ ] **Step 3: Dựng 2 con lăn tỳ dưới Ø110x80mm có rãnh uốn ống**
- [ ] **Step 4: Dựng con lăn ép trên Ø110mm cùng gối trượt dẫn hướng chữ U**
- [ ] **Step 5: Dựng trục vít me ren Tr28 và tay vặn chữ T đỉnh máy**

---

### Task 3: Dựng Bộ Truyền Xích Đôi, Tay Quay Lực & Phôi Ống Uốn (Transmission, Crank & Pipe)

**Files:**
- Modify: `scratch/create_pipe_bender.rb`
- Test: Gọi via `sketchup_execute_ruby` MCP tool

**Interfaces:**
- Produces: Group `Chain_Transmission_Rear`, `Drive_Crank_Front`, `Bent_Pipe_Specimen`.

- [ ] **Step 1: Dựng 2 đĩa xích Z=16 và sợi xích tải đôi ở mặt sau**
- [ ] **Step 2: Dựng tay quay cơ khí chữ Z dài 380mm có núm xoay ở mặt trước**
- [ ] **Step 3: Dựng phôi ống thép Ø27mm uốn cong cung tròn lồng qua 3 con lăn**

---

### Task 4: Kiểm Tra Trực Quan Viewport & Báo Cáo Kết Quả

**Files:**
- Test: `sketchup_zoom_extents`, `sketchup_capture_viewport`
- Verify: Kiểm tra hình khối cơ khí, góc máy kỹ thuật 3/4 và độ chính xác tỷ lệ

- [ ] **Step 1: Thực thi tạo toàn bộ máy uốn ống trong SketchUp 2026**
- [ ] **Step 2: Zoom extents và căn chỉnh góc camera kỹ thuật công nghiệp**
- [ ] **Step 3: Chụp ảnh Viewport, lưu artifact và cập nhật walkthrough.md**
