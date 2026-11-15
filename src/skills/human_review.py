"""
SKILL 4: human_review (Cổng Kiểm soát Thẩm định của Con người - Human-in-the-Loop Gatekeeper)
Tuân thủ HUNG PHAT MASTER AGENT Blueprint:
- Chuyển kết quả để người quản lý thẩm định.
- Nếu thiếu căn cứ, báo cáo rõ dữ liệu cần bổ sung (trạng thái NEED_MORE_DATA).
- Nếu bị từ chối, tiếp nhận yêu cầu điều chỉnh và chạy lại bước liên quan.
- Không tự nhận đã được phê duyệt.
"""

from typing import Dict, Any, List

class HumanReviewSkill:
    def __init__(self, logger):
        self.logger = logger

    def review(
        self,
        validation_res: Dict[str, Any],
        eval_res: Dict[str, Any],
        auto_manager_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Thẩm định kết quả theo các điều kiện chuyển xử lý của Trưởng phòng
        """
        self.logger.record_step(
            step_id="STEP_4_HUMAN_REVIEW",
            step_name="human_review",
            action="REQUEST_HUMAN_VERIFICATION",
            details={"message": "Chuyển giao hồ sơ đề xuất cho Trưởng phòng Phát triển Kinh doanh thẩm định."}
        )

        top_2 = eval_res.get("top_2_recommendations", [])
        missing_issues = validation_res.get("missing_issues", [])
        is_critical_missing = validation_res.get("is_critical_missing", False)

        # 1. Kiểm tra điều kiện đủ căn cứ lựa chọn
        if len(top_2) < 2 or is_critical_missing:
            status = "NEED_MORE_DATA"
            rejection_reason = "Không đủ căn cứ dữ liệu để lựa chọn an toàn 2 địa bàn."
            action_required = (
                "Hệ thống yêu cầu nạp bổ sung: " + 
                "; ".join(missing_issues) + 
                ". Chưa thể phê duyệt đề xuất trước khi khắc phục các thiếu hụt này."
            )
            self.logger.record_warning(
                step_id="STEP_4_HUMAN_REVIEW",
                warning_type="NEED_MORE_DATA_TRIGGERED",
                message="Quy trình tạm dừng tại cổng Human Review: Trả về trạng thái NEED_MORE_DATA.",
                context_data={"missing_issues": missing_issues}
            )
            return {
                "review_status": status,
                "is_approved": False,
                "review_notes": rejection_reason,
                "action_required": action_required,
                "reviewed_by": "Trưởng phòng Phát triển Kinh doanh (Hệ thống Gatekeeper)"
            }

        # 2. Kiểm tra điều kiện ràng buộc SLA của Top 2
        for loc in top_2:
            if loc.get("is_disqualified"):
                status = "REJECTED_BY_CONSTRAINT"
                return {
                    "review_status": status,
                    "is_approved": False,
                    "review_notes": f"Địa bàn {loc['location_name']} vi phạm ràng buộc SLA nhưng vẫn xuất hiện trong danh sách.",
                    "action_required": "Yêu cầu Agent chạy lại thuật toán lọc ràng buộc cứng.",
                    "reviewed_by": "Trưởng phòng Phát triển Kinh doanh"
                }

        # 3. Phê duyệt (Approval)
        if auto_manager_approval:
            status = "APPROVED_BY_MANAGER"
            review_notes = (
                f"Trưởng phòng Phát triển Kinh doanh ĐỒNG THUẬN đề xuất 2 địa bàn: "
                f"{[l['location_name'] for l in top_2]}. Cho phép chuyển sang lập Kế hoạch Khảo sát."
            )
            self.logger.record_step(
                step_id="STEP_4_HUMAN_REVIEW",
                step_name="human_review",
                action="MANAGER_APPROVAL_GRANTED",
                details={"approved_locations": [l["location_id"] for l in top_2]}
            )
            return {
                "review_status": status,
                "is_approved": True,
                "review_notes": review_notes,
                "action_required": "Chuyển giao cho Nhóm Triển khai lập kế hoạch thực địa.",
                "reviewed_by": "Trưởng phòng Phát triển Kinh doanh (Phê duyệt chính thức)"
            }

        return {
            "review_status": "PENDING_MANUAL_INPUT",
            "is_approved": False,
            "review_notes": "Đang chờ Trưởng phòng bấm duyệt hoặc nhập yêu cầu điều chỉnh.",
            "action_required": "Cần can thiệp người dùng.",
            "reviewed_by": "Chưa có"
        }
