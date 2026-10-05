from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderedPublishable, SEOFields
from apps.core.validators import validate_image_file


class Service(OrderedPublishable, SEOFields):
    title = models.CharField(_("عنوان"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), max_length=220, unique=True, blank=True)
    short_description = models.CharField(_("توضیح کوتاه"), max_length=300)
    full_description = models.TextField(_("توضیح کامل"))
    main_image = models.ImageField(_("تصویر اصلی"), upload_to="services/", validators=[validate_image_file])

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("خدمت")
        verbose_name_plural = _("خدمات")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", kwargs={"slug": self.slug})


class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="gallery_images", verbose_name=_("خدمت"))
    image = models.ImageField(_("تصویر"), upload_to="services/gallery/", validators=[validate_image_file])
    alt_text = models.CharField(_("متن جایگزین"), max_length=200, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("تصویر خدمت")
        verbose_name_plural = _("تصاویر خدمت")
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.service.title} — image {self.pk}"
