"""
HUNG PHAT MASTER AGENT - CLI ENTRYPOINT
Sử dụng tại buổi thi hoặc chạy thực tế với file dữ liệu bất kỳ:
Cách dùng:
    python run_agent.py [đường_dẫn_file_json] [--output_dir thư_mục_xuất]

Ví dụ:
    python run_agent.py data/dataset_normal.json
    python run_agent.py data/dataset_boundary.json
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.agent_coordinator import HungPhatMasterAgent

def main():
    parser = argparse.ArgumentParser(description="HUNG PHAT MASTER AGENT - Hệ thống Hỗ trợ Quyết định Mở rộng Địa bàn WMS")
    parser.add_argument("data_path", nargs="?", default="data/dataset_normal.json", help="Đường dẫn đến file JSON gói dữ liệu dự án")
    parser.add_argument("--output_dir", default="outputs", help="Thư mục xuất 6 đầu ra bắt buộc")
    parser.add_argument("--tag", default="exam", help="Thẻ định danh lần chạy")

    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        print(f"❌ Lỗi: Không tìm thấy file dữ liệu tại '{args.data_path}'")
        sys.exit(1)

    print("\n" + "="*80)
    print("🤖 HUNG PHAT MASTER AGENT - SYSTEM EXECUTION (AI301)")
    print(f"📂 Nạp gói dữ liệu dự án: {args.data_path}")
    print("="*80)

    agent = HungPhatMasterAgent(session_name=f"RUN_{args.tag.upper()}")
    result = agent.run_pipeline(
        raw_data_or_path=args.data_path,
        output_dir=args.output_dir,
        run_tag=args.tag
    )

    print(f"\n📊 TRẠNG THÁI CUỐI: {result['final_status']}")
    print(f"🩺 Điểm sức khỏe dữ liệu (Data Health Score): {result['data_health_score']}%")
    
    if result["final_status"] == "NEED_MORE_DATA":
        print(f"⚠️  CẢNH BÁO: CHƯA ĐỦ CĂN CỨ ĐỂ CHỌN 2 ĐỊA BÀN!")
        print(f"👉 Thông tin cần bổ sung: {result['action_required']}")
    else:
        print(f"🎯 2 ĐỊA BÀN ĐƯỢC ĐỀ XUẤT: {result['top_2_recommendations']}")
        print(f"⚠️  CÁC ĐỊA BÀN CHƯA ƯU TIÊN / BỊ LOẠI TRỪ: {result['unprioritized_locations']}")

    print("\n📁 6 ĐẦU RA BẮT BUỘC ĐÃ ĐƯỢC TẠO LẬP:")
    for key, path in result["output_files"].items():
        print(f"  + [{key.upper()}]: {path}")

    print("="*80 + "\n")

if __name__ == "__main__":
    main()
