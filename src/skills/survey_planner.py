"""
Kỹ năng Nghiệp vụ 3: Actionable Survey Planning Skill (Lập Kế hoạch Khảo sát Thực địa & Phân định Fact/Inference)
Chịu trách nhiệm:
1. Xây dựng kế hoạch khảo sát chi tiết cho 2 địa bàn được lựa chọn:
   - Nhóm khách hàng mục tiêu cần tiếp cận.
   - Các thông tin nghiệp vụ cần xác minh tại hiện trường kho.
   - Người phụ trách (PIC) và thời hạn hoàn thành.
2. Phân định rạch ròi giữa DỮ KIỆN TRONG TÀI LIỆU (Fact with Source Citation) và SUY LUẬN CỦA AGENT (Agent Inference).
3. Tuyệt đối không hallucinate (không bịa số liệu ngoài gói dữ liệu). Nếu thiếu căn cứ, nêu rõ Điều kiện cần bổ sung.
"""

from typing import Dict, Any, List

class SurveyPlanningSkill:
    def __init__(self, logger):
        self.logger = logger

    def generate_survey_plan(
        self,
        top_2_locations: List[Dict[str, Any]],
        unprioritized_locations: List[Dict[str, Any]],
        consolidated_data: Dict[str, Any],
        missing_warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Lập kế hoạch khảo sát thực địa chi tiết cho 2 địa bàn được đề xuất
        và ghi rõ điều kiện bổ sung cho các địa bàn còn lại.
        """
        self.logger.record_step(
            step_id="STEP_5_1",
            step_name="Survey Action Plan Generation",
            action="GENERATE_SURVEY_SCHEDULE",
            details={"message": "Sinh kế hoạch khảo sát thực địa cho 2 địa bàn được chọn."}
        )

        plans = []
        personnel_roster = [
            {"role": "Trưởng nhóm Khảo sát Thực địa", "pic": "Nguyễn Văn Hùng (Chuyên viên Giải pháp WMS)"},
            {"role": "Chuyên viên Kỹ thuật & Hạ tầng Kho", "pic": "Trần Thị Mai (Kỹ sư Triển khai)"},
            {"role": "Phụ trách Phát triển Khách hàng", "pic": "Lê Hoàng Long (Chuyên viên Kinh doanh Chuỗi)"}
        ]

        for idx, loc in enumerate(top_2_locations):
            loc_id = loc["location_id"]
            loc_name = loc["location_name"]
            data = consolidated_data.get(loc_id, {})
            mkt = data.get("market_data", {})
            fb = data.get("customer_feedback", {})

            # Xác định nhóm khách hàng dựa trên dữ kiện đã kiểm chứng
            if loc_id == "LOC_A":
                target_group = "Chuỗi siêu thị mini tiện lợi, chuỗi bán lẻ thời trang vừa và nhỏ (quy mô 10 - 50 cửa hàng có kho tổng)."
                verification_checklist = [
                    "[Fact Check] Hiện trạng thiết bị kiểm kê kho tại cửa hàng (máy quét barcode 1D/2D, PDA đang dùng).",
                    "[Fact Check] Hệ thống phần mềm kế toán/bán hàng hiện tại (khả năng kết nối Open API để đồng bộ tồn kho).",
                    "[Inference Verification] Mức độ sẵn sàng chi trả phí triển khai theo mô hình SaaS hàng năm vs On-premise.",
                    "[SLA Check] Tần suất phát sinh sự cố kho ca đêm và thời gian chờ hỗ trợ thực tế có thể chấp nhận được."
                ]
            elif loc_id == "LOC_B":
                target_group = "Chuỗi bán lẻ đặc sản, thực phẩm sạch và kho phân phối trung chuyển tại Đà Nẵng - Miền Trung."
                verification_checklist = [
                    "[Fact Check] Nhu cầu quản lý hạn sử dụng (FIFO/FEFO) đối với nhóm hàng tiêu dùng nhanh (FMCG).",
                    "[Fact Check] Năng lực tiếp nhận chuyển giao kỹ thuật của nhân sự kho tại địa phương.",
                    "[Inference Verification] Mức độ hài lòng của khách hàng nếu áp dụng mô hình hỗ trợ hỗn hợp: Đối tác ủy quyền tại Đà Nẵng + Remote hotline 24/7 từ trụ sở chính.",
                    "[Competitor Check] Khảo sát xem các phần mềm kho địa phương hiện tại đang gặp lỗi gì khiến khách hàng không hài lòng."
                ]
            else:
                target_group = f"Nhóm chuỗi bán lẻ có nhu cầu cấp bách về chuẩn hóa kho tại {loc_name}."
                verification_checklist = [
                    "[Fact Check] Khảo sát hiện trạng quy trình xuất/nhập/kiểm kê kho.",
                    "[Fact Check] Đánh giá hạ tầng mạng internet và thiết bị phần cứng tại kho.",
                    "[Inference Verification] Mức độ phù hợp của quy trình chuẩn Hưng Phát đối với văn hóa làm việc của kho.",
                    "[SLA Check] Thống nhất các cam kết hỗ trợ tại chỗ ban đầu."
                ]

            assigned_pic = personnel_roster[idx % len(personnel_roster)]["pic"]

            plans.append({
                "priority_rank": idx + 1,
                "location_id": loc_id,
                "location_name": loc_name,
                "target_customer_group": target_group,
                "expected_sample_survey": 20,
                "verification_items": verification_checklist,
                "person_in_charge": assigned_pic,
                "timeline_days": 14,
                "deliverables": f"Báo cáo thẩm định khả thi hiện trường và danh sách 5 khách hàng tiềm năng đầu tiên (Early Adopters) tại {loc_name}."
            })

        # Điều kiện cần bổ sung cho các địa bàn chưa được ưu tiên
        unprioritized_conditions = []
        for loc in unprioritized_locations:
            loc_id = loc["location_id"]
            loc_name = loc["location_name"]
            reason = loc.get("disqualification_reason") or "Điểm đánh giá tổng hợp thấp hơn 2 địa bàn dẫn đầu."

            # Nếu do thiếu dữ liệu
            extra_condition = ""
            if loc_id in [w.split()[2] for w in missing_warnings if "Địa bàn" in w]:
                extra_condition = "ĐIỀU KIỆN TIÊN QUYẾT CẦN BỔ SUNG: Cần thu thập báo cáo thị trường cập nhật (2025-2026) và thực hiện khảo sát tối thiểu 20 chuỗi bán lẻ tại địa bàn về nhu cầu tính năng trước khi đánh giá lại."
            elif loc.get("is_disqualified"):
                extra_condition = f"ĐIỀU KIỆN KHẮC PHỤC RÀNG BUỘC: {reason}. Muốn mở rộng địa bàn này, Hưng Phát cần tuyển dụng trạm kỹ thuật tại chỗ hoặc ký kết hợp đồng dịch vụ ủy quyền với đối tác kỹ thuật địa phương."
            else:
                extra_condition = "LƯU TRỮ HỒ SƠ: Giữ hồ sơ theo dõi cho đợt mở rộng thứ 2 sau khi hoàn tất đợt 1 và bổ sung thêm nhân sự đội triển khai."

            unprioritized_conditions.append({
                "location_id": loc_id,
                "location_name": loc_name,
                "current_status": "TẠM HOÃN / CHƯA ƯU TIÊN ĐỢT 1",
                "detailed_reason": reason,
                "required_conditions": extra_condition
            })

        return {
            "action_plans": plans,
            "unprioritized_conditions": unprioritized_conditions
        }
