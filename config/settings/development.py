"""
Development settings.
Usage: export DJANGO_SETTINGS_MODULE=config.settings.development
"""

from .base import *  # noqa — imports everything from serializers
from .base import REST_FRAMEWORK as BASE_REST_FRAMEWORK
from datetime import timedelta

DEBUG = True

# ─── Database (SQLite for dev) ────────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ─── Email — Gmail SMTP ───────────────────────────────────────
# Uses Gmail App Password — never your real Gmail password.
# Generate one at: myaccount.google.com → Security → App Passwords

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="akumbomwesley7@gmail.com",
)

# ─── Media / Document Storage (local filesystem) ─────────────

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ─── DRF: add browsable API in dev only ──────────────────────

REST_FRAMEWORK = {
    **BASE_REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# ─── JWT: use our custom token class ─────────────────────────

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_CLASS": "apps.authentication.tokens.AuthToken",
}

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ─── CORS: allow all origins in dev ──────────────────────────

CORS_ALLOW_ALL_ORIGINS = True  # overrides CORS_ALLOWED_ORIGINS from serializers

# ─── Relaxed security for local dev ──────────────────────────

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False