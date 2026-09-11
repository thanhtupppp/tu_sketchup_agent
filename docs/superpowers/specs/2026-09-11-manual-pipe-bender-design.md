# Thiết Kế Chi Tiết Máy Uốn Ống 3 Trục Lăn Bằng Tay (Chân Đứng + Truyền Động Xích Đôi)

**Ngày lập:** 2026-09-11  
**Mục tiêu:** Thiết kế mô hình 3D hoàn chỉnh máy uốn ống cơ khí 3 trục lăn bằng tay, tích hợp chân đứng xưởng và bộ truyền xích đồng tốc cho 2 con lăn dưới, đạt chuẩn đồ án kỹ thuật cơ khí chế tạo máy trong SketchUp 2026.

---

## 1. Kết Cấu & Kích Thước Kỹ Thuật (Đơn vị: mm)

### 1.1. Cụm Chân Đế Đứng (Stand & Pedestal)
- **Mặt bích đế sàn (Base Plate):** Thép tấm $420 \times 480 \times 12\text{mm}$, vát 4 góc, có 4 bu-lông neo $M14$ kèm vòng đệm.
- **Trụ đứng chính (Main Column):** Thép hộp vuông $100 \times 100 \times 4\text{mm}$, chiều cao $720\text{mm}$.
- **Gân tăng cứng (Gusset Ribs):** 4 bản mã tam giác $120 \times 120 \times 8\text{mm}$ hàn giằng giữa mặt bích đế và 4 mặt trụ đứng.
- **Bích đỉnh gá đầu máy (Top Mounting Flange):** Thép tấm $220 \times 280 \times 12\text{mm}$ có 4 lỗ bắt bu-lông liên kết với cụm đầu uốn.

### 1.2. Cụm Đầu Máy Uốn 3 Trục (Bending Head Unit)
- **Má máy đôi (Dual Side Plates):** 2 tấm thép kết cấu dày $16\text{mm}$, kích thước $320\text{mm}$ (ngang) $\times 440\text{mm}$ (cao), cách nhau $140\text{mm}$.
  - Ở giữa có rãnh phay dẫn hướng đứng (kích thước rãnh rộng $60\text{mm}$, dài $180\text{mm}$) cho gối trượt con lăn ép.
- **2 Con lăn tỳ dưới (Bottom Drive Rollers):**
  - Đường kính ngoài $\varnothing 110\text{mm}$, bề rộng $80\text{mm}$.
  - Tiện rãnh bán nguyệt uốn ống $\varnothing 27 - \varnothing 34\text{mm}$ ở giữa mặt lăn.
  - Khoảng cách tâm giữa 2 trục dưới: $240\text{mm}$.
  - Trục con lăn $\varnothing 30\text{mm}$ kéo dài ra phía sau để gắn đĩa xích và phía trước để gắn tay quay.
- **1 Con lăn ép giữa (Top Pressing Roller & Slider Block):**
  - Đường kính $\varnothing 110\text{mm}$, bề rộng $80\text{mm}$, có rãnh uốn đồng trục với 2 con lăn dưới.
  - Gối trượt dẫn hướng (Slider Carriage Block): Khối thép $90 \times 58 \times 100\text{mm}$ trượt êm trong rãnh má máy.

### 1.3. Cơ Cấu Vít Me Ép (Lead Screw & Pressing Handwheel)
- **Thanh xà đỉnh (Top Crossbeam):** Tấm thép dày $25\text{mm}$ gối trên đỉnh 2 má máy.
- **Trục vít me ren vuông/thang (Tr28x5):** Chiều dài $240\text{mm}$, dẫn hướng ren qua bạc ren đỉnh.
- **Tay vặn vô-lăng chữ T (Pressing T-Handle):** Tay vặn 2 cánh dài $300\text{mm}$ có núm cầu ở hai đầu, giúp công nhân siết ép con lăn giữa xuống phôi ống.

### 1.4. Bộ Truyền Động Xích Đôi & Tay Quay Lực (Dual Chain Drive & Crank)
- **Mặt sau máy (Rear Transmission):**
  - 2 Đĩa xích răng $Z=16$ (đường kính $\approx \varnothing 85\text{mm}$) lắp then trên 2 trục con lăn dưới.
  - Sợi xích tải công nghiệp ôm qua 2 đĩa xích giúp cả 2 con lăn quay đồng tốc cùng chiều.
  - Con lăn tăng xích (Chain Tensioner) nhỏ nằm giữa.
- **Mặt trước máy (Front Manual Drive):**
  - Tay quay cơ khí chữ Z bằng thép tròn $\varnothing 22\text{mm}$, bán kính quay $380\text{mm}$, đầu gắn núm xoay tự do bọc đen dài $110\text{mm}$.

### 1.5. Phôi Ống Thép Uốn Cong Minh Họa (Curved Pipe Sample)
- Đoạn ống thép tròn tiêu chuẩn $\varnothing 27\text{mm}$ (dày thành $2\text{mm}$), chiều dài trải $\approx 850\text{mm}$.
- Được uốn thành cung vòm tròn bán kính cong $R \approx 320\text{mm}$ nằm đúng trong rãnh của 3 con lăn, minh họa chân thực quá trình uốn.

---

## 2. Bảng Màu & Vật Liệu Cơ Khí (Palette)

| Tên Vật Liệu | Màu HEX / RGB | Ứng Dụng |
|---|---|---|
| `Mat_Machine_Blue` | `#1F4E79` (RGB: 31, 78, 121) | Thân má máy, khung chân trụ đứng, gân tăng cứng |
| `Mat_Steel_Machined`| `#CCD1D1` (RGB: 204, 209, 209)| 3 Con lăn uốn, các trục dẫn động, mặt bích tiếp xúc |
| `Mat_Thread_LeadScrew`| `#EAEDED` (RGB: 234, 237, 237)| Trục vít me ren tiện bóng mạ crom |
| `Mat_Sprocket_Chain`| `#5D6D7E` (RGB: 93, 109, 126) | Cặp đĩa xích, vòng xích tải và then truyền lực |
| `Mat_Black_Hardware`| `#2C3E50` (RGB: 44, 62, 80)   | Bu-lông $M14$, đai ốc, núm vặn tay quay cao su |
| `Mat_Steel_Pipe`   | `#F2F4F4` (RGB: 242, 244, 244)| Phôi ống thép uốn tròn minh họa |

---

## 3. Cấu Trúc Group Phân Cấp Trong SketchUp

```text
Model.active_entities
└── Group: "Manual_3Roller_Pipe_Bender"
    ├── Group: "Pedestal_and_Stand"
    │   ├── Group: "Base_Plate_Bolts"
    │   ├── Group: "Square_Column"
    │   ├── Group: "Gusset_Plates"
    │   └── Group: "Top_Flange"
    ├── Group: "Bending_Head_Chassis"
    │   ├── Group: "Front_Side_Plate"
    │   ├── Group: "Rear_Side_Plate"
    │   ├── Group: "Top_Beam_Nut"
    │   └── Group: "Tie_Rods_Spacers"
    ├── Group: "Rollers_and_Bearings"
    │   ├── Group: "Bottom_Roller_Left"
    │   ├── Group: "Bottom_Roller_Right"
    │   └── Group: "Top_Roller_and_Slider"
    ├── Group: "LeadScrew_Mechanism"
    │   ├── Group: "Threaded_Spindle"
    │   └── Group: "T_Handle_Wheel"
    ├── Group: "Chain_Transmission_Rear"
    │   ├── Group: "Sprocket_Left"
    │   ├── Group: "Sprocket_Right"
    │   └── Group: "Roller_Chain"
    ├── Group: "Drive_Crank_Front"
    │   └── Group: "Crank_Arm_and_Grip"
    └── Group: "Bent_Pipe_Specimen"
```
