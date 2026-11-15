"""
SKILL 3: location_evaluation (Chấm điểm Đa tiêu chí, Ràng buộc Khả thi & Lập Ma trận So sánh)
Tuân thủ HUNG PHAT MASTER AGENT Blueprint:
- Đối chiếu 4 địa bàn theo bộ tiêu chí.
- Áp dụng đúng công thức và trọng số được cung cấp.
- Phân biệt dữ liệu thực tế và nhận định suy luận.
- Đề xuất 2 địa bàn ưu tiên.
- Giải thích lý do chưa ưu tiên 2 địa bàn còn lại.
- Tạo Comparison Matrix.
"""

from typing import Dict, Any, List
from datetime import datetime

class LocationEvaluationSkill:
    def __init__(self, logger):
        self.logger = logger

    def execute(
        self,
        location_insights: Dict[str, Any],
        criteria_list: List[Dict[str, Any]],
        deployment_capacity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Thực thi đối chiếu đa tiêu chí và sinh Comparison Matrix"""
        self.logger.record_step(
            step_id="STEP_3_LOCATION_EVALUATION",
            step_name="location_evaluation",
            action="EVALUATE_MCDA_AND_CONSTRAINTS",
            details={"message": "Chấm điểm theo bộ tiêu chí trọng số và kiểm tra ràng buộc ranh giới SLA."}
        )

        criteria_map = {c["criteria_id"]: c for c in criteria_list}
        scores = {}

        # 1. Chuẩn hóa thang đo quy mô thị trường (tối đa 10 điểm)
        max_stores = 1
        for ins in location_insights.values():
            stores = ins.get("retail_stores_count") or 0
            if stores > max_stores:
                max_stores = stores

        for loc_id, ins in location_insights.items():
            stores = ins.get("retail_stores_count")
            growth = ins.get("annual_growth_rate_pct")

            # Tiêu chí 1: Quy mô & Tăng trưởng (CRIT_01)
            if stores is None or growth is None:
                market_score = 3.0
            else:
                norm_size = (stores / max_stores) * 6.0
                growth_bonus = min(4.0, (growth / 20.0) * 4.0)
                market_score = round(norm_size + growth_bonus, 2)

            # Tiêu chí 2: Khớp sản phẩm PMF (CRIT_02)
            pmf_score = ins.get("pmf_score", 0.0)

            # Tiêu chí 3: Cạnh tranh (CRIT_03)
            comp_score = ins.get("comp_score", 5.0)

            # Tiêu chí 4: Khả năng triển khai & SLA (CRIT_04) - RÀNG BUỘC CỨNG (Hard Constraint)
            strictness = ins.get("strictness")
            hub_status = ins.get("hub_status", "")
            response_time = ins.get("response_time_hours", 999)

            feasibility_score = 10.0
            is_disqualified = False
            disqualification_reason = None

            # Boundary Rule 1: Khách hàng bắt buộc trực đêm ca 24/7 (22h - 6h)
            if strictness == "Extreme_Night_Shift_Mandatory":
                is_disqualified = True
                feasibility_score = 0.0
                disqualification_reason = "VI PHẠM RÀNG BUỘC CỨNG: Khách hàng bắt buộc trực đêm tại kho 24/7 (vượt quá năng lực phục vụ của 1 đội triển khai duy nhất)."
                self.logger.record_warning(
                    step_id="STEP_3_LOCATION_EVALUATION",
                    warning_type="HARD_CONSTRAINT_VIOLATED",
                    message=f"Địa bàn {loc_id} bị LOẠI TRỪ do yêu cầu trực đêm vượt quá năng lực phục vụ.",
                    context_data={"location": loc_id, "demand": ins.get("onsite_demand")}
                )

            # Boundary Rule 2: Chưa có trạm nhưng khách đòi có mặt trong 1-2h
            elif "Chưa có trạm" in hub_status and (strictness == "Ultra_Strict_Immediate" or response_time > 12):
                is_disqualified = True
                feasibility_score = 1.0
                disqualification_reason = f"VI PHẠM NĂNG LỰC SLA: Chưa có trạm kỹ thuật tại chỗ (mất 24h-48h di chuyển), khách yêu cầu có mặt tại kho trong 1-2h."
                self.logger.record_warning(
                    step_id="STEP_3_LOCATION_EVALUATION",
                    warning_type="HARD_CONSTRAINT_VIOLATED",
                    message=f"Địa bàn {loc_id} bị LOẠI TRỪ do khoảng cách địa lý gây vỡ SLA.",
                    context_data={"location": loc_id, "response_time_hours": response_time}
                )

            # Rule 3: Khách đòi hỏi kỹ sư trực 24/7 nhiều tháng tại nơi đã có chi nhánh
            elif strictness == "Strict_24_7":
                feasibility_score = 4.5
                disqualification_reason = "RỦI RO QUÁ TẢI NHÂN SỰ: Đòi hỏi kỹ sư trực 24/7 tại kho nhiều tháng, gây cạn kiệt đội triển khai duy nhất."

            elif "Đã có văn phòng" in hub_status:
                feasibility_score = 9.5
            elif "Có đối tác" in hub_status:
                feasibility_score = 8.5
            else:
                feasibility_score = 5.0

            # Tính điểm có trọng số
            w1 = criteria_map["CRIT_01"]["weight"]
            w2 = criteria_map["CRIT_02"]["weight"]
            w3 = criteria_map["CRIT_03"]["weight"]
            w4 = criteria_map["CRIT_04"]["weight"]

            total_score = round(
                (market_score * w1) +
                (pmf_score * w2) +
                (comp_score * w3) +
                (feasibility_score * w4),
                2
            )

            scores[loc_id] = {
                "location_id": loc_id,
                "location_name": ins["location_name"],
                "market_score": market_score,
                "pmf_score": pmf_score,
                "comp_score": comp_score,
                "feasibility_score": feasibility_score,
                "total_score": total_score,
                "is_disqualified": is_disqualified,
                "disqualification_reason": disqualification_reason,
                "source": ins.get("source"),
                "timestamp": ins.get("timestamp"),
                "stores": ins.get("retail_stores_count"),
                "growth": ins.get("annual_growth_rate_pct"),
                "pmf_verdict": ins.get("pmf_verdict"),
                "comp_verdict": ins.get("comp_verdict"),
                "onsite_demand": ins.get("onsite_demand")
            }

        # Sắp xếp và chọn Top 2
        eligible = [v for v in scores.values() if not v["is_disqualified"]]
        eligible.sort(key=lambda x: x["total_score"], reverse=True)
        disqualified = [v for v in scores.values() if v["is_disqualified"]]

        top_2 = eligible[:2]
        unprioritized = eligible[2:] + disqualified

        comparison_matrix_md = self._generate_comparison_matrix(scores, top_2)

        return {
            "all_scores": scores,
            "top_2_recommendations": top_2,
            "unprioritized_locations": unprioritized,
            "comparison_matrix_md": comparison_matrix_md
        }

    def _generate_comparison_matrix(self, scores: Dict[str, Any], top_2: List[Dict[str, Any]]) -> str:
        md = []
        md.append("# ⚖️ MA TRẬN SO SÁNH 4 ĐỊA BÀN (COMPARISON MATRIX)")
        md.append(f"**Thời điểm tạo:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("\n| Địa bàn | Quy mô & Tăng trưởng (25%) | Khớp SP PMF (30%) | Dư địa Cạnh tranh (20%) | Khả năng Hỗ trợ SLA (25%) | Tổng điểm (10) | Trạng thái | Căn cứ Nguồn & Kỳ thống kê |")
        md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|")

        top_ids = [l["location_id"] for l in top_2]
        for loc_id, sc in scores.items():
            if sc["is_disqualified"]:
                status = "⛔ Loại trừ (Vi phạm SLA)"
            elif loc_id in top_ids:
                status = "✅ Ưu tiên chọn"
            else:
                status = "⚠️ Tạm hoãn đợt 1"

            source_cite = f"{sc.get('source', 'N/A')} ({sc.get('timestamp', 'N/A')})"
            md.append(
                f"| **{sc['location_name']}** | {sc['market_score']}/10 | {sc['pmf_score']}/10 | "
                f"{sc['comp_score']}/10 | {sc['feasibility_score']}/10 | **{sc['total_score']}** | "
                f"{status} | {source_cite} |"
            )

        md.append("\n---\n> **Quy tắc Kiểm soát:** Phân định rõ số liệu trong tài liệu với suy luận chấm điểm của AI Agent. Tuyệt đối không đánh đồng quy mô thị trường với mức độ phù hợp sản phẩm.")
        return "\n".join(md)
