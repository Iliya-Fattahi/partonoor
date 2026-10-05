import os

from .base import *  # noqa

DEBUG = False

# --- Fail loudly, not silently, if SECRET_KEY was never configured ---
# base.py defines a permissive default ("unsafe-dev-key-change-me") purely
# so `manage.py` commands work out of the box in local development without
# a .env file. That default must never reach production — check explicitly
# rather than trusting every deployer to remember to set the env var.
if not env("SECRET_KEY", default="") or SECRET_KEY == "unsafe-dev-key-change-me" or SECRET_KEY.startswith("change-me"):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "SECRET_KEY is not set (or still has the insecure development default). "
        "Set a real, unique SECRET_KEY in your production .env file before starting the server."
    )

# The public domain comes from the environment (SITE_URL); nothing is hard-coded here.
if not env("SITE_URL", default=""):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SITE_URL is not set (e.g. SITE_URL=https://your-domain.example) in the production .env file.")

from urllib.parse import urlparse  # noqa: E402

_host = urlparse(SITE_URL).hostname or ""
_bare = _host[4:] if _host.startswith("www.") else _host
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[_bare, f"www.{_bare}"])
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[f"https://{_bare}", f"https://www.{_bare}"],
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME"),
        "USER": env("DATABASE_USER"),
        "PASSWORD": env("DATABASE_PASSWORD"),
        "HOST": env("DATABASE_HOST"),
        "PORT": env("DATABASE_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# --- Security hardening ---
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Logging ---
_LOG_FILE = env("LOG_FILE", default=str(BASE_DIR / "logs" / "partonoor.log"))
os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)  # a fresh checkout has no logs/ directory

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": _LOG_FILE,
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}
