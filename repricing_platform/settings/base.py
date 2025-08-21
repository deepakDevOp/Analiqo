"""
Django settings for repricing_platform project.
Base settings shared across all environments.
"""

import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ""),
    DATABASE_URL=(str, ""),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/0"),
    EMAIL_URL=(str, "consolemail://"),
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "django_filters",
    "django_tables2",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "flags",
    "guardian",
    "corsheaders",
    "django_prometheus",
]

LOCAL_APPS = [
    "accounts.apps.AccountsConfig",
    # Temporarily commented out other apps to isolate User model issue
    "core",  # Core utilities and base classes  
    "billing",
    "credentials",
    "catalog",
    "integrations",
    "pricing_rules",
    "pricing_ml",
    "repricer",
    "analytics",
    "notifications",
    "adminpanel",
    "audit",
    "web",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Temporarily commented out custom middleware that might cause import issues
    "accounts.middleware.OrganizationMiddleware",
    "audit.middleware.AuditMiddleware", 
    "core.middleware.TimezoneMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "repricing_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Temporarily commented out custom context processors
                # "accounts.context_processors.organization",
                # "billing.context_processors.subscription", 
                # "notifications.context_processors.alerts",
            ],
        },
    },
]

WSGI_APPLICATION = "repricing_platform.wsgi.application"

# Database
DATABASES = {
    "default": env.db()
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Site ID
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]

# Django Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_SIGNUP_FORM_CLASS = "accounts.forms.SignupForm"
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"

# Login/Logout URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"
SIGNUP_REDIRECT_URL = "/onboarding/"

# Email settings
EMAIL_CONFIG = env.email_url("EMAIL_URL")
vars().update(EMAIL_CONFIG)

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ROUTES = {
    "integrations.*": {"queue": "integrations"},
    "pricing_ml.*": {"queue": "ml"},
    "repricer.*": {"queue": "repricing"},
    "analytics.*": {"queue": "analytics"},
}

# Redis Configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "repricing_platform",
        "TIMEOUT": 300,
    }
}

# Session Configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_SAVE_EVERY_REQUEST = True

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# DRF Spectacular Settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Repricing Platform API",
    "DESCRIPTION": "AI-Powered SaaS Repricing Platform for Amazon and Flipkart",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
}

# Guardian Settings
GUARDIAN_MONKEY_PATCH_USER = False

# Django Tables2 Settings
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/django.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "repricing_platform": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(BASE_DIR / "logs", exist_ok=True)

# Multi-tenancy settings
TENANT_MODEL = "accounts.Organization"
TENANT_FOREIGN_KEY_FIELD = "organization"

# Feature Flags
FLAGS = {
    "ML_PRICING_ENABLED": [
        {"condition": "boolean", "value": True, "required": False}
    ],
    "ADVANCED_ANALYTICS": [
        {"condition": "boolean", "value": True, "required": False}
    ],
    "FLIPKART_INTEGRATION": [
        {"condition": "boolean", "value": True, "required": False}
    ],
}

# Rate Limiting
RATE_LIMIT_PER_TENANT = {
    "FREE": {"api_calls_per_hour": 100, "repricing_runs_per_day": 10},
    "PRO": {"api_calls_per_hour": 1000, "repricing_runs_per_day": 100},
    "ENTERPRISE": {"api_calls_per_hour": 10000, "repricing_runs_per_day": 1000},
}

# API Configuration
AMAZON_SP_API = {
    "BASE_URL": env("AMAZON_SP_API_BASE_URL", default="https://sellingpartnerapi-na.amazon.com"),
    "SANDBOX_URL": env("AMAZON_SP_API_SANDBOX_URL", default="https://sandbox.sellingpartnerapi-na.amazon.com"),
    "RATE_LIMIT": 20,  # requests per second
}

FLIPKART_API = {
    "BASE_URL": env("FLIPKART_API_BASE_URL", default="https://api.flipkart.net"),
    "SANDBOX_URL": env("FLIPKART_API_SANDBOX_URL", default="https://sandbox-api.flipkart.net"),
    "RATE_LIMIT": 10,  # requests per second
}

# ML Configuration
ML_CONFIG = {
    "MODEL_STORAGE_PATH": BASE_DIR / "ml_models",
    "FEATURE_CACHE_TTL": 3600,  # 1 hour
    "RETRAIN_SCHEDULE": "0 2 * * *",  # Daily at 2 AM
    "MIN_TRAINING_SAMPLES": 100,
}

# Billing Configuration
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# Monitoring
SENTRY_DSN = env("SENTRY_DSN", default="")
# 2

# Health Check URLs
HEALTH_CHECK_URLS = {
    "readiness": "/health/ready/",
    "liveness": "/health/live/",
}

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
