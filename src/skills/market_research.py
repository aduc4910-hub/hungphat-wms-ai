"""
Kỹ năng Nghiệp vụ 1: Market Research Skill (Phân tích Nghiên cứu Thị trường & Chuẩn hóa Dữ liệu)
Chịu trách nhiệm:
1. Kiểm tra nguồn, kỳ thời gian, phát hiện trùng lặp & thiếu dữ liệu (Sanitization & Auditing).
2. Đối chiếu nhu cầu khách hàng với danh mục giải pháp (Product-Market Fit Analysis).
3. Đánh giá bức tranh đối thủ cạnh tranh tại từng địa bàn.
"""

from typing import Dict, Any, List
from datetime import datetime

class MarketResearchSkill:
    def __init__(self, logger):
        self.logger = logger

    def sanitize_and_audit_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Làm sạch dữ liệu, kiểm tra nguồn, phát hiện trùng lặp và thiếu thông tin.
        """
        self.logger.record_step(
            step_id="STEP_2_1",
            step_name="Data Sanitization & Source Auditing",
            action="EXECUTE_DATA_AUDIT",
            details={"message": "Bắt đầu kiểm tra nguồn, thời điểm và khử trùng lặp dữ liệu."}
        )

        market_docs = raw_data.get("market_documents", [])
        competitors = raw_data.get("competitor_profiles", [])
        customer_feedbacks = raw_data.get("customer_feedback", [])
        current_year = 2026

        audited_market_data: Dict[str, Dict[str, Any]] = {}
        missing_warnings = []
        duplicate_warnings = []

        # 1. Kiểm tra và lọc tài liệu thị trường theo địa bàn
        for doc in market_docs:
            loc_id = doc.get("location_id")
            if not loc_id:
                continue

            if loc_id not in audited_market_data:
                audited_market_data[loc_id] = {
                    "valid_documents": [],
                    "excluded_documents": [],
                    "latest_market_size_vnd_bil": None,
                    "latest_retail_stores_count": None,
                    "latest_growth_rate_pct": None,
                    "primary_source": None,
                    "primary_timestamp": None,
                    "audit_notes": []
                }

            # Kiểm tra cờ trùng lặp hoặc dẫn lại nguồn cũ
            if doc.get("duplicate_flag") is True or "Dẫn lại" in str(doc.get("source", "")):
                self.logger.record_warning(
                    step_id="STEP_2_1",
                    warning_type="DUPLICATE_SOURCE_DETECTED",
                    message=f"Phát hiện số liệu lặp nguồn tại {loc_id} trong tài liệu '{doc.get('title')}' (Dẫn lại từ {doc.get('duplicate_of_source', 'nguồn khác')}). Loại bỏ khỏi tính toán kép.",
                    context_data={"doc_id": doc.get("doc_id")}
                )
                audited_market_data[loc_id]["excluded_documents"].append(doc)
                duplicate_warnings.append(f"Tài liệu {doc.get('doc_id')} tại {loc_id} là số liệu lặp nguồn.")
                continue

            # Kiểm tra thời điểm dữ liệu
            ts_str = doc.get("timestamp")
            if ts_str:
                try:
                    doc_year = int(ts_str.split("-")[0])
                    if current_year - doc_year >= 4:
                        self.logger.record_warning(
                            step_id="STEP_2_1",
                            warning_type="OUTDATED_DATA_WARNING",
                            message=f"Tài liệu {doc.get('doc_id')} tại {loc_id} có kỳ thống kê cũ ({ts_str}), có thể không phản ánh đúng thực tế hiện nay.",
                            context_data={"doc_id": doc.get("doc_id"), "year": doc_year}
                        )
                except Exception:
                    pass

            # Kiểm tra trường thiếu
            if doc.get("source") is None or doc.get("retail_stores_count") is None:
                self.logger.record_warning(
                    step_id="STEP_2_1",
                    warning_type="MISSING_MARKET_METRICS",
                    message=f"Địa bàn {loc_id} bị thiếu nguồn hoặc thiếu số liệu quy mô cửa hàng.",
                    context_data={"doc_id": doc.get("doc_id")}
                )
                missing_warnings.append(f"Địa bàn {loc_id} thiếu chỉ số quy mô thị trường chính xác.")

            audited_market_data[loc_id]["valid_documents"].append(doc)
            
            # Cập nhật số liệu mới nhất
            if doc.get("retail_stores_count") is not None:
                audited_market_data[loc_id]["latest_retail_stores_count"] = doc.get("retail_stores_count")
            if doc.get("market_size_vnd_bil") is not None:
                audited_market_data[loc_id]["latest_market_size_vnd_bil"] = doc.get("market_size_vnd_bil")
            if doc.get("annual_growth_rate_pct") is not None:
                audited_market_data[loc_id]["latest_growth_rate_pct"] = doc.get("annual_growth_rate_pct")
            if doc.get("source"):
                audited_market_data[loc_id]["primary_source"] = doc.get("source")
            if doc.get("timestamp"):
                audited_market_data[loc_id]["primary_timestamp"] = doc.get("timestamp")

        # 2. Ghép dữ liệu đối thủ
        competitor_map = {c.get("location_id"): c for c in competitors}
        # 3. Ghép phản hồi khách hàng
        feedback_map = {f.get("location_id"): f for f in customer_feedbacks}

        # Tổng hợp toàn bộ 4 địa bàn mục tiêu
        all_loc_ids = list(raw_data.get("deployment_capacity", {}).get("regional_support_hubs", {}).keys())
        consolidated_data = {}

        for loc_id in all_loc_ids:
            mkt_info = audited_market_data.get(loc_id, {
                "valid_documents": [],
                "excluded_documents": [],
                "latest_market_size_vnd_bil": None,
                "latest_retail_stores_count": None,
                "latest_growth_rate_pct": None,
                "primary_source": "Không có tài liệu",
                "primary_timestamp": "N/A"
            })
            comp_info = competitor_map.get(loc_id, {})
            fb_info = feedback_map.get(loc_id, {})

            # Cảnh báo thiếu nếu không có đối thủ hoặc feedback
            if not comp_info.get("competitors"):
                missing_warnings.append(f"Địa bàn {loc_id} chưa có hồ sơ phân tích đối thủ cạnh tranh.")
                self.logger.record_warning(
                    step_id="STEP_2_1",
                    warning_type="MISSING_COMPETITOR_DATA",
                    message=f"Địa bàn {loc_id} thiếu dữ liệu đối thủ cạnh tranh.",
                    context_data={"location_id": loc_id}
                )

            if not fb_info or fb_info.get("sample_size", 0) == 0:
                missing_warnings.append(f"Địa bàn {loc_id} thiếu mẫu phản hồi khảo sát nhu cầu khách hàng.")
                self.logger.record_warning(
                    step_id="STEP_2_1",
                    warning_type="MISSING_CUSTOMER_FEEDBACK",
                    message=f"Địa bàn {loc_id} không có dữ liệu khảo sát khách hàng hợp lệ.",
                    context_data={"location_id": loc_id}
                )

            consolidated_data[loc_id] = {
                "market_data": mkt_info,
                "competitor_data": comp_info,
                "customer_feedback": fb_info
            }

        return {
            "consolidated_data": consolidated_data,
            "missing_warnings": missing_warnings,
            "duplicate_warnings": duplicate_warnings
        }

    def analyze_product_fit_and_competition(
        self, 
        consolidated_data: Dict[str, Any], 
        solution_catalog: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phân tích độ tương thích sản phẩm (Product-Market Fit) và môi trường cạnh tranh.
        """
        self.logger.record_step(
            step_id="STEP_2_2",
            step_name="Product-Market Fit & Competition Analysis",
            action="EVALUATE_FIT_AND_COMPETITORS",
            details={"message": "Đang đối chiếu tính năng giải pháp Hưng Phát với nhu cầu từng địa bàn."}
        )

        supported_features = set(solution_catalog.get("supported_features", []))
        unsupported_features = set(solution_catalog.get("unsupported_features", []))

        analysis_results = {}

        for loc_id, data in consolidated_data.items():
            fb = data.get("customer_feedback", {})
            demanded = fb.get("demanded_features", [])
            sample_size = fb.get("sample_size", 0)

            # 1. Tính toán Product-Market Fit Score
            if sample_size == 0 or not demanded:
                pmf_score = 0.0
                matched_features = []
                unmatched_features = []
                gap_analysis = "Không đủ dữ liệu khảo sát khách hàng để đánh giá độ khớp giải pháp."
            else:
                matched_features = [f for f in demanded if f in supported_features]
                unmatched_features = [f for f in demanded if f not in supported_features]
                
                # Điểm khớp cơ sở theo tỷ lệ tính năng đáp ứng
                fit_ratio = len(matched_features) / len(demanded)
                pmf_score = round(fit_ratio * 10.0, 1)

                # Kiểm tra xem khách có yêu cầu tính năng vượt năng lực (Unsupported)
                critical_gaps = [f for f in unmatched_features if f in unsupported_features]
                if critical_gaps:
                    gap_analysis = f"Khách hàng đòi hỏi tính năng Hưng Phát CHƯA HỖ TRỢ: {', '.join(critical_gaps)}."
                    # Phạt điểm PMF nếu khách đòi hỏi hệ thống ngoài danh mục
                    pmf_score = max(0.0, round(pmf_score * 0.6, 1))
                else:
                    gap_analysis = "Giải pháp của Hưng Phát đáp ứng đúng các bài toán cốt lõi của khách hàng."

            # 2. Đánh giá Cạnh tranh (Competition Score từ 1 đến 10)
            comp_profile = data.get("competitor_data", {})
            competitors = comp_profile.get("competitors", [])

            if not competitors:
                comp_score = 5.0  # Mặc định trung tính nếu thiếu dữ liệu
                comp_summary = "Chưa có dữ liệu đối thủ (Cần khảo sát bổ sung)."
            else:
                # Tính tổng thị phần của đối thủ lớn nhất
                max_market_share = max((c.get("market_share_pct", 0) for c in competitors), default=0)
                if max_market_share >= 60.0:
                    comp_score = 3.0  # Cạnh tranh rất gay gắt / Độc quyền
                    comp_summary = f"Thị trường bị độc quyền bởi đối thủ lớn chiếm {max_market_share}% thị phần. Rào cản thâm nhập cao."
                elif max_market_share >= 35.0:
                    comp_score = 6.5  # Cạnh tranh trung bình
                    comp_summary = f"Có đối thủ đáng kể ({max_market_share}% thị phần) nhưng còn nhiều phân khúc trống."
                else:
                    comp_score = 9.0  # Cạnh tranh thuận lợi, phân mảnh
                    comp_summary = "Thị trường phân mảnh, đối thủ địa phương yếu hoặc phục vụ phân khúc khác. Rất thuận lợi thâm nhập."

            analysis_results[loc_id] = {
                "pmf_score": pmf_score,
                "matched_features": matched_features,
                "unmatched_features": unmatched_features,
                "gap_analysis": gap_analysis,
                "comp_score": comp_score,
                "comp_summary": comp_summary,
                "customer_onsite_demand": fb.get("onsite_support_demanded"),
                "onsite_strictness": fb.get("onsite_support_strictness")
            }

        return analysis_results
