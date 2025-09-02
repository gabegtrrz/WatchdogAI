# Gunicorn configuration file for deployment
# This file configures Gunicorn with adaptive settings for different platforms and tiers

import os
import multiprocessing
import psutil

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Platform detection
def detect_platform():
    """Detect the deployment platform based on environment variables."""
    if 'RENDER' in os.environ:
        return 'render'
    elif 'RAILWAY' in os.environ:
        return 'railway'
    elif 'HEROKU' in os.environ or 'DYNO' in os.environ:
        return 'heroku'
    elif 'DIGITALOCEAN' in os.environ:
        return 'digitalocean'
    elif 'AWS' in os.environ or 'EC2' in os.environ:
        return 'aws'
    elif 'GCP' in os.environ or 'GOOGLE_CLOUD' in os.environ:
        return 'gcp'
    elif 'AZURE' in os.environ:
        return 'azure'
    else:
        return 'unknown'

# Adaptive worker configuration based on platform and available resources
def get_adaptive_workers():
    """Determine optimal worker count based on platform, memory, and CPU."""
    try:
        platform = detect_platform()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = multiprocessing.cpu_count()
        
        # Platform-specific optimizations
        if platform == 'render':
            # Render tier detection based on memory
            if memory_gb < 1:  # Free tier (~512MB)
                return 1
            elif memory_gb < 2:  # Starter tier (~1GB)
                return 2
            elif memory_gb < 4:  # Standard tier (~2GB)
                return min(cpu_count, 4)
            else:  # Higher tiers
                return min(cpu_count * 2 + 1, 8)
        elif platform == 'railway':
            # Railway has generous memory limits
            return min(cpu_count * 2 + 1, 6)
        elif platform == 'heroku':
            # Heroku dyno detection
            if memory_gb < 1:  # Eco/Basic dynos
                return 1
            elif memory_gb < 2:  # Standard dynos
                return 2
            else:  # Performance dynos
                return min(cpu_count * 2 + 1, 8)
        elif platform in ['aws', 'gcp', 'azure', 'digitalocean']:
            # Cloud platforms - more conservative
            if memory_gb < 2:
                return 2
            elif memory_gb < 4:
                return min(cpu_count, 4)
            else:
                return min(cpu_count * 2 + 1, 8)
        else:
            # Unknown platform - conservative default
            if memory_gb < 1:
                return 1
            elif memory_gb < 2:
                return 2
            else:
                return min(cpu_count, 4)
    except:
        # Fallback to conservative default
        return 2

# Worker processes - adaptive to Render tier
workers = get_adaptive_workers()
worker_class = 'sync'

# Adaptive connection settings based on worker count
if workers <= 2:
    worker_connections = 50   # Conservative for low-memory tiers
    max_requests = 50         # Lower for free/starter tiers
    max_requests_jitter = 5
else:
    worker_connections = 100  # Standard for higher tiers
    max_requests = 100        # Standard for higher tiers
    max_requests_jitter = 10

# Adaptive timeout settings based on worker count
if workers <= 2:
    timeout = 30  # Shorter timeouts for low-memory tiers
    keepalive = 1
    graceful_timeout = 15
else:
    timeout = 60  # Standard timeouts for higher tiers
    keepalive = 2
    graceful_timeout = 30

# Log the adaptive configuration
platform = detect_platform()
print(f"Detected platform: {platform}")
print(f"Adaptive Gunicorn config: {workers} workers, {worker_connections} connections, {timeout}s timeout")

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