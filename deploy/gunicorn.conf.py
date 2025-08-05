#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gunicorn 配置文件
用于生产环境部署AI助手平台
"""

import multiprocessing
import os

# 获取CPU核心数
workers = multiprocessing.cpu_count() * 2 + 1

# 服务器绑定
bind = "127.0.0.1:5000"

# 工作进程设置
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 超时设置
timeout = 30
keepalive = 2

# 用户和组
user = "aiplatform"
group = "aiplatform"

# 日志配置
accesslog = "/home/aiplatform/ai_assistant_platform/logs/gunicorn_access.log"
errorlog = "/home/aiplatform/ai_assistant_platform/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程文件
pidfile = "/home/aiplatform/ai_assistant_platform/logs/gunicorn.pid"

# 临时目录
tmp_upload_dir = "/home/aiplatform/ai_assistant_platform/tmp"

# 安全设置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 性能调优
worker_tmp_dir = "/dev/shm"

# 进程管理
max_requests = 1000  # 请求数达到后重启worker
max_requests_jitter = 100

# 优雅关闭
graceful_timeout = 30

# SSL配置（如果需要）
# keyfile = "/path/to/ssl/keyfile"
# certfile = "/path/to/ssl/certfile"

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)