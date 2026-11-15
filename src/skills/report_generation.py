"""
SKILL 5: report_generation (Sinh Báo cáo Đề xuất, Kế hoạch Khảo sát & Đóng gói Đầu ra)
Tuân thủ HUNG PHAT MASTER AGENT Blueprint:
- Tạo Recommendation Report.
- Tạo Survey Plan (nhóm khách hàng mục tiêu, câu hỏi cần xác minh, người phụ trách theo vai trò).
- Đóng gói đầy đủ 6 đầu ra bắt buộc:
  1. Data Quality Report
  2. Market Analysis Report
  3. Comparison Matrix
  4. Recommendation Report
  5. Survey Plan
  6. Execution Log
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime

class ReportGenerationSkill:
    def __init__(self, logger):
        self.logger = logger

    def execute(
        self,
        project_meta: Dict[str, Any],
        validation_res: Dict[str, Any],
        market_res: Dict[str, Any],
        eval_res: Dict[str, Any],
        review_res: Dict[str, Any],
        output_dir: str = "outputs",
        tag: str = "latest"
    ) -> Dict[str, str]:
        """Tạo và xuất đầy đủ 6 đầu ra bắt buộc"""
        self.logger.record_step(
            step_id="STEP_5_REPORT_GENERATION",
            step_name="report_generation",
            action="GENERATE_MANDATORY_OUTPUTS",
            details={"message": "Bắt đầu sinh 6 đầu ra chính thức theo chuẩn HUNG PHAT MASTER AGENT."}
        )

        os.makedirs(output_dir, exist_ok=True)
        top_2 = eval_res.get("top_2_recommendations", [])
        unprioritized = eval_res.get("unprioritized_locations", [])
        all_scores = eval_res.get("all_scores", {})

        # -------------------------------------------------------------
        # OUTPUT 4: Recommendation Report
        # -------------------------------------------------------------
        rec_md = self._generate_recommendation_report(
            project_meta=project_meta,
            top_2=top_2,
            unprioritized=unprioritized,
            all_scores=all_scores,
            review_res=review_res
        )

        # -------------------------------------------------------------
        # OUTPUT 5: Survey Plan
        # -------------------------------------------------------------
        survey_md = self._generate_survey_plan(
            top_2=top_2,
            unprioritized=unprioritized,
            review_res=review_res
        )

        # Đường dẫn 6 file bắt buộc
        file_paths = {
            "data_quality_report": os.path.join(output_dir, f"1_data_quality_report_{tag}.md"),
            "market_analysis_report": os.path.join(output_dir, f"2_market_analysis_report_{tag}.md"),
            "comparison_matrix": os.path.join(output_dir, f"3_comparison_matrix_{tag}.md"),
            "recommendation_report": os.path.join(output_dir, f"4_recommendation_report_{tag}.md"),
            "survey_plan": os.path.join(output_dir, f"5_survey_plan_{tag}.md"),
            "execution_log": os.path.join(output_dir, f"6_execution_log_{tag}.json")
        }

        # Lưu OUTPUT 1: Data Quality Report
        with open(file_paths["data_quality_report"], "w", encoding="utf-8") as f:
            f.write(validation_res["data_quality_report_md"])

        # Lưu OUTPUT 2: Market Analysis Report
        with open(file_paths["market_analysis_report"], "w", encoding="utf-8") as f:
            f.write(market_res["market_analysis_report_md"])

        # Lưu OUTPUT 3: Comparison Matrix
        with open(file_paths["comparison_matrix"], "w", encoding="utf-8") as f:
            f.write(eval_res["comparison_matrix_md"])

        # Lưu OUTPUT 4: Recommendation Report
        with open(file_paths["recommendation_report"], "w", encoding="utf-8") as f:
            f.write(rec_md)

        # Lưu OUTPUT 5: Survey Plan
        with open(file_paths["survey_plan"], "w", encoding="utf-8") as f:
            f.write(survey_md)

        # Lưu OUTPUT 6: Execution Log
        self.logger.export_json(file_paths["execution_log"])

        return file_paths

    def _generate_recommendation_report(self, project_meta, top_2, unprioritized, all_scores, review_res) -> str:
        md = []
        md.append("# 🎯 BÁO CÁO ĐỀ XUẤT MỞ RỘNG ĐỊA BÀN (RECOMMENDATION REPORT)")
        md.append(f"**Dự án:** {project_meta.get('project_name', 'Mở rộng thị trường WMS')}")
        md.append(f"**Doanh nghiệp:** {project_meta.get('company', 'Công ty Hưng Phát')}")
        md.append(f"**Ngày lập báo cáo:** {datetime.now().strftime('%Y-%m-%d')} | **Trạng thái Thẩm định:** `{review_res.get('review_status')}`")
        md.append("\n---\n")

        md.append("## 1. KẾT LUẬN ĐỀ XUẤT TỔNG THỂ")
        if review_res.get("review_status") == "NEED_MORE_DATA":
            md.append("⚠️ **TRẠNG THÁI: NEED_MORE_DATA (CHƯA ĐỦ CĂN CỨ ĐỂ LỰA CHỌN 2 ĐỊA BÀN)**")
            md.append(f"> {review_res.get('action_required')}")
        else:
            md.append("Hệ thống HUNG PHAT MASTER AGENT trân trọng đề xuất **2 ĐỊA BÀN ƯU TIÊN HÀNG ĐẦU**:")
            for idx, loc in enumerate(top_2):
                md.append(f"### {idx+1}. {loc['location_name']} (Điểm tổng hợp: {loc['total_score']}/10)")
                md.append(f"- **Quy mô & Tăng trưởng:** Điểm {loc['market_score']}/10 (Số chuỗi: {loc.get('stores')}, Tăng trưởng: {loc.get('growth')}%/năm - Nguồn: *{loc.get('source')}*)")
                md.append(f"- **Mức độ khớp sản phẩm (PMF):** Điểm {loc['pmf_score']}/10 - {loc.get('pmf_verdict')}")
                md.append(f"- **Lợi thế cạnh tranh:** Điểm {loc['comp_score']}/10 - {loc.get('comp_verdict')}")
                md.append(f"- **Khả năng hỗ trợ SLA tại chỗ:** Điểm {loc['feasibility_score']}/10 - Đạt chuẩn, trong tầm phục vụ của 1 đội triển khai duy nhất.")

        md.append("\n---\n## 2. GIẢI THÍCH LÝ DO CHƯA ƯU TIÊN CÁC ĐỊA BÀN CÒN LẠI")
        for loc in unprioritized:
            md.append(f"### 📍 {loc['location_name']}")
            if loc.get("is_disqualified"):
                md.append(f"- **Lý do Loại trừ:** ⛔ **{loc.get('disqualification_reason')}**")
                md.append(f"- **Điều kiện cần bổ sung để xem xét lại:** Cần thiết lập trạm kỹ thuật tại chỗ hoặc ký kết hợp đồng dịch vụ ủy quyền với đối tác trước khi mở rộng.")
            else:
                md.append(f"- **Lý do Tạm hoãn:** ⚠️ Tổng điểm cạnh tranh và khớp sản phẩm thấp hơn Top 2 ({loc['total_score']}/10 vs {top_2[-1]['total_score'] if top_2 else 'N/A'}/10).")
                md.append(f"- **Điều kiện xem xét lại:** Lưu hồ sơ sang đợt 2 sau khi bổ sung thêm nhân lực cho đội triển khai.")

        md.append("\n---\n## 3. Ý KIẾN THẨM ĐỊNH CỦA TRƯỞNG PHÒNG (HUMAN REVIEW GATE)")
        md.append(f"- **Người thẩm định:** {review_res.get('reviewed_by')}")
        md.append(f"- **Trạng thái:** `{review_res.get('review_status')}`")
        md.append(f"- **Ghi chú đánh giá:** {review_res.get('review_notes')}")
        return "\n".join(md)

    def _generate_survey_plan(self, top_2, unprioritized, review_res) -> str:
        md = []
        md.append("# 📋 KẾ HOẠCH KHẢO SÁT THỰC ĐỊA CHI TIẾT (SURVEY PLAN)")
        md.append(f"**Ngày tạo lập:** {datetime.now().strftime('%Y-%m-%d')} | **Trạng thái:** Dành cho 2 địa bàn được phê duyệt")
        md.append("\n---\n")

        if review_res.get("review_status") == "NEED_MORE_DATA":
            md.append("⚠️ **Kế hoạch khảo sát thực địa chính thức tạm hoãn do hệ thống trả về trạng thái `NEED_MORE_DATA`.**")
            md.append(f"Yêu cầu ưu tiên thực hiện khảo sát bổ sung dữ liệu: {review_res.get('action_required')}")
            return "\n".join(md)

        assigned_roles = [
            {"role": "Trưởng đoàn Khảo sát", "name": "Nguyễn Văn Hùng - Chuyên viên Giải pháp WMS", "dept": "Phòng Phát triển Kinh doanh"},
            {"role": "Chuyên viên Kỹ thuật & Hiện trường", "name": "Trần Thị Mai - Kỹ sư Triển khai Hệ thống", "dept": "Phòng Kỹ thuật & Triển khai"}
        ]

        for idx, loc in enumerate(top_2):
            role_info = assigned_roles[idx % len(assigned_roles)]
            loc_id = loc["location_id"]
            
            if loc_id == "LOC_A":
                target_group = "Chuỗi siêu thị mini tiện lợi, chuỗi thời trang bán lẻ vừa và nhỏ (10 - 50 cửa hàng có kho tổng)."
                questions = [
                    "Hiện tại kho đang dùng máy quét Barcode/QR hay kiểm kê thủ công trên sổ sách?",
                    "Hệ thống phần mềm POS/kế toán hiện nay có cổng Open API để đồng bộ dữ liệu tồn kho thời gian thực hay không?",
                    "Mức chi trả chấp nhận được cho phí dịch vụ SaaS hàng tháng/năm là bao nhiêu?",
                    "Tần suất phát sinh sự cố kho ngoài giờ hành chính và thời gian chờ hỗ trợ chấp nhận được là bao lâu?"
                ]
            else:
                target_group = "Chuỗi bán lẻ đặc sản, thực phẩm sạch và kho trung chuyển phân phối hàng FMCG tại Đà Nẵng - Miền Trung."
                questions = [
                    "Quy trình quản lý hạn sử dụng (FIFO/FEFO) đối với hàng tiêu dùng nhanh hiện đang gặp vướng mắc lớn nhất ở khâu nào?",
                    "Nhân sự thủ kho tại địa phương có khả năng tiếp nhận chuyển giao phần mềm trên điện thoại/máy tính bảng trong bao lâu?",
                    "Khách hàng có chấp nhận mô hình hỗ trợ: Kỹ sư đối tác tại Đà Nẵng hỗ trợ trực tiếp khi cần + Hotline trực tuyến 24/7 từ trụ sở chính không?",
                    "Các phần mềm nội địa hiện tại đang gặp lỗi gì khiến doanh nghiệp muốn đổi sang giải pháp mới?"
                ]

            md.append(f"## 🏢 ĐỊA BÀN #{idx+1}: {loc['location_name']}")
            md.append(f"- **Nhóm khách hàng mục tiêu tiếp cận:** {target_group}")
            md.append(f"- **Quy mô mẫu khảo sát:** Tối thiểu 20 chuỗi bán lẻ.")
            md.append(f"- **Bộ phận & Người phụ trách (PIC):**")
            md.append(f"  + **Vai trò:** `{role_info['role']}`")
            md.append(f"  + **Họ tên & Chức danh:** **{role_info['name']}**")
            md.append(f"  + **Đơn vị công tác:** *{role_info['dept']}*")
            md.append(f"- **Thời hạn hoàn thành:** 14 ngày làm việc.")
            md.append(f"- **Danh mục câu hỏi nghiệp vụ cần xác minh tại thực địa kho:**")
            for q_idx, q in enumerate(questions):
                md.append(f"  {q_idx+1}. {q}")
            md.append(f"- **Kết quả bàn giao (Deliverables):** Biên bản thẩm định hiện trường kho và danh sách tối thiểu 5 khách hàng tiềm năng sẵn sàng chạy thử nghiệm (Trial Run).")
            md.append("\n" + "-"*50 + "\n")

        return "\n".join(md)
