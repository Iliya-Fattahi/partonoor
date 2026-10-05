"""
Base settings for the Parto Noor project.
Nothing environment-specific lives here — see development.py / production.py.
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Reads a .env file if present (never committed — see .env.example)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-key-change-me")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",

    # Third-party
    "imagekit",

    # Parto Noor apps
    "apps.core",
    "apps.projects",
    "apps.services",
    "apps.products",
    "apps.articles",
    "apps.gallery",
    "apps.company",
    "apps.contact",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SiteSettingsMiddleware",
    "apps.core.middleware.MaintenanceModeMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "apps.core.context_processors.site_settings",
                "apps.core.context_processors.navigation",
                "apps.core.context_processors.seo_defaults",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

# Internationalization — Persian / RTL first
LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_ROOT = env(
    "STATIC_ROOT",
    default=str(BASE_DIR / "staticfiles"),
)
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise static file storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = env("MEDIA_URL", default="/media/")

# Public base URL used for canonical links, sitemap, JSON-LD and robots.txt.
SITE_URL = env(
    "SITE_URL",
    default="http://localhost:8000",
).rstrip("/")

MEDIA_ROOT = env(
    "MEDIA_ROOT",
    default=str(BASE_DIR / "media"),
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Upload safety ---
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
ALLOWED_IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
]
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".webm"]
ALLOWED_VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/webm",
]
MAX_IMAGE_UPLOAD_SIZE_MB = 15
MAX_VIDEO_UPLOAD_SIZE_MB = 300

# --- Email (optional) ---
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="no-reply@localhost",
)

CONSULTATION_NOTIFY_EMAIL = env(
    "CONSULTATION_NOTIFY_EMAIL",
    default="",
)

# --- Caching ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

LOGIN_URL = "/admin/login/"

# Custom admin dashboard branding
ADMIN_SITE_HEADER = "پنل مدیریت پرتو نور"
ADMIN_SITE_TITLE = "پرتو نور"
ADMIN_INDEX_TITLE = "مدیریت محتوا"