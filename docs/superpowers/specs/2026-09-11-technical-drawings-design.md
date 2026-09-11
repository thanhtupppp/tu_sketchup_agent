# Thiết Kế Bản Vẽ Kỹ Thuật Máy Uốn Ống 3 Trục Lăn Bằng Tay

**Ngày lập:** 2026-09-11  
**Mục tiêu:** Thiết lập trọn bộ bản vẽ kỹ thuật cơ khí tiêu chuẩn cho máy uốn ống 3 trục lăn bằng tay trong SketchUp 2026, bao gồm 4 Scenes trực giao chuẩn (Đứng, Cạnh, Bằng, Trục đo) với camera Chiếu song song (Parallel Projection), hệ thống kích thước hình học chính xác (Dimensions), Khung tên kỹ thuật & Bảng kê danh mục chi tiết (BOM), cùng bộ ảnh xuất độ phân giải cao.

---

## 1. Hệ Thống Các Khung Nhìn Trực Giao (Orthographic Scenes)

### 1.1. Scene 1: `01_Hinh_Chieu_Dung` (Front Orthographic View)
- **Thiết lập Camera:**
  - `parallel_projection = true` (Chiếu song song trực giao không tụ điểm).
  - Vị trí camera: Nhìn vuông góc từ hướng trước (`eye = [0, -3000, 700]`, `target = [0, 0, 700]`, `up = [0, 0, 1]`).
- **Nội dung kích thước dóng ghi (Dimensions mm):**
  - Chiều cao tổng thể từ sàn đến đỉnh tay vặn: $1355\text{mm}$.
  - Chiều cao sàn đến tâm trục con lăn dưới: $860\text{mm}$.
  - Khoảng cách tâm 2 con lăn tỳ dưới: $240\text{mm}$.
  - Chiều rộng má máy: $320\text{mm}$.
  - Chiều dài thanh tay vặn vít me đỉnh: $340\text{mm}$.
  - Chiều rộng mặt bích đế sàn: $420\text{mm}$.
  - Bán kính tay quay công: $360\text{mm}$.

### 1.2. Scene 2: `02_Hinh_Chieu_Canh` (Right Side Orthographic View)
- **Thiết lập Camera:**
  - `parallel_projection = true`.
  - Vị trí camera: Nhìn vuông góc từ bên phải (`eye = [3000, 0, 700]`, `target = [0, 0, 700]`, `up = [0, 0, 1]`).
- **Nội dung kích thước dóng ghi (Dimensions mm):**
  - Chiều sâu mặt bích đế sàn: $480\text{mm}$.
  - Khoảng cách giữa 2 má máy: $140\text{mm}$.
  - Chiều rộng thân hộp trụ đứng: $100\text{mm}$.
  - Độ vươn cụm tay quay lực ra phía trước: $\approx 180\text{mm}$.
  - Cụm đĩa xích nhô ra phía sau: $\approx 115\text{mm}$.

### 1.3. Scene 3: `03_Hinh_Chieu_Bang` (Top Orthographic View)
- **Thiết lập Camera:**
  - `parallel_projection = true`.
  - Vị trí camera: Nhìn từ trên đỉnh máy thẳng xuống (`eye = [0, 0, 3000]`, `target = [0, 0, 700]`, `up = [0, 1, 0]`).
- **Nội dung kích thước dóng ghi (Dimensions mm):**
  - Kích thước phủ bì bích đế sàn: $420 \times 480\text{mm}$.
  - Khoảng cách tâm 4 lỗ bu-lông neo: $340 \times 400\text{mm}$.
  - Bích đỉnh gá máy: $220 \times 280\text{mm}$.
  - Độ mở tay vặn đỉnh chữ T: $340\text{mm}$.

### 1.4. Scene 4: `04_Phoi_Canh_Truc_Do` (Isometric Technical View)
- **Thiết lập Camera:**
  - `parallel_projection = true` hoặc phối cảnh góc rộng kỹ thuật.
  - Vị trí camera: Góc nhìn 3/4 trục đo (`eye = [1800, -2200, 1600]`, `target = [0, 0, 750]`, `up = [0, 0, 1]`).
- **Mục đích:** Cung cấp góc nhìn 3D trực quan tổng thể máy, phôi ống uốn cong và toàn bộ đường dóng kích thước.

---

## 2. Hệ Thống Đường Ghi Kích Thước Kỹ Thuật (Dimension Layer)

- Sử dụng phương thức `entities.add_dimension_linear(pt1, pt2, offset_vector)` trong SketchUp Ruby API.
- Các đường dóng kích thước được đặt trong Group riêng `Drawing_Dimensions` để có thể quản lý ẩn/hiện linh hoạt.
- Kiểu hiển thị kích thước: Text màu đen sắc nét, đường dóng thanh mảnh, mũi tên cơ khí chuẩn xác, đơn vị hiển thị rõ ràng bằng milimét (mm).

---

## 3. Khung Tên Tiêu Chuẩn & Bảng Kê Danh Mục Chi Tiết (Title Block & BOM)

- Tạo khung viền bản vẽ kỹ thuật cơ khí.
- **Khung tên góc (Title Block):**
  - Tên máy: `MÁY UỐN ỐNG 3 TRỤC LĂN BẰNG TAY (MANUAL 3-ROLLER PIPE BENDER)`
  - Tỷ lệ: `1:1 (Kích thước thiết kế thực mm)`
  - Ngày lập: `2026-09-11`
  - Vật liệu chính: `Thép CT3, Thép C45 mạ crom, Bạc đồng`
- **Bảng kê chi tiết cơ khí (BOM - Bill of Materials):**
  1. Mặt bích đế & Bu-lông neo $M14$
  2. Khung trụ đứng thép hộp $100 \times 100\text{mm}$ & 4 Gân tăng cứng
  3. Bích đỉnh gá cụm uốn
  4. Cặp má máy đôi thép dày $16\text{mm}$ có rãnh phay trượt
  5. 2 Con lăn tỳ dưới có rãnh uốn $\varnothing 110\text{mm}$ & Trục dẫn động $\varnothing 30\text{mm}$
  6. Con lăn ép trên $\varnothing 110\text{mm}$ & Gối trượt dẫn hướng chữ U
  7. Trục vít me nén ép $Tr28\text{mm}$ & Tay vặn chữ T đỉnh
  8. Cặp đĩa xích răng $Z=16$ & Sợi xích tải công nghiệp
  9. Cụm tay quay cơ khí chữ Z bán kính $360\text{mm}$ có núm xoay bọc đen
  10. Phôi ống thép tròn tiêu chuẩn $\varnothing 27\text{mm}$ uốn cong cung tròn

---

## 4. Xuất Bộ Ảnh Bản Vẽ Kỹ Thuật
- Tự động kích hoạt lần lượt 4 Scenes trong SketchUp.
- Xuất các file ảnh chất lượng cao 1920x1080px:
  1. `drawing_01_front_view.png`
  2. `drawing_02_side_view.png`
  3. `drawing_03_top_view.png`
  4. `drawing_04_isometric_view.png`
