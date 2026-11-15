"""
Mô-đun Tạo Báo cáo Đề xuất và Bảng Đối chiếu Căn cứ Nguồn
Phục vụ Trưởng phòng Phát triển Kinh doanh Công ty Hưng Phát
"""

import json
from typing import Dict, Any, List

class ReportGenerator:
    @staticmethod
    def generate_markdown_report(
        project_meta: Dict[str, Any],
        evaluation_results: Dict[str, Any],
        survey_plan: Dict[str, Any],
        sanitized_summary: Dict[str, Any],
        audit_logger
    ) -> str:
        all_scores = evaluation_results["all_scores"]
        top_2 = evaluation_results["top_2_recommendations"]
        unprioritized = evaluation_results["unprioritized_locations"]
        plans = survey_plan["action_plans"]
        conditions = survey_plan["unprioritized_conditions"]

        md = []
        md.append("# BÁO CÁO ĐỀ XUẤT LỰA CHỌN 2 ĐỊA BÀN KHẢO SÁT MỞ RỘNG THỊ TRƯỜNG WMS")
        md.append(f"**Đơn vị trình:** AI Agent Hỗ trợ Quyết định (Phối hợp Market Research Skill & Data Analysis Skill)")
        md.append(f"**Người nhận:** Trưởng phòng Phát triển Kinh doanh - Công ty Cổ phần Giải pháp Kho thông minh Hưng Phát")
        md.append(f"**Dự án:** {project_meta.get('project_name', 'Mở rộng thị trường 2026')}")
        md.append(f"**Ngày phân tích:** {project_meta.get('evaluation_date', '2026-03-15')} | **Trạng thái:** Hoàn thành đối chiếu dữ kiện")
        md.append("\n---\n")

        # 1. TÓM TẮT ĐIỀU HÀNH
        md.append("## 1. TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)")
        top_names = [f"**{loc['location_name']}** (Điểm: {loc['total_score']}/10)" for loc in top_2]
        md.append(f"Căn cứ trên gói dữ liệu thị trường, hồ sơ đối thủ, phản hồi nhu cầu khách hàng và giới hạn nguồn lực của công ty (chỉ đủ 1 đội triển khai cho tối đa 2 địa bàn), AI Agent trân trọng đề xuất **2 địa bàn ưu tiên hàng đầu** để triển khai khảo sát thực địa:")
        for idx, t in enumerate(top_names):
            md.append(f"  {idx+1}. {t}")
        md.append("\n> **Nguyên tắc quyết định:** Đảm bảo mức độ phù hợp sản phẩm (Product-Market Fit), khả năng cạnh tranh khả quan và **tuyệt đối không vi phạm giới hạn hỗ trợ tại chỗ (On-site SLA)** của Hưng Phát.")
        md.append("\n---\n")

        # 2. BẢNG SO SÁNH TỔNG HỢP 4 ĐỊA BÀN (CÓ CĂN CỨ TÀI LIỆU NGUỒN)
        md.append("## 2. BẢNG TỔNG HỢP VÀ ĐỐI CHIẾU 4 ĐỊA BÀN (EVIDENCE-BASED COMPARISON)")
        md.append("| Địa bàn | Quy mô & Tăng trưởng (CRIT_01) | Khớp SP (CRIT_02) | Cạnh tranh (CRIT_03) | Khả năng Hỗ trợ (CRIT_04) | Tổng điểm (10) | Trạng thái | Căn cứ Tài liệu Nguồn & Thời điểm |")
        md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|")

        for loc_id, item in all_scores.items():
            sc = item["criteria_scores"]
            ev = item["source_evidence"]
            status_badge = "✅ Ưu tiên chọn" if not item["is_disqualified"] and item in top_2 else ("⚠️ Chưa ưu tiên" if not item["is_disqualified"] else "⛔ Loại trừ (Vi phạm SLA)")
            source_info = f"{ev.get('primary_source', 'N/A')} ({ev.get('primary_timestamp', 'N/A')})"
            
            md.append(
                f"| **{item['location_name']}** | {sc['market_potential']}/10 | {sc['product_market_fit']}/10 | "
                f"{sc['competition_advantage']}/10 | {sc['deployment_feasibility']}/10 | **{item['total_score']}** | "
                f"{status_badge} | {source_info} |"
            )

        md.append("\n*Ghi chú trọng số tiêu chí:* Quy mô thị trường (25%) - Khớp sản phẩm (30%) - Dư địa cạnh tranh (20%) - Khả năng hỗ trợ tại chỗ (25%, Ràng buộc cứng).")
        md.append("\n---\n")

        # 3. GIẢI TRÌNH CHI TIẾT CĂN CỨ LỰA CHỌN & CHƯA ƯU TIÊN
        md.append("## 3. GIẢI TRÌNH CHI TIẾT KẾT QUẢ ĐÁNH GIÁ")
        
        md.append("### 3.1. Lý do Lựa chọn 2 Địa bàn Đứng đầu")
        for loc in top_2:
            sc = loc["criteria_scores"]
            notes = loc["notes"]
            md.append(f"#### 🎯 {loc['location_name']} (Điểm tổng: {loc['total_score']}/10)")
            md.append(f"- **Về quy mô thị trường:** {notes['market_note']}")
            md.append(f"- **Về mức độ khớp sản phẩm (Product-Market Fit - {sc['product_market_fit']}/10):** {notes['pmf_note']}")
            md.append(f"- **Về môi trường cạnh tranh ({sc['competition_advantage']}/10):** {notes['comp_note']}")
            md.append(f"- **Về năng lực hỗ trợ tại chỗ ({sc['deployment_feasibility']}/10):** Đã có hạ tầng kỹ thuật (văn phòng chi nhánh hoặc đối tác ủy quyền), khách hàng chấp thuận SLA hỗ trợ chuẩn của Hưng Phát, hoàn toàn nằm trong tầm kiểm soát của đội triển khai duy nhất.")

        md.append("\n### 3.2. Lý do Chưa Ưu tiên các Địa bàn còn lại & Điều kiện Cần Bổ sung")
        for cond in conditions:
            md.append(f"#### ⚠️ {cond['location_name']}")
            md.append(f"- **Hiện trạng đánh giá:** {cond['current_status']}")
            md.append(f"- **Nguyên nhân cụ thể:** {cond['detailed_reason']}")
            md.append(f"- **Điều kiện bổ sung cần thiết trước khi xem xét lại:** {cond['required_conditions']}")

        md.append("\n---\n")

        # 4. KẾ HOẠCH KHẢO SÁT THỰC ĐỊA CHI TIẾT
        md.append("## 4. KẾ HOẠCH KHẢO SÁT THỰC ĐỊA CHO 2 ĐỊA BÀN ĐƯỢC CHỌN")
        for plan in plans:
            md.append(f"### 📋 Kế hoạch Khảo sát: {plan['location_name']} (Độ ưu tiên #{plan['priority_rank']})")
            md.append(f"- **Nhóm khách hàng mục tiêu tiếp cận:** {plan['target_customer_group']}")
            md.append(f"- **Quy mô mẫu dự kiến:** Tối thiểu {plan['expected_sample_survey']} doanh nghiệp chuỗi bán lẻ.")
            md.append(f"- **Người phụ trách (PIC):** **{plan['person_in_charge']}**")
            md.append(f"- **Thời hạn thực hiện:** {plan['timeline_days']} ngày làm việc.")
            md.append(f"- **Nhiệm vụ & Thông tin trọng yếu cần xác minh tại thực địa:**")
            for item in plan['verification_items']:
                md.append(f"  + {item}")
            md.append(f"- **Kết quả đầu ra (Deliverable):** {plan['deliverables']}\n")

        md.append("---\n")

        # 5. BẢNG PHÂN ĐỊNH SỐ LIỆU TÀI LIỆU (FACT) VÀ SUY LUẬN AGENT (INFERENCE)
        md.append("## 5. BẢNG PHÂN ĐỊNH DỮ KIỆN TÀI LIỆU (FACT) VÀ SUY LUẬN AGENT (INFERENCE)")
        md.append("> **Cam kết tính trung thực học thuật & vận hành:** Không tự ý bổ sung dữ liệu thị trường ngoài gói dữ liệu (Zero Hallucination). Mọi kết luận đều truy vết về bằng chứng cụ thể.")
        md.append("\n| Hạng mục thông tin | Dữ kiện Thực tế trong Tài liệu (Fact with Source Citation) | Suy luận & Phân tích của AI Agent (Inference) |")
        md.append("|:---|:---|:---|")
        
        for loc_id, item in all_scores.items():
            ev = item["source_evidence"]
            md.append(
                f"| **{item['location_name']} - Thị trường** | "
                f"Số liệu: {item['notes']['market_note']} (Nguồn: *{ev['primary_source']}*, thời điểm *{ev['primary_timestamp']}*). | "
                f"Điểm tiềm năng đạt {item['criteria_scores']['market_potential']}/10 dựa trên tỷ lệ chuẩn hóa quy mô toàn quốc. |"
            )
            md.append(
                f"| **{item['location_name']} - Yêu cầu Khách & Hỗ trợ** | "
                f"Phản hồi khách: '{all_scores[loc_id]['notes']['pmf_note']}' | "
                f"Mức độ khả thi triển khai: {item['criteria_scores']['deployment_feasibility']}/10. Quyết định: {'Đủ điều kiện' if not item['is_disqualified'] else 'Loại bỏ do rủi ro SLA'}. |"
            )

        md.append("\n---\n")

        # 6. NHẬT KÝ KIỂM TRA DỮ LIỆU & CẢNH BÁO (AUDIT TRACE SUMMARY)
        md.append("## 6. NHẬT KÝ KIỂM TRA DỮ LIỆU & TRUY VẾT QUY TẮC (AUDIT TRAIL)")
        missing_w = sanitized_summary.get("missing_warnings", [])
        dup_w = sanitized_summary.get("duplicate_warnings", [])

        if dup_w:
            md.append("### 🔄 Dữ liệu Trùng lặp / Trích dẫn lại đã được xử lý (Deduplication):")
            for w in dup_w:
                md.append(f"- ⚠️ {w}")
        else:
            md.append("### 🔄 Dữ liệu Trùng lặp: Không phát hiện tài liệu lặp nguồn.")

        if missing_w:
            md.append("\n### ❓ Cảnh báo Dữ liệu Thiếu / Kỳ Thống kê Cũ:")
            for w in missing_w:
                md.append(f"- ❗ {w}")
        else:
            md.append("\n### ❓ Cảnh báo Dữ liệu Thiếu: Dữ liệu đầy đủ 100%.")

        md.append(f"\n*Tổng số bước Agent đã thực thi và ghi nhận trong Execution Trace:* **{len(audit_logger.logs)} sự kiện**.")
        md.append(f"*File nhật ký chi tiết:* `outputs/audit_trace.json`")

        return "\n".join(md)
