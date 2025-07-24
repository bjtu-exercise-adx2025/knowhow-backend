# Gunicorn 配置文件
import multiprocessing
import os

# 服务器配置
bind = "0.0.0.0:8888"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# 超时配置
timeout = 120  # 增加超时时间到 120 秒
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程配置
preload_app = True
daemon = False

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 工作进程配置
worker_connections = 1000

# 临时目录配置 - 根据操作系统选择合适的临时目录
if os.path.exists("/dev/shm"):
    # Linux 系统使用内存临时目录
    worker_tmp_dir = "/dev/shm"
else:
    # macOS 和其他系统使用系统临时目录
    worker_tmp_dir = "/tmp" 