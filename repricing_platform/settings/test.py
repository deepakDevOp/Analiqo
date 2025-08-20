"""
Test settings for repricing_platform project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Use dummy cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Password hashers for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Media files for tests
MEDIA_ROOT = "/tmp/repricing_platform_test_media"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Test-specific settings
SECRET_KEY = "test-secret-key-for-testing-only"
ALLOWED_HOSTS = ["*"]

# Disable security features for tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use test API keys
STRIPE_PUBLISHABLE_KEY = "pk_test_test"
STRIPE_SECRET_KEY = "sk_test_test"
STRIPE_WEBHOOK_SECRET = "whsec_test"

# Disable external API calls in tests
USE_SANDBOX_APIS = True
AMAZON_SP_API["USE_SANDBOX"] = True
FLIPKART_API["USE_SANDBOX"] = True

# Test feature flags
FLAGS = {
    "ML_PRICING_ENABLED": [{"condition": "boolean", "value": True}],
    "ADVANCED_ANALYTICS": [{"condition": "boolean", "value": True}],
    "FLIPKART_INTEGRATION": [{"condition": "boolean", "value": True}],
}

# Disable Sentry in tests
SENTRY_DSN = None

# Test data
CREATE_DEMO_DATA = False
