"""
Production settings for watchdog_ai project.
This file contains settings optimized for production deployment on Railway.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# Configure allowed hosts for production
ALLOWED_HOSTS = ["*"]

# Data Augmentation Settings
ENABLE_PRICE_SCRAPING = os.environ.get('ENABLE_PRICE_SCRAPING', 'false').lower() in ('true', '1', 't')
SCRAPING_TIMEOUT = int(os.environ.get('SCRAPING_TIMEOUT', 10))  # seconds

# Performance Monitoring Settings
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
    'django_celery_results',
    
    # Local apps
    'apps.core',
    'apps.users',
    'apps.ai_analytics',
    'apps.blockchain',
    'apps.transaction_management',
    'apps.data_generation',
    'apps.data_augmentation',
    'apps.performance_monitoring',
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
DATABASE_URL = os.environ.get('DATABASE_URL')

# Database configuration for Railway PostgreSQL

# # Check if we're on Railway and have database variables
# DB_LIVE = os.environ.get("DB_LIVE", "false").lower() in ('true', '1', 't')
# print(f"DB_LIVE: {DB_LIVE}")

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

ENVIRONMENT = os.environ.get("ENVIRONMENT")
POSTGRES_LOCAL = os.environ.get("POSTGRES_LOCAL", "False").lower() in ('true', '1', 't')

print(f"ENVIRONMENT: {ENVIRONMENT}")
print(f"POSTGRES_LOCAL: {POSTGRES_LOCAL}")

# Check if we have valid PostgreSQL credentials
has_postgres_creds = all([
    os.environ.get("PGHOST"),
    os.environ.get("PGUSER"),
    os.environ.get("PGPASSWORD"),
    os.environ.get("PGDATABASE")
])

print(f"Has PostgreSQL credentials: {has_postgres_creds}")
    
if (ENVIRONMENT == 'production' or POSTGRES_LOCAL == True) and has_postgres_creds:
    try:
        # Fallback to PostgreSQL configuration
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get("PGDATABASE", "railway"),
            'USER': os.environ.get("PGUSER","postgres"),
            'PASSWORD': os.environ.get("PGPASSWORD"),
            'HOST': os.environ.get("PGHOST"),
            'PORT': os.environ.get("PGPORT"),
        }
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        # Fallback to SQLite for development
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
else:
    # Use SQLite for development
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }





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

CSRF_TRUSTED_ORIGINS = [
    f"https://{os.getenv('RAILWAY_STATIC_URL', 'localhost')}",
    f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost')}",
]

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
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# Celery configuration for production
CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously (no Redis needed)
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in eager mode
CELERY_RESULT_BACKEND = 'django-db'  # Use database instead of Redis
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# CORS settings for production
CORS_ALLOWED_ORIGINS = [
    os.getenv('FRONTEND_URL', 'http://localhost:3000'),
]

CORS_ALLOW_CREDENTIALS = True 