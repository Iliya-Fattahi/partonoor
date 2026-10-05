from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.admin_site import partonoor_admin_site
from apps.core.views import home_view, search_view
from config.sitemaps import sitemaps


def robots_txt(request):
    from django.shortcuts import render
    return render(request, "robots.txt", {"site_url": settings.SITE_URL}, content_type="text/plain; charset=utf-8")


urlpatterns = [
    path("admin/", partonoor_admin_site.urls),

    path("", home_view, name="home"),
    path("search/", search_view, name="search"),

    path("projects/", include("apps.projects.urls")),
    path("services/", include("apps.services.urls")),
    path("products/", include("apps.products.urls")),
    path("articles/", include("apps.articles.urls")),
    path("gallery/", include("apps.gallery.urls")),
    path("contact/", include("apps.contact.urls")),
    path("", include("apps.company.urls")),  # /about/, /workshop/

    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Screenshot / local-QA only (settings.shots): production-like DEBUG=False with media served by Django,
# plus two routes that trigger the real 403 / 500 handlers. Never enabled in production settings.
if getattr(settings, "QA_MODE", False):
    from django.core.exceptions import PermissionDenied
    from django.urls import re_path
    from django.views.static import serve

    def _qa_403(request):
        raise PermissionDenied

    def _qa_500(request):
        raise RuntimeError("QA 500")

    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
        path("__qa/403/", _qa_403),
        path("__qa/500/", _qa_500),
    ]

handler404 = "apps.core.error_views.handler404"
handler403 = "apps.core.error_views.handler403"
handler500 = "apps.core.error_views.handler500"
