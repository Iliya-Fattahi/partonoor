from django.core.cache import cache
from django.shortcuts import render

from .models import SiteSettings

CACHE_KEY = "site_settings_singleton"
CACHE_TTL = 60 * 15  # 15 minutes — content changes go live quickly without hitting DB every request


class SiteSettingsMiddleware:
    """Attaches request.site_settings, cached, so every view/template can rely on it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        settings_obj = cache.get(CACHE_KEY)
        if settings_obj is None:
            settings_obj = SiteSettings.load()
            cache.set(CACHE_KEY, settings_obj, CACHE_TTL)
        request.site_settings = settings_obj
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Adds a Permissions-Policy header and keeps the admin area out of search results."""

    PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", self.PERMISSIONS_POLICY)
        if request.path.startswith("/admin/"):
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response


class MaintenanceModeMiddleware:
    """Shows the on-brand maintenance page (HTTP 503) to visitors while «حالت تعمیرات» is on.

    The admin panel, static/media files and logged-in staff are never blocked, so the manager can
    keep working and preview the site. Must sit after SiteSettingsMiddleware and AuthenticationMiddleware.
    """

    ALWAYS_OPEN = ("/admin/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ss = getattr(request, "site_settings", None)
        if ss is not None and ss.maintenance_mode and not request.path.startswith(self.ALWAYS_OPEN):
            user = getattr(request, "user", None)
            if not (user is not None and user.is_authenticated and user.is_staff):
                response = render(request, "maintenance.html", status=503)
                response["Retry-After"] = "3600"
                response["Cache-Control"] = "no-store"
                response["X-Robots-Tag"] = "noindex, nofollow"
                return response
        return self.get_response(request)
