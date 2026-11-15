import os
import sys

# Đảm bảo thư mục gốc dự án nằm trong sys.path để import app_server và src
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import app_server

# Tự động khởi tạo cấu trúc dữ liệu (/tmp trên Vercel)
app_server.init_storage()

# Handler chuẩn cho Vercel Serverless Function
class handler(app_server.AgentWebHandler):
    """
    Vercel Python Serverless Function Entrypoint
    Kế thừa trực tiếp từ AgentWebHandler để xử lý tất cả API endpoints:
    /api/datasets, /api/data-groups, /api/data-inventory, /api/run, /api/step2/...
    """
    pass
