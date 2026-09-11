# Thiết Kế Bản Vẽ Bóc Tách Chi Tiết Từng Linh Kiện Máy Uốn Ống 3 Trục

**Ngày lập:** 2026-09-11  
**Mục tiêu:** Thiết lập khu vực bóc tách gia công chế tạo (Component Parts Layout) và lập bản vẽ chi tiết cho 8 linh kiện cơ khí chính của máy uốn ống 3 trục lăn trong SketchUp 2026 kèm đường dóng kích thước gia công, các Scenes cận cảnh và bộ ảnh xuất độ nét cao.

---

## 1. Bố Trí Không Gian Khu Vực Gia Công (Component Layout)

- Vị trí: Đặt song song bên phải cụm máy chính dọc theo trục X (từ $X = 1200\text{mm}$ đến $X = 3600\text{mm}$).
- Mỗi linh kiện được đặt trên một bệ gá gia công riêng biệt, cách sàn $Z = 50\text{mm}$, phân chia theo 3 cụm chức năng:
  - **Cụm 1: Cụm Trục & Con Lăn (Rollers & Shafts)** tại $X \approx [1300..1900\text{mm}]$
  - **Cụm 2: Cụm Má Thép & Gối Trượt (Plates & Sliders)** tại $X \approx [2000..2600\text{mm}]$
  - **Cụm 3: Cụm Truyền Động & Tay Lực (Drive & Screws)** tại $X \approx [2700..3500\text{mm}]$

---

## 2. Thông Số Kỹ Thuật 8 Linh Kiện Gia Công

### 2.1. Con lăn uốn ống định hình (Bending Die Roller)
- Đường kính ngoài: $\varnothing 110\text{mm}$, bán kính $R = 55\text{mm}$.
- Rãnh uốn bán nguyệt ở giữa: đường kính đáy rãnh $\varnothing 82\text{mm}$ (bán kính $R = 13.5\text{mm}$ cho ống $\varnothing 27$).
- Chiều rộng tổng: $90\text{mm}$ (2 gờ mép $29\text{mm}$, rãnh giữa $32\text{mm}$).
- Lỗ trục xuyên tâm: $\varnothing 30\text{mm}$, có rãnh then tiêu chuẩn $8 \times 4\text{mm}$.
- Vật liệu: Thép C45 tiện và tôi cứng bề mặt rãnh $48 - 52\text{HRC}$.

### 2.2. Trục dẫn động con lăn (Drive Shaft)
- Đường kính danh nghĩa: $\varnothing 30\text{mm}$.
- Chiều dài toàn bộ: $360\text{mm}$.
- Các đoạn trục chức năng:
  - Đoạn lắp con lăn giữa: $\varnothing 30 \times 90\text{mm}$ kèm rãnh then.
  - 2 Ngõng trục lắp bạc đạn/ổ bi: $\varnothing 30 \times 16\text{mm}$.
  - Đoạn kéo dài phía sau lắp đĩa xích: $\varnothing 30 \times 35\text{mm}$ kèm rãnh then.
  - Đoạn kéo dài phía trước lắp tay quay: $\varnothing 30 \times 40\text{mm}$ vát mép $2\times 45^\circ$.
- Vật liệu: Thép C45 mài bóng.

### 2.3. Má thép máy đứng đôi (Slotted Side Plate)
- Kích thước phủ bì: $320\text{mm}$ (ngang) $\times 440\text{mm}$ (cao) $\times 16\text{mm}$ (dày).
- Rãnh phay dẫn hướng đứng ở giữa: rộng $60\text{mm}$, dài $180\text{mm}$ (tọa độ $Z = [880..1060\text{mm}]$).
- 2 Lỗ gá ổ bi con lăn dưới: $\varnothing 48\text{mm}$, khoảng cách tâm $240\text{mm}$, cao $98\text{mm}$ từ đáy tấm.
- 4 Lỗ bu-lông góc liên kết thanh giằng: $\varnothing 18\text{mm}$.
- Vật liệu: Thép tấm kết cấu C45 phay phẳng 2 mặt.

### 2.4. Gối trượt dẫn hướng chữ U (Slider Carriage Block)
- Kích thước bao: $58\text{mm}$ (ngang) $\times 130\text{mm}$ (dài) $\times 115\text{mm}$ (cao).
- 2 Ngàm vai trượt dẫn hướng ôm khít rãnh má máy $60\text{mm}$.
- Lỗ chốt lắp con lăn ép đỉnh: $\varnothing 30\text{mm}$.
- Bề mặt phẳng đỉnh gối đỡ chịu lực ép từ bạc vít me.
- Vật liệu: Thép phay C45.

### 2.5. Trục vít me nén ép & Tay vặn chữ T (Lead Screw & T-Handle)
- Trục ren vuông/thang: $Tr28 \times 5$, chiều dài ren $245\text{mm}$.
- Đầu đè nén: Bạc cầu tự lựa $\varnothing 44 \times 25\text{mm}$.
- Đầu trên: Moay-ơ tay vặn $\varnothing 42 \times 35\text{mm}$, thanh ngang $\varnothing 18 \times 340\text{mm}$ có 2 núm cầu $\varnothing 26\text{mm}$ ở hai đầu.
- Vật liệu: Thép C45 tiện ren mạ crom bóng.

### 2.6. Đĩa xích dẫn động (Sprocket $Z=16$)
- Số răng: $Z = 16$, bước xích $p = 15.875\text{mm}$ (xích tải đơn công nghiệp).
- Đường kính đỉnh răng: $\varnothing 90\text{mm}$, đường kính vòng chia: $\approx 81.4\text{mm}$.
- Bề dày đĩa răng: $8\text{mm}$, Moay-ơ trục $\varnothing 48 \times 16\text{mm}$, lỗ then $\varnothing 30\text{mm}$.
- Vật liệu: Thép $45$ tôi cao tần răng.

### 2.7. Tay quay cơ khí chữ Z (Drive Crank Handle)
- Cần tay quay thép dẹp: tiết diện $36 \times 14\text{mm}$, bán kính quay $R = 350\text{mm}$.
- Moay-ơ gắn trục: $\varnothing 46 \times 26\text{mm}$, có lỗ then then và vít hãm $M8$.
- Chốt tay nắm thép $\varnothing 12\text{mm}$, tay nắm bọc xoay tự do $\varnothing 28 \times 100\text{mm}$.
- Vật liệu: Thép C45, tay nắm nhựa cứng kỹ thuật đen.

### 2.8. Khung chân đế & Cột trụ hàn (Pedestal Frame)
- Mặt bích đế sàn: $420 \times 480 \times 14\text{mm}$, vát 4 góc, 4 lỗ neo $M14$ khoảng cách $340 \times 400\text{mm}$.
- Cột trụ chính: Thép hộp vuông $100 \times 100 \times 4\text{mm}$, cao $720\text{mm}$.
- 4 Bản mã gân tam giác tăng cứng: $130 \times 130 \times 10\text{mm}$.
- Mặt bích đỉnh gá máy: $220 \times 280 \times 14\text{mm}$.
- Vật liệu: Kết cấu thép hàn CT3 sơn tĩnh điện màu xanh máy.

---

## 3. Hệ Thống 4 Scenes Mới Trong SketchUp

1. `05_Tong_The_Linh_Kien`: Toàn cảnh bãi dàn trải các linh kiện gia công bên cạnh máy.
2. `06_Chi_Tiet_Con_Lan_Truc`: Cận cảnh bản vẽ gia công con lăn uốn và trục dẫn động.
3. `07_Chi_Tiet_Ma_May_Goi_Truot`: Cận cảnh bản vẽ gia công má máy phay rãnh và gối trượt chữ U.
4. `08_Chi_Tiet_VitMe_TayQuay_Xich`: Cận cảnh bản vẽ gia công vít me Tr28, tay quay chữ Z và đĩa xích.
