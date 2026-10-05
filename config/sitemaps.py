from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.articles.models import Article
from apps.products.models import Product
from apps.projects.models import Project
from apps.services.models import Service


class BaseSitemap(Sitemap):
    """Always emits absolute URLs on the public host (settings.SITE_URL), whatever host served the request."""

    def get_urls(self, page=1, site=None, protocol=None):
        u = urlparse(settings.SITE_URL)

        class _Site:
            domain = u.netloc
        return super().get_urls(page=page, site=_Site(), protocol=u.scheme)


class StaticViewSitemap(BaseSitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return ["home", "gallery:index", "projects:list", "products:list", "services:list", "articles:list",
                "company:about", "company:workshop", "contact:index"]

    def location(self, item):
        return reverse(item)


class ProjectSitemap(BaseSitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return Project.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ServiceSitemap(BaseSitemap):
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return Service.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ProductSitemap(BaseSitemap):
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return Product.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(BaseSitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return Article.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at


class WorkCategorySitemap(BaseSitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        from apps.gallery.views import public_categories
        return public_categories()

    def location(self, obj):
        return obj.url


sitemaps = {
    "works": WorkCategorySitemap,
    "static": StaticViewSitemap,
    "projects": ProjectSitemap,
    "services": ServiceSitemap,
    "products": ProductSitemap,
    "articles": ArticleSitemap,
}
