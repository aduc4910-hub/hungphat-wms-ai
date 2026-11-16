import os
import sys
import json
import traceback

# 1. Tự động thêm toàn bộ các đường dẫn gốc có thể chứa app_server và src vào sys.path
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_ROOT_DIR = os.path.dirname(CURRENT_FILE_DIR)

for search_dir in [PARENT_ROOT_DIR, CURRENT_FILE_DIR, "/var/task", "/var/task/api", os.getcwd()]:
    if search_dir and os.path.exists(search_dir) and search_dir not in sys.path:
        sys.path.insert(0, search_dir)

# 2. Khởi tạo app_server hoặc Fallback Handler để bảo đảm không bao giờ sập container
try:
    import app_server
    app_server.init_storage()
    BaseHandler = app_server.AgentWebHandler
except Exception as startup_err:
    trace_err = traceback.format_exc()
    print(f"[VERCEL_STARTUP_EXCEPTION] {trace_err}")

    from http.server import BaseHTTPRequestHandler
    class FallbackHandler(BaseHTTPRequestHandler):
        def _send_fail_json(self):
            try:
                cl = int(self.headers.get('Content-Length', 0) or 0)
                if cl > 0:
                    self.rfile.read(cl)
            except Exception:
                pass

            body = json.dumps({
                "success": False,
                "error": "SERVER_STARTUP_ERROR",
                "message": f"Không thể tải module backend: {str(startup_err)}",
                "traceback": trace_err,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "cwd_files": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else []
            }, ensure_ascii=False).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._send_fail_json()

        def do_POST(self):
            self._send_fail_json()

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.send_header('Content-Length', '0')
            self.end_headers()

    BaseHandler = FallbackHandler

# Handler chuẩn cho Vercel Serverless Function
class handler(BaseHandler):
    """
    Vercel Python Serverless Function Entrypoint
    Kế thừa trực tiếp từ AgentWebHandler để xử lý tất cả API endpoints:
    /api/datasets, /api/data-groups, /api/data-inventory, /api/upload, /api/confirm-input, /api/step2/...
    """
    pass
