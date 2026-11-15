"""
SKILL 2: market_analysis (Phân tích Thị trường, Đối thủ & Khớp Sản phẩm)
Tuân thủ HUNG PHAT MASTER AGENT Blueprint:
- Phân tích riêng từng địa bàn.
- Đánh giá nhu cầu khách hàng.
- Đối chiếu nhu cầu với danh mục sản phẩm (Product-Market Fit).
- Đánh giá đối thủ và năng lực triển khai.
- Tạo Market Analysis Report.
"""

from typing import Dict, Any, List
from datetime import datetime

class MarketAnalysisSkill:
    def __init__(self, logger):
        self.logger = logger

    def execute(self, validated_data: Dict[str, Any], solution_catalog: Dict[str, Any]) -> Dict[str, Any]:
        """Thực thi phân tích chuyên sâu từng địa bàn và sinh Market Analysis Report"""
        self.logger.record_step(
            step_id="STEP_2_MARKET_ANALYSIS",
            step_name="market_analysis",
            action="ANALYZE_MARKET_AND_COMPETITORS",
            details={"message": "Bắt đầu phân tích nhu cầu khách hàng, độ khớp giải pháp và đối thủ cạnh tranh cho từng địa bàn."}
        )

        supported_features = set(solution_catalog.get("supported_features", []))
        unsupported_features = set(solution_catalog.get("unsupported_features", []))
        validated_locations = validated_data.get("validated_locations", {})

        location_insights = {}

        for loc_id, val in validated_locations.items():
            loc_name = val["location_name"]
            valid_docs = val["valid_market_documents"]
            comp_profile = val["competitor_profile"] or {}
            customer_fb = val["customer_feedback"] or {}
            hub_info = val["deployment_hub"] or {}

            # 1. Định lượng quy mô thị trường & Căn cứ nguồn
            primary_source = "N/A"
            primary_timestamp = "N/A"
            retail_stores = None
            growth_rate = None
            market_size = None

            if valid_docs:
                latest_doc = valid_docs[0]
                primary_source = latest_doc.get("source", "N/A")
                primary_timestamp = latest_doc.get("timestamp", "N/A")
                retail_stores = latest_doc.get("retail_stores_count")
                growth_rate = latest_doc.get("annual_growth_rate_pct")
                market_size = latest_doc.get("market_size_vnd_bil")

            # 2. Đánh giá Nhu cầu & Product-Market Fit (PMF)
            demanded = customer_fb.get("demanded_features", [])
            sample_size = customer_fb.get("sample_size", 0)

            if sample_size == 0 or not demanded:
                pmf_score = 0.0
                matched_features = []
                unmatched_features = []
                critical_gaps = []
                pmf_verdict = "KHUYẾT DỮ LIỆU: Chưa có mẫu khảo sát khách hàng hợp lệ để đánh giá độ khớp giải pháp."
            else:
                matched_features = [f for f in demanded if f in supported_features]
                unmatched_features = [f for f in demanded if f not in supported_features]
                critical_gaps = [f for f in unmatched_features if f in unsupported_features]

                fit_ratio = len(matched_features) / len(demanded)
                pmf_score = round(fit_ratio * 10.0, 1)

                if critical_gaps:
                    pmf_verdict = f"CẢNH BÁO LỆCH SẢN PHẨM: Khách hàng đòi hỏi tính năng Hưng Phát CHƯA HỖ TRỢ ({', '.join(critical_gaps)})."
                    pmf_score = max(0.0, round(pmf_score * 0.6, 1))
                else:
                    pmf_verdict = f"KHỚP CAO: Giải pháp hiện có đáp ứng 100% bài toán cốt lõi ({len(matched_features)}/{len(demanded)} tính năng)."

            # 3. Đánh giá Môi trường Cạnh tranh
            competitors = comp_profile.get("competitors", [])
            if not competitors:
                comp_score = 5.0
                comp_verdict = "KHUYẾT DỮ LIỆU: Chưa có hồ sơ đối thủ (Ước lượng trung tính)."
            else:
                max_share = max((c.get("market_share_pct", 0) for c in competitors), default=0)
                if max_share >= 60.0:
                    comp_score = 3.0
                    comp_verdict = f"ĐỘC QUYỀN CAO: Đối thủ lớn nắm {max_share}% thị phần; chi phí thâm nhập và lôi kéo khách cực lớn."
                elif max_share >= 35.0:
                    comp_score = 6.5
                    comp_verdict = f"CẠNH TRANH TRUNG BÌNH: Có đối thủ chi phối ({max_share}% thị phần) nhưng còn nhiều phân khúc trống."
                else:
                    comp_score = 9.0
                    comp_verdict = "DƯ ĐỊA RẤT LỚN: Thị trường phân mảnh, đối thủ địa phương yếu hoặc chỉ phục vụ cửa hàng đơn lẻ."

            # 4. Đánh giá Yêu cầu Hỗ trợ tại chỗ vs Năng lực Triển khai
            onsite_demand = customer_fb.get("onsite_support_demanded") or "Không có thông tin"
            strictness = customer_fb.get("onsite_support_strictness")
            hub_status = hub_info.get("hub_status", "Chưa có trạm")
            response_time = hub_info.get("onsite_response_time_hours", 999)

            location_insights[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "market_size_vnd_bil": market_size,
                "retail_stores_count": retail_stores,
                "annual_growth_rate_pct": growth_rate,
                "source": primary_source,
                "timestamp": primary_timestamp,
                "pmf_score": pmf_score,
                "matched_features": matched_features,
                "unmatched_features": unmatched_features,
                "critical_gaps": critical_gaps,
                "pmf_verdict": pmf_verdict,
                "comp_score": comp_score,
                "comp_verdict": comp_verdict,
                "onsite_demand": onsite_demand,
                "strictness": strictness,
                "hub_status": hub_status,
                "response_time_hours": response_time,
                "max_onsite_sla": hub_info.get("max_onsite_sla", "N/A")
            }

        report_md = self._generate_market_report(location_insights)

        return {
            "location_insights": location_insights,
            "market_analysis_report_md": report_md
        }

    def _generate_market_report(self, insights: Dict[str, Any]) -> str:
        md = []
        md.append("# 📈 BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG & ĐỐI THỦ (MARKET ANALYSIS REPORT)")
        md.append(f"**Thời điểm thực thi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("\n---\n")

        for loc_id, ins in insights.items():
            md.append(f"## 📍 {ins['location_name']} ({loc_id})")
            md.append(f"- **Quy mô định lượng:** Số chuỗi: `{ins['retail_stores_count'] or 'Khuyết'}` | Tăng trưởng: `{ins['annual_growth_rate_pct']}%/năm` | Doanh số: `{ins['market_size_vnd_bil']} tỷ VND`")
            md.append(f"- **Căn cứ nguồn & thời điểm:** *{ins['source']}* (Kỳ thống kê: *{ins['timestamp']}*)")
            md.append(f"- **Mức độ khớp sản phẩm (PMF Score: {ins['pmf_score']}/10):** {ins['pmf_verdict']}")
            if ins['matched_features']:
                md.append(f"  + *Tính năng đáp ứng:* {', '.join(ins['matched_features'])}")
            if ins['critical_gaps']:
                md.append(f"  + *Tính năng thiếu hụt (Gaps):* {', '.join(ins['critical_gaps'])}")
            md.append(f"- **Môi trường cạnh tranh ({ins['comp_score']}/10):** {ins['comp_verdict']}")
            md.append(f"- **Hạ tầng & Yêu cầu hỗ trợ tại chỗ:**")
            md.append(f"  + Hiện trạng Hub Hưng Phát: `{ins['hub_status']}` (Thời gian tiếp cận: {ins['response_time_hours']}h)")
            md.append(f"  + Yêu cầu từ khách hàng: *\"{ins['onsite_demand']}\"*")
            md.append("\n" + "-"*50 + "\n")

        return "\n".join(md)
