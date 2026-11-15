import os
import sys

# Entrypoint cho Vercel / Cloud Serverless & Local Execution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app_server import AgentWebHandler as handler, init_storage, start_server

# Khởi tạo lưu trữ dữ liệu
init_storage()

if __name__ == '__main__':
    start_server()
