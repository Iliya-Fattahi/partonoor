from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_image_file, validate_video_file
from apps.projects.models import Project


class Gallery(models.Model):
    """Optional named grouping (e.g. 'Workshop 2025') — GalleryItems can also stand alone."""

    title = models.CharField(_("عنوان"), max_length=200)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)
    published = models.BooleanField(_("منتشر شده"), default=True)

    class Meta:
        verbose_name = _("مجموعه گالری")
        verbose_name_plural = _("مجموعه‌های گالری")
        ordering = ["display_order"]

    def __str__(self):
        return self.title


class WorkCategory(models.Model):
    """دسته‌بندی آثار — مطابق برگه‌ی مشتری (المان‌های داستانی، لوسترهای شهری، ...)."""

    title = models.CharField(_("عنوان"), max_length=150)
    slug = models.SlugField(_("اسلاگ"), max_length=170, unique=True, blank=True, allow_unicode=True)
    description = models.CharField(_("توضیح کوتاه"), max_length=300, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)
    published = models.BooleanField(_("نمایش در سایت"), default=True)
    seo_title = models.CharField(_("عنوان سئو"), max_length=70, blank=True, help_text=_("اختیاری؛ اگر خالی باشد از عنوان دسته ساخته می‌شود."))
    seo_description = models.CharField(_("توضیحات متا"), max_length=160, blank=True, help_text=_("اختیاری؛ اگر خالی باشد از «توضیح کوتاه» ساخته می‌شود."))

    class Meta:
        verbose_name = _("دسته‌بندی آثار")
        verbose_name_plural = _("دسته‌بندی آثار")
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class GalleryItem(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", _("تصویر")
        VIDEO = "video", _("ویدیو")

    gallery = models.ForeignKey(Gallery, on_delete=models.SET_NULL, null=True, blank=True, related_name="items", verbose_name=_("مجموعه"))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="gallery_items", verbose_name=_("پروژه مرتبط"))

    media_type = models.CharField(_("نوع رسانه"), max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    image = models.ImageField(_("تصویر"), upload_to="gallery/images/", blank=True, null=True, validators=[validate_image_file])
    video = models.FileField(_("ویدیو"), upload_to="gallery/videos/", blank=True, null=True, validators=[validate_video_file])
    video_poster = models.ImageField(_("پوستر ویدیو"), upload_to="gallery/videos/posters/", blank=True, null=True, validators=[validate_image_file])

    category = models.ForeignKey(
        WorkCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items",
        verbose_name=_("دسته‌بندی اثر"),
        help_text=_("اثر در بخش «آثار» زیر همین دسته نمایش داده می‌شود."),
    )
    title = models.CharField(_("عنوان اثر"), max_length=200, blank=True)
    needs_review = models.BooleanField(
        _("در انتظار تأیید"), default=False,
        help_text=_("اگر از دسته‌ی این عکس مطمئن نیستید، تیک بزنید؛ تا تأیید نهایی در سایت نمایش داده نمی‌شود."),
    )
    caption = models.CharField(_("زیرنویس"), max_length=300, blank=True)
    alt_text = models.CharField(_("متن جایگزین"), max_length=200, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)
    is_visible = models.BooleanField(_("نمایش عمومی"), default=True)

    class Meta:
        verbose_name = _("آیتم گالری")
        verbose_name_plural = _("آیتم‌های گالری")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or self.caption or f"اثر {self.pk}"
