# Thiết Kế Chi Tiết Bộ Sofa Scandinavian Trong SketchUp

**Ngày lập:** 2026-09-11  
**Mục tiêu:** Tạo mô hình 3D bộ sofa phòng khách phong cách Bắc Âu (Scandinavian) hoàn chỉnh, tỷ lệ chuẩn kiến trúc và nhân trắc học trong SketchUp 2026 thông qua Ruby API.

---

## 1. Thành Phần & Kích Thước Kiến Trúc (mm)

### 1.1. Sofa văng 3 chỗ (`Sofa_3Seater`)
- **Kích thước bao:** Dài 2100mm, Sâu 850mm, Cao 780mm.
- **Khung chân & bệ đỡ (`Base_and_Legs`):**
  - Khung đế gỗ sồi mỏng (dày 40mm) nâng đỡ toàn bộ đệm.
  - 4 chân gỗ sồi tiện tròn vát thuôn (tapered legs), góc choãi nghiêng 10 độ ra ngoài, chiều cao chân 160mm.
- **Đệm ngồi (`Seat_Cushions`):**
  - Gồm 3 khối đệm ngồi êm ái, mỗi đệm kích thước ~640mm x 600mm x 150mm, viền bo nhẹ tạo độ phồng thực tế.
  - Chiều cao mặt đệm ngồi so với sàn: 430mm (chuẩn nhân trắc học thoải mái).
- **Đệm tựa lưng & Khung lưng (`Backrest`):**
  - Tựa lưng hơi nghiêng về sau 5-8 độ để ngồi thư giãn.
  - 3 đệm tựa lưng tựa vào thành lưng với độ dày 120mm, chiều cao từ mặt đệm đến đỉnh tựa ~400mm.
- **Tay vịn (`Armrests`):**
  - 2 bên tay vịn thon gọn rộng 90mm, lượn cong nhẹ phía trước, cao 620mm so với sàn.
- **Gối tựa decor (`Pillows`):**
  - 2 gối tựa kích thước 400mm x 400mm x 100mm đặt tựa nhẹ vào hai góc tay vịn.

### 1.2. Đôn sofa chữ nhật (`Sofa_Ottoman`)
- **Kích thước bao:** Dài 650mm, Rộng 500mm, Cao 430mm (bằng chiều cao mặt đệm sofa).
- **Chân & Đế:** 4 chân gỗ sồi đồng bộ với sofa chính, bọc đệm nỉ êm ái ở trên.

### 1.3. Bộ bàn trà đôi lồng (`Coffee_Table_Set`)
- **Bàn trà lớn (Mặt đá trắng Marble):**
  - Đường kính Ø700mm, Chiều cao 420mm, mặt đá dày 20mm bo cạnh tròn.
  - Chân kiềng 3 chân bằng gỗ sồi tự nhiên.
- **Bàn trà nhỏ (Mặt gỗ sồi mộc):**
  - Đường kính Ø500mm, Chiều cao 360mm, mặt gỗ dày 20mm.
  - Lồng nhẹ một phần dưới gầm bàn lớn tạo bố cục so le hiện đại.

### 1.4. Thảm trải sàn (`Living_Room_Rug`)
- Kích thước: 2400mm x 1600mm, dày 8mm, đặt ở trung tâm nâng đỡ toàn bộ cụm bàn ghế.

---

## 2. Bảng Màu & Vật Liệu (Palette)

| Tên Vật Liệu | Mã Màu HEX / RGB | Ứng Dụng |
|---|---|---|
| `Mat_Fabric_Grey` | `#D8DBE2` (RGB: 216, 219, 226) | Nỉ bọc sofa, đệm ngồi, đệm tựa, đôn |
| `Mat_Oak_Wood` | `#C49A6C` (RGB: 196, 154, 108) | Khung đế gỗ, 4 chân sofa, chân đôn, bàn nhỏ |
| `Mat_White_Marble`| `#F7F9F9` (RGB: 247, 249, 249) | Mặt bàn trà tròn lớn |
| `Mat_Pillow_Mustard`| `#DE9B35` (RGB: 222, 155, 53) | Gối decor vàng mù tạt |
| `Mat_Pillow_Sage` | `#6C8276` (RGB: 108, 130, 118) | Gối decor xanh xám sage |
| `Mat_Rug_Texture` | `#B0B5B3` (RGB: 176, 181, 179) | Thảm trải sàn mộc dệt |

---

## 3. Cấu Trúc Group / Component trong SketchUp Model

```text
Model.active_entities
└── Group: "Scandinavian_Living_Room_Set"
    ├── Group: "Sofa_3Seater"
    │   ├── Group: "Legs_and_Base"
    │   ├── Group: "Backrest_Frame"
    │   ├── Group: "Armrests"
    │   ├── Group: "Seat_Cushions"
    │   ├── Group: "Back_Cushions"
    │   └── Group: "Throw_Pillows"
    ├── Group: "Sofa_Ottoman"
    │   ├── Group: "Ottoman_Legs"
    │   └── Group: "Ottoman_Cushion"
    ├── Group: "Coffee_Table_Nesting"
    │   ├── Group: "Large_Table_Marble"
    │   └── Group: "Small_Table_Wood"
    └── Group: "Area_Rug"
```

---

## 4. Cơ Chế Triển Khai (Execution)
- Tạo bằng Ruby Script chạy qua `sketchup_execute_ruby`.
- Được bọc trong 1 `model.start_operation("Create Scandinavian Sofa Set", true)` đảm bảo toàn bộ bộ ghế được tạo an toàn và có thể hoàn tác (Undo) chỉ với 1 phím tắt `Ctrl+Z`.
- Sau khi tạo xong, tự động gọi `sketchup_zoom_extents` để góc nhìn camera bao quát toàn bộ bộ ghế đẹp mắt.
