# DỰ ÁN AI AGENT: HỆ THỐNG HỖ TRỢ QUYẾT ĐỊNH MỞ RỘNG ĐỊA BÀN
## MÔN HỌC: AI301 | ĐỀ TÀI: ĐỀ SỐ 04 | DOANH NGHIỆP: HƯNG PHÁT SMART WAREHOUSE

---

## 📌 GIỚI THIỆU TỔNG QUAN
Hệ thống AI Agent hỗ trợ Trưởng phòng Phát triển Kinh doanh Công ty Hưng Phát lựa chọn chính xác **2 địa bàn tiềm năng** (trong số 4 địa bàn ứng viên) để tiến hành khảo sát thực địa trước khi trình Ban Giám đốc. 

Hệ thống được thiết kế theo kiến trúc **Multi-Skill Agent** với cơ chế kiểm tra ràng buộc cứng (Hard-Constraint Filter), loại bỏ hoàn toàn cảm tính chủ quan, khử trùng lặp dữ liệu, kiểm soát rủi ro cam kết dịch vụ (On-site SLA) và lưu vết 100% các bước quyết định (Audit Traceability).

---

## 📁 CẤU TRÚC THƯ MỤC
```text
Đề 4 Hưng phát/
├── data/                                # Gói dữ liệu dự án mẫu & kịch bản kiểm thử
│   ├── dataset_normal.json              # Kịch bản 1: Dữ liệu chuẩn, đầy đủ 4 địa bàn
│   ├── dataset_missing.json             # Kịch bản 2: Dữ liệu thiếu & kỳ thống kê cũ
│   └── dataset_boundary.json            # Kịch bản 3: Ranh giới quy tắc (Quy mô cực lớn nhưng vi phạm SLA)
├── src/                                 # Mã nguồn kiến trúc AI Agent
│   ├── agent_core.py                    # Ngữ cảnh AgentContext & Bộ ghi nhật ký AuditLogger
│   ├── agent_coordinator.py             # Bộ điều phối toàn diện Pipeline
│   ├── report_generator.py              # Sinh Báo cáo Markdown & Bảng đối chiếu nguồn
│   └── skills/                          # Các kỹ năng nghiệp vụ chuyên biệt
│       ├── market_research.py           # Skill 1: Khử trùng lặp, chuẩn hóa nguồn & Phân tích Product Fit
│       ├── criteria_eval.py             # Skill 2: Chấm điểm đa tiêu chí MCDA & Kiểm tra ràng buộc SLA
│       └── survey_planner.py            # Skill 3: Lập kế hoạch khảo sát & Phân định Fact/Inference
├── tests/
│   └── run_all_tests.py                 # Bộ kiểm thử tự động 3 kịch bản
├── outputs/                             # Thư mục lưu kết quả chạy tự động
│   ├── report_normal.md                 # Báo cáo đề xuất kịch bản chuẩn
│   ├── report_missing.md                # Báo cáo kịch bản thiếu dữ liệu
│   ├── report_boundary.md               # Báo cáo kịch bản ranh giới quy tắc
│   └── audit_trace_*.json               # File JSON nhật ký truy vết từng bước
├── docs/
│   └── THIET_KE_AI_AGENT_AI301_DE04.md  # Báo cáo thiết kế học thuật đầy đủ Task 1 & Task 2
├── run_agent.py                         # Điểm chạy CLI chính thức nạp dataset bất kỳ
└── README.md                            # Tài liệu hướng dẫn sử dụng
```

---

## ⚡ HƯỚNG DẪN CHẠY TẠI BUỔI THI (DÀNH CHO HỘI ĐỒNG / GIẢNG VIÊN)

Hệ thống được thiết kế hoàn toàn bằng thư viện tiêu chuẩn của Python (Python Standard Library), không yêu cầu cài đặt thêm các thư viện bên ngoài phức tạp, đảm bảo chạy ổn định trên mọi môi trường máy chấm thi.

### 1. Chạy nhanh toàn bộ 3 kịch bản kiểm thử tự động:
```bash
python tests/run_all_tests.py
```

### 2. Nạp bộ dữ liệu mới do Giảng viên cung cấp tại buổi thi:
Khi Giảng viên đưa một file dữ liệu mới (ví dụ `test_dataset_moi.json` có cùng cấu trúc schema):
```bash
python run_agent.py test_dataset_moi.json --tag buoi_thi
```
Kết quả báo cáo và log truy vết sẽ được tự động xuất vào thư mục `outputs/`:
- Báo cáo trình Trưởng phòng KD: `outputs/report_buoi_thi.md`
- Nhật ký truy vết (Audit Trail): `outputs/audit_trace_buoi_thi.json`
- Kết quả máy đọc: `outputs/evaluation_result_buoi_thi.json`

---

## 🎯 3 ĐIỂM SÁNG CỐT LÕI CỦA GIẢI PHÁP
1. **Khử trùng lặp và Chuẩn hóa nguồn (Source Deduplication):** Tự động phát hiện các báo cáo dẫn lại số liệu cũ từ cùng một nguồn gốc, tránh tính kép quy mô thị trường.
2. **Kiểm tra Ràng buộc Ranh giới (Boundary Constraint Enforcement):** Dù một địa bàn có điểm thị trường 10/10 nhưng nếu yêu cầu hỗ trợ tại chỗ (on-site) vượt quá năng lực phục vụ của Hưng Phát, Agent sẽ lập tức loại trừ (Disqualify) và cảnh báo rủi ro vỡ cam kết SLA.
3. **Phân định Minh bạch Fact vs Inference:** Mọi con số đều trích dẫn rõ nguồn và năm thống kê; phân định rạch ròi giữa dữ kiện thực tế và suy luận của Agent; tuyệt đối không bịa đặt số liệu (Zero Hallucination).
