# Gunicorn配置文件
import multiprocessing

# 绑定地址和端口
bind = '0.0.0.0:8001'

# 进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = 'uvicorn.workers.UvicornWorker'

# 进程名称
proc_name = 'personal_task_system'

# 日志级别
loglevel = 'info'

# 日志文件路径
accesslog = './logs/gunicorn.access.log'
errorlog = './logs/gunicorn.error.log'

# 超时时间
timeout = 30

# 守护进程模式
daemon = False
