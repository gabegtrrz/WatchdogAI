# Gunicorn configuration file for Railway deployment
# This file configures Gunicorn with appropriate timeout settings to prevent worker timeouts

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings - critical for preventing worker timeouts
timeout = 120  # Worker timeout in seconds (2 minutes)
keepalive = 2
graceful_timeout = 30  # Graceful shutdown timeout

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'watchdog_ai'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (not needed for Railway as it handles SSL termination)
keyfile = None
certfile = None

# Preload app for better performance
preload_app = True

# Worker lifecycle
worker_tmp_dir = None
worker_exit_on_app_exit = False

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
max_requests_jitter = 50
worker_abort_on_exit = False 