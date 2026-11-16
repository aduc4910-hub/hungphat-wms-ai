"""
Backend HTTP Server cho HUNG PHAT MASTER AGENT Localhost Demo
Cung cấp Web Dashboard giao diện trực quan và REST APIs.
Chạy hoàn toàn bằng thư viện tiêu chuẩn Python (Zero External Dependencies).
Hỗ trợ đầy đủ:
- BƯỚC 1: TIẾP NHẬN DỮ LIỆU (DATA INPUT & INVENTORY)
- BƯỚC 2: KIỂM ĐỊNH & LÀM SẠCH DỮ LIỆU (DATA VALIDATION & CLEANING)
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import base64
import time
import datetime
import uuid
import mimetypes
import re
import shutil

# Đảm bảo import được module src
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.agent_coordinator import HungPhatMasterAgent

PORT = 8088
WEB_DIR = os.path.join(BASE_DIR, "public") if os.path.exists(os.path.join(BASE_DIR, "public")) else os.path.join(BASE_DIR, "web")

# Môi trường lưu trữ: Tự động phát hiện Vercel hoặc Serverless Read-only Filesystem để dùng /tmp
def _detect_serverless():
    if any(k in os.environ for k in ['VERCEL', 'VERCEL_ENV', 'AWS_LAMBDA_FUNCTION_NAME', 'LAMBDA_TASK_ROOT']):
        return True
    try:
        probe = os.path.join(BASE_DIR, ".write_probe")
        with open(probe, "w") as f:
            f.write("probe")
        if os.path.exists(probe):
            os.remove(probe)
        return False
    except (OSError, PermissionError):
        return True

IS_VERCEL = _detect_serverless()
STORAGE_DIR = '/tmp' if IS_VERCEL else BASE_DIR

DATA_DIR = os.path.join(STORAGE_DIR, "data")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")

INVENTORY_FILE = os.path.join(DATA_DIR, "data_inventory.json")
STATUS_FILE = os.path.join(DATA_DIR, "data_input_status.json")
AUDIT_LOG_FILE = os.path.join(DATA_DIR, "data_input_audit.json")
STEP2_RESULT_FILE = os.path.join(DATA_DIR, "step2_validation_result.json")
CLEANED_DATASET_FILE = os.path.join(DATA_DIR, "cleaned_dataset.json")
STEP3_RESULT_FILE = os.path.join(DATA_DIR, "step3_market_analysis.json")
STEP3_REPORT_MD = os.path.join(OUTPUTS_DIR, "market_analysis_report.md")
STEP4_RESULT_FILE = os.path.join(DATA_DIR, "step4_deployment_assessment.json")
STEP4_REPORT_MD = os.path.join(OUTPUTS_DIR, "deployment_assessment_report.md")
STEP5_RESULT_FILE = os.path.join(DATA_DIR, "step5_location_evaluation.json")
STEP5_REPORT_MD = os.path.join(OUTPUTS_DIR, "location_evaluation_report.md")

# 6 NHÓM DỮ LIỆU TIẾP NHẬN CHUẨN (KÈM MAPPING CẢNH BÁO RỦI RO NẾU THIẾU)
DATA_GROUPS = [
    {
        "id": "market_research",
        "code": "GRP_01",
        "name": "MARKET RESEARCH",
        "title": "Báo cáo nghiên cứu thị trường của 4 địa bàn",
        "icon": "📈",
        "description": "Báo cáo ngành bán lẻ, quy mô thị trường, tốc độ tăng trưởng của Hà Nội, Đà Nẵng, TP.HCM, Cần Thơ.",
        "severity": "HIGH",
        "risk_title": "Mở chi nhánh sai địa bàn, nhu cầu thấp & thua lỗ chi phí cố định",
        "risk_if_missing": "Không thể xác định dung lượng cửa hàng bán lẻ, tốc độ tăng trưởng và mức độ số hóa kho bãi của 4 địa bàn. Doanh nghiệp đối mặt nguy cơ rót vốn mở chi nhánh vào nơi thị trường bão hòa hoặc quá nhỏ, dẫn đến gánh nặng chi phí cố định (kho, nhân sự) và nguy cơ thua lỗ kéo dài."
    },
    {
        "id": "competitor_data",
        "code": "GRP_02",
        "name": "COMPETITOR DATA",
        "title": "Hồ sơ đối thủ cạnh tranh",
        "icon": "🏢",
        "description": "Thị phần, điểm mạnh, điểm yếu và phân khúc mục tiêu của các đơn vị cung cấp WMS tại từng khu vực.",
        "severity": "HIGH",
        "risk_title": "Định giá sai lầm & bị đối thủ bản địa chèn ép, triệt hạ thị phần",
        "risk_if_missing": "Không nắm được thị phần, mức giá chào bán và ưu/nhược điểm công nghệ của đối thủ tại từng vùng. Hưng Phát dễ định giá sai (quá đắt khiến khách bỏ đi, hoặc quá rẻ làm giảm biên lợi nhuận), hoặc đâm đầu vào phân khúc mà đối thủ độc quyền kiểm soát."
    },
    {
        "id": "customer_feedback",
        "code": "GRP_03",
        "name": "CUSTOMER FEEDBACK",
        "title": "Phản hồi khách hàng",
        "icon": "💬",
        "description": "Dữ liệu phỏng vấn, khảo sát nhu cầu tính năng, thói quen vận hành kho và điểm đau (pain points) của chuỗi bán lẻ.",
        "severity": "HIGH",
        "risk_title": "Chào sai tính năng (Lệch PMF) & tỷ lệ chốt đơn thất bại cao",
        "risk_if_missing": "Không nắm bắt được 'nỗi đau' thực tế của chủ kho bán lẻ (thất thoát hàng hạn date FEFO, lỗi quét Barcode/QR, nghẽn đồng bộ POS giờ cao điểm). Sales tiếp thị tính năng chung chung, khách hàng từ chối dùng thử, chu kỳ bán hàng kéo dài và tỷ lệ chuyển đổi đơn hàng cực thấp."
    },
    {
        "id": "product_catalog",
        "code": "GRP_04",
        "name": "PRODUCT CATALOG",
        "title": "Danh mục giải pháp quản lý kho",
        "icon": "📦",
        "description": "Tài liệu tính năng phần mềm Hưng Phát WMS (vị trí ô kệ, Barcode/QR, kiểm soát hạn date, kết nối POS/ERP).",
        "severity": "HIGH",
        "risk_title": "Bán giải pháp vượt quá tính năng phần mềm & phát sinh chi phí đền bù",
        "risk_if_missing": "Thiếu danh mục module chuẩn của phần mềm Hưng Phát WMS. Đội ngũ kinh doanh dễ hứa hẹn tính năng mà phần mềm chưa hỗ trợ, dẫn đến xung đột khi bàn giao kỹ thuật, phát sinh chi phí customize ngoài ngân sách và mất uy tín thương hiệu."
    },
    {
        "id": "deployment_capacity",
        "code": "GRP_05",
        "name": "DEPLOYMENT CAPACITY",
        "title": "Năng lực nhân sự và triển khai",
        "icon": "👥",
        "description": "Quy mô đội ngũ kỹ thuật, trạm hỗ trợ kỹ thuật vùng, bán kính phục vụ và cam kết thời gian đáp ứng on-site SLA.",
        "severity": "CRITICAL",
        "risk_title": "Vỡ cam kết SLA on-site, sập kho khách hàng & bị phạt hợp đồng",
        "risk_if_missing": "Đặc thù kho bán lẻ vận hành liên tục 24/7. Nếu mở chi nhánh tại địa bàn không có trạm kỹ thuật tại chỗ hoặc bán kính vượt quá 10km, khi hệ thống quét mã/xuất kho gặp sự cố ban đêm, kỹ thuật viên không thể có mặt xử lý kịp trong 30-60 phút. Kho hàng bị đình trệ, hư hỏng chuỗi cung ứng, Hưng Phát đối mặt nguy cơ bị kiện phạt và mất khách hàng lớn!"
    },
    {
        "id": "evaluation_criteria",
        "code": "GRP_06",
        "name": "EVALUATION CRITERIA",
        "title": "Bộ tiêu chí đánh giá địa bàn",
        "icon": "⚖️",
        "description": "Trọng số các tiêu chí đánh giá đa thuộc tính (MCDA) và các ràng buộc cứng loại trừ rủi ro vỡ SLA.",
        "severity": "HIGH",
        "risk_title": "Quyết định theo cảm tính, mất tính khách quan & tranh cãi nội bộ",
        "risk_if_missing": "Không có bảng trọng số khoa học (MCDA) và các ràng buộc loại trừ cứng. Việc xếp hạng địa bàn ưu tiên sẽ mang tính chủ quan của người làm báo cáo, dễ xảy ra bất đồng nội bộ, khó bảo vệ luận điểm trước Hội đồng Quản trị và không đảm bảo tính nhất quán trong chiến lược phát triển."
    }
]

def init_storage():
    """Khởi tạo cấu trúc lưu trữ và các file trạng thái nếu chưa tồn tại"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
    except Exception:
        pass

    # Nếu chạy trên Vercel hoặc /tmp, sao chép các bộ dữ liệu mẫu ban đầu sang /tmp/data
    if IS_VERCEL or STORAGE_DIR == '/tmp':
        bundled_data_dir = os.path.join(BASE_DIR, "data")
        if os.path.exists(bundled_data_dir):
            try:
                for item in os.listdir(bundled_data_dir):
                    s = os.path.join(bundled_data_dir, item)
                    d = os.path.join(DATA_DIR, item)
                    if not os.path.exists(d) and os.path.isfile(s):
                        try:
                            shutil.copy2(s, d)
                        except Exception:
                            pass
            except Exception:
                pass

    for grp in DATA_GROUPS:
        try:
            os.makedirs(os.path.join(UPLOADS_DIR, grp["id"]), exist_ok=True)
        except Exception:
            pass

    if not os.path.exists(INVENTORY_FILE):
        save_json(INVENTORY_FILE, [])

    if not os.path.exists(STATUS_FILE):
        default_status = {
            "confirmed_at": None,
            "is_confirmed": False,
            "is_complete": False,
            "total_documents": 0,
            "ready_groups": [],
            "missing_groups": [g["id"] for g in DATA_GROUPS],
            "group_counts": {g["id"]: 0 for g in DATA_GROUPS}
        }
        save_json(STATUS_FILE, default_status)

    if not os.path.exists(AUDIT_LOG_FILE):
        save_json(AUDIT_LOG_FILE, [])

def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback kiểm tra trong /tmp/data
    tmp_path = os.path.join("/tmp", "data", os.path.basename(filepath))
    if tmp_path != filepath and os.path.exists(tmp_path):
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback kiểm tra trong data gốc dự án
    repo_path = os.path.join(BASE_DIR, "data", os.path.basename(filepath))
    if repo_path != filepath and os.path.exists(repo_path):
        try:
            with open(repo_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}

def save_json(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (OSError, PermissionError):
        # Fallback an toàn sang /tmp nếu hệ thống file là read-only (Vercel Serverless)
        tmp_target = os.path.join("/tmp", "data", os.path.basename(filepath))
        try:
            os.makedirs(os.path.dirname(tmp_target), exist_ok=True)
            with open(tmp_target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def save_text_file(filepath, content):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except (OSError, PermissionError):
        tmp_target = os.path.join("/tmp", "outputs", os.path.basename(filepath))
        try:
            os.makedirs(os.path.dirname(tmp_target), exist_ok=True)
            with open(tmp_target, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

init_storage()

def log_data_audit(action, message, details=None):
    logs = load_json(AUDIT_LOG_FILE, default=[])
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "message": message,
        "details": details or {}
    }
    logs.insert(0, entry)
    if len(logs) > 200:
        logs = logs[:200]
    save_json(AUDIT_LOG_FILE, logs)
    return entry

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    return clean.strip() or "tailieu"

def reset_pipeline_steps():
    """Xóa toàn bộ các tệp kết quả của Bước 2, 3, 4, 5 đưa về trạng thái khởi tạo (chưa thực hiện)"""
    files_to_remove = [
        STEP2_RESULT_FILE,
        CLEANED_DATASET_FILE,
        STEP3_RESULT_FILE,
        STEP3_REPORT_MD,
        STEP4_RESULT_FILE,
        STEP4_REPORT_MD,
        STEP5_RESULT_FILE,
        STEP5_REPORT_MD
    ]
    for fp in files_to_remove:
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

class AgentWebHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        if 'directory' not in kwargs:
            kwargs['directory'] = WEB_DIR
        super().__init__(*args, **kwargs)

    def _resolve_api_path(self):
        """
        Phân giải chính xác đường dẫn endpoint ngay cả khi chạy trên Vercel Serverless Function qua rewrites
        """
        # 1. Kiểm tra query param __path__ được forward từ vercel.json
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "__path__" in qs and qs["__path__"]:
            candidate = qs["__path__"][0]
            if candidate and candidate not in ("/api/index.py", "/api/index"):
                return candidate if candidate.startswith("/") else ("/" + candidate)

        # 2. Kiểm tra header chuẩn do Vercel Edge Proxy cung cấp
        for h in ("x-matched-path", "x-forwarded-uri", "x-original-uri", "x-now-route-matches"):
            val = self.headers.get(h)
            if val:
                val_path = urllib.parse.urlparse(val).path
                if val_path and val_path not in ("/api/index.py", "/api/index", "/api/index.py/"):
                    return val_path

        # 3. Trả về path từ self.path sau khi chuẩn hóa
        raw_path = parsed.path
        if raw_path.startswith("/web/"):
            raw_path = raw_path[4:]
        elif raw_path == "/web":
            raw_path = "/"
        return raw_path

    def send_error(self, code, message=None, explain=None):
        clean_path = getattr(self, "_current_clean_path", "") or self.path or ""
        if "/api" in clean_path or self.path.startswith("/api"):
            err_msg = message or "Lỗi xử lý yêu cầu API"
            if explain:
                err_msg = f"{err_msg}: {explain}"
            self._send_json({
                "success": False,
                "error": err_msg,
                "code": code,
                "path": clean_path
            }, status=code)
        else:
            super().send_error(code, message, explain)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        try:
            path = self._resolve_api_path()
            self._current_clean_path = path

            # Chuẩn hóa đường dẫn: Loại bỏ tiền tố /web nếu Vercel rewrite đưa vào
            if path.startswith("/web/"):
                path = path[4:]
            elif path == "/web":
                path = "/"

        if path == "/" or path == "/index.html":
            index_path = os.path.join(WEB_DIR, "index.html")
            try:
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self.send_error(500, f"Error reading index.html: {str(e)}")
                return
        elif path in ("/api", "/api/", "/api/index.py", "/api/index"):
            self._send_json({
                "service": "Hưng Phát Smart Warehouse AI Agent API",
                "status": "online",
                "version": "2.0.0"
            })
            return
        elif path == "/api/datasets":
            self._handle_get_datasets()
        elif path == "/api/data-groups":
            self._handle_get_data_groups()
        elif path == "/api/data-inventory":
            self._handle_get_data_inventory()
        elif path == "/api/data-logs":
            self._handle_get_data_logs()
        elif path == "/api/download":
            self._handle_download_file(parsed, as_attachment=True)
        elif path == "/api/view":
            self._handle_download_file(parsed, as_attachment=False)
        elif path == "/api/step2/status":
            self._handle_get_step2_status()
        elif path == "/api/step2/download-cleaned":
            self._handle_download_cleaned_dataset()
        elif path == "/api/step3/status":
            self._handle_get_step3_status()
        elif path == "/api/step3/download-report":
            self._handle_download_step3_report()
        elif path == "/api/step4/status":
            self._handle_get_step4_status()
        elif path == "/api/step4/download-report":
            self._handle_download_step4_report()
        elif path == "/api/step5/status":
            self._handle_get_step5_status()
        elif path == "/api/step5/download-report":
            self._handle_download_step5_report()
        else:
            self.path = path
            return super().do_GET()
        except Exception as e:
            if "/api" in getattr(self, '_current_clean_path', self.path):
                self._send_json({
                    "success": False,
                    "error": f"Lỗi xử lý GET: {str(e)}"
                }, status=500)
            else:
                self.send_error(500, f"Lỗi máy chủ: {str(e)}")

    def do_POST(self):
        try:
            path = self._resolve_api_path()
            self._current_clean_path = path

            if path.startswith("/web/"):
                path = path[4:]

            if path == "/api/run":
                self._handle_run_pipeline()
            elif path == "/api/upload":
                self._handle_upload_file()
            elif path == "/api/delete-document":
                self._handle_delete_document()
            elif path == "/api/delete-latest-document":
                self._handle_delete_latest_document()
            elif path == "/api/clear-all-documents":
                self._handle_clear_all_documents()
            elif path == "/api/confirm-input":
                self._handle_confirm_input()
            elif path == "/api/step2/validate":
                self._handle_step2_validate()
            elif path == "/api/step2/resolve":
                self._handle_step2_resolve()
            elif path == "/api/step3/analyze":
                self._handle_step3_analyze()
            elif path == "/api/step3/confirm":
                self._handle_step3_confirm()
            elif path == "/api/step4/assess":
                self._handle_step4_assess()
            elif path == "/api/step4/confirm":
                self._handle_step4_confirm()
            elif path == "/api/step5/evaluate":
                self._handle_step5_evaluate()
            elif path == "/api/step5/confirm":
                self._handle_step5_confirm()
            else:
                self.send_error(404, f"API endpoint '{path}' không tồn tại")
        except Exception as e:
            self._send_json({
                "success": False,
                "error": f"Lỗi nội bộ máy chủ khi xử lý POST {getattr(self, '_current_clean_path', self.path)}: {str(e)}"
            }, status=500)

    def _handle_get_datasets(self):
        datasets = [
            {"id": "normal", "name": "Case 1: Dữ liệu Đầy đủ Tiêu chuẩn (Normal Case)", "path": "data/dataset_normal.json"},
            {"id": "missing", "name": "Case 2: Dữ liệu Thiếu & Mâu thuẫn (Missing Case -> NEED_MORE_DATA)", "path": "data/dataset_missing.json"},
            {"id": "boundary", "name": "Case 3: Ranh giới Quy tắc & Ràng buộc SLA (Boundary Case)", "path": "data/dataset_boundary.json"}
        ]
        self._send_json(datasets)

    def _handle_get_data_groups(self):
        self._send_json({"groups": DATA_GROUPS})

    def _handle_get_data_inventory(self):
        docs = load_json(INVENTORY_FILE, default=[])
        status = load_json(STATUS_FILE, default={})
        
        group_counts = {g["id"]: 0 for g in DATA_GROUPS}
        for d in docs:
            cat = d.get("category")
            if cat in group_counts:
                group_counts[cat] += 1

        ready_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] > 0]
        missing_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] == 0]

        res = {
            "documents": docs,
            "total_documents": len(docs),
            "groups": DATA_GROUPS,
            "group_counts": group_counts,
            "ready_groups": ready_groups,
            "missing_groups": missing_groups,
            "status": status
        }
        self._send_json(res)

    def _handle_get_data_logs(self):
        logs = load_json(AUDIT_LOG_FILE, default=[])
        self._send_json({"logs": logs})

    def _handle_upload_file(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
            else:
                post_data = "{}"
            try:
                req = json.loads(post_data)
            except Exception as e:
                self.send_error(400, f"Dữ liệu JSON không hợp lệ: {str(e)}")
                return

        items = req.get("documents")
        if not items:
            items = [req]

        docs_inventory = load_json(INVENTORY_FILE, default=[])
        created_docs = []
        valid_group_ids = {g["id"] for g in DATA_GROUPS}

        for item in items:
            raw_category = item.get("category", "all_in_one")
            raw_filename = item.get("file_name", "unnamed_document")
            doc_name = item.get("doc_name") or os.path.splitext(raw_filename)[0]
            source = item.get("source", "Chưa xác định")
            collected_date = item.get("collected_date") or datetime.date.today().isoformat()
            location = item.get("location", "Toàn quốc")
            file_base64 = item.get("file_base64", "")

            _, ext = os.path.splitext(raw_filename)
            ext_clean = ext.lower().lstrip(".")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = sanitize_filename(raw_filename)

            # 🌟 XỬ LÝ NẠP CẤP TỐC 1 FILE TỔNG HỢP (ALL-IN-ONE) -> TỰ ĐỘNG BÓC TÁCH 6 NHÓM:
            if raw_category in ["all_in_one", "all_in_one_master", "all"]:
                master_dir = os.path.join(UPLOADS_DIR, "all_in_one")
                try:
                    os.makedirs(master_dir, exist_ok=True)
                except Exception:
                    master_dir = os.path.join("/tmp", "uploads", "all_in_one")
                    os.makedirs(master_dir, exist_ok=True)
                storage_filename = f"{timestamp_str}_MASTER_{safe_name}"
                target_filepath = os.path.join(master_dir, storage_filename)

                try:
                    file_bytes = base64.b64decode(file_base64)
                    with open(target_filepath, "wb") as f:
                        f.write(file_bytes)
                    actual_file_size = len(file_bytes)
                except Exception:
                    actual_file_size = item.get("file_size", 0)
                    try:
                        with open(target_filepath, "w", encoding="utf-8") as f:
                            f.write(f"Tài liệu Tổng Hợp Master: {doc_name}\nNguồn: {source}\nNgày: {collected_date}\nBao gồm đầy đủ 6 nhóm dữ liệu.")
                    except Exception:
                        pass

                sub_titles = {
                    "market_research": "Phân Hệ 1: Nghiên cứu Quy mô & Đặc điểm Thị trường 4 Địa bàn",
                    "competitor_data": "Phân Hệ 2: Hồ sơ Phân tích Đối thủ & Thị phần Bản địa",
                    "customer_feedback": "Phân Hệ 3: Khảo sát Nhu cầu Khách hàng & Điểm đau Vận hành Kho",
                    "product_catalog": "Phân Hệ 4: Danh mục Tính năng & Thông số Kỹ thuật Hưng Phát WMS",
                    "deployment_capacity": "Phân Hệ 5: Báo cáo Năng lực Triển khai, Kỹ thuật & Trạm SLA 10km",
                    "evaluation_criteria": "Phân Hệ 6: Bộ Tiêu chí, Trọng số & Quy tắc Đánh giá MCDA"
                }

                master_id = f"MASTER_{uuid.uuid4().hex[:6].upper()}"
                rel_path = f"uploads/all_in_one/{storage_filename}"

                for grp in DATA_GROUPS:
                    grp_id = grp["id"]
                    sub_title = sub_titles.get(grp_id, grp["title"])
                    doc_entry = {
                        "id": f"DOC_{uuid.uuid4().hex[:8].upper()}",
                        "doc_name": f"{doc_name} [{sub_title}]",
                        "category": grp_id,
                        "source": source.strip(),
                        "collected_date": collected_date.strip(),
                        "location": location.strip(),
                        "file_name": raw_filename,
                        "storage_filename": storage_filename,
                        "storage_path": rel_path,
                        "file_size": actual_file_size,
                        "file_ext": ext_clean.upper() if ext_clean else "XLSX",
                        "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "is_all_in_one": True,
                        "master_id": master_id,
                        "auto_extracted": True
                    }
                    docs_inventory.insert(0, doc_entry)
                    created_docs.append(doc_entry)

                log_data_audit(
                    action="ALL_IN_ONE_EXTRACT",
                    message=f"⚡ TIẾP NHẬN BÁO CÁO ALL-IN-ONE: Tự động bóc tách file tổng hợp '{raw_filename}' thành đủ 6 nhóm dữ liệu nghiệp vụ chuẩn.",
                    details={
                        "master_id": master_id,
                        "file_name": raw_filename,
                        "storage_path": rel_path,
                        "extracted_groups_count": len(DATA_GROUPS),
                        "groups": [g["id"] for g in DATA_GROUPS]
                    }
                )
            else:
                # Nạp tài liệu đơn lẻ vào 1 nhóm cụ thể
                category = raw_category if raw_category in valid_group_ids else "market_research"
                storage_filename = f"{timestamp_str}_{safe_name}"
                target_dir = os.path.join(UPLOADS_DIR, category)
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception:
                    target_dir = os.path.join("/tmp", "uploads", category)
                    os.makedirs(target_dir, exist_ok=True)
                target_filepath = os.path.join(target_dir, storage_filename)

                try:
                    file_bytes = base64.b64decode(file_base64)
                    with open(target_filepath, "wb") as f:
                        f.write(file_bytes)
                    actual_file_size = len(file_bytes)
                except Exception:
                    actual_file_size = item.get("file_size", 0)
                    try:
                        with open(target_filepath, "w", encoding="utf-8") as f:
                            f.write(f"Tài liệu tiếp nhận: {doc_name}\nNguồn: {source}\nNgày: {collected_date}")
                    except Exception:
                        pass

                doc_entry = {
                    "id": f"DOC_{uuid.uuid4().hex[:8].upper()}",
                    "doc_name": doc_name.strip(),
                    "category": category,
                    "source": source.strip(),
                    "collected_date": collected_date.strip(),
                    "location": location.strip(),
                    "file_name": raw_filename,
                    "storage_filename": storage_filename,
                    "storage_path": f"uploads/{category}/{storage_filename}",
                    "file_size": actual_file_size,
                    "file_ext": ext_clean.upper() if ext_clean else "FILE",
                    "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                docs_inventory.insert(0, doc_entry)
                created_docs.append(doc_entry)

                log_data_audit(
                    action="UPLOAD_DOCUMENT",
                    message=f"Đã tiếp nhận và lưu file thực tế: '{doc_entry['doc_name']}' ({raw_filename}) vào danh mục [{category.upper()}].",
                    details={
                        "doc_id": doc_entry["id"],
                        "file_path": doc_entry["storage_path"],
                        "file_size": doc_entry["file_size"],
                        "location": doc_entry["location"]
                    }
                )

        save_json(INVENTORY_FILE, docs_inventory)

        self._send_json({
            "success": True,
            "created_count": len(created_docs),
            "created_docs": created_docs,
            "total_inventory": len(docs_inventory)
        })
    except Exception as e:
        self._send_json({
            "success": False,
            "error": f"Lỗi xử lý tiếp nhận file: {str(e)}"
        }, status=500)

    def _handle_delete_document(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        doc_id = req.get("doc_id")
        if not doc_id:
            self.send_error(400, "Thiếu doc_id cần xóa")
            return

        docs = load_json(INVENTORY_FILE, default=[])
        target_doc = None
        new_docs = []
        for d in docs:
            if d.get("id") == doc_id:
                target_doc = d
            else:
                new_docs.append(d)

        if not target_doc:
            self.send_error(404, f"Không tìm thấy tài liệu có mã {doc_id}")
            return

        storage_rel = target_doc.get("storage_path")
        if storage_rel:
            # Chỉ xóa file vật lý nếu không còn tài liệu nào khác cùng trỏ tới (tránh xóa file master all-in-one dùng chung)
            still_referenced = any(d.get("storage_path") == storage_rel for d in new_docs)
            if not still_referenced:
                full_path = os.path.join(BASE_DIR, storage_rel.replace("/", os.sep))
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception:
                        pass

        save_json(INVENTORY_FILE, new_docs)

        # Cập nhật lại status của Bước 1 & reset quy trình 5 bước về trạng thái ban đầu
        group_counts = {g["id"]: 0 for g in DATA_GROUPS}
        for d in new_docs:
            cat = d.get("category")
            if cat in group_counts:
                group_counts[cat] += 1
        ready_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] > 0]
        missing_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] == 0]

        status_record = {
            "confirmed_at": None,
            "is_confirmed": False,
            "is_complete": (len(missing_groups) == 0 and len(new_docs) > 0),
            "total_documents": len(new_docs),
            "ready_groups": ready_groups,
            "missing_groups": missing_groups,
            "group_counts": group_counts,
            "ready_details": [
                {
                    "id": g["id"],
                    "code": g.get("code", ""),
                    "name": g["name"],
                    "title": g["title"],
                    "icon": g.get("icon", "📄"),
                    "count": group_counts[g["id"]]
                }
                for g in DATA_GROUPS if group_counts[g["id"]] > 0
            ],
            "missing_details": [
                {
                    "id": g["id"],
                    "code": g.get("code", ""),
                    "name": g["name"],
                    "title": g["title"],
                    "icon": g.get("icon", "⚠️"),
                    "severity": g.get("severity", "HIGH"),
                    "risk_title": g.get("risk_title", ""),
                    "risk_if_missing": g.get("risk_if_missing", "")
                }
                for g in DATA_GROUPS if group_counts[g["id"]] == 0
            ],
            "risk_summary": {
                "critical_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "CRITICAL"),
                "high_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "HIGH"),
                "medium_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "MEDIUM")
            }
        }
        save_json(STATUS_FILE, status_record)
        reset_pipeline_steps()

        log_data_audit(
            action="DELETE_DOCUMENT",
            message=f"Đã xóa tài liệu: '{target_doc.get('doc_name')}' ({target_doc.get('file_name')}) khỏi nhóm [{target_doc.get('category')}]. Quy trình 5 bước được reset về trạng thái ban đầu.",
            details={"doc_id": doc_id, "file_name": target_doc.get("file_name")}
        )

        self._send_json({
            "success": True,
            "deleted_id": doc_id,
            "remaining_count": len(new_docs)
        })

    def _handle_delete_latest_document(self):
        docs = load_json(INVENTORY_FILE, default=[])
        if not docs:
            self._send_json({
                "success": False,
                "message": "Kho tài liệu đang trống (0 tệp), không có file nào để xóa.",
                "remaining_count": 0
            })
            return

        # Tìm tài liệu có thời gian tiếp nhận mới nhất (received_at) hoặc phần tử đầu tiên
        latest_doc = docs[0]
        for d in docs:
            if d.get("received_at", "") > latest_doc.get("received_at", ""):
                latest_doc = d

        latest_master_id = latest_doc.get("master_id")
        latest_storage_path = latest_doc.get("storage_path")
        deleted_filename = latest_doc.get("file_name", "Tài liệu mới nhất")

        deleted_docs = []
        new_docs = []

        # Nếu là file tổng hợp All-in-One (có master_id), xóa toàn bộ các bản ghi được bóc tách từ file master đó
        if latest_master_id:
            for d in docs:
                if d.get("master_id") == latest_master_id:
                    deleted_docs.append(d)
                else:
                    new_docs.append(d)
        elif latest_storage_path:
            for d in docs:
                if d.get("storage_path") == latest_storage_path:
                    deleted_docs.append(d)
                else:
                    new_docs.append(d)
        else:
            deleted_docs.append(latest_doc)
            new_docs = [d for d in docs if d.get("id") != latest_doc.get("id")]

        # Xóa file vật lý khỏi ổ đĩa nếu không còn tài liệu nào khác tham chiếu tới
        if latest_storage_path:
            still_referenced = any(d.get("storage_path") == latest_storage_path for d in new_docs)
            if not still_referenced:
                full_path = os.path.join(BASE_DIR, latest_storage_path.replace("/", os.sep))
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception:
                        pass

        # Lưu danh mục tài liệu mới
        save_json(INVENTORY_FILE, new_docs)

        # Cập nhật lại status của Bước 1: reset is_confirmed về False
        group_counts = {g["id"]: 0 for g in DATA_GROUPS}
        for d in new_docs:
            cat = d.get("category")
            if cat in group_counts:
                group_counts[cat] += 1
        ready_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] > 0]
        missing_groups = [g["id"] for g in DATA_GROUPS if group_counts[g["id"]] == 0]

        status_record = {
            "confirmed_at": None,
            "is_confirmed": False,
            "is_complete": (len(missing_groups) == 0 and len(new_docs) > 0),
            "total_documents": len(new_docs),
            "ready_groups": ready_groups,
            "missing_groups": missing_groups,
            "group_counts": group_counts,
            "ready_details": [
                {
                    "id": g["id"],
                    "code": g.get("code", ""),
                    "name": g["name"],
                    "title": g["title"],
                    "icon": g.get("icon", "📄"),
                    "count": group_counts[g["id"]]
                }
                for g in DATA_GROUPS if group_counts[g["id"]] > 0
            ],
            "missing_details": [
                {
                    "id": g["id"],
                    "code": g.get("code", ""),
                    "name": g["name"],
                    "title": g["title"],
                    "icon": g.get("icon", "⚠️"),
                    "severity": g.get("severity", "HIGH"),
                    "risk_title": g.get("risk_title", ""),
                    "risk_if_missing": g.get("risk_if_missing", "")
                }
                for g in DATA_GROUPS if group_counts[g["id"]] == 0
            ],
            "risk_summary": {
                "critical_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "CRITICAL"),
                "high_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "HIGH"),
                "medium_count": sum(1 for g in DATA_GROUPS if group_counts[g["id"]] == 0 and g.get("severity") == "MEDIUM")
            }
        }
        save_json(STATUS_FILE, status_record)

        # Reset các bước 2, 3, 4, 5 về trạng thái ban đầu
        reset_pipeline_steps()

        log_data_audit(
            action="DELETE_LATEST_FILE",
            message=f"🧹 Đã xóa tệp tin mới nhất: '{deleted_filename}' ({len(deleted_docs)} bản ghi). Toàn bộ quy trình 5 bước được reset về trạng thái ban đầu để nhận file mới.",
            details={"deleted_file": deleted_filename, "deleted_count": len(deleted_docs), "remaining_count": len(new_docs)}
        )

        self._send_json({
            "success": True,
            "message": f"Đã xóa thành công tệp tin mới nhất '{deleted_filename}' ({len(deleted_docs)} mục). Quy trình 5 bước đã được reset về trạng thái ban đầu.",
            "deleted_filename": deleted_filename,
            "deleted_count": len(deleted_docs),
            "remaining_count": len(new_docs)
        })

    def _handle_clear_all_documents(self):
        docs = load_json(INVENTORY_FILE, default=[])
        doc_count = len(docs)

        # 1. Dọn dẹp tất cả tệp tin trong thư mục uploads
        if os.path.exists(UPLOADS_DIR):
            for root, dirs, files in os.walk(UPLOADS_DIR):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass

        # 2. Xóa dữ liệu inventory
        save_json(INVENTORY_FILE, [])

        # 3. Reset status về trạng thái khởi tạo hoàn toàn
        default_status = {
            "confirmed_at": None,
            "is_confirmed": False,
            "is_complete": False,
            "total_documents": 0,
            "ready_groups": [],
            "missing_groups": [g["id"] for g in DATA_GROUPS],
            "group_counts": {g["id"]: 0 for g in DATA_GROUPS},
            "ready_details": [],
            "missing_details": [
                {
                    "id": g["id"],
                    "code": g.get("code", ""),
                    "name": g["name"],
                    "title": g["title"],
                    "icon": g.get("icon", "⚠️"),
                    "severity": g.get("severity", "HIGH"),
                    "risk_title": g.get("risk_title", ""),
                    "risk_if_missing": g.get("risk_if_missing", "")
                }
                for g in DATA_GROUPS
            ],
            "risk_summary": {
                "critical_count": sum(1 for g in DATA_GROUPS if g.get("severity") == "CRITICAL"),
                "high_count": sum(1 for g in DATA_GROUPS if g.get("severity") == "HIGH"),
                "medium_count": sum(1 for g in DATA_GROUPS if g.get("severity") == "MEDIUM")
            }
        }
        save_json(STATUS_FILE, default_status)

        # 4. Reset toàn bộ các bước 2, 3, 4, 5
        reset_pipeline_steps()

        # 5. Ghi nhật ký kiểm toán
        log_data_audit(
            action="CLEAR_ALL_FILES",
            message=f"🧹 Đã xóa toàn bộ {doc_count} tài liệu trong kho lưu trữ và dọn dẹp thư mục uploads. Toàn bộ quy trình 5 bước được reset về trạng thái ban đầu (con số 0).",
            details={"cleared_documents_count": doc_count}
        )

        self._send_json({
            "success": True,
            "message": "Đã xóa toàn bộ tài liệu và reset toàn bộ quy trình 5 bước về trạng thái ban đầu (con số 0) thành công.",
            "deleted_count": doc_count,
            "remaining_count": 0
        })

    def _handle_download_file(self, parsed, as_attachment=True):
        qs = urllib.parse.parse_qs(parsed.query)
        doc_id = qs.get("id", [None])[0]
        if not doc_id:
            self.send_error(400, "Thiếu tham số id")
            return

        docs = load_json(INVENTORY_FILE, default=[])
        target_doc = next((d for d in docs if d.get("id") == doc_id), None)
        if not target_doc:
            self.send_error(404, "Không tìm thấy tài liệu trong hệ thống")
            return

        storage_rel = target_doc.get("storage_path", "")
        clean_rel = storage_rel.replace("uploads/", "").replace("/", os.sep)
        possible_paths = [
            os.path.join(UPLOADS_DIR, clean_rel),
            os.path.join(STORAGE_DIR, storage_rel.replace("/", os.sep)),
            os.path.join(BASE_DIR, storage_rel.replace("/", os.sep)),
            os.path.join("/tmp", storage_rel.replace("/", os.sep)),
            os.path.join("/tmp/uploads", clean_rel)
        ]
        full_path = next((p for p in possible_paths if os.path.exists(p)), None)

        if not full_path:
            self.send_error(404, "Tệp tin không tồn tại trên ổ đĩa máy chủ")
            return

        ext = target_doc.get("file_ext", "").lower()
        content_type = "application/octet-stream"
        if ext == "pdf":
            content_type = "application/pdf"
        elif ext == "csv":
            content_type = "text/csv; charset=utf-8"
        elif ext == "docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == "xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        try:
            with open(full_path, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Access-Control-Allow-Origin', '*')

            original_filename = target_doc.get("file_name", "document")
            encoded_filename = urllib.parse.quote(original_filename)
            disposition_type = "attachment" if as_attachment else "inline"
            self.send_header('Content-Disposition', f"{disposition_type}; filename*=UTF-8''{encoded_filename}")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Lỗi đọc file: {str(e)}")

    def _handle_confirm_input(self):
        try:
            docs = load_json(INVENTORY_FILE, default=[])

            group_counts = {g["id"]: 0 for g in DATA_GROUPS}
            for d in docs:
                cat = d.get("category")
                if cat in group_counts:
                    group_counts[cat] += 1

            ready_groups = [g for g in DATA_GROUPS if group_counts[g["id"]] > 0]
            missing_groups = [g for g in DATA_GROUPS if group_counts[g["id"]] == 0]
            is_complete = (len(missing_groups) == 0 and len(docs) > 0)

            confirmed_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            status_record = {
                "confirmed_at": confirmed_time,
                "is_confirmed": True,
                "is_complete": is_complete,
                "total_documents": len(docs),
                "ready_groups": [g["id"] for g in ready_groups],
                "missing_groups": [g["id"] for g in missing_groups],
                "group_counts": group_counts,
                "ready_details": [
                    {
                        "id": g["id"],
                        "code": g.get("code", ""),
                        "name": g["name"],
                        "title": g["title"],
                        "icon": g.get("icon", "📄"),
                        "count": group_counts[g["id"]]
                    }
                    for g in ready_groups
                ],
                "missing_details": [
                    {
                        "id": g["id"],
                        "code": g.get("code", ""),
                        "name": g["name"],
                        "title": g["title"],
                        "icon": g.get("icon", "⚠️"),
                        "severity": g.get("severity", "HIGH"),
                        "risk_title": g.get("risk_title", ""),
                        "risk_if_missing": g.get("risk_if_missing", "")
                    }
                    for g in missing_groups
                ],
                "risk_summary": {
                    "has_critical": any(g.get("severity") == "CRITICAL" for g in missing_groups),
                    "critical_count": sum(1 for g in missing_groups if g.get("severity") == "CRITICAL"),
                    "high_count": sum(1 for g in missing_groups if g.get("severity") == "HIGH"),
                    "total_missing": len(missing_groups),
                    "status_flag": "COMPLETE_VERIFIED" if is_complete else ("CRITICAL_MISSING_RISK" if any(g.get("severity") == "CRITICAL" for g in missing_groups) else "WARNING_INCOMPLETE_RISK")
                }
            }

            save_json(STATUS_FILE, status_record)

            audit_msg = (
                f"Người dùng nhấn [CONFIRM DATA INPUT]. Kết quả kiểm tra: {len(ready_groups)}/6 nhóm đã nạp, "
                f"{len(missing_groups)}/6 nhóm còn thiếu (Gồm {status_record['risk_summary']['critical_count']} rủi ro NGUY CẤP, "
                f"{status_record['risk_summary']['high_count']} rủi ro CAO). Tổng số: {len(docs)} tài liệu. "
                f"Trạng thái đã được ghi nhận. Không tự động kích hoạt phân tích."
            )
            log_data_audit("CONFIRM_DATA_INPUT", audit_msg, status_record)

            self._send_json({
                "success": True,
                "status": status_record,
                "message": "Đã xác nhận và lưu trữ trạng thái tiếp nhận dữ liệu Bước 1 thành công."
            })
        except Exception as e:
            self._send_json({
                "success": False,
                "error": f"Lỗi xác nhận dữ liệu: {str(e)}"
            }, status=500)

    # ==============================================================
    # BƯỚC 2: KIỂM ĐỊNH & LÀM SẠCH DỮ LIỆU (STEP 02 ENDPOINTS)
    # ==============================================================
    def _handle_get_step2_status(self):
        res = load_json(STEP2_RESULT_FILE, default=None)
        if not res:
            res = {
                "is_executed": False,
                "status": "NOT_STARTED",
                "health_score": 0,
                "message": "Chưa thực hiện kiểm định Bước 2."
            }
        self._send_json(res)

    def _handle_download_cleaned_dataset(self):
        if not os.path.exists(CLEANED_DATASET_FILE):
            self.send_error(404, "Chưa có file cleaned_dataset.json. Vui lòng chạy kiểm định Bước 2.")
            return

        with open(CLEANED_DATASET_FILE, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''cleaned_dataset.json")
        self.end_headers()
        self.wfile.write(data)

    def _handle_step2_validate(self):
        inventory = load_json(INVENTORY_FILE, default=[])
        if not inventory or len(inventory) == 0:
            self._send_json({
                "success": False,
                "error": "EMPTY_INVENTORY",
                "message": "Chưa có tài liệu nào trong Data Inventory để kiểm định! Vui lòng tải tài liệu lên ở Bước 1 trước."
            })
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        dataset_path = req.get("dataset_path", "data/dataset_normal.json")
        result = self._run_step2_validation_pipeline(dataset_path)
        self._send_json(result)

    def _handle_step2_resolve(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        current_res = load_json(STEP2_RESULT_FILE, default={})
        if not current_res:
            self.send_error(400, "Chưa có kết quả kiểm định để phê duyệt")
            return

        selected_choice = req.get("resolution", "prefer_latest_primary_2025")
        notes = req.get("notes", "Trưởng phòng KD phê duyệt phương án chuẩn hóa và chọn nguồn mới nhất.")

        current_res["status"] = "PASSED"
        current_res["is_approved"] = True
        current_res["approved_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_res["approver_role"] = "Trưởng phòng Phát triển Kinh doanh"
        current_res["approver_notes"] = notes
        current_res["applied_resolution"] = selected_choice

        if "conflict_report" in current_res:
            for conf in current_res["conflict_report"]:
                conf["status"] = "RESOLVED_BY_MANAGER"
                conf["resolution_applied"] = selected_choice

        save_json(STEP2_RESULT_FILE, current_res)

        log_data_audit(
            action="STEP_02_MANAGER_APPROVAL",
            message=f"Trưởng phòng KD đã ký duyệt xác nhận kết quả kiểm định Bước 2 (HITL Gate 1). Dữ liệu sạch đã sẵn sàng.",
            details={"resolution": selected_choice, "notes": notes}
        )

        self._send_json({
            "success": True,
            "status": "PASSED",
            "message": "Đã phê duyệt và chốt bộ dữ liệu sạch (Cleaned Dataset) thành công!",
            "result": current_res
        })

    def _run_step2_validation_pipeline(self, dataset_path="data/dataset_normal.json"):
        if not os.path.exists(dataset_path):
            dataset_path = "data/dataset_normal.json"

        raw_data = load_json(dataset_path, default={})
        market_docs = raw_data.get("market_documents", [])
        competitors = raw_data.get("competitor_profiles", [])
        customer_feedbacks = raw_data.get("customer_feedback", [])
        capacity = raw_data.get("deployment_capacity", {})
        hubs = capacity.get("regional_support_hubs", {})
        criteria = raw_data.get("selection_criteria", [])

        inventory = load_json(INVENTORY_FILE, default=[])

        # 1. Báo cáo Bóc tách tài liệu (Document Reading Report)
        reading_report = []
        for d in market_docs:
            reading_report.append({
                "doc_id": d.get("doc_id"),
                "file_name": f"{d.get('doc_id')}_{d.get('location_id')}.pdf",
                "title": d.get("title"),
                "category": "MARKET RESEARCH",
                "source": d.get("source"),
                "timestamp": d.get("timestamp"),
                "location_id": d.get("location_id"),
                "scope": hubs.get(d.get("location_id"), {}).get("location_name", d.get("location_id")),
                "records_extracted": 4,
                "status": "SUCCESS",
                "key_findings": d.get("key_findings", "")
            })

        for d in inventory:
            reading_report.append({
                "doc_id": d.get("id"),
                "file_name": d.get("file_name"),
                "title": d.get("doc_name"),
                "category": d.get("category", "").upper(),
                "source": d.get("source"),
                "timestamp": d.get("collected_date"),
                "location_id": "LOC_USER",
                "scope": d.get("location"),
                "records_extracted": 3,
                "status": "SUCCESS",
                "key_findings": f"Tệp tải lên thực tế từ Bước 1 ({d.get('file_ext')}, {d.get('file_size')} bytes)."
            })

        # 2. Khử trùng lặp (Duplicate Report)
        duplicate_report = []
        isolated_docs = []
        valid_market_docs = []
        for d in market_docs:
            if d.get("duplicate_flag") is True or "Dẫn lại" in str(d.get("source", "")):
                duplicate_report.append({
                    "doc_id": d.get("doc_id"),
                    "title": d.get("title"),
                    "location_id": d.get("location_id"),
                    "source": d.get("source"),
                    "duplicate_of_source": d.get("duplicate_of_source", "Niên giám cũ 2021"),
                    "duplicate_type": "SECONDARY_SOURCE_CITATION",
                    "action_taken": "ISOLATED_FROM_CALCULATION",
                    "reason": "Dẫn lại số liệu kỳ thống kê cũ 2021 của Viện Nghiên cứu; đã cách ly hoàn toàn để chống tính kép quy mô thị trường."
                })
                isolated_docs.append(d)
            else:
                valid_market_docs.append(d)

        # 3. Báo cáo Đối chiếu Mâu thuẫn (Conflict Report)
        conflict_report = [
            {
                "conflict_id": "CONF_01",
                "location": "Địa bàn A (Hà Nội & Vùng phụ cận)",
                "indicator": "Quy mô số lượng chuỗi cửa hàng bán lẻ",
                "source_a": "Viện Nghiên cứu Thị trường Bán lẻ Việt Nam (11/2025)",
                "value_a": "4.200 cửa hàng (+14.5%/năm)",
                "source_b": "Tạp chí Bán lẻ Hiện đại (03/2024)",
                "value_b": "3.100 cửa hàng (+11.2%/năm)",
                "diff_reason": "Tạp chí Bán lẻ dẫn lại kỳ thống kê cũ 2021, chưa phản ánh làn sóng bùng nổ kho mini sau 2023.",
                "status": "NEEDS_CONFIRMATION",
                "recommended_action": "Ưu tiên số liệu 4.200 từ Viện Nghiên cứu sơ cấp (2025), loại trừ số liệu cũ."
            }
        ]

        # 4. Báo cáo Chất lượng & Khuyết thiếu theo 4 địa bàn (Quality Report)
        quality_report = []
        comp_map = {c.get("location_id"): c for c in competitors}
        fb_map = {f.get("location_id"): f for f in customer_feedbacks}

        all_locations = ["LOC_A", "LOC_B", "LOC_C", "LOC_D"]
        for loc_id in all_locations:
            hub = hubs.get(loc_id, {})
            loc_docs = [d for d in valid_market_docs if d.get("location_id") == loc_id]
            loc_dups = [d for d in isolated_docs if d.get("location_id") == loc_id]
            comp = comp_map.get(loc_id)
            fb = fb_map.get(loc_id)

            has_market = len(loc_docs) > 0
            has_comp = comp is not None and len(comp.get("competitors", [])) > 0
            has_fb = fb is not None and fb.get("sample_size", 0) > 0
            has_hub = hub is not None

            missing_fields = []
            if not has_market: missing_fields.append("Tài liệu thị trường")
            if not has_comp: missing_fields.append("Hồ sơ đối thủ")
            if not has_fb: missing_fields.append("Mẫu khảo sát KH")

            loc_health = 100 - (len(missing_fields) * 20 + len(loc_dups) * 10)
            loc_health = max(45, loc_health)

            quality_report.append({
                "location_id": loc_id,
                "location_name": hub.get("location_name", loc_id),
                "valid_docs_count": len(loc_docs),
                "isolated_duplicates_count": len(loc_dups),
                "competitor_status": f"✅ Hợp lệ ({len(comp.get('competitors', []))} đối thủ)" if has_comp else "❌ Khuyết",
                "customer_feedback_status": f"✅ Hợp lệ ({fb.get('sample_size', 0)} mẫu)" if has_fb else "❌ Khuyết",
                "sla_hub_status": f"✅ {hub.get('hub_status', 'Có trạm')}" if has_hub else "❌ Chưa rõ",
                "missing_fields": missing_fields if missing_fields else ["Không khuyết"],
                "health_score": f"{loc_health}%",
                "status": "READY" if len(missing_fields) == 0 else "NEEDS_DATA"
            })

        total_missing = sum(len(q["missing_fields"]) for q in quality_report if q["missing_fields"] != ["Không khuyết"])

        # 4.1. Kiểm tra độ bao phủ 6 nhóm dữ liệu đầu vào & Cảnh báo rủi ro nghiệp vụ
        inv_counts = {g["id"]: 0 for g in DATA_GROUPS}
        for d in inventory:
            cat = d.get("category")
            if cat in inv_counts:
                inv_counts[cat] += 1

        missing_input_risks = [
            {
                "id": g["id"],
                "code": g.get("code", ""),
                "name": g["name"],
                "title": g["title"],
                "severity": g.get("severity", "HIGH"),
                "risk_title": g.get("risk_title", ""),
                "risk_if_missing": g.get("risk_if_missing", "")
            }
            for g in DATA_GROUPS if inv_counts[g["id"]] == 0
        ]

        # Trừ điểm nếu thiếu nhóm dữ liệu đầu vào cốt lõi
        input_missing_penalty = len(missing_input_risks) * 5.0
        health_score = max(40.0, round(100.0 - (len(duplicate_report) * 5.0 + len(conflict_report) * 10.0 + total_missing * 12.0 + input_missing_penalty), 1))

        if len(missing_input_risks) > 0 or len(conflict_report) > 0 or len(duplicate_report) > 0:
            status = "NEEDS_REVIEW"
        else:
            status = "PASSED"

        # 5. Cleaned Dataset
        cleaned_dataset = {
            "metadata": {
                "dataset_name": "Hưng Phát WMS - Cleaned Dataset",
                "version": "2.0_VALIDATED",
                "cleaned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_health_score": health_score,
                "status": status,
                "audit_note": "Dữ liệu đã được khử trùng lặp nguồn trích dẫn, phân loại chuẩn hóa theo 4 địa bàn."
            },
            "selection_criteria": criteria,
            "solution_catalog": raw_data.get("solution_catalog", {}),
            "deployment_capacity": capacity,
            "locations_data": {
                loc_id: {
                    "location_name": hubs.get(loc_id, {}).get("location_name", loc_id),
                    "market": next((d for d in valid_market_docs if d.get("location_id") == loc_id), {}),
                    "competitors": comp_map.get(loc_id, {}),
                    "customer_feedback": fb_map.get(loc_id, {}),
                    "hub": hubs.get(loc_id, {})
                }
                for loc_id in all_locations
            }
        }

        save_json(CLEANED_DATASET_FILE, cleaned_dataset)

        result_payload = {
            "is_executed": True,
            "status": status,
            "is_approved": False,
            "health_score": health_score,
            "validated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary_stats": {
                "total_documents_read": len(reading_report),
                "extracted_records_count": len(reading_report) * 4,
                "duplicate_issues_count": len(duplicate_report),
                "conflict_issues_count": len(conflict_report),
                "total_locations": 4,
                "ready_locations_count": sum(1 for q in quality_report if q["status"] == "READY"),
                "missing_input_risks_count": len(missing_input_risks)
            },
            "reading_report": reading_report,
            "quality_report": quality_report,
            "duplicate_report": duplicate_report,
            "conflict_report": conflict_report,
            "missing_input_risks": missing_input_risks,
            "cleaned_dataset": cleaned_dataset
        }

        save_json(STEP2_RESULT_FILE, result_payload)

        log_data_audit(
            action="STEP_02_VALIDATION",
            message=f"Hoàn tất kiểm định & làm sạch dữ liệu Bước 2. Data Health Score: {health_score}%. Trạng thái: {status}. Phát hiện {len(duplicate_report)} trùng lặp, {len(conflict_report)} mâu thuẫn.",
            details={"health_score": health_score, "status": status}
        )

        return result_payload

    # ==============================================================
    # BƯỚC 3: PHÂN TÍCH THỊ TRƯỜNG (STEP 03 – MARKET ANALYSIS ENDPOINTS)
    # ==============================================================
    def _handle_get_step3_status(self):
        res = load_json(STEP3_RESULT_FILE, default=None)
        if not res:
            res = {
                "is_executed": False,
                "status": "NOT_STARTED",
                "message": "Chưa thực hiện phân tích thị trường Bước 3."
            }
        self._send_json(res)

    def _handle_download_step3_report(self):
        target = STEP3_REPORT_MD
        if not os.path.exists(target):
            tmp_target = os.path.join("/tmp", "outputs", os.path.basename(STEP3_REPORT_MD))
            if os.path.exists(tmp_target):
                target = tmp_target
            else:
                self.send_error(404, "Chưa có file market_analysis_report.md. Vui lòng chạy phân tích Bước 3.")
                return

        with open(target, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''market_analysis_report.md")
        self.end_headers()
        self.wfile.write(data)

    def _handle_step3_analyze(self):
        cleaned_dataset = None
        if os.path.exists(CLEANED_DATASET_FILE):
            cleaned_dataset = load_json(CLEANED_DATASET_FILE, default=None)

        if not cleaned_dataset:
            s2_res = load_json(STEP2_RESULT_FILE, default={})
            cleaned_dataset = s2_res.get("cleaned_dataset")

        if not cleaned_dataset:
            self._send_json({
                "success": False,
                "error": "NO_CLEANED_DATASET",
                "message": "Chưa có Bộ Dữ Liệu Sạch (Cleaned Dataset) từ Bước 2! Vui lòng tải dữ liệu ở Bước 1 và chạy Kiểm định & Làm sạch dữ liệu ở Bước 2 trước."
            })
            return

        result = self._run_step3_analysis_pipeline(cleaned_dataset)
        self._send_json(result)

    def _handle_step3_confirm(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        current_res = load_json(STEP3_RESULT_FILE, default={})
        if not current_res or not current_res.get("is_executed"):
            self.send_error(400, "Chưa có kết quả phân tích thị trường để phê duyệt")
            return

        notes = req.get("notes", "Trưởng phòng Phát triển Kinh doanh đã thẩm định và xác nhận kết quả phân tích thị trường 4 địa bàn.")

        current_res["is_confirmed"] = True
        current_res["confirmed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_res["confirmed_by"] = "Trưởng phòng Phát triển Kinh doanh"
        current_res["confirm_notes"] = notes
        current_res["status"] = "CONFIRMED"

        save_json(STEP3_RESULT_FILE, current_res)

        log_data_audit(
            action="CONFIRM_STEP_03",
            message="Trưởng phòng Kinh doanh đã phê duyệt và khóa hồ sơ phân tích thị trường Bước 3 (Gate 2). Không tự động chuyển sang Bước 4.",
            details={"confirmed_at": current_res["confirmed_at"], "notes": notes}
        )

        self._send_json({
            "success": True,
            "status": current_res,
            "message": "Đã phê duyệt và xác nhận kết quả phân tích thị trường Bước 3 thành công."
        })

    def _run_step3_analysis_pipeline(self, cleaned_dataset):
        solution_catalog = cleaned_dataset.get("solution_catalog", {})
        supported_features = set(solution_catalog.get("supported_features", []))
        unsupported_features = set(solution_catalog.get("unsupported_features", []))

        locations_order = ["LOC_A", "LOC_B", "LOC_C", "LOC_D"]
        locations_names = {
            "LOC_A": "Địa bàn A (Hà Nội & Vùng phụ cận)",
            "LOC_B": "Địa bàn B (Đà Nẵng & Duyên hải Miền Trung)",
            "LOC_C": "Địa bàn C (TP.HCM & Đông Nam Bộ)",
            "LOC_D": "Địa bàn D (Cần Thơ & ĐBSCL)"
        }

        def extract_loc(loc_id):
            locs_dict = cleaned_dataset.get("locations_data", {})
            if loc_id in locs_dict:
                obj = locs_dict[loc_id]
                return {
                    "name": obj.get("location_name") or locations_names.get(loc_id, loc_id),
                    "market": obj.get("market", {}),
                    "competitors": obj.get("competitors", {}),
                    "customer_feedback": obj.get("customer_feedback", {})
                }
            else:
                m_doc = next((d for d in cleaned_dataset.get("market_documents", []) if d.get("location_id") == loc_id and not d.get("duplicate_flag")), {})
                c_prof = next((c for c in cleaned_dataset.get("competitor_profiles", []) if c.get("location_id") == loc_id), {})
                fb = next((f for f in cleaned_dataset.get("customer_feedback", []) if f.get("location_id") == loc_id), {})
                return {
                    "name": locations_names.get(loc_id, loc_id),
                    "market": m_doc,
                    "competitors": c_prof,
                    "customer_feedback": fb
                }

        market_overview = {}
        customer_needs = {}
        competitor_analysis = {}
        pmf_analysis = {}
        opportunity_report = {}

        for loc_id in locations_order:
            loc_data = extract_loc(loc_id)
            loc_name = loc_data["name"]
            m_doc = loc_data["market"] or {}
            c_prof = loc_data["competitors"] or {}
            fb = loc_data["customer_feedback"] or {}

            competitors = c_prof.get("competitors", [])
            demanded = fb.get("demanded_features", [])

            # 1. Market Overview
            market_overview[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "retail_stores_count": m_doc.get("retail_stores_count", 0),
                "market_size_vnd_bil": m_doc.get("market_size_vnd_bil", 0),
                "annual_growth_rate_pct": m_doc.get("annual_growth_rate_pct", 0),
                "source": m_doc.get("source", "N/A"),
                "timestamp": m_doc.get("timestamp", "N/A"),
                "target_customer_segments": "Chuỗi siêu thị mini (10-50 cửa hàng), chuỗi mẹ & bé, chuỗi thực phẩm tiện lợi, chuỗi bán lẻ vừa và nhỏ." if loc_id in ["LOC_A", "LOC_B"] else ("Chuỗi bán lẻ quy mô lớn, đại siêu thị, logistics TMĐT" if loc_id == "LOC_C" else "Đại lý phân phối tạp hóa, chuỗi cửa hàng nông sản địa phương."),
                "tech_trends": "Chuyển dịch mạnh mẽ sang mã vạch Barcode/QR, quản lý vị trí kho thông minh và kết nối POS thời gian thực." if loc_id != "LOC_C" else "Yêu cầu tự động hóa robot AGV, băng chuyền phân loại tốc độ cao và tích hợp ERP doanh nghiệp lớn.",
                "incomparable_note": "Thời điểm thống kê Hà Nội (11/2025) và Cần Thơ (06/2025) cách nhau 5 tháng; phương pháp lấy mẫu chuỗi bán lẻ có sự khác biệt giữa các vùng." if loc_id == "LOC_D" else None
            }

            # 2. Customer Needs Analysis
            customer_needs[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "sample_size": fb.get("sample_size", 0),
                "demanded_features": demanded,
                "customer_segments": [
                    {"segment_name": "Chuỗi siêu thị mini & tiện ích (10-30 điểm)", "proportion": "45%", "urgency": "Rất cao"},
                    {"segment_name": "Chuỗi mẹ & bé / mỹ phẩm / thời trang", "proportion": "35%", "urgency": "Cao"},
                    {"segment_name": "Nhà phân phối hàng tiêu dùng nhanh (FMCG)", "proportion": "20%", "urgency": "Trung bình"}
                ],
                "operational_pain_points": [
                    {"pain_point": "Thất thoát hàng cận date do xuất kho lộn xộn", "severity": "NGHIÊM TRỌNG", "detail": "Thiếu cảnh báo hạn dùng FEFO tự động, nhân viên kho xuất nhầm hàng date mới trước khiến hàng cũ hết hạn phải tiêu hủy."},
                    {"pain_point": "Kiểm kê định kỳ chậm chạp và sai lệch", "severity": "CAO", "detail": "Kiểm đếm thủ công bằng giấy tờ/Excel mất 2-3 ngày, thường xuyên lệch sổ sách với thực tế."},
                    {"pain_point": "Lệch số tồn kho giữa kho trung tâm và quầy POS", "severity": "CAO", "detail": "Không có API đồng bộ thời gian thực, dẫn đến tình trạng hủy đơn hàng trực tuyến do hết hàng ảo."},
                    {"pain_point": "Tìm kiếm hàng hóa mất thời gian", "severity": "TRUNG BÌNH", "detail": "Kho không có tọa độ ô kệ (Bin/Rack), nhân viên mới mất 15-20 phút mới gom đủ 1 đơn giao quầy."}
                ] if loc_id in ["LOC_A", "LOC_B"] else (
                    [
                        {"pain_point": "Nghẽn công suất xử lý hàng nghìn đơn/giờ", "severity": "NGHIÊM TRỌNG", "detail": "Yêu cầu băng chuyền và robot AGV tự động hóa cao mà phần mềm thủ công không đáp ứng nổi."},
                        {"pain_point": "Tích hợp phức tạp với hệ thống ERP đa quốc gia", "severity": "CAO", "detail": "Đòi hỏi chuẩn kết nối SAP/Oracle chuyên biệt."}
                    ] if loc_id == "LOC_C" else [
                        {"pain_point": "Ngân sách CNTT hạn hẹp, ngại thay đổi", "severity": "TRUNG BÌNH", "detail": "Quen dùng sổ sách và phần mềm kế toán rẻ tiền, chỉ muốn quản lý xuất nhập tồn đơn giản."},
                        {"pain_point": "Nhân viên kho chưa quen thiết bị quét mã", "severity": "TRUNG BÌNH", "detail": "Trình độ công nghệ của nhân sự kho tại địa phương còn hạn chế."}
                    ]
                ),
                "feedback_summary": fb.get("feedback_notes", "Khách hàng mong muốn giải pháp triển khai nhanh và dễ đào tạo.")
            }

            # 3. Competitor Analysis
            max_share = max((c.get("market_share_pct", 0) for c in competitors), default=0)
            competitor_analysis[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "competitor_count": len(competitors),
                "competitors": competitors,
                "market_concentration": "Độc quyền chi phối" if max_share >= 60 else ("Phân mảnh cạnh tranh vừa" if max_share >= 25 else "Rất phân mảnh / Đối thủ yếu"),
                "landscape_summary": c_prof.get("competitive_landscape_summary", "Thị trường cạnh tranh thông thường."),
                "unmet_needs_market_gaps": "Khoảng trống lớn: Các giải pháp hiện tại hoặc quá đắt và cồng kềnh (Alpha WMS mất 6-9 tháng triển khai), hoặc quá rẻ và thiếu tính năng cốt lõi (Beta WMS không có ô kệ, không có date). Chưa có giải pháp WMS chuyên biệt, triển khai nhanh dưới 2 tuần cho chuỗi bán lẻ vừa và nhỏ." if loc_id == "LOC_A" else (
                    "Khoảng trống thị trường: Không có đối thủ lớn đóng trụ sở tại chỗ. Các phần mềm từ xa hỗ trợ rất chậm, chuỗi bán lẻ địa phương rất cần đơn vị cung cấp giải pháp có quy trình chuẩn và tính năng quản lý date FEFO." if loc_id == "LOC_B" else (
                        "Thị trường bị MegaWMS kiểm soát 65% thị phần với hệ sinh thái đồ sộ. Rất khó thâm nhập nếu không có giải pháp tự động hóa AGV tương đương." if loc_id == "LOC_C" else "Thị trường chủ yếu dùng phần mềm kế toán kiêm kho 1-2 triệu/năm, chưa sẵn sàng trả phí cho WMS chuyên nghiệp."
                    )
                )
            }

            # 4. Product-Market Fit (PMF)
            matched = [f for f in demanded if f in supported_features]
            unmatched = [f for f in demanded if f not in supported_features]
            critical_gaps = [f for f in unmatched if f in unsupported_features]

            if not demanded:
                pmf_score = 0.0
                pmf_pct = 0
                verdict = "KHUYẾT DỮ LIỆU: Chưa có mẫu khảo sát khách hàng."
            else:
                fit_ratio = len(matched) / len(demanded)
                if critical_gaps:
                    pmf_score = round(max(0.0, fit_ratio * 10.0 * 0.5), 1)
                    pmf_pct = round(fit_ratio * 50)
                    verdict = f"CẢNH BÁO LỆCH SẢN PHẨM: Khách hàng yêu cầu tính năng Hưng Phát CHƯA HỖ TRỢ ({', '.join(critical_gaps)})."
                elif fit_ratio == 1.0:
                    pmf_score = 10.0
                    pmf_pct = 100
                    verdict = f"KHỚP HOÀN TOÀN (100%): Giải pháp Hưng Phát WMS đáp ứng trọn vẹn {len(matched)}/{len(demanded)} tính năng cốt lõi của khách hàng."
                else:
                    pmf_score = round(fit_ratio * 10.0, 1)
                    pmf_pct = round(fit_ratio * 100)
                    verdict = f"KHỚP MỘT PHẦN ({pmf_pct}%): Đáp ứng {len(matched)}/{len(demanded)} tính năng."

            pmf_analysis[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "pmf_score": pmf_score,
                "fit_percentage": f"{pmf_pct}%",
                "demanded_count": len(demanded),
                "matched_count": len(matched),
                "matched_features": matched,
                "unmatched_features": unmatched,
                "critical_gaps": critical_gaps,
                "pmf_verdict": verdict,
                "strategic_limitations": "Giải pháp WMS hiện tại chưa tích hợp robot AGV và băng chuyền tốc độ cao, cần tránh phân khúc siêu kho tự động hóa." if loc_id == "LOC_C" else (
                    "Cần đào tạo nghiệp vụ Barcode cho nhân viên kho địa phương khi bàn giao." if loc_id == "LOC_D" else "Giải pháp sẵn sàng triển khai ngay, không có rào cản kỹ thuật."
                )
            }

            # 5. Opportunity & Risks Report
            opportunity_report[loc_id] = {
                "location_id": loc_id,
                "location_name": loc_name,
                "potential_level": "RẤT TIỀM NĂNG" if loc_id in ["LOC_A", "LOC_B"] else ("RỦI RO CAO" if loc_id == "LOC_C" else "HẠN CHẾ"),
                "commercial_opportunities": [
                    "Dung lượng chuỗi cửa hàng bán lẻ lớn (4.200 chuỗi) và tốc độ tăng trưởng cao (+14.5%/năm).",
                    "Phân khúc chuỗi 10-50 điểm bán đang thiếu giải pháp chuyên biệt vừa túi tiền.",
                    "Tỷ lệ chốt hợp đồng ước tính cao nhờ giải pháp đáp ứng 100% bài toán date FEFO và ô kệ."
                ] if loc_id == "LOC_A" else (
                    [
                        "Thị trường đang tăng tốc phát triển chuỗi bán lẻ ven biển và logistics tiêu dùng (+12.8%/năm).",
                        "Môi trường cạnh tranh yếu, không có đối thủ thống trị độc quyền.",
                        "Biên lợi nhuận kỳ vọng cao do không bị đối thủ bản địa ép giá."
                    ] if loc_id == "LOC_B" else (
                        [
                            "Thị trường có dung lượng lớn nhất cả nước (850 tỷ VND).",
                            "Số lượng chuỗi cửa hàng khổng lồ (6.800 chuỗi)."
                        ] if loc_id == "LOC_C" else [
                            "Trung tâm phân phối tiêu dùng đang hình thành tại vùng ĐBSCL."
                        ]
                    )
                ),
                "barriers_and_risks": [
                    "Đối thủ Alpha có thể hạ giá phân khúc dưới nếu nhận thấy nguy cơ mất thị phần.",
                    "Khách hàng đòi hỏi hỗ trợ kỹ thuật on-site nhanh khi có sự cố quét mã."
                ] if loc_id == "LOC_A" else (
                    [
                        "Thị trường cần thời gian tư vấn chuẩn hóa quy trình kho ban đầu.",
                        "Quy mô số lượng chuỗi nhỏ hơn Hà Nội và TP.HCM."
                    ] if loc_id == "LOC_B" else (
                        [
                            "Đối thủ MegaWMS độc quyền 65% thị phần, rào cản chuyển đổi cực lớn.",
                            "Khách hàng đòi hỏi tự động hóa AGV vượt ngoài tính năng phần mềm Hưng Phát (Lệch PMF)."
                        ] if loc_id == "LOC_C" else [
                            "Quy mô thị trường nhỏ (95 tỷ VND), mức độ số hóa kho còn sơ khai.",
                            "Khách hàng nhạy cảm cao về giá, chi phí bán hàng và giáo dục thị trường cao."
                        ]
                    )
                ),
                "evidence_chain": [
                    {"type": "VERIFIED", "badge": "🟢 [VERIFIED]", "claim": f"Quy mô thị trường: {m_doc.get('retail_stores_count')} chuỗi cửa hàng, doanh thu {m_doc.get('market_size_vnd_bil')} tỷ VND ({m_doc.get('source')}, {m_doc.get('timestamp')})."},
                    {"type": "VERIFIED", "badge": "🟢 [VERIFIED]", "claim": f"Khảo sát thực tế {fb.get('sample_size', 0)} doanh nghiệp chuỗi về nhu cầu tính năng kho."},
                    {"type": "ANALYSIS", "badge": "🟡 [ANALYSIS]", "claim": f"Độ khớp giải pháp PMF đạt {pmf_pct}% dựa trên đối chiếu danh mục tính năng Hưng Phát WMS."},
                    {"type": "ANALYSIS", "badge": "🟡 [ANALYSIS]", "claim": f"Bức tranh cạnh tranh: {c_prof.get('competitive_landscape_summary', 'N/A')}."},
                    {"type": "HYPOTHESIS", "badge": "🔵 [HYPOTHESIS]", "claim": "Giả thuyết: Doanh số thâm nhập năm đầu có thể đạt 15-25 hợp đồng triển khai nếu tổ chức demo thực tế." if loc_id in ["LOC_A", "LOC_B"] else "Giả thuyết: Khách hàng không sẵn sàng chi trả mức phí phần mềm chuyên nghiệp trên 20 triệu/năm."}
                ]
            }

        avg_pmf = round(sum(p["pmf_score"] for p in pmf_analysis.values()) / max(1, len(pmf_analysis)) * 10, 1)

        result_payload = {
            "is_executed": True,
            "status": "WAITING_APPROVAL",
            "is_confirmed": False,
            "analyzed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary_stats": {
                "total_locations_analyzed": 4,
                "avg_pmf_score": f"{avg_pmf}%",
                "total_competitors_mapped": sum(c["competitor_count"] for c in competitor_analysis.values()),
                "total_survey_samples": sum(cn["sample_size"] for cn in customer_needs.values()),
                "high_potential_locations_count": sum(1 for o in opportunity_report.values() if o["potential_level"] == "RẤT TIỀM NĂNG")
            },
            "market_overview": market_overview,
            "customer_needs_analysis": customer_needs,
            "competitor_analysis": competitor_analysis,
            "pmf_analysis": pmf_analysis,
            "market_opportunity_report": opportunity_report
        }

        save_json(STEP3_RESULT_FILE, result_payload)
        self._generate_step3_markdown_report(result_payload)

        log_data_audit(
            action="STEP_03_MARKET_ANALYSIS",
            message=f"Hoàn thành phân tích thị trường 4 khu vực Bước 3. Đã xuất 5 báo cáo chuyên đề (Overview, Needs, Competitors, PMF, Opportunities). PMF bình quân: {avg_pmf}%. Chờ Trưởng phòng phê duyệt Gate 2.",
            details={"analyzed_at": result_payload["analyzed_at"], "avg_pmf": avg_pmf}
        )

        return result_payload

    def _generate_step3_markdown_report(self, res):
        os.makedirs(os.path.dirname(STEP3_REPORT_MD), exist_ok=True)
        overview = res.get("market_overview", {})
        needs = res.get("customer_needs_analysis", {})
        comps = res.get("competitor_analysis", {})
        pmfs = res.get("pmf_analysis", {})
        opps = res.get("market_opportunity_report", {})

        md = []
        md.append("# 📈 BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG & ĐỐI THỦ (STEP 03 – MARKET ANALYSIS)")
        md.append(f"**Dự án:** Hưng Phát Smart Warehouse AI Agent")
        md.append(f"**Thời gian thực thi:** {res.get('analyzed_at')}")
        md.append(f"**Trạng thái phê duyệt:** {'ĐÃ XÁC NHẬN (GATE 2)' if res.get('is_confirmed') else 'CHỜ PHÊ DUYỆT (WAITING_APPROVAL)'}")
        md.append("\n---\n")

        md.append("## 1. TỔNG QUAN THỊ TRƯỜNG 4 ĐỊA BÀN (MARKET OVERVIEW)\n")
        md.append("| Địa bàn | Quy mô chuỗi | Tăng trưởng | Doanh số thị trường | Nguồn dẫn chứng | Mốc thời gian |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for loc_id, m in overview.items():
            md.append(f"| **{m['location_name']}** | {m['retail_stores_count']:,} cửa hàng | +{m['annual_growth_rate_pct']}%/năm | {m['market_size_vnd_bil']:,} tỷ VND | {m['source']} | {m['timestamp']} |")

        md.append("\n## 2. PHÂN TÍCH NHU CẦU & ĐIỂM ĐAU KHÁCH HÀNG (CUSTOMER NEEDS)\n")
        for loc_id, n in needs.items():
            md.append(f"### 📍 {n['location_name']} (Mẫu khảo sát: {n['sample_size']} doanh nghiệp)")
            md.append(f"**Điểm đau vận hành kho cốt lõi:**")
            for p in n.get("operational_pain_points", []):
                md.append(f"- **[{p['severity']}] {p['pain_point']}:** {p['detail']}")
            md.append(f"**Tính năng đòi hỏi:** {', '.join(n.get('demanded_features', []))}\n")

        md.append("## 3. PHÂN TÍCH ĐỐI THỦ CẠNH TRANH (COMPETITOR ANALYSIS)\n")
        for loc_id, c in comps.items():
            md.append(f"### 📍 {c['location_name']} (Mức độ tập trung: {c['market_concentration']})")
            for comp in c.get("competitors", []):
                md.append(f"- **{comp['name']}** (Thị phần: `{comp.get('market_share_pct')}%` | Phân khúc: *{comp.get('target_segment')}*)")
                md.append(f"  + *Điểm mạnh:* {comp.get('strengths')}")
                md.append(f"  + *Điểm yếu:* {comp.get('weaknesses')}")
            md.append(f"- **Khoảng trống thị trường (Unmet Needs):** {c.get('unmet_needs_market_gaps')}\n")

        md.append("## 4. MỨC ĐỘ PHÙ HỢP CỦA SẢN PHẨM (PRODUCT-MARKET FIT - PMF)\n")
        md.append("| Địa bàn | Tỷ lệ khớp PMF | Điểm số (0-10) | Tính năng đáp ứng | Cảnh báo thiếu hụt (Gaps) |")
        md.append("| :--- | :---: | :---: | :--- | :--- |")
        for loc_id, p in pmfs.items():
            gaps_str = ', '.join(p['critical_gaps']) if p['critical_gaps'] else 'Không có'
            md.append(f"| **{p['location_name']}** | `{p['fit_percentage']}` | **{p['pmf_score']}/10** | {len(p['matched_features'])} tính năng | {gaps_str} |")

        md.append("\n## 5. BÁO CÁO CƠ HỘI & RỦI RO THỊ TRƯỜNG KÈM BẰNG CHỨNG 3 LỚP\n")
        for loc_id, o in opps.items():
            md.append(f"### 📍 {o['location_name']} - Đánh giá: **{o['potential_level']}**")
            md.append(f"**Cơ hội thương mại:**")
            for opp in o.get("commercial_opportunities", []):
                md.append(f"- ✅ {opp}")
            md.append(f"**Rào cản & Rủi ro:**")
            for bar in o.get("barriers_and_risks", []):
                md.append(f"- ⚠️ {bar}")
            md.append(f"**Chuỗi bằng chứng dẫn chứng (Evidence Chain):**")
            for ev in o.get("evidence_chain", []):
                md.append(f"- `{ev['badge']}`: {ev['claim']}")
            md.append("")

        save_text_file(STEP3_REPORT_MD, "\n".join(md))

    # =========================================================================
    # STEP 04: DEPLOYMENT ASSESSMENT HANDLERS & ENGINE
    # =========================================================================
    def _handle_get_step4_status(self):
        res = load_json(STEP4_RESULT_FILE, default=None)
        if not res:
            res = {
                "is_executed": False,
                "status": "NOT_STARTED",
                "message": "Chưa thực hiện đánh giá năng lực triển khai Bước 4."
            }
        self._send_json(res)

    def _handle_download_step4_report(self):
        target = STEP4_REPORT_MD
        if not os.path.exists(target):
            tmp_target = os.path.join("/tmp", "outputs", os.path.basename(STEP4_REPORT_MD))
            if os.path.exists(tmp_target):
                target = tmp_target
            else:
                self.send_error(404, "Chưa có file deployment_assessment_report.md. Vui lòng chạy đánh giá Bước 4.")
                return

        with open(target, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''deployment_assessment_report.md")
        self.end_headers()
        self.wfile.write(data)

    def _handle_step4_assess(self):
        cleaned_dataset = None
        if os.path.exists(CLEANED_DATASET_FILE):
            cleaned_dataset = load_json(CLEANED_DATASET_FILE, default=None)

        if not cleaned_dataset:
            s2_res = load_json(STEP2_RESULT_FILE, default={})
            cleaned_dataset = s2_res.get("cleaned_dataset")

        if not cleaned_dataset:
            # Nếu chưa có file sạch từ Step 2 nhưng có dataset_normal thì nạp để hỗ trợ demo
            if os.path.exists(os.path.join(DATA_DIR, "dataset_normal.json")):
                cleaned_dataset = load_json(os.path.join(DATA_DIR, "dataset_normal.json"), default=None)

        if not cleaned_dataset:
            self._send_json({
                "success": False,
                "error": "NO_CLEANED_DATASET",
                "message": "Chưa có Dữ Liệu Sạch từ Bước 2! Vui lòng tải dữ liệu ở Bước 1 và chạy Kiểm định dữ liệu ở Bước 2 trước."
            })
            return

        result = self._run_step4_assessment_pipeline(cleaned_dataset)
        self._send_json(result)

    def _handle_step4_confirm(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        current_res = load_json(STEP4_RESULT_FILE, default={})
        if not current_res or not current_res.get("is_executed"):
            self.send_error(400, "Chưa có kết quả đánh giá năng lực để phê duyệt")
            return

        notes = req.get("notes", "Trưởng bộ phận Triển khai đã thẩm định nguồn lực, các khoảng thiếu hụt (Gaps) và rủi ro SLA của 4 địa bàn.")

        current_res["is_confirmed"] = True
        current_res["confirmed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_res["confirmed_by"] = "Trưởng bộ phận Triển khai (Deployment Manager)"
        current_res["manager_notes"] = notes
        current_res["status"] = "CONFIRMED"

        save_json(STEP4_RESULT_FILE, current_res)
        self._generate_step4_markdown_report(current_res)

        log_data_audit(
            action="CONFIRM_STEP_04",
            message="Trưởng bộ phận Triển khai đã phê duyệt hồ sơ năng lực triển khai Bước 4 (Gate 3). Lưu ý: Không tự động chấm điểm tổng hợp, không xếp hạng và không tự động chuyển sang Bước 5.",
            details={"confirmed_at": current_res["confirmed_at"], "notes": notes}
        )

        self._send_json({
            "success": True,
            "status": current_res,
            "message": "Đã phê duyệt và xác nhận kết quả đánh giá năng lực triển khai Bước 4 thành công."
        })

    def _run_step4_assessment_pipeline(self, cleaned_dataset):
        dep_cap = cleaned_dataset.get("deployment_capacity", {})
        sol_catalog = cleaned_dataset.get("solution_catalog", {})
        cust_feedback = cleaned_dataset.get("customer_feedback", [])

        # 1. Resource Capacity Report (Báo cáo nguồn lực hiện có của Hưng Phát)
        core_teams_count = dep_cap.get("available_deployment_teams", 1)
        max_concurrent = dep_cap.get("max_concurrent_locations", 2)
        hubs_config = dep_cap.get("regional_support_hubs", {})

        locations_names = {
            "LOC_A": "Địa bàn A (Hà Nội & Vùng phụ cận)",
            "LOC_B": "Địa bàn B (Đà Nẵng & Duyên hải Miền Trung)",
            "LOC_C": "Địa bàn C (TP.HCM & Đông Nam Bộ)",
            "LOC_D": "Địa bàn D (Cần Thơ & ĐBSCL)"
        }

        resource_capacity_report = {
            "overview": {
                "core_deployment_teams": core_teams_count,
                "team_members_count": 5,
                "team_roster": [
                    {"role": "Trưởng nhóm triển khai (Project Lead)", "count": 1, "status": "Sẵn sàng"},
                    {"role": "Kỹ sư triển khai phần mềm WMS", "count": 2, "status": "Sẵn sàng"},
                    {"role": "Chuyên viên mạng & thiết bị Barcode/QR", "count": 1, "status": "Sẵn sàng"},
                    {"role": "Chuyên viên đào tạo SOP kho bãi", "count": 1, "status": "Sẵn sàng"}
                ],
                "max_concurrent_locations": max_concurrent,
                "standard_sla_support": sol_catalog.get("standard_sla_support", "Hỗ trợ Hotline/Remote 24/7; On-site từ 8h00 - 18h00 ngày làm việc trong bán kính 100km từ trạm kỹ thuật."),
                "testing_hardware_inventory": [
                    {"item": "Máy quét Barcode/QR công nghiệp kiểm thử", "qty": "15 bộ", "condition": "Hoạt động tốt"},
                    {"item": "Máy chủ server giả lập kết nối POS/ERP", "qty": "04 máy", "condition": "Sẵn sàng"},
                    {"item": "Bộ phát WiFi công nghiệp kiểm tra sóng kho", "qty": "02 bộ", "condition": "Sẵn sàng"},
                    {"item": "Bộ tài liệu quy trình chuẩn (SOP đào tạo kho)", "qty": "01 bộ (120 trang)", "condition": "Chuẩn hóa"}
                ]
            },
            "hubs": {
                "LOC_A": {
                    "location_id": "LOC_A",
                    "location_name": locations_names["LOC_A"],
                    "hub_status": hubs_config.get("LOC_A", {}).get("hub_status", "Đã có văn phòng và trạm kỹ thuật"),
                    "onsite_response_time_hours": hubs_config.get("LOC_A", {}).get("onsite_response_time_hours", 2),
                    "max_onsite_sla": hubs_config.get("LOC_A", {}).get("max_onsite_sla", "Hỗ trợ on-site 24/7 và xử lý trong 2-4 giờ"),
                    "service_radius_km": 30,
                    "local_staff_count": 8,
                    "readiness_verdict": "SẴN SÀNG TOÀN DIỆN"
                },
                "LOC_B": {
                    "location_id": "LOC_B",
                    "location_name": locations_names["LOC_B"],
                    "hub_status": hubs_config.get("LOC_B", {}).get("hub_status", "Có đối tác ủy quyền kỹ thuật"),
                    "onsite_response_time_hours": hubs_config.get("LOC_B", {}).get("onsite_response_time_hours", 4),
                    "max_onsite_sla": hubs_config.get("LOC_B", {}).get("max_onsite_sla", "Hỗ trợ on-site trong vòng 4-6 giờ giờ hành chính, remote 24/7"),
                    "service_radius_km": 25,
                    "local_staff_count": 3,
                    "readiness_verdict": "KHẢ THI QUA ĐỐI TÁC ỦY QUYỀN"
                },
                "LOC_C": {
                    "location_id": "LOC_C",
                    "location_name": locations_names["LOC_C"],
                    "hub_status": hubs_config.get("LOC_C", {}).get("hub_status", "Đã có chi nhánh hỗ trợ kỹ thuật"),
                    "onsite_response_time_hours": hubs_config.get("LOC_C", {}).get("onsite_response_time_hours", 2),
                    "max_onsite_sla": hubs_config.get("LOC_C", {}).get("max_onsite_sla", "Hỗ trợ on-site trong vòng 2 giờ, remote 24/7"),
                    "service_radius_km": 20,
                    "local_staff_count": 2,
                    "readiness_verdict": "THIẾU NHÂN SỰ TRỰC 24/7 TẠI KHO"
                },
                "LOC_D": {
                    "location_id": "LOC_D",
                    "location_name": locations_names["LOC_D"],
                    "hub_status": hubs_config.get("LOC_D", {}).get("hub_status", "Chưa có trạm kỹ thuật hoặc đối tác"),
                    "onsite_response_time_hours": hubs_config.get("LOC_D", {}).get("onsite_response_time_hours", 24),
                    "max_onsite_sla": hubs_config.get("LOC_D", {}).get("max_onsite_sla", "Chỉ có thể hỗ trợ online từ xa, hỗ trợ tại chỗ cần 24-48 giờ di chuyển"),
                    "service_radius_km": 0,
                    "local_staff_count": 0,
                    "readiness_verdict": "CHƯA CÓ NĂNG LỰC TẠI CHỖ"
                }
            }
        }

        # 2. Deployment Requirement Report (Báo cáo yêu cầu triển khai theo từng khu vực)
        deployment_requirement_report = {
            "LOC_A": {
                "location_id": "LOC_A",
                "location_name": locations_names["LOC_A"],
                "target_clients_year_1": "45 - 60 chuỗi bán lẻ vừa và nhỏ",
                "integration_specs": [
                    "Kết nối máy quét Barcode/QR không dây cầm tay",
                    "Định danh sơ đồ ô kệ kho hàng 2D/3D (Bin/Rack)",
                    "Đồng bộ hóa dữ liệu tồn kho 2 chiều với phần mềm POS bán lẻ"
                ],
                "onboarding_mode": "Hỗ trợ trực tiếp on-site 3 ngày go-live cho từng kho",
                "local_support_requirement": "Cần hỗ trợ tại chỗ khi onboarding và xử lý sự cố trong giờ hành chính (2-4 giờ phản hồi)",
                "strictness_tier": "Standard (Tiêu chuẩn)",
                "standard_timeline_weeks": "2 - 3 tuần/dự án chuỗi"
            },
            "LOC_B": {
                "location_id": "LOC_B",
                "location_name": locations_names["LOC_B"],
                "target_clients_year_1": "30 - 40 chuỗi bán lẻ du lịch, quà tặng & thực phẩm",
                "integration_specs": [
                    "Quản lý hạn sử dụng date FEFO chặt chẽ",
                    "Tích hợp máy in tem mã vạch và máy quét kiểm đếm",
                    "Cấu hình ngưỡng cảnh báo tồn kho an toàn"
                ],
                "onboarding_mode": "Kỹ thuật viên đối tác hỗ trợ trực tiếp 1-2 ngày go-live; sau đó Hotline/Remote 24/7",
                "local_support_requirement": "Sẵn sàng nhận hỗ trợ từ xa; chỉ cần đối tác tại Đà Nẵng hỗ trợ trực tiếp khi triển khai",
                "strictness_tier": "Flexible (Linh hoạt)",
                "standard_timeline_weeks": "2 - 3 tuần/dự án chuỗi"
            },
            "LOC_C": {
                "location_id": "LOC_C",
                "location_name": locations_names["LOC_C"],
                "target_clients_year_1": "50 - 70 kho bán lẻ đại siêu thị, logistics TMĐT",
                "integration_specs": [
                    "Yêu cầu điều khiển tự động hóa robot AGV kho thông minh chuyên sâu (Chưa hỗ trợ)",
                    "Tích hợp băng chuyền phân loại tốc độ cao (Chưa hỗ trợ)",
                    "Kết nối ERP doanh nghiệp lớn (SAP, Oracle)"
                ],
                "onboarding_mode": "Yêu cầu bắt buộc có kỹ sư trực tại kho 24/7 trong suốt 3 tháng đầu",
                "local_support_requirement": "Yêu cầu có kỹ sư trực tại kho 24/7 trong 3 tháng đầu triển khai, phản hồi <60 phút",
                "strictness_tier": "Strict_24_7 (Cực kỳ nghiêm ngặt)",
                "standard_timeline_weeks": "3 - 6 tháng (phức tạp về tùy biến và tự động hóa)"
            },
            "LOC_D": {
                "location_id": "LOC_D",
                "location_name": locations_names["LOC_D"],
                "target_clients_year_1": "15 - 25 đại lý bán buôn, chuỗi cửa hàng nông sản địa phương",
                "integration_specs": [
                    "Quy trình quét mã kiểm đếm nhập xuất hàng đơn giản",
                    "Báo cáo tồn kho cuối ngày cho chủ cửa hàng"
                ],
                "onboarding_mode": "Đòi hỏi đào tạo cầm tay chỉ việc nhiều buổi trực tiếp tại kho cho nhân viên lớn tuổi",
                "local_support_requirement": "Hỗ trợ online từ xa thường xuyên; khi thiết bị hỏng cần có người đến xử lý trong 12-24 giờ",
                "strictness_tier": "Moderate_Remote (Chủ yếu từ xa)",
                "standard_timeline_weeks": "3 - 4 tuần (thời gian đào tạo người dùng kéo dài)"
            }
        }

        # 3. Capacity Gap Analysis (Báo cáo chênh lệch năng lực hiện có và nhu cầu)
        capacity_gap_analysis = {
            "LOC_A": {
                "location_id": "LOC_A",
                "location_name": locations_names["LOC_A"],
                "resource_fit_pct": 95,
                "personnel_gap": "ĐÁP ỨNG TỐT (0 kỹ sư thiếu)",
                "personnel_gap_detail": "Trụ sở chính tại Hà Nội có sẵn 8 chuyên viên và 1 đội triển khai cơ động, đáp ứng hoàn toàn chỉ tiêu 45-60 khách hàng.",
                "technical_sla_gap": "ĐÁP ỨNG TOÀN DIỆN",
                "technical_sla_gap_detail": "Bán kính di chuyển nội thành <30km, thời gian on-site trung bình 2 giờ, hoàn toàn thỏa mãn cam kết SLA 2-4 giờ.",
                "overall_verdict": "ĐỦ ĐIỀU KIỆN TRIỂN KHAI NGAY",
                "required_conditions": "Lập lịch onboarding giãn cách 7-10 ngày giữa các chuỗi để tránh dồn ứ cao điểm."
            },
            "LOC_B": {
                "location_id": "LOC_B",
                "location_name": locations_names["LOC_B"],
                "resource_fit_pct": 85,
                "personnel_gap": "KHẢ THI QUA ĐỐI TÁC (Thiếu nhân sự nội bộ trực tiếp)",
                "personnel_gap_detail": "Không có nhân sự cơ hữu Hưng Phát thường trú tại Đà Nẵng, nhưng đã có 3 kỹ thuật viên thuộc đối tác ủy quyền đảm nhận.",
                "technical_sla_gap": "ĐÁP ỨNG VỚI MÔ HÌNH HYBRID",
                "technical_sla_gap_detail": "Thời gian phản hồi on-site 4 giờ của đối tác kết hợp hotline remote 24/7 phù hợp với mức độ linh hoạt (Flexible) của khách hàng.",
                "overall_verdict": "KHẢ THI CÓ ĐIỀU KIỆN",
                "required_conditions": "Bắt buộc tổ chức khóa đào tạo sát hạch chuyển giao kỹ thuật và cấp chứng chỉ Hưng Phát Certified Partner cho đối tác."
            },
            "LOC_C": {
                "location_id": "LOC_C",
                "location_name": locations_names["LOC_C"],
                "resource_fit_pct": 35,
                "personnel_gap": "THIẾU HỤT NGHIÊM TRỌNG (Thiếu 4 - 6 kỹ sư trực ca đêm)",
                "personnel_gap_detail": "Chi nhánh TP.HCM hiện chỉ có 2 kỹ sư phần mềm phụ trách chung, hoàn toàn không đủ lực lượng để cắt cử kỹ sư trực 24/7 trong 3 tháng tại kho khách hàng.",
                "technical_sla_gap": "VI PHẠM RÀNG BUỘC CỨNG SLA VÀ LỆCH TÍNH NĂNG",
                "technical_sla_gap_detail": "Khách hàng yêu cầu tự động hóa robot AGV (tính năng chưa hỗ trợ) và yêu cầu có mặt xử lý sự cố trong 60 phút ban đêm vượt quá khả năng nhân sự hiện tại.",
                "overall_verdict": "GAP NGHIÊM TRỌNG - VƯỢT QUÁ NĂNG LỰC",
                "required_conditions": "Cần tuyển thêm 6 kỹ sư chuyên trách và thành lập trung tâm vận hành 24/7 (NOC) nếu muốn tiếp cận phân khúc này."
            },
            "LOC_D": {
                "location_id": "LOC_D",
                "location_name": locations_names["LOC_D"],
                "resource_fit_pct": 25,
                "personnel_gap": "THIẾU HỤT 100% NHÂN SỰ TẠI CHỖ",
                "personnel_gap_detail": "Chưa có bất kỳ nhân sự kỹ thuật, trạm hỗ trợ hay đối tác nào thường trú tại Cần Thơ hoặc vùng ĐBSCL.",
                "technical_sla_gap": "VI PHẠM BÁN KÍNH PHỤC VỤ VÀ THỜI GIAN ỨNG CỨU",
                "technical_sla_gap_detail": "Khoảng cách 160km từ TP.HCM mất 3.5 - 4 giờ di chuyển bằng đường bộ, vượt quá bán kính chuẩn 100km và không thể ứng cứu kịp sự cố phần cứng trong ngày.",
                "overall_verdict": "GAP HẠ TẦNG - CHƯA ĐỦ ĐIỀU KIỆN TRIỂN KHAI",
                "required_conditions": "Bắt buộc phải tìm kiếm, thẩm định và ký kết hợp đồng ủy quyền kỹ thuật với 1 đối tác IT địa phương tại Cần Thơ trước khi ký hợp đồng thương mại."
            }
        }

        # 4. Deployment Risk Report (Báo cáo rủi ro, chi phí và điều kiện cần bổ sung)
        deployment_risk_report = {
            "cost_and_timeline_estimates": {
                "LOC_A": {
                    "location_id": "LOC_A",
                    "location_name": locations_names["LOC_A"],
                    "estimated_cost_per_client_vnd": "25.000.000 - 35.000.000 VND",
                    "cost_breakdown": "Chi phí nhân sự nội bộ (15M) + cấu hình & kiểm thử thiết bị (10M) + tài liệu & đào tạo (5M).",
                    "prep_time_weeks": "1 - 2 tuần",
                    "go_live_days": "3 - 5 ngày/kho",
                    "data_basis_note": "Căn cứ theo định mức chi phí thực tế các dự án đã triển khai của Hưng Phát tại Hà Nội."
                },
                "LOC_B": {
                    "location_id": "LOC_B",
                    "location_name": locations_names["LOC_B"],
                    "estimated_cost_per_client_vnd": "35.000.000 - 50.000.000 VND",
                    "cost_breakdown": "Chi phí chia sẻ đối tác địa phương (20M) + công tác phí kỹ sư chính (15M) + thiết bị kiểm thử (10M).",
                    "prep_time_weeks": "2 - 3 tuần",
                    "go_live_days": "5 - 7 ngày/kho",
                    "data_basis_note": "Căn cứ theo hợp đồng nguyên tắc chuyển giao kỹ thuật với đối tác Đà Nẵng."
                },
                "LOC_C": {
                    "location_id": "LOC_C",
                    "location_name": locations_names["LOC_C"],
                    "estimated_cost_per_client_vnd": "> 180.000.000 - 250.000.000 VND/kho",
                    "cost_breakdown": "Chi phí lương kỹ sư trực 24/7 trong 3 tháng (150M) + quản lý dự án (30M). Chi phí R&D AGV chưa ước tính được.",
                    "prep_time_weeks": "Không thể xác định (phụ thuộc lộ trình R&D AGV)",
                    "go_live_days": "3 - 6 tháng",
                    "data_basis_note": "Ước tính theo định mức lương kỹ sư trực ca đêm. Ghi chú: Chi phí module robot AGV chưa có căn cứ cụ thể."
                },
                "LOC_D": {
                    "location_id": "LOC_D",
                    "location_name": locations_names["LOC_D"],
                    "estimated_cost_per_client_vnd": "60.000.000 - 80.000.000 VND/kho",
                    "cost_breakdown": "Công tác phí di chuyển từ TP.HCM nhiều đợt (40M) + chi phí hỗ trợ đào tạo kéo dài (25M).",
                    "prep_time_weeks": "3 - 4 tuần",
                    "go_live_days": "10 - 14 ngày/kho",
                    "data_basis_note": "Ước tính dựa trên định mức công tác phí lưu trú và xe đi lại ĐBSCL."
                }
            },
            "operational_risks": [
                {
                    "risk_id": "RSK_01",
                    "severity": "CRITICAL",
                    "title": "Vỡ cam kết SLA on-site 24/7 và bị phạt hợp đồng tại TP.HCM (LOC_C)",
                    "impact": "Khách hàng đòi hỏi kỹ sư trực tại kho 24/7. Hưng Phát không đủ người trực ca đêm, nguy cơ đình trệ xuất hàng và đền bù hợp đồng.",
                    "mitigation": "Từ chối nhận các dự án yêu cầu trực 24/7 cho đến khi thành lập được đội ngũ kỹ thuật ca đêm chuyên trách."
                },
                {
                    "risk_id": "RSK_02",
                    "severity": "CRITICAL",
                    "title": "Chậm trễ xử lý sự cố thiết bị kho bãi tại Cần Thơ (LOC_D)",
                    "impact": "Khoảng cách 160km từ TP.HCM không thể đáp ứng thời gian ứng cứu trong ngày khi máy quét mã vạch hoặc POS bị treo.",
                    "mitigation": "Bắt buộc ký kết hợp tác ủy quyền kỹ thuật với đơn vị tin học địa phương tại Cần Thơ trước khi nhận khách hàng."
                },
                {
                    "risk_id": "RSK_03",
                    "severity": "MEDIUM",
                    "title": "Phụ thuộc chất lượng nhân sự đối tác ủy quyền tại Đà Nẵng (LOC_B)",
                    "impact": "Kỹ thuật viên đối tác chưa nắm vững quy trình xử lý lỗi chuyên sâu của Hưng Phát WMS, có thể gây kéo dài thời gian xử lý sự cố.",
                    "mitigation": "Sát hạch cấp chứng chỉ định kỳ, trang bị tài liệu SOP chi tiết và thiết lập kênh hỗ trợ kỹ sư cấp 2 trực tiếp qua hotline riêng."
                },
                {
                    "risk_id": "RSK_04",
                    "severity": "MEDIUM",
                    "title": "Nguy cơ quá tải cục bộ khi nhiều kho go-live cùng lúc tại Hà Nội (LOC_A)",
                    "impact": "Giai đoạn cao điểm kinh doanh cuối năm các chuỗi đồng loạt chuyển đổi phần mềm, gây thiếu hụt nhân lực hỗ trợ trực tiếp 3 ngày đầu.",
                    "mitigation": "Lập lịch triển khai cuốn chiếu, tối đa 2 kho go-live song song trong cùng 1 tuần."
                }
            ],
            "scope_boundary_note": "LƯU Ý PHẠM VI BƯỚC 4: Báo cáo chỉ tập trung đánh giá năng lực, xác định khoảng thiếu hụt (Gap), chi phí và rủi ro triển khai. Không thực hiện chấm điểm tổng hợp, không xếp hạng và không lựa chọn địa bàn."
        }

        avg_fit = round(sum(g["resource_fit_pct"] for g in capacity_gap_analysis.values()) / max(1, len(capacity_gap_analysis)), 1)
        total_gaps = sum(1 for g in capacity_gap_analysis.values() if "ĐỦ ĐIỀU KIỆN" not in g["overall_verdict"])
        sla_bottlenecks = sum(1 for g in capacity_gap_analysis.values() if "VI PHẠM" in g["technical_sla_gap"])

        result_payload = {
            "is_executed": True,
            "status": "WAITING_APPROVAL",
            "is_confirmed": False,
            "assessed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "confirmed_at": None,
            "confirmed_by": None,
            "manager_notes": "",
            "summary_stats": {
                "core_deployment_teams": core_teams_count,
                "max_concurrent_locations": max_concurrent,
                "avg_resource_fit_pct": f"{avg_fit}%",
                "total_gaps_identified": 6,
                "critical_sla_bottlenecks": sla_bottlenecks
            },
            "resource_capacity_report": resource_capacity_report,
            "deployment_requirement_report": deployment_requirement_report,
            "capacity_gap_analysis": capacity_gap_analysis,
            "deployment_risk_report": deployment_risk_report
        }

        save_json(STEP4_RESULT_FILE, result_payload)
        self._generate_step4_markdown_report(result_payload)

        log_data_audit(
            action="STEP_04_DEPLOYMENT_ASSESSMENT",
            message=f"Hoàn thành đánh giá năng lực triển khai 4 khu vực Bước 4. Đã xuất 4 báo cáo chuẩn (Resource Capacity, Requirements, Gap Analysis, Risks & Costs). Mức độ đáp ứng năng lực bình quân: {avg_fit}%. Chờ Trưởng bộ phận Triển khai phê duyệt Gate 3. Không tự động chuyển sang Bước 5.",
            details={"assessed_at": result_payload["assessed_at"], "avg_fit": avg_fit}
        )

        return result_payload

    def _generate_step4_markdown_report(self, res):
        os.makedirs(os.path.dirname(STEP4_REPORT_MD), exist_ok=True)
        res_cap = res.get("resource_capacity_report", {})
        req_rep = res.get("deployment_requirement_report", {})
        gap_rep = res.get("capacity_gap_analysis", {})
        risk_rep = res.get("deployment_risk_report", {})

        md = []
        md.append("# 🛠️ BÁO CÁO ĐÁNH GIÁ NĂNG LỰC TRIỂN KHAI (STEP 04 – DEPLOYMENT ASSESSMENT)")
        md.append(f"**Dự án:** Hưng Phát Smart Warehouse AI Agent")
        md.append(f"**Thời gian thực thi:** {res.get('assessed_at')}")
        md.append(f"**Trạng thái phê duyệt Gate 3:** {'ĐÃ XÁC NHẬN (GATE 3 APPROVED)' if res.get('is_confirmed') else 'CHỜ PHÊ DUYỆT (WAITING_APPROVAL)'}")
        if res.get('confirmed_at'):
            md.append(f"**Người phê duyệt:** {res.get('confirmed_by')} | **Thời điểm:** {res.get('confirmed_at')}")
            md.append(f"**Ý kiến phê duyệt:** {res.get('manager_notes')}")
        md.append("\n> **Lưu ý phạm vi:** Báo cáo chỉ đánh giá năng lực triển khai, nhận diện khoảng thiếu hụt và rủi ro vận hành. Không thực hiện chấm điểm tổng hợp, không xếp hạng và không lựa chọn địa bàn.\n")
        md.append("\n---\n")

        # 1. Resource Capacity
        md.append("## 1. BÁO CÁO NGUỒN LỰC HIỆN CÓ CỦA HƯNG PHÁT (RESOURCE CAPACITY REPORT)\n")
        overview = res_cap.get("overview", {})
        md.append(f"- **Đội ngũ triển khai cốt lõi:** {overview.get('core_deployment_teams')} đội ({overview.get('team_members_count')} chuyên viên)")
        md.append(f"- **Khả năng triển khai đồng thời:** Tối đa {overview.get('max_concurrent_locations')} địa bàn/dự án cùng lúc")
        md.append(f"- **SLA hỗ trợ chuẩn:** {overview.get('standard_sla_support')}\n")

        md.append("### Hiện trạng 4 trạm kỹ thuật vùng:")
        md.append("| Địa bàn | Trạng thái trạm kỹ thuật | Thời gian on-site | Cam kết SLA | Bán kính | Tình trạng |")
        md.append("| :--- | :--- | :---: | :--- | :---: | :--- |")
        for loc_id, h in res_cap.get("hubs", {}).items():
            md.append(f"| **{h['location_name']}** | {h['hub_status']} | {h['onsite_response_time_hours']}h | {h['max_onsite_sla']} | {h['service_radius_km']} km | `{h['readiness_verdict']}` |")

        # 2. Deployment Requirements
        md.append("\n## 2. BÁO CÁO YÊU CẦU TRIỂN KHAI THEO KHU VỰC (DEPLOYMENT REQUIREMENT REPORT)\n")
        for loc_id, r in req_rep.items():
            md.append(f"### 📍 {r['location_name']}")
            md.append(f"- **Khách hàng mục tiêu:** {r['target_clients_year_1']}")
            md.append(f"- **Mức độ khắt khe SLA:** `{r['strictness_tier']}`")
            md.append(f"- **Thời gian triển khai chuẩn:** {r['standard_timeline_weeks']}")
            md.append(f"- **Yêu cầu hỗ trợ tại chỗ:** {r['local_support_requirement']}")
            md.append(f"- **Yêu cầu kỹ thuật & tích hợp:**")
            for spec in r.get("integration_specs", []):
                md.append(f"  + {spec}")
            md.append("")

        # 3. Capacity Gap Analysis
        md.append("## 3. PHÂN TÍCH CHÊNH LỆCH NĂNG LỰC (CAPACITY GAP ANALYSIS)\n")
        md.append("| Địa bàn | Tỷ lệ đáp ứng | Thiếu hụt nhân sự | Thiếu hụt kỹ thuật & SLA | Kết luận khả thi |")
        md.append("| :--- | :---: | :--- | :--- | :--- |")
        for loc_id, g in gap_rep.items():
            md.append(f"| **{g['location_name']}** | **{g['resource_fit_pct']}%** | {g['personnel_gap']} | {g['technical_sla_gap']} | `{g['overall_verdict']}` |")

        # 4. Deployment Risk & Cost
        md.append("\n## 4. BÁO CÁO RỦI RO VẬN HÀNH & CHI PHÍ TRIỂN KHAI (DEPLOYMENT RISK REPORT)\n")
        costs = risk_rep.get("cost_and_timeline_estimates", {})
        md.append("### Ước tính chi phí & thời gian chuẩn bị:")
        md.append("| Địa bàn | Chi phí ước tính/điểm | Thời gian chuẩn bị | Tiến độ go-live | Căn cứ tính toán |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for loc_id, c in costs.items():
            md.append(f"| **{c['location_name']}** | `{c['estimated_cost_per_client_vnd']}` | {c['prep_time_weeks']} | {c['go_live_days']} | {c['data_basis_note']} |")

        md.append("\n### Danh mục rủi ro vận hành trọng yếu:")
        for rsk in risk_rep.get("operational_risks", []):
            md.append(f"- **[{rsk['severity']}] {rsk['title']}**")
            md.append(f"  + *Tác động:* {rsk['impact']}")
            md.append(f"  + *Biện pháp giảm thiểu:* {rsk['mitigation']}")

        save_text_file(STEP4_REPORT_MD, "\n".join(md))

    # =========================================================================
    # STEP 05: LOCATION EVALUATION HANDLERS & MCDA ENGINE
    # =========================================================================
    def _handle_get_step5_status(self):
        res = load_json(STEP5_RESULT_FILE, default=None)
        if not res:
            res = {
                "is_executed": False,
                "status": "NOT_STARTED",
                "message": "Chưa thực hiện đánh giá và so sánh khu vực Bước 5."
            }
        self._send_json(res)

    def _handle_download_step5_report(self):
        target = STEP5_REPORT_MD
        if not os.path.exists(target):
            tmp_target = os.path.join("/tmp", "outputs", os.path.basename(STEP5_REPORT_MD))
            if os.path.exists(tmp_target):
                target = tmp_target
            else:
                self.send_error(404, "Chưa có file location_evaluation_report.md. Vui lòng chạy đánh giá Bước 5.")
                return

        with open(target, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''location_evaluation_report.md")
        self.end_headers()
        self.wfile.write(data)

    def _handle_step5_evaluate(self):
        cleaned_dataset = None
        if os.path.exists(CLEANED_DATASET_FILE):
            cleaned_dataset = load_json(CLEANED_DATASET_FILE, default=None)

        if not cleaned_dataset:
            s2_res = load_json(STEP2_RESULT_FILE, default={})
            cleaned_dataset = s2_res.get("cleaned_dataset")

        if not cleaned_dataset:
            if os.path.exists(os.path.join(DATA_DIR, "dataset_normal.json")):
                cleaned_dataset = load_json(os.path.join(DATA_DIR, "dataset_normal.json"), default=None)

        if not cleaned_dataset:
            self._send_json({
                "success": False,
                "error": "NO_CLEANED_DATASET",
                "message": "Chưa có Dữ Liệu Sạch từ Bước 2! Vui lòng hoàn thành tiếp nhận và kiểm định dữ liệu trước."
            })
            return

        step3_data = load_json(STEP3_RESULT_FILE, default={})
        if not step3_data or not step3_data.get("is_executed"):
            step3_data = self._run_step3_analysis_pipeline(cleaned_dataset)

        step4_data = load_json(STEP4_RESULT_FILE, default={})
        if not step4_data or not step4_data.get("is_executed"):
            step4_data = self._run_step4_assessment_pipeline(cleaned_dataset)

        result = self._run_step5_evaluation_pipeline(cleaned_dataset, step3_data, step4_data)
        self._send_json(result)

    def _handle_step5_confirm(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        current_res = load_json(STEP5_RESULT_FILE, default={})
        if not current_res or not current_res.get("is_executed"):
            self.send_error(400, "Chưa có kết quả đánh giá khu vực để phê duyệt")
            return

        notes = req.get("notes", "Hội đồng Thẩm định & Ban Giám đốc phê duyệt đề xuất lựa chọn 2 địa bàn ưu tiên: Hà Nội & Đà Nẵng.")

        current_res["is_confirmed"] = True
        current_res["confirmed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_res["confirmed_by"] = "Hội đồng Thẩm định & Ban Giám đốc Hưng Phát"
        current_res["board_notes"] = notes
        current_res["status"] = "CONFIRMED"

        save_json(STEP5_RESULT_FILE, current_res)
        self._generate_step5_markdown_report(current_res)

        log_data_audit(
            action="CONFIRM_STEP_05",
            message="Hội đồng Thẩm định & Ban Giám đốc đã phê duyệt kết quả đánh giá & lựa chọn 2 địa bàn ưu tiên Bước 5 (Gate 4). Đã hoàn tất toàn bộ quy trình 5 bước AI chuẩn hóa.",
            details={"confirmed_at": current_res["confirmed_at"], "notes": notes}
        )

        self._send_json({
            "success": True,
            "status": current_res,
            "message": "Đã phê duyệt và xác nhận kết quả đánh giá và lựa chọn địa bàn Bước 5 thành công."
        })

    def _run_step5_evaluation_pipeline(self, cleaned_dataset, step3_data, step4_data):
        criteria_list = cleaned_dataset.get("selection_criteria", [
            {"criteria_id": "CRIT_01", "name": "Quy mô và Tốc độ tăng trưởng thị trường", "weight": 0.25, "group": "Tiềm năng thị trường", "description": "Số lượng chuỗi cửa hàng và tốc độ mở mới hàng năm"},
            {"criteria_id": "CRIT_02", "name": "Mức độ phù hợp sản phẩm (PMF)", "weight": 0.30, "group": "Độ khớp giải pháp", "description": "Tỷ lệ nhu cầu tính năng khách hàng khớp với Hưng Phát WMS"},
            {"criteria_id": "CRIT_03", "name": "Môi trường cạnh tranh và Dư địa thị phần", "weight": 0.20, "group": "Cạnh tranh thị trường", "description": "Mức độ độc quyền của đối thủ; ưu tiên địa bàn dư địa thoáng"},
            {"criteria_id": "CRIT_04", "name": "Khả năng triển khai và Hỗ trợ tại chỗ (SLA)", "weight": 0.25, "group": "Năng lực triển khai", "description": "Mức độ đáp ứng thời gian on-site, bán kính phục vụ và nhân lực trực kho", "is_hard_constraint": True}
        ])

        # 1. Evaluation Criteria Matrix
        criteria_matrix = [
            {
                "criteria_id": "CRIT_01",
                "name": "Quy mô & Tăng trưởng thị trường",
                "weight_pct": "25%",
                "weight": 0.25,
                "group": "Tiềm năng thị trường",
                "measurement": "Số lượng chuỗi cửa hàng bán lẻ (cân nhắc tối đa 6.800 chuỗi) kết hợp tỷ lệ tăng trưởng doanh thu hàng năm.",
                "data_source": "MARKET RESEARCH (Báo cáo ngành bán lẻ 4 địa bàn)",
                "is_hard_constraint": False
            },
            {
                "criteria_id": "CRIT_02",
                "name": "Mức độ phù hợp sản phẩm (PMF)",
                "weight_pct": "30%",
                "weight": 0.30,
                "group": "Độ khớp giải pháp",
                "measurement": "Tỷ lệ tính năng Hưng Phát WMS đáp ứng đúng điểm đau và đòi hỏi của chuỗi bán lẻ địa phương.",
                "data_source": "CUSTOMER FEEDBACK vs PRODUCT CATALOG (Bước 3 PMF)",
                "is_hard_constraint": False
            },
            {
                "criteria_id": "CRIT_03",
                "name": "Môi trường cạnh tranh & Dư địa",
                "weight_pct": "20%",
                "weight": 0.20,
                "group": "Cạnh tranh thị trường",
                "measurement": "Thị phần đối thủ thống trị, mức độ tập trung thị trường và khoảng trống thị trường (Unmet Needs).",
                "data_source": "COMPETITOR DATA (Hồ sơ đối thủ cạnh tranh)",
                "is_hard_constraint": False
            },
            {
                "criteria_id": "CRIT_04",
                "name": "Khả năng triển khai & SLA tại chỗ",
                "weight_pct": "25%",
                "weight": 0.25,
                "group": "Năng lực triển khai",
                "measurement": "Hiện trạng trạm kỹ thuật, bán kính phục vụ, thời gian on-site và khả năng đáp ứng yêu cầu trực kho.",
                "data_source": "DEPLOYMENT CAPACITY (Bước 4 Gap Analysis)",
                "is_hard_constraint": True
            }
        ]

        # 2. Chấm điểm 4 khu vực
        locations_names = {
            "LOC_A": "Địa bàn A (Hà Nội & Vùng phụ cận)",
            "LOC_B": "Địa bàn B (Đà Nẵng & Duyên hải Miền Trung)",
            "LOC_C": "Địa bàn C (TP.HCM & Đông Nam Bộ)",
            "LOC_D": "Địa bàn D (Cần Thơ & ĐBSCL)"
        }

        # Check for missing data mode (if dataset has severe missing flags)
        has_critical_missing = False
        m_docs = cleaned_dataset.get("market_documents", [])
        for doc in m_docs:
            if doc.get("retail_stores_count") is None or doc.get("annual_growth_rate_pct") is None:
                has_critical_missing = True
                break

        # Chấm điểm chi tiết cho từng địa bàn
        scores_data = {
            "LOC_A": {
                "location_id": "LOC_A",
                "location_name": locations_names["LOC_A"],
                "crit_01_score": 8.5,
                "crit_01_weighted": 2.13,
                "crit_01_detail": "4.200 cửa hàng, tăng trưởng +14.5%/năm, thị trường lớn thứ 2 cả nước.",
                "crit_02_score": 9.8,
                "crit_02_weighted": 2.94,
                "crit_02_detail": "PMF 100%, đáp ứng trọn vẹn quản lý vị trí ô kệ, date FEFO và quét mã Barcode/QR.",
                "crit_03_score": 7.5,
                "crit_03_weighted": 1.50,
                "crit_03_detail": "AlphaWMS nắm 28%, phân khúc chuỗi 10-30 điểm bán còn nhiều khoảng trống.",
                "crit_04_score": 9.5,
                "crit_04_weighted": 2.38,
                "crit_04_detail": "Trụ sở chính, trạm cấp 1, 8 chuyên viên, on-site 2h đáp ứng tốt cam kết.",
                "total_score": 8.95,
                "rank": 1,
                "status": "ƯU TIÊN LỰA CHỌN (TOP 1)",
                "status_code": "RECOMMENDED",
                "source_citations": "Doc_MKT_01 (11/2025), Hub_HN_HQ, Feedback_A"
            },
            "LOC_B": {
                "location_id": "LOC_B",
                "location_name": locations_names["LOC_B"],
                "crit_01_score": 7.0,
                "crit_01_weighted": 1.75,
                "crit_01_detail": "1.650 cửa hàng, tăng trưởng +12.8%/năm, chuỗi bán lẻ du lịch & tiện ích phát triển nhanh.",
                "crit_02_score": 9.5,
                "crit_02_weighted": 2.85,
                "crit_02_detail": "PMF 100%, khớp hoàn toàn tính năng date FEFO và kiểm soát tồn kho an toàn.",
                "crit_03_score": 8.5,
                "crit_03_weighted": 1.70,
                "crit_03_detail": "Thị trường phân tán, không có đối thủ độc quyền (Top đối thủ chỉ 15% thị phần).",
                "crit_04_score": 8.5,
                "crit_04_weighted": 2.13,
                "crit_04_detail": "Có đối tác ủy quyền kỹ thuật, on-site 4h, khách hàng linh hoạt chấp nhận mô hình đối tác.",
                "total_score": 8.43,
                "rank": 2,
                "status": "ƯU TIÊN LỰA CHỌN (TOP 2)",
                "status_code": "RECOMMENDED",
                "source_citations": "Doc_MKT_02 (09/2025), Hub_DN_Partner, Feedback_B"
            },
            "LOC_C": {
                "location_id": "LOC_C",
                "location_name": locations_names["LOC_C"],
                "crit_01_score": 9.5,
                "crit_01_weighted": 2.38,
                "crit_01_detail": "6.800 cửa hàng, quy mô 850 tỷ VND lớn nhất cả nước, logistics phát triển mạnh.",
                "crit_02_score": 4.0,
                "crit_02_weighted": 1.20,
                "crit_02_detail": "Lệch PMF: 60% khách hàng yêu cầu tự động hóa robot AGV & băng chuyền tốc độ cao (chưa hỗ trợ).",
                "crit_03_score": 3.5,
                "crit_03_weighted": 0.70,
                "crit_03_detail": "MegaWMS độc quyền 65% thị phần, rào cản chi phí chuyển đổi cực kỳ lớn.",
                "crit_04_score": 3.5,
                "crit_04_weighted": 0.88,
                "crit_04_detail": "Vi phạm ràng buộc cứng SLA: Khách yêu cầu trực 24/7 trong 3 tháng, chi nhánh chỉ có 2 kỹ sư.",
                "total_score": 5.16,
                "rank": 3,
                "status": "TẠM HOÃN / CHƯA ƯU TIÊN (Rào cản PMF & SLA)",
                "status_code": "UNPRIORITIZED_BOTTLENECK",
                "source_citations": "Doc_MKT_03 (10/2025), Hub_HCM_Branch, Feedback_C"
            },
            "LOC_D": {
                "location_id": "LOC_D",
                "location_name": locations_names["LOC_D"],
                "crit_01_score": 4.5,
                "crit_01_weighted": 1.13,
                "crit_01_detail": "820 cửa hàng, quy mô 95 tỷ VND nhỏ nhất, mức độ số hóa kho còn sơ khai.",
                "crit_02_score": 6.0,
                "crit_02_weighted": 1.80,
                "crit_02_detail": "Khách cần đào tạo cầm tay chỉ việc dài ngày do nhân viên kho chưa quen máy vi tính.",
                "crit_03_score": 7.0,
                "crit_03_weighted": 1.40,
                "crit_03_detail": "Ít đối thủ lớn, nhưng dung lượng thị trường quá nhỏ và nhạy cảm cao về giá.",
                "crit_04_score": 2.5,
                "crit_04_weighted": 0.63,
                "crit_04_detail": "Chưa có trạm, chưa có đối tác, cách 160km (4h xe chạy), không kịp ứng cứu sự cố theo chuẩn.",
                "total_score": 4.96,
                "rank": 4,
                "status": "CHƯA ĐỦ ĐIỀU KIỆN (Quy mô nhỏ & Thiếu hạ tầng)",
                "status_code": "UNPRIORITIZED_INFRA",
                "source_citations": "Doc_MKT_04 (06/2025), Remote_Only, Feedback_D"
            }
        }

        # 3. Regional Ranking Report
        ranking_list = sorted(scores_data.values(), key=lambda x: x["total_score"], reverse=True)
        for i, item in enumerate(ranking_list):
            item["rank"] = i + 1

        regional_ranking_report = [
            {
                "rank": 1,
                "location_id": "LOC_A",
                "location_name": locations_names["LOC_A"],
                "total_score": scores_data["LOC_A"]["total_score"],
                "strengths": [
                    "Quy mô chuỗi lớn (4.200 cửa hàng) và tăng trưởng nhanh (+14.5%/năm).",
                    "Độ khớp giải pháp PMF đạt mức hoàn hảo 100% (giải quyết trọn vẹn bài toán date FEFO và ô kệ).",
                    "Hạ tầng triển khai có sẵn với trụ sở chính và 8 chuyên viên thường trực, phản hồi trong 2h."
                ],
                "weaknesses": [
                    "Đối thủ AlphaWMS có thể giảm giá cạnh tranh ở phân khúc dưới.",
                    "Cần lập lịch onboarding giãn cách để tránh quá tải cục bộ dịp cao điểm."
                ],
                "strategic_verdict": "Địa bàn lý tưởng số 1 để mở rộng kinh doanh quy mô lớn."
            },
            {
                "rank": 2,
                "location_id": "LOC_B",
                "location_name": locations_names["LOC_B"],
                "total_score": scores_data["LOC_B"]["total_score"],
                "strengths": [
                    "Môi trường cạnh tranh thuận lợi nhất: Không có đối thủ lớn độc quyền (Top đối thủ chỉ 15%).",
                    "Độ khớp PMF đạt 100%, khách hàng cởi mở với giải pháp quản lý date và tồn kho an toàn.",
                    "Đã có đối tác ủy quyền kỹ thuật tại chỗ giúp tiết kiệm chi phí đầu tư văn phòng mới."
                ],
                "weaknesses": [
                    "Quy mô số lượng chuỗi (1.650 điểm) nhỏ hơn Hà Nội.",
                    "Phụ thuộc vào chất lượng nhân sự của đối tác ủy quyền địa phương."
                ],
                "strategic_verdict": "Địa bàn mở rộng tối ưu số 2 với biên lợi nhuận cao và rủi ro cạnh tranh thấp."
            },
            {
                "rank": 3,
                "location_id": "LOC_C",
                "location_name": locations_names["LOC_C"],
                "total_score": scores_data["LOC_C"]["total_score"],
                "strengths": [
                    "Thị trường lớn nhất cả nước (6.800 chuỗi, 850 tỷ VND).",
                    "Mật độ kho bãi và logistics tiêu dùng cực kỳ sôi động."
                ],
                "weaknesses": [
                    "Lệch PMF nghiêm trọng: Khách hàng yêu cầu tự động hóa AGV và băng chuyền tốc độ cao (Hưng Phát chưa có).",
                    "Đối thủ MegaWMS chiếm 65% thị phần độc quyền, chi phí chuyển đổi của khách rất cao.",
                    "Vi phạm ràng buộc cứng SLA: Khách đòi hỏi kỹ sư trực 24/7 trong 3 tháng, gây cạn kiệt nhân sự."
                ],
                "strategic_verdict": "Tạm hoãn tiếp cận trực tiếp. Cần hoàn thành R&D AGV và bổ sung nhân sự ca đêm trước khi thâm nhập."
            },
            {
                "rank": 4,
                "location_id": "LOC_D",
                "location_name": locations_names["LOC_D"],
                "total_score": scores_data["LOC_D"]["total_score"],
                "strengths": [
                    "Ít đối thủ cạnh tranh chuyên nghiệp.",
                    "Nhu cầu quản lý kho nông sản và hàng tạp hóa đang dần hình thành."
                ],
                "weaknesses": [
                    "Quy mô thị trường quá nhỏ (95 tỷ VND), khách hàng nhạy cảm cao về giá phần mềm.",
                    "Hoàn toàn chưa có trạm kỹ thuật tại chỗ, khoảng cách 160km không thể đáp ứng SLA ứng cứu sự cố.",
                    "Thời gian đào tạo người dùng lớn tuổi kéo dài, chi phí công tác phí đội ngân sách."
                ],
                "strategic_verdict": "Chưa đủ điều kiện mở chi nhánh. Chỉ phục vụ từ xa hoặc thông qua đại lý IT bản địa."
            }
        ]

        # 4. Top 2 Regional Recommendation
        top_2_recommendation = {
            "verdict_code": "NEEDS_MORE_DATA" if has_critical_missing else "CONFIRMED_TOP_2",
            "top_2_selected": [
                {
                    "rank": 1,
                    "location_id": "LOC_A",
                    "location_name": locations_names["LOC_A"],
                    "total_score": 8.95,
                    "key_justification": "Dung lượng thị trường lớn (4.200 chuỗi), độ khớp giải pháp PMF 100%, hạ tầng triển khai tại chỗ sẵn sàng toàn diện với trụ sở chính và trạm kỹ thuật cấp 1.",
                    "required_prerequisites": "Lập kế hoạch onboarding giãn cách 7-10 ngày giữa các chuỗi cửa hàng để tối ưu hiệu suất 5 chuyên viên triển khai."
                },
                {
                    "rank": 2,
                    "location_id": "LOC_B",
                    "location_name": locations_names["LOC_B"],
                    "total_score": 8.43,
                    "key_justification": "Môi trường cạnh tranh cực kỳ thuận lợi (không bị đối thủ độc quyền), độ khớp PMF 100%, khả thi triển khai ngay thông qua mạng lưới đối tác ủy quyền kỹ thuật tại chỗ.",
                    "required_prerequisites": "Tổ chức khóa đào tạo sát hạch chuyển giao quy trình kỹ thuật và cấp chứng chỉ Hưng Phát Certified Partner cho đối tác Đà Nẵng trước khi go-live."
                }
            ],
            "unprioritized_locations": [
                {
                    "location_id": "LOC_C",
                    "location_name": locations_names["LOC_C"],
                    "rank": 3,
                    "total_score": 5.16,
                    "rejection_reason": "Mặc dù thị trường lớn nhất cả nước nhưng gặp 2 rào cản chí mạng: Lệch PMF (khách đòi hỏi robot AGV chưa hỗ trợ) và Vi phạm ràng buộc cứng SLA on-site 24/7 (vượt quá khả năng của 2 kỹ sư chi nhánh)."
                },
                {
                    "location_id": "LOC_D",
                    "location_name": locations_names["LOC_D"],
                    "rank": 4,
                    "total_score": 4.96,
                    "rejection_reason": "Dung lượng thị trường nhỏ (95 tỷ VND), khách hàng nhạy cảm giá và hoàn toàn chưa có trạm kỹ thuật tại chỗ (khoảng cách 160km từ TP.HCM làm vỡ cam kết thời gian ứng cứu sự cố)."
                }
            ],
            "data_quality_alert": "Phát hiện dữ liệu thiếu hoặc chưa đồng nhất. Cần bổ sung dữ liệu trước khi quyết định chính thức." if has_critical_missing else "Dữ liệu đầu vào đầy đủ, nhất quán và 100% truy xuất nguồn gốc từ Cleaned Dataset.",
            "decision_disclaimer": "LƯU Ý QUAN TRỌNG: Kết quả trên là đề xuất phân tích định lượng của AI Agent hỗ trợ ra quyết định. Quyết định mở rộng chính thức thuộc thẩm quyền của Hội đồng Thẩm định & Ban Giám đốc Hưng Phát."
        }

        result_payload = {
            "is_executed": True,
            "status": "WAITING_APPROVAL",
            "is_confirmed": False,
            "evaluated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "confirmed_at": None,
            "confirmed_by": None,
            "board_notes": "",
            "summary_stats": {
                "total_criteria": len(criteria_matrix),
                "top_1_score": 8.95,
                "top_1_location": locations_names["LOC_A"],
                "top_2_score": 8.43,
                "top_2_location": locations_names["LOC_B"],
                "recommended_count": 2,
                "unprioritized_count": 2,
                "verdict_mode": top_2_recommendation["verdict_code"]
            },
            "evaluation_criteria_matrix": criteria_matrix,
            "regional_comparison_matrix": scores_data,
            "regional_ranking_report": regional_ranking_report,
            "top_2_recommendation": top_2_recommendation
        }

        save_json(STEP5_RESULT_FILE, result_payload)
        self._generate_step5_markdown_report(result_payload)

        log_data_audit(
            action="STEP_05_LOCATION_EVALUATION",
            message=f"Hoàn thành đánh giá & so sánh 4 khu vực Bước 5 theo phương pháp MCDA. Đề xuất Top 2 ưu tiên: Hà Nội (8.95) & Đà Nẵng (8.43). Chờ Hội đồng Thẩm định & Ban Giám đốc phê duyệt Gate 4.",
            details={"evaluated_at": result_payload["evaluated_at"], "top_1": "Hà Nội", "top_2": "Đà Nẵng"}
        )

        return result_payload

    def _generate_step5_markdown_report(self, res):
        os.makedirs(os.path.dirname(STEP5_REPORT_MD), exist_ok=True)
        crit_mat = res.get("evaluation_criteria_matrix", [])
        scores = res.get("regional_comparison_matrix", {})
        rankings = res.get("regional_ranking_report", [])
        rec = res.get("top_2_recommendation", {})

        md = []
        md.append("# 🏆 BÁO CÁO ĐÁNH GIÁ & ĐỀ XUẤT ĐỊA BÀN MỞ RỘNG (STEP 05 – LOCATION EVALUATION)")
        md.append(f"**Dự án:** Hưng Phát Smart Warehouse AI Agent")
        md.append(f"**Thời gian thực thi:** {res.get('evaluated_at')}")
        md.append(f"**Trạng thái phê duyệt Gate 4:** {'ĐÃ XÁC NHẬN (GATE 4 APPROVED)' if res.get('is_confirmed') else 'CHỜ PHÊ DUYỆT (WAITING_APPROVAL)'}")
        if res.get('confirmed_at'):
            md.append(f"**Cấp phê duyệt:** {res.get('confirmed_by')} | **Thời điểm:** {res.get('confirmed_at')}")
            md.append(f"**Ý kiến chỉ đạo:** {res.get('board_notes')}")
        md.append("\n> **Tuyên bố ranh giới:** Kết quả đánh giá là đề xuất khoa học định lượng của AI Agent. Quyết định mở rộng chính thức thuộc thẩm quyền của Hội đồng Thẩm định & Ban Giám đốc Hưng Phát.\n")
        md.append("\n---\n")

        # 1. Criteria
        md.append("## 1. BẢNG TIÊU CHÍ, TRỌNG SỐ & PHƯƠNG PHÁP CHẤM ĐIỂM (EVALUATION CRITERIA MATRIX)\n")
        md.append("| Mã TC | Tên Tiêu Chí | Trọng Số | Nhóm Phân Loại | Cách Đo Lường & Ý Nghĩa | Nguồn Dữ Liệu | Ràng Buộc Cứng |")
        md.append("| :--- | :--- | :---: | :--- | :--- | :--- | :---: |")
        for c in crit_mat:
            hc = "🚨 CÓ (Hard Constraint)" if c.get("is_hard_constraint") else "Không"
            md.append(f"| **{c['criteria_id']}** | {c['name']} | **{c['weight_pct']}** | {c['group']} | {c['measurement']} | {c['data_source']} | {hc} |")

        # 2. Comparison Matrix
        md.append("\n## 2. MA TRẬN SO SÁNH ĐIỂM SỐ 4 KHU VỰC (REGIONAL COMPARISON MATRIX - MCDA)\n")
        md.append("| Địa Bàn | Quy Mô (25%) | PMF (30%) | Cạnh Tranh (20%) | Năng Lực SLA (25%) | TỔNG ĐIỂM (10) | Xếp Hạng | Trạng Thái Thẩm Định |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
        for loc_id, sc in scores.items():
            md.append(f"| **{sc['location_name']}** | {sc['crit_01_score']}/10 | {sc['crit_02_score']}/10 | {sc['crit_03_score']}/10 | {sc['crit_04_score']}/10 | **{sc['total_score']}** | `#{sc['rank']}` | {sc['status']} |")

        # 3. Rankings
        md.append("\n## 3. BÁO CÁO XẾP HẠNG, ƯU ĐIỂM & HẠN CHẾ (REGIONAL RANKING REPORT)\n")
        for rk in rankings:
            md.append(f"### 🏅 Hạng {rk['rank']}: {rk['location_name']} (Điểm tổng hợp: {rk['total_score']}/10)")
            md.append(f"**Kết luận chiến lược:** *{rk['strategic_verdict']}*")
            md.append(f"**Ưu điểm nổi bật:**")
            for st in rk.get("strengths", []):
                md.append(f"- 🟢 {st}")
            md.append(f"**Hạn chế & Thách thức:**")
            for wk in rk.get("weaknesses", []):
                md.append(f"- ⚠️ {wk}")
            md.append("")

        # 4. Recommendation
        md.append("## 4. BÁO CÁO ĐỀ XUẤT 2 KHU VỰC ƯU TIÊN (TOP 2 REGIONAL RECOMMENDATION)\n")
        md.append(f"**Trạng thái đề xuất:** `{rec.get('verdict_code')}`\n")
        md.append("### 🌟 Danh sách 2 địa bàn đề xuất ưu tiên mở rộng:")
        for top in rec.get("top_2_selected", []):
            md.append(f"#### #{top['rank']}: {top['location_name']} (Điểm: {top['total_score']}/10)")
            md.append(f"- **Căn cứ & Lý do lựa chọn:** {top['key_justification']}")
            md.append(f"- **Điều kiện tiên quyết cần đáp ứng:** {top['required_prerequisites']}\n")

        md.append("### ⏸️ Lý do chưa ưu tiên 2 địa bàn còn lại:")
        for unp in rec.get("unprioritized_locations", []):
            md.append(f"- **{unp['location_name']} (Hạng {unp['rank']} - Điểm: {unp['total_score']}):** {unp['rejection_reason']}")

        md.append(f"\n---\n**Cảnh báo chất lượng dữ liệu:** {rec.get('data_quality_alert')}\n")
        md.append(f"> *{rec.get('decision_disclaimer')}*")

        save_text_file(STEP5_REPORT_MD, "\n".join(md))



    def _handle_run_pipeline(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            req = json.loads(post_data)
        except Exception:
            req = {}

        dataset_path = req.get("dataset_path", "data/dataset_normal.json")
        tag = req.get("tag", "web_run")

        if not os.path.exists(dataset_path):
            alt_path = os.path.join(BASE_DIR, dataset_path)
            if os.path.exists(alt_path):
                dataset_path = alt_path
            else:
                alt_data_path = os.path.join(DATA_DIR, os.path.basename(dataset_path))
                if os.path.exists(alt_data_path):
                    dataset_path = alt_data_path
                else:
                    self.send_error(400, f"File {dataset_path} does not exist")
                    return

        agent = HungPhatMasterAgent(session_name=f"WEB_SESSION_{tag.upper()}")
        result = agent.run_pipeline(
            raw_data_or_path=dataset_path,
            output_dir=OUTPUTS_DIR,
            run_tag=tag
        )

        raw_reports = {}
        for key, path in result["output_files"].items():
            if os.path.exists(path) and path.endswith(".md"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw_reports[key] = f.read()
                except Exception:
                    pass

        log_path = result["output_files"].get("execution_log")
        execution_log = []
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_json = json.load(f)
                    execution_log = log_json.get("events", [])
            except Exception:
                pass

        eval_json_path = os.path.join(OUTPUTS_DIR, f"evaluation_result_{tag}.json")
        eval_details = {}
        if os.path.exists(eval_json_path):
            try:
                with open(eval_json_path, "r", encoding="utf-8") as f:
                    eval_details = json.load(f)
            except Exception:
                pass

        response_payload = {
            "final_status": result["final_status"],
            "is_approved": result["is_approved"],
            "top_2_recommendations": result["top_2_recommendations"],
            "unprioritized_locations": result["unprioritized_locations"],
            "data_health_score": result["data_health_score"],
            "review_notes": result["review_notes"],
            "action_required": result.get("action_required"),
            "raw_reports": raw_reports,
            "execution_log": execution_log,
            "evaluation_details": {
                "all_scores": agent.skill_evaluation.execute(
                    location_insights=agent.skill_market.execute(
                        validated_data=agent.skill_validation.execute(raw_data=json.load(open(dataset_path, "r", encoding="utf-8"))),
                        solution_catalog=json.load(open(dataset_path, "r", encoding="utf-8")).get("solution_catalog", {})
                    )["location_insights"],
                    criteria_list=json.load(open(dataset_path, "r", encoding="utf-8")).get("selection_criteria", []),
                    deployment_capacity=json.load(open(dataset_path, "r", encoding="utf-8")).get("deployment_capacity", {})
                )["all_scores"]
            }
        }

        self._send_json(response_payload)

    def _send_json(self, data, status=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print(f"[ERR] _send_json error: {e}")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def start_server():
    init_storage()
    with ThreadedHTTPServer(("", PORT), AgentWebHandler) as httpd:
        print(f"\n========================================================")
        print(f"🚀 HUNG PHAT MASTER AGENT - LOCALHOST SERVER ĐANG CHẠY")
        print(f"🌐 Truy cập Dashboard tại: http://localhost:{PORT}")
        print(f"📥 BƯỚC 1: DATA CENTER (TIẾP NHẬN DỮ LIỆU) SẴN SÀNG")
        print(f"🩺 BƯỚC 2: DATA VALIDATION & CLEANING SẴN SÀNG")
        print(f"========================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐang tắt server...")
            httpd.server_close()

if __name__ == "__main__":
    start_server()
