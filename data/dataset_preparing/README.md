# Pipeline Documentation — Dataset Simulation (NTS)

## Tổng quan

Pipeline này thực hiện mô phỏng và phân tích dữ liệu quy trình mua hàng/quản lý đơn hàng dựa trên chuẩn OCEL (Object-Centric Event Log) và sinh ra các biểu đồ DFG (Directly-Follows Graph).

---

## Cấu trúc thư mục

```
dataset_simulation/
│
├── DFG_nts.py                          # Script chính: chạy toàn bộ pipeline
│
└── Data/
    └── Order_procurement/
        │
        ├── inputs/                     # Dữ liệu đầu vào
        │   ├── NTS_bds.md              # Mô tả nghiệp vụ BDS (giữ lại)
        │   ├── order-management.json   # Dữ liệu đơn hàng thô (giữ lại)
        │   ├── BPMN_NTS.md             # (*) .gitignore
        │   └── Cong_viec_PM_MinhNV.md  # (*) .gitignore
        │
        ├── outputs/                    # Kết quả sinh ra từ pipeline
        │   └── NTS_OCEL_2026.json      # File OCEL chuẩn hóa đầu ra
        │
        ├── prompts/                    # Prompt sử dụng cho LLM/sinh dữ liệu
        │   └── nts_ocel_prompt.txt     # Prompt sinh OCEL log
        │
        └── raw_data/                   # Dữ liệu thô (ảnh minh họa quy trình)
            ├── BPMN_NTS.png            # (*) .gitignore
            └── Cong_viec_PM_MinhNV.png # (*) .gitignore
│
└── Result/
    └── NTS-ocdfg/                      # Kết quả phân tích DFG
        ├── ocdfg_analysis.json         # Phân tích DFG dạng JSON
        ├── object_type_summary.csv     # Tóm tắt theo loại object
        └── visualizations/             # Các biểu đồ DFG xuất ra
            ├── BOM_dfg.png
            ├── Department_dfg.png
            ├── InventoryRecord_dfg.png
            ├── LicensingDocument_dfg.png
            ├── PurchaseOrder_dfg.png
            ├── ShipmentDocument_dfg.png
            ├── Vendor_dfg.png
            └── VendorQuotation_dfg.png
```

> **(\*) .gitignore** — Các file này không được commit lên repository.

---

## Các bước trong Pipeline

### Bước 1 — Chuẩn bị đầu vào (`inputs/`)

| File | Mô tả |
|---|---|
| `NTS_bds.md` | Mô tả nghiệp vụ, quy trình mua hàng của NTS |
| `order-management.json` | Dữ liệu đơn hàng thô, dùng làm nguồn sinh event log |
| `nts_ocel_prompt.txt` | Prompt hướng dẫn mô hình sinh OCEL log từ dữ liệu thô |

### Bước 2 — Sinh OCEL Log (`outputs/`)

Script `DFG_nts.py` đọc dữ liệu từ `inputs/`, kết hợp với prompt trong `prompts/`, và sinh ra:

- **`NTS_OCEL_2026.json`** — File event log chuẩn OCEL 2.0, chứa các sự kiện và object liên quan đến quy trình mua hàng.

### Bước 3 — Phân tích DFG (`Result/NTS-ocdfg/`)

Từ file OCEL, pipeline tính toán Object-Centric DFG và xuất ra:

- **`ocdfg_analysis.json`** — Kết quả phân tích đầy đủ dạng JSON (tần suất các cạnh, node, object type).
- **`object_type_summary.csv`** — Bảng tóm tắt thống kê theo từng loại object.

### Bước 4 — Visualization (`Result/NTS-ocdfg/visualizations/`)

Mỗi loại object trong OCEL log được sinh ra một biểu đồ DFG riêng biệt:

| File | Object Type |
|---|---|
| `BOM_dfg.png` | Bill of Materials |
| `Department_dfg.png` | Department |
| `InventoryRecord_dfg.png` | Inventory Record |
| `LicensingDocument_dfg.png` | Licensing Document |
| `PurchaseOrder_dfg.png` | Purchase Order |
| `ShipmentDocument_dfg.png` | Shipment Document |
| `Vendor_dfg.png` | Vendor |
| `VendorQuotation_dfg.png` | Vendor Quotation |

---

## .gitignore

Các file sau **không được** đưa vào version control:

```
# inputs
Data/Order_procurement/inputs/BPMN_NTS.md
Data/Order_procurement/inputs/Cong_viec_PM_MinhNV.md

# raw_data
Data/Order_procurement/raw_data/BPMN_NTS.png
Data/Order_procurement/raw_data/Cong_viec_PM_MinhNV.png
```

---

## Luồng dữ liệu tóm tắt

```
order-management.json  ──┐
NTS_bds.md             ──┤──▶  DFG_nts.py  ──▶  NTS_OCEL_2026.json  ──▶  ocdfg_analysis.json
nts_ocel_prompt.txt    ──┘                                                  object_type_summary.csv
                                                                            visualizations/*.png
```
