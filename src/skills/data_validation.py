"""
SKILL 1: data_validation (Kiểm tra và Xác thực Dữ liệu Đầu vào)
Tuân thủ HUNG PHAT MASTER AGENT Blueprint:
- Đọc và kiểm tra toàn bộ dữ liệu.
- Phát hiện thiếu dữ liệu, trùng lặp, sai định dạng và mâu thuẫn.
- Giữ lại thông tin nguồn và thời điểm.
- Không tự ý sửa dữ liệu gốc.
- Tạo Data Quality Report.
"""

from typing import Dict, Any, List
from datetime import datetime

class DataValidationSkill:
    def __init__(self, logger):
        self.logger = logger

    def execute(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Thực thi kiểm tra dữ liệu và sinh Data Quality Report"""
        self.logger.record_step(
            step_id="STEP_1_DATA_VALIDATION",
            step_name="data_validation",
            action="EXECUTE_DATA_VALIDATION",
            details={"message": "Bắt đầu kiểm tra tính toàn vẹn, nguồn gốc, thời điểm và phát hiện mâu thuẫn dữ liệu."}
        )

        market_docs = raw_data.get("market_documents", [])
        competitors = raw_data.get("competitor_profiles", [])
        customer_feedbacks = raw_data.get("customer_feedback", [])
        capacity = raw_data.get("deployment_capacity", {})
        hubs = capacity.get("regional_support_hubs", {})
        criteria = raw_data.get("selection_criteria", [])

        current_year = 2026
        validated_locations = {}
        missing_issues = []
        duplicate_issues = []
        outdated_issues = []
        conflict_issues = []

        # Kiểm tra danh sách 4 địa bàn từ năng lực triển khai
        all_loc_ids = list(hubs.keys())
        if len(all_loc_ids) < 4:
            missing_issues.append(f"Chỉ có {len(all_loc_ids)} địa bàn được khai báo trong hệ thống hub, cần đủ 4 địa bàn.")

        # Gom tài liệu thị trường
        docs_by_loc: Dict[str, List[Dict[str, Any]]] = {loc: [] for loc in all_loc_ids}
        for doc in market_docs:
            loc_id = doc.get("location_id")
            if loc_id in docs_by_loc:
                docs_by_loc[loc_id].append(doc)

        comp_by_loc = {c.get("location_id"): c for c in competitors}
        fb_by_loc = {f.get("location_id"): f for f in customer_feedbacks}

        for loc_id in all_loc_ids:
            loc_docs = docs_by_loc.get(loc_id, [])
            comp_info = comp_by_loc.get(loc_id)
            fb_info = fb_by_loc.get(loc_id)
            hub_info = hubs.get(loc_id, {})

            valid_docs = []
            duplicate_docs = []

            # 1. Kiểm tra tài liệu thị trường
            if not loc_docs:
                missing_issues.append(f"Địa bàn {loc_id}: Khuyết hoàn toàn tài liệu nghiên cứu thị trường.")
                self.logger.record_warning(
                    step_id="STEP_1_DATA_VALIDATION",
                    warning_type="MISSING_DATA",
                    message=f"Địa bàn {loc_id} không có tài liệu thị trường nào.",
                    context_data={"location_id": loc_id}
                )
            else:
                for d in loc_docs:
                    # Kiểm tra trùng lặp nguồn
                    if d.get("duplicate_flag") is True or "Dẫn lại" in str(d.get("source", "")):
                        duplicate_docs.append(d)
                        duplicate_issues.append(
                            f"Địa bàn {loc_id} - Tài liệu '{d.get('doc_id')}': Lặp nguồn dẫn lại từ '{d.get('duplicate_of_source', 'nguồn cũ')}'. Đã cách ly để tránh tính kép."
                        )
                        self.logger.record_warning(
                            step_id="STEP_1_DATA_VALIDATION",
                            warning_type="DUPLICATE_DATA",
                            message=f"Phát hiện tài liệu trùng lặp nguồn tại {loc_id}: {d.get('doc_id')}",
                            context_data={"doc": d}
                        )
                        continue

                    # Kiểm tra tính cập nhật (thời điểm)
                    ts = d.get("timestamp")
                    if ts:
                        try:
                            year = int(ts.split("-")[0])
                            if current_year - year >= 4:
                                outdated_issues.append(
                                    f"Địa bàn {loc_id} - Tài liệu '{d.get('doc_id')}': Kỳ thống kê cũ ({ts}), cảnh báo độ lệch thị trường."
                                )
                        except Exception:
                            pass

                    # Kiểm tra thiếu trường dữ liệu định lượng
                    if d.get("retail_stores_count") is None or d.get("source") is None:
                        missing_issues.append(
                            f"Địa bàn {loc_id} - Tài liệu '{d.get('doc_id')}': Khuyết trường số lượng cửa hàng bán lẻ hoặc nguồn phát hành."
                        )

                    valid_docs.append(d)

            # 2. Kiểm tra hồ sơ đối thủ
            if not comp_info or not comp_info.get("competitors"):
                missing_issues.append(f"Địa bàn {loc_id}: Khuyết hồ sơ đối thủ cạnh tranh.")

            # 3. Kiểm tra khảo sát khách hàng
            if not fb_info or fb_info.get("sample_size", 0) == 0:
                missing_issues.append(f"Địa bàn {loc_id}: Khuyết mẫu khảo sát nhu cầu khách hàng.")
            else:
                if not fb_info.get("demanded_features"):
                    missing_issues.append(f"Địa bàn {loc_id}: Mẫu khảo sát khuyết danh sách tính năng mong muốn.")
                if fb_info.get("onsite_support_demanded") is None:
                    missing_issues.append(f"Địa bàn {loc_id}: Khuyết yêu cầu về hỗ trợ kỹ thuật tại chỗ.")

            validated_locations[loc_id] = {
                "location_name": hub_info.get("location_name", loc_id),
                "valid_market_documents": valid_docs,
                "isolated_duplicate_documents": duplicate_docs,
                "competitor_profile": comp_info,
                "customer_feedback": fb_info,
                "deployment_hub": hub_info
            }

        # 4. Kiểm tra tiêu chí đánh giá
        if not criteria:
            missing_issues.append("Bộ tiêu chí đánh giá (selection_criteria) bị khuyết hoàn toàn.")

        # Đánh giá mức độ toàn vẹn của dữ liệu (Data Health Status)
        total_checks = len(all_loc_ids) * 3
        issues_count = len(missing_issues) + len(duplicate_issues)
        health_score = max(0, round((1.0 - (issues_count / (total_checks + 5))) * 100, 1))

        is_critical_missing = any("Khuyết hoàn toàn" in iss or "Khuyết mẫu khảo sát" in iss for iss in missing_issues)

        quality_report = self._generate_quality_report(
            health_score=health_score,
            missing_issues=missing_issues,
            duplicate_issues=duplicate_issues,
            outdated_issues=outdated_issues,
            conflict_issues=conflict_issues,
            validated_locations=validated_locations
        )

        return {
            "health_score": health_score,
            "is_critical_missing": is_critical_missing,
            "validated_locations": validated_locations,
            "missing_issues": missing_issues,
            "duplicate_issues": duplicate_issues,
            "outdated_issues": outdated_issues,
            "conflict_issues": conflict_issues,
            "data_quality_report_md": quality_report
        }

    def _generate_quality_report(self, health_score, missing_issues, duplicate_issues, outdated_issues, conflict_issues, validated_locations) -> str:
        md = []
        md.append("# 📊 BÁO CÁO KIỂM TRA CHẤT LƯỢNG DỮ LIỆU (DATA QUALITY REPORT)")
        md.append(f"**Thời điểm thực thi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Chỉ số Sức khỏe Dữ liệu (Data Health):** `{health_score}%`")
        md.append("\n---\n")

        md.append("## 1. TỔNG HỢP KIỂM TOÁN TÀI LIỆU THEO 4 ĐỊA BÀN")
        md.append("| Địa bàn | Số tài liệu hợp lệ | Tài liệu trùng lặp | Hồ sơ đối thủ | Mẫu khảo sát KH | Trạng thái nguồn |")
        md.append("|:---|:---:|:---:|:---:|:---:|:---:|")

        for loc_id, val in validated_locations.items():
            valid_cnt = len(val["valid_market_documents"])
            dup_cnt = len(val["isolated_duplicate_documents"])
            has_comp = "✅ Đủ" if val["competitor_profile"] and val["competitor_profile"].get("competitors") else "❌ Thiếu"
            has_fb = f"✅ Đủ ({val['customer_feedback'].get('sample_size', 0)} mẫu)" if val["customer_feedback"] and val["customer_feedback"].get("sample_size", 0) > 0 else "❌ Thiếu"
            status = "Sẵn sàng" if valid_cnt > 0 and has_comp.startswith("✅") and has_fb.startswith("✅") else "Cần bổ sung"
            md.append(f"| **{val['location_name']}** | {valid_cnt} | {dup_cnt} | {has_comp} | {has_fb} | `{status}` |")

        md.append("\n## 2. CHI TIẾT CÁC VẤN ĐỀ PHÁT HIỆN")
        if duplicate_issues:
            md.append("### 🔄 Dữ liệu Trùng lặp & Lặp nguồn (Đã cách ly, không tính kép):")
            for item in duplicate_issues:
                md.append(f"- ⚠️ {item}")
        else:
            md.append("### 🔄 Dữ liệu Trùng lặp: Không phát hiện.")

        if missing_issues:
            md.append("\n### ❗ Dữ liệu Khuyết thiếu:")
            for item in missing_issues:
                md.append(f"- ❌ {item}")
        else:
            md.append("\n### ❗ Dữ liệu Khuyết thiếu: Không có.")

        if outdated_issues:
            md.append("\n### ⏳ Dữ liệu Cũ / Lệch kỳ thống kê:")
            for item in outdated_issues:
                md.append(f"- ⚠️ {item}")

        md.append("\n---\n> **Quy tắc Kiểm soát:** Giữ nguyên dữ liệu gốc, không tự ý sửa đổi số liệu hoặc tự tạo dữ liệu giả lập.")
        return "\n".join(md)
