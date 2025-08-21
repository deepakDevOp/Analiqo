"""
Development settings for repricing_platform project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]

# Database for development - using SQLite for simplicity
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Use database sessions instead of cache for development
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Disable CSRF for development API testing
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
    
    INTERNAL_IPS = [
        "127.0.0.1",
        "localhost",
    ]

# Development-specific settings
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously in development
CELERY_TASK_EAGER_PROPAGATES = True

# Disable secure settings for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow all CORS origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Use sandbox APIs in development
USE_SANDBOX_APIS = True

# Feature flags for development
FLAGS["ML_PRICING_ENABLED"][0]["value"] = True
FLAGS["ADVANCED_ANALYTICS"][0]["value"] = True
FLAGS["FLIPKART_INTEGRATION"][0]["value"] = True

# Logging for development
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["loggers"]["repricing_platform"]["level"] = "DEBUG"

# Django Extensions
INSTALLED_APPS += ["django_extensions"]

# Shell Plus
SHELL_PLUS_PRE_IMPORTS = [
    ("django.test", "TestCase"),
    ("django.contrib.auth", "get_user_model"),
]

# Development API Keys (use sandbox/test keys)
AMAZON_SP_API["USE_SANDBOX"] = True
FLIPKART_API["USE_SANDBOX"] = True

# Stripe test keys
STRIPE_PUBLISHABLE_KEY = env("STRIPE_TEST_PUBLISHABLE_KEY", default="pk_test_...")
STRIPE_SECRET_KEY = env("STRIPE_TEST_SECRET_KEY", default="sk_test_...")

# Create demo data on startup
CREATE_DEMO_DATA = env("CREATE_DEMO_DATA", default=True)
