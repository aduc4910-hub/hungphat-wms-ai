"""
Kỹ năng Nghiệp vụ 2: Criteria Evaluation Skill (Đánh giá Đa tiêu chí & Kiểm tra Ràng buộc Khả năng Triển khai)
Chịu trách nhiệm:
1. Chấm điểm ma trận đa tiêu chí (MCDA - Multi-Criteria Decision Analysis).
2. Kiểm tra ràng buộc cứng (Hard Constraint): Yêu cầu hỗ trợ tại chỗ vs Năng lực SLA thực tế.
3. Xếp hạng, lựa chọn 2 địa bàn tối ưu và giải trình quyết định kèm căn cứ tài liệu nguồn.
"""

from typing import Dict, Any, List, Tuple

class CriteriaEvaluationSkill:
    def __init__(self, logger):
        self.logger = logger

    def evaluate_and_rank_locations(
        self,
        consolidated_data: Dict[str, Any],
        market_insights: Dict[str, Any],
        criteria_list: List[Dict[str, Any]],
        deployment_capacity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tính điểm theo bộ tiêu chí, kiểm tra ràng buộc ranh giới và xếp hạng địa bàn.
        """
        self.logger.record_step(
            step_id="STEP_3_1",
            step_name="Multi-Criteria Decision Analysis & Feasibility Check",
            action="EVALUATE_MCDA_AND_CONSTRAINTS",
            details={"message": "Bắt đầu chấm điểm đa tiêu chí và kiểm tra ràng buộc SLA hỗ trợ tại chỗ."}
        )

        hubs = deployment_capacity.get("regional_support_hubs", {})
        scores = {}
        criteria_map = {c["criteria_id"]: c for c in criteria_list}

        # Tìm giá trị cực đại để chuẩn hóa điểm quy mô thị trường (từ 1 - 10)
        max_stores = 1
        for loc_id, data in consolidated_data.items():
            stores = data["market_data"].get("latest_retail_stores_count") or 0
            if stores > max_stores:
                max_stores = stores

        for loc_id, data in consolidated_data.items():
            mkt_data = data["market_data"]
            insight = market_insights.get(loc_id, {})
            hub_info = hubs.get(loc_id, {})

            # -------------------------------------------------------------
            # 1. TIÊU CHÍ 1: Quy mô & Tốc độ tăng trưởng thị trường (CRIT_01)
            # -------------------------------------------------------------
            stores = mkt_data.get("latest_retail_stores_count")
            growth = mkt_data.get("latest_growth_rate_pct")
            if stores is None or growth is None:
                market_score = 3.0  # Phạt điểm nếu thiếu số liệu định lượng
                market_eval_note = "Thiếu dữ liệu quy mô hoặc tăng trưởng (chỉ ước lượng tối thiểu)."
            else:
                norm_size = (stores / max_stores) * 6.0  # Tối đa 6 điểm quy mô
                growth_bonus = min(4.0, (growth / 20.0) * 4.0)  # Tối đa 4 điểm tăng trưởng
                market_score = round(norm_size + growth_bonus, 2)
                market_eval_note = f"Số chuỗi: {stores}, Tăng trưởng: {growth}%/năm."

            # -------------------------------------------------------------
            # 2. TIÊU CHÍ 2: Mức độ phù hợp sản phẩm (CRIT_02)
            # -------------------------------------------------------------
            pmf_score = insight.get("pmf_score", 0.0)
            pmf_eval_note = insight.get("gap_analysis", "")

            # -------------------------------------------------------------
            # 3. TIÊU CHÍ 3: Môi trường cạnh tranh (CRIT_03)
            # -------------------------------------------------------------
            comp_score = insight.get("comp_score", 5.0)
            comp_eval_note = insight.get("comp_summary", "")

            # -------------------------------------------------------------
            # 4. TIÊU CHÍ 4: Khả năng triển khai & Hỗ trợ tại chỗ (CRIT_04)
            # (RÀNG BUỘC CỨNG / HARD CONSTRAINT CHECK)
            # -------------------------------------------------------------
            onsite_demand = insight.get("customer_onsite_demand") or "Không rõ"
            strictness = insight.get("onsite_strictness")
            hub_status = hub_info.get("hub_status", "Chưa xác định")
            response_time = hub_info.get("onsite_response_time_hours", 999)

            feasibility_score = 10.0
            is_disqualified = False
            disqualification_reason = None

            # Kiểm tra các điều kiện ranh giới (Boundary Rules)
            # Quy tắc 1: Khách hàng bắt buộc hỗ trợ trực ca đêm tại kho (22h - 6h)
            if strictness == "Extreme_Night_Shift_Mandatory":
                is_disqualified = True
                feasibility_score = 0.0
                disqualification_reason = "VI PHẠM RÀNG BUỘC CỨNG: Khách hàng bắt buộc trực ca đêm tại kho 24/7; Hưng Phát hiện chỉ có 1 đội triển khai ban ngày, không có nhân lực trực đêm."
                self.logger.record_warning(
                    step_id="STEP_3_1",
                    warning_type="HARD_CONSTRAINT_VIOLATED",
                    message=f"Địa bàn {loc_id} bị LOẠI BỎ: Yêu cầu trực đêm vượt quá năng lực phục vụ.",
                    context_data={"location": loc_id, "demand": onsite_demand}
                )

            # Quy tắc 2: Chưa có trạm kỹ thuật/đối tác nhưng khách đòi có mặt trong 1-2h
            elif "Chưa có trạm" in hub_status and (strictness == "Ultra_Strict_Immediate" or response_time > 12):
                is_disqualified = True
                feasibility_score = 1.0
                disqualification_reason = f"VI PHẠM NĂNG LỰC SLA: Chưa có trạm kỹ thuật tại địa bàn (mất 24h-48h di chuyển), nhưng khách yêu cầu có mặt tại kho trong 1-2 giờ."
                self.logger.record_warning(
                    step_id="STEP_3_1",
                    warning_type="HARD_CONSTRAINT_VIOLATED",
                    message=f"Địa bàn {loc_id} bị LOẠI BỎ: Khoảng cách địa lý và thiếu trạm kỹ thuật gây nguy cơ vỡ SLA.",
                    context_data={"location": loc_id, "response_time_hours": response_time}
                )

            # Quy tắc 3: Khách đòi hỏi có kỹ sư trực 24/7 tại kho trong nhiều tháng nhưng địa bàn đã có chi nhánh
            elif strictness == "Strict_24_7":
                feasibility_score = 4.5  # Bị trừ điểm nặng do thâm dụng nhân sự
                disqualification_reason = "Nguy cơ quá tải nhân sự triển khai (đòi hỏi kỹ sư trực 24/7 tại kho nhiều tháng)."

            # Quy tắc 4: Địa bàn thuận lợi có trạm kỹ thuật hoặc đối tác ủy quyền, khách đồng thuận SLA
            elif "Đã có văn phòng" in hub_status:
                feasibility_score = 9.5
            elif "Có đối tác" in hub_status:
                feasibility_score = 8.5
            else:
                feasibility_score = 5.0

            # -------------------------------------------------------------
            # TÍNH ĐIỂM TỔNG HỢP CÓ TRỌNG SỐ (Weighted Score)
            # -------------------------------------------------------------
            w1 = criteria_map["CRIT_01"]["weight"]
            w2 = criteria_map["CRIT_02"]["weight"]
            w3 = criteria_map["CRIT_03"]["weight"]
            w4 = criteria_map["CRIT_04"]["weight"]

            total_weighted_score = round(
                (market_score * w1) + 
                (pmf_score * w2) + 
                (comp_score * w3) + 
                (feasibility_score * w4), 
                2
            )

            # Nếu vi phạm ràng buộc cứng thì không cho phép lọt vào đề xuất
            final_status = "ELIGIBLE" if not is_disqualified else "DISQUALIFIED_BY_CONSTRAINT"

            scores[loc_id] = {
                "location_id": loc_id,
                "location_name": hub_info.get("location_name", loc_id),
                "criteria_scores": {
                    "market_potential": market_score,
                    "product_market_fit": pmf_score,
                    "competition_advantage": comp_score,
                    "deployment_feasibility": feasibility_score
                },
                "total_score": total_weighted_score,
                "status": final_status,
                "is_disqualified": is_disqualified,
                "disqualification_reason": disqualification_reason,
                "source_evidence": {
                    "primary_source": mkt_data.get("primary_source"),
                    "primary_timestamp": mkt_data.get("primary_timestamp"),
                    "doc_count": len(mkt_data.get("valid_documents", []))
                },
                "notes": {
                    "market_note": market_eval_note,
                    "pmf_note": pmf_eval_note,
                    "comp_note": comp_eval_note
                }
            }

        # -------------------------------------------------------------
        # XẾP HẠNG VÀ CHỌN TOP 2
        # -------------------------------------------------------------
        eligible_locations = [v for v in scores.values() if not v["is_disqualified"]]
        # Sắp xếp giảm dần theo tổng điểm
        eligible_locations.sort(key=lambda x: x["total_score"], reverse=True)

        disqualified_locations = [v for v in scores.values() if v["is_disqualified"]]

        top_2_recommendations = eligible_locations[:2]
        unprioritized_locations = eligible_locations[2:] + disqualified_locations

        self.logger.record_step(
            step_id="STEP_3_2",
            step_name="Location Selection & Justification",
            action="FINALIZE_TOP_LOCATIONS",
            details={
                "message": f"Đã hoàn thành đánh giá. Chọn 2 địa bàn: {[l['location_id'] for l in top_2_recommendations]}",
                "top_2": [l["location_id"] for l in top_2_recommendations],
                "unprioritized": [l["location_id"] for l in unprioritized_locations]
            }
        )

        return {
            "all_scores": scores,
            "top_2_recommendations": top_2_recommendations,
            "unprioritized_locations": unprioritized_locations
        }
