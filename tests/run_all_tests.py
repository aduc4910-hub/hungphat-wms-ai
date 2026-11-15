"""
Bộ Kiểm thử Tự động cho HUNG PHAT MASTER AGENT
Kiểm tra 3 kịch bản theo đúng System Instructions & Agent Blueprint:
1. Normal Case: Đầy đủ dữ liệu -> Status: APPROVED_BY_MANAGER, sinh đủ 6 file đầu ra, Top 2 = LOC_A, LOC_B.
2. Missing Case: Khuyết dữ liệu trọng yếu -> Status: NEED_MORE_DATA, cảnh báo và liệt kê thông tin cần bổ sung.
3. Boundary Case: Dung lượng cực đại nhưng vi phạm SLA -> Loại trừ LOC_MEGA, bảo vệ cam kết SLA.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent_coordinator import HungPhatMasterAgent

def test_normal_case():
    print("\n" + "="*70)
    print("▶ CHẠY KIỂM THỬ KỊCH BẢN 1: DỮ LIỆU CHUẨN (NORMAL CASE)")
    print("="*70)
    agent = HungPhatMasterAgent(session_name="TEST_NORMAL_CASE")
    res = agent.run_pipeline("data/dataset_normal.json", output_dir="outputs", run_tag="normal")

    print(f"Trạng thái thực thi: {res['final_status']}")
    print(f"Top 2 đề xuất: {res['top_2_recommendations']}")
    print(f"6 Đầu ra bắt buộc:")
    for name, path in res["output_files"].items():
        assert os.path.exists(path), f"Thiếu file đầu ra bắt buộc: {path}"
        print(f"  + {name}: {path}")

    assert res["final_status"] == "APPROVED_BY_MANAGER", "Lỗi: Đáng lẽ phải được phê duyệt!"
    assert res["top_2_recommendations"] == ["LOC_A", "LOC_B"], "Lỗi: Top 2 phải là LOC_A và LOC_B!"
    print("  => KẾT QUẢ: ĐẠT CHUẨN (PASS) ✅")
    return res

def test_missing_data_case():
    print("\n" + "="*70)
    print("▶ CHẠY KIỂM THỬ KỊCH BẢN 2: THIẾU DỮ LIỆU CỐT LÕI (MISSING CASE)")
    print("="*70)
    agent = HungPhatMasterAgent(session_name="TEST_MISSING_CASE")
    res = agent.run_pipeline("data/dataset_missing.json", output_dir="outputs", run_tag="missing")

    print(f"Trạng thái thực thi: {res['final_status']}")
    print(f"Yêu cầu bổ sung dữ liệu: {res['action_required']}")

    # Tuân thủ Final Behavior của Blueprint: trả về trạng thái NEED_MORE_DATA
    assert res["final_status"] == "NEED_MORE_DATA", f"Lỗi: Thiếu dữ liệu cốt lõi phải trả về NEED_MORE_DATA, nhưng nhận được {res['final_status']}"
    assert len(res["top_2_recommendations"]) == 0, "Lỗi: Khi ở trạng thái NEED_MORE_DATA không được chốt Top 2!"
    print("  => KẾT QUẢ: ĐẠT CHUẨN (PASS) ✅ (Đã kích hoạt đúng trạng thái NEED_MORE_DATA)")
    return res

def test_boundary_edge_case():
    print("\n" + "="*70)
    print("▶ CHẠY KIỂM THỬ KỊCH BẢN 3: RANH GIỚI QUY TẮC & VƯỢT NĂNG LỰC SLA (BOUNDARY CASE)")
    print("="*70)
    agent = HungPhatMasterAgent(session_name="TEST_BOUNDARY_CASE")
    res = agent.run_pipeline("data/dataset_boundary.json", output_dir="outputs", run_tag="boundary")

    print(f"Trạng thái thực thi: {res['final_status']}")
    print(f"Top 2 đề xuất: {res['top_2_recommendations']}")
    print(f"Địa bàn bị loại trừ: {res['unprioritized_locations']}")

    assert "LOC_MEGA" not in res["top_2_recommendations"], "Lỗi nghiêm trọng: LOC_MEGA vi phạm SLA nhưng vẫn lọt vào Top 2!"
    assert "LOC_MEGA" in res["unprioritized_locations"], "Lỗi: LOC_MEGA phải nằm trong danh sách bị loại trừ!"
    print("  => KẾT QUẢ: ĐẠT CHUẨN (PASS) ✅ (Đã kích hoạt Hard Constraint loại trừ LOC_MEGA)")
    return res

if __name__ == "__main__":
    test_normal_case()
    test_missing_data_case()
    test_boundary_edge_case()
    print("\n" + "#"*70)
    print("🏆 TOÀN BỘ 3 KIỂM THỬ THEO BLUEPRINT ĐÃ CHẠY THÀNH CÔNG 100%!")
    print("#"*70)
