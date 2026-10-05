"""Local/CI settings that need no PostgreSQL:  DJANGO_SETTINGS_MODULE=config.settings.sqlite_test"""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test_db.sqlite3"}}
