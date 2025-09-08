"""
Production Settings for Watchdog AI Django Application
"""

import os
from datetime import timedelta
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
import sys
import logging
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------
# Load ENVIRONMENT and environment variables
# ---------------------------

load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")  # Default to production for deployment
print(f"ENVIRONMENT: {ENVIRONMENT}")

# ---------------------------
# Custom logging handler for Windows compatibility
# ---------------------------
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback: encode as ASCII with replacement characters
            try:
                msg = self.format(record)
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                stream = self.stream
                stream.write(safe_msg)
                stream.write(self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
       raise ImproperlyConfigured("SECRET_KEY environment variable must be set")


# ---------------------------
# Data Augmentation Settings
# ---------------------------
ENABLE_PRICE_SCRAPING = os.environ.get('ENABLE_PRICE_SCRAPING', 'false').lower() in ('true', '1', 't')
ENABLE_STARTUP_PRICE_SCRAPING = os.environ.get('ENABLE_STARTUP_PRICE_SCRAPING', 'false').lower() in ('true', '1', 't')
SCRAPING_TIMEOUT = int(os.environ.get('SCRAPING_TIMEOUT', 10))  # seconds

# Platform and tier detection
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

def get_platform_tier():
    """Detect platform tier based on environment variables and memory."""
    try:
        import psutil
        platform = detect_platform()
        memory_gb = psutil.virtual_memory().total / (1024**3)
                
        if platform == 'render':
            render_tier = os.environ.get('RENDER_SERVICE_TYPE')
            if render_tier:
                return render_tier.lower()
            
            # Fallback to memory-based detection
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 0.6:  # More conservative threshold
                return 'free'
            elif memory_gb < 1.2:
                return 'starter'
            elif memory_gb < 2.5:
                return 'standard'
            else:
                return 'premium'
        elif platform == 'heroku':
            # Heroku provides DYNO environment variable
            dyno_type = os.environ.get('DYNO', '').split('.')[0] if os.environ.get('DYNO') else None
            if dyno_type:
                return dyno_type.lower()
            
            # Fallback to memory-based detection
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 0.6:
                return 'eco'
            elif memory_gb < 1.2:
                return 'basic'
            else:
                return 'performance'
        elif platform == 'railway':
            return 'standard'  # Railway has consistent resources
        elif platform in ['aws', 'gcp', 'azure', 'digitalocean']:
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 1.5:
                return 'small'
            elif memory_gb < 3:
                return 'medium'
            else:
                return 'large'
        else:
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 0.6:
                return 'minimal'
            elif memory_gb < 1.5:
                return 'small'
            else:
                return 'standard'
    except:
        return 'unknown'


# ---------------------------
# Performance Monitoring Settings
# ---------------------------
ENABLE_PERFORMANCE_MONITORING = os.environ.get('ENABLE_PERFORMANCE_MONITORING', 'false').lower() in ('true', '1', 't')
PERFORMANCE_LOG_PATH = os.environ.get('PERFORMANCE_LOG_PATH', os.path.join(BASE_DIR, 'logs', 'performance_monitoring', 'performance_metrics.json'))

# Railway-specific settings
RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL')
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'apps.core',
    'apps.users',
    'apps.ai_analytics',
    'apps.blockchain',
    'apps.transaction_management',
    'apps.data_generation',
    'apps.data_augmentation',
    'apps.performance_monitoring',

    # Celery
    # 'django_celery_results',
    'django_celery_beat',
]

# Add whitenoise middleware for static file serving
MIDDLEWARE = [
    # Should be first for security best practices
    'django.middleware.security.SecurityMiddleware',
    
    # WhiteNoise is most efficient when placed high up
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    # CORS should come before middleware that can generate responses
    'corsheaders.middleware.CorsMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'watchdog_ai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'watchdog_ai.wsgi.application'


# Database Configuration
    # DB_LIVE = os.environ.get("DB_LIVE", "false").lower() in ('true', '1', 't')
    # print(f"DB_LIVE: {DB_LIVE}")

DATABASE_URL = os.environ.get('DATABASE_URL')

# Initialize DATABASES dict
DATABASES = {}

if ENVIRONMENT == 'development':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('LCLNAME'),
            'USER': os.environ.get('LCLUSER'),
            'PASSWORD': os.environ.get('LCLPASSWORD'),
            'HOST': os.environ.get('LCLHOST'),
            'PORT': os.environ.get('LCLPORT', 5432),
        }
    }
elif ENVIRONMENT == 'production':
    if not DATABASE_URL:
        raise ImproperlyConfigured(
            "DATABASE_URL environment variable must be set for production deployment"
        )
    
    try:
        # Production PostgreSQL configuration
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                ssl_require=True
            )
        }
        print("Successfully configured PostgreSQL database for production")
    except Exception as e:
        raise ImproperlyConfigured(
            f"Failed to configure PostgreSQL database: {e}. "
            "Please check your DATABASE_URL environment variable."
        )

'''
else:
    # Use SQLite for development
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
    print("Using SQLite database for development.")
'''
PLATFORM = detect_platform()
PLATFORM_TIER = get_platform_tier()
print(f"Detected platform: {PLATFORM}, tier: {PLATFORM_TIER}")

# Secure ALLOWED_HOSTS configuration
_env_allowed = os.environ.get('ALLOWED_HOSTS', '')
_env_allowed_list = [h.strip() for h in _env_allowed.split(',') if h.strip()]

hosts: list[str] = []

# Platform-derived hosts
if PLATFORM == 'render':
    render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if render_host:
        hosts.append(render_host)
elif PLATFORM == 'railway':
    railway_host = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    if railway_host:
        hosts.append(railway_host)
elif PLATFORM == 'heroku':
    heroku_app = os.environ.get('HEROKU_APP_NAME')
    if heroku_app:
        hosts.append(f"{heroku_app}.herokuapp.com")
elif PLATFORM in ['aws', 'gcp', 'azure', 'digitalocean']:
    cloud_host = os.environ.get('ALLOWED_HOST')
    if cloud_host:
        hosts.append(cloud_host)

# Explicit env override/appends
hosts.extend(_env_allowed_list)

# Development safety
if DEBUG:
    hosts.extend(['localhost', '127.0.0.1'])

# Deduplicate and filter empties
ALLOWED_HOSTS = [h for i, h in enumerate(hosts) if h and h not in hosts[:i]]

# Final guard: must not be wildcard and must not be empty in production
if not DEBUG:
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("ALLOWED_HOSTS is empty. Set platform host env var or ALLOWED_HOSTS.")
    if '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Wildcard '*' is not allowed in ALLOWED_HOSTS for production.")

'''
POSTGRES_LOCAL = os.environ.get("POSTGRES_LOCAL", "False").lower() in ('true', '1', 't')

print(f"POSTGRES_LOCAL: {POSTGRES_LOCAL}")

# Check if we have valid PostgreSQL credentials
# has_postgres_creds = all([
#     os.environ.get("PGHOST"),
#     os.environ.get("PGUSER"),
#     os.environ.get("PGPASSWORD"),
#     os.environ.get("PGDATABASE")
# ])
# print(f"Has PostgreSQL credentials: {has_postgres_creds}")
'''


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration for production
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Static files finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Authentication settings
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Platform-specific and env-provided CSRF trusted origins
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    # Only add hostnames (not IPs without scheme) for CSRF
    if host and host != 'localhost' and host != '127.0.0.1':
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

# Add localhost for development
CSRF_TRUSTED_ORIGINS.extend(['http://localhost:8000', 'http://127.0.0.1:8000'])

# HTTPS settings (enable when SSL is configured)
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'watchdog_ai.production_settings.SafeStreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'watchdog_ai.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Specific logger for data_augmentation app
        'apps.data_augmentation': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Capture all levels for debugging
            'propagate': False,
        },
        'apps.data_augmentation.services': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.data_augmentation.tasks': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Performance monitoring logs
        'apps.performance_monitoring': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',  # Lowered from WARNING to INFO
    },
}

### CELERY SETTINGS ###

# ---------------------------
# CELERY BROKER & BACKEND
# ---------------------------
if ENVIRONMENT == "development":
    # Local Redis via Docker
    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    # CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")
else:
    # Production: Managed Redis (Render, Railway, etc.)
    CELERY_BROKER_URL = os.environ["REDIS_URL"]       # must exist in env
    # CELERY_RESULT_BACKEND = os.environ["REDIS_URL"]

# ---------------------------
# SERIALIZATION
# ---------------------------
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_RESULT_SERIALIZER = "json"
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

# ---------------------------
# TASK RELIABILITY & PERFORMANCE
# ---------------------------
CELERY_TASK_ACKS_LATE = True                # only ack (acknowledge) after successful completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True    # requeue if worker crashes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1       # fair task distribution
CELERY_TASK_TRACK_STARTED = True
# Adaptive task time limits in section below
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100     # recycle workers to prevent memory leaks

# ---------------------------
# RESULT EXPIRATION
# ---------------------------
# CELERY_RESULT_EXPIRES = timedelta(days=1)


# ---------------------------
# Adaptive task time limits based on platform and tier
# ---------------------------
if PLATFORM_TIER in ['free', 'eco', 'minimal']:
    CELERY_TASK_TIME_LIMIT = 5 * 60  # 5 minutes for free/low tiers
    CELERY_TASK_SOFT_TIME_LIMIT = 3 * 60  # 3 minutes graceful timeout before hard-kill

elif PLATFORM_TIER in ['starter', 'basic', 'small']:
    CELERY_TASK_TIME_LIMIT = 10 * 60  # 10 minutes for starter tiers
    CELERY_TASK_SOFT_TIME_LIMIT = 8 * 60  # 8 minutes soft limit
elif PLATFORM_TIER in ['standard', 'medium']:
    CELERY_TASK_TIME_LIMIT = 20 * 60  # 20 minutes for standard tiers
    CELERY_TASK_SOFT_TIME_LIMIT = 15 * 60  # 15 minutes soft limit
else:  # premium, performance, large
    CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes for higher tiers
    CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit


# ---------------------------
# Sycnhronous Processing Celery configuration (archived)
# ---------------------------
# CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously (no Redis needed)
# CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in eager mode
# # CELERY_RESULT_BACKEND = 'django-db'  # Use database instead of Redis
# CELERY_TASK_TRACK_STARTED = True

#


# ---------------------------
# Email configuration for production
# ---------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# ---------------------------
# CORS settings for production
# ---------------------------
CORS_ALLOWED_ORIGINS = [
    os.getenv('FRONTEND_URL', 'http://localhost:3000'),
]
CORS_ALLOW_CREDENTIALS = True 