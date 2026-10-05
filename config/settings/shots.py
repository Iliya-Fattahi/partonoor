"""Production-like local settings used only to take real screenshots (DEBUG off => real 404/403/500 pages)."""
from .sqlite_test import *  # noqa

DEBUG = False
QA_MODE = True
SITE_URL = "http://127.0.0.1:8125"
