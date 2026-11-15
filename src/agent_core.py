"""
Hệ thống AI Agent hỗ trợ Quyết định Mở rộng Địa bàn - Hưng Phát Smart Warehouse Solutions
Mô-đun Lõi: Quản lý Ngữ cảnh, Bộ điều phối Pipeline và Nhật ký Truy vết (Audit Trace)
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List

class AuditLogger:
    """
    Ghi nhật ký thực thi (Execution Trace) để đảm bảo tính minh bạch, 
    khả năng kiểm tra lại và giải trình từng bước quyết định của Agent.
    """
    def __init__(self, log_name: str = "agent_trace"):
        self.log_name = log_name
        self.logs: List[Dict[str, Any]] = []
        self.created_at = datetime.now().isoformat()

    def record_step(self, step_id: str, step_name: str, action: str, details: Dict[str, Any]):
        """Ghi nhận một bước thực thi"""
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "step_id": step_id,
            "step_name": step_name,
            "action": action,
            "details": details
        }
        self.logs.append(entry)

    def record_warning(self, step_id: str, warning_type: str, message: str, context_data: Any = None):
        """Ghi nhận cảnh báo dữ liệu mâu thuẫn, thiếu hoặc vi phạm quy tắc"""
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "step_id": step_id,
            "step_name": "WARNING_TRIGGERED",
            "action": warning_type,
            "details": {
                "message": message,
                "context": context_data
            }
        }
        self.logs.append(entry)

    def export_json(self, output_path: str):
        """Xuất nhật ký truy vết ra file JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "trace_session": self.log_name,
                "created_at": self.created_at,
                "total_events": len(self.logs),
                "events": self.logs
            }, f, ensure_ascii=False, indent=2)

    def get_summary_text(self) -> str:
        """Tóm tắt ngắn gọn nhật ký thực thi"""
        lines = [f"=== AUDIT TRACE LOG: {self.log_name} ==="]
        for log in self.logs:
            lines.append(f"[{log['timestamp']}] [{log['step_id']}] {log['action']}: {log['details'].get('message', '')}")
        return "\n".join(lines)


class AgentContext:
    """
    Lưu trữ trạng thái làm việc xuyên suốt quy trình của AI Agent
    """
    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self.sanitized_data: Dict[str, Any] = {}
        self.market_insights: Dict[str, Any] = {}
        self.evaluation_results: Dict[str, Any] = {}
        self.recommended_locations: List[Dict[str, Any]] = []
        self.rejected_locations: List[Dict[str, Any]] = []
        self.survey_plan: Dict[str, Any] = {}
        self.data_warnings: List[Dict[str, Any]] = []
        self.execution_status: str = "INITIALIZED"
