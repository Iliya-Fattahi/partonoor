from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import SEOFields
from apps.core.sanitize import sanitize_article_html
from apps.core.validators import validate_image_file


class ArticleCategory(models.Model):
    title = models.CharField(_("عنوان"), max_length=100)
    slug = models.SlugField(_("اسلاگ"), max_length=120, unique=True, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("دسته‌بندی مقاله")
        verbose_name_plural = _("دسته‌بندی‌های مقاله")
        ordering = ["display_order"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Tag(models.Model):
    title = models.CharField(_("عنوان"), max_length=60, unique=True)
    slug = models.SlugField(_("اسلاگ"), max_length=80, unique=True, blank=True)

    class Meta:
        verbose_name = _("برچسب")
        verbose_name_plural = _("برچسب‌ها")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Article(SEOFields):
    title = models.CharField(_("عنوان"), max_length=255)
    slug = models.SlugField(_("اسلاگ"), max_length=280, unique=True, blank=True)
    excerpt = models.CharField(_("خلاصه"), max_length=300)
    content = models.TextField(_("محتوا"), help_text=_("محتوای HTML سالم‌سازی‌شده از ادیتور متن غنی."))
    cover_image = models.ImageField(_("تصویر کاور"), upload_to="articles/", validators=[validate_image_file])
    author_name = models.CharField(_("نام نویسنده و سمت"), max_length=200, blank=True,
                                   help_text=_("مثلاً: مرتضی اسفندیاری — مدیرعامل شرکت پرتونور"))

    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT, related_name="articles", verbose_name=_("دسته‌بندی"))
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles", verbose_name=_("برچسب‌ها"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="articles", verbose_name=_("نویسنده"),
    )

    published = models.BooleanField(_("منتشر شده"), default=False)
    published_at = models.DateTimeField(_("تاریخ انتشار"), null=True, blank=True)
    created_at = models.DateTimeField(_("تاریخ ایجاد"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاریخ بروزرسانی"), auto_now=True)

    class Meta:
        verbose_name = _("مقاله")
        verbose_name_plural = _("مقالات")
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["published", "published_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        if self.published and not self.published_at:
            self.published_at = timezone.now()
        # Sanitize on every save — enforced at the model layer so no entry
        # point (admin, future API, management command) can bypass it.
        self.content = sanitize_article_html(self.content)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("articles:detail", kwargs={"slug": self.slug})
