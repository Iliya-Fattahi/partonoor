from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default="partonoor_dev"),
        "USER": env("DATABASE_USER", default="partonoor"),
        "PASSWORD": env("DATABASE_PASSWORD", default="partonoor"),
        "HOST": env("DATABASE_HOST", default="localhost"),
        "PORT": env("DATABASE_PORT", default="5432"),
    }
}

# Loosen a couple of things locally only
INTERNAL_IPS = ["127.0.0.1"]
