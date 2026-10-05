from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderedPublishable, SEOFields
from apps.core.validators import validate_image_file, validate_video_file


class ProjectCategory(OrderedPublishable):
    title = models.CharField(_("عنوان"), max_length=100)
    slug = models.SlugField(_("اسلاگ"), max_length=120, unique=True, blank=True)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("دسته‌بندی پروژه")
        verbose_name_plural = _("دسته‌بندی‌های پروژه")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Project(OrderedPublishable, SEOFields):
    title = models.CharField(_("عنوان پروژه"), max_length=255)
    slug = models.SlugField(_("اسلاگ"), max_length=280, unique=True, blank=True)

    short_description = models.CharField(_("توضیح کوتاه"), max_length=300)
    full_description = models.TextField(_("توضیح کامل / داستان پروژه"))
    design_concept = models.TextField(_("مفهوم طراحی"), blank=True)
    manufacturing_notes = models.TextField(_("ساخت و تولید"), blank=True)
    execution_notes = models.TextField(_("اجرا و نصب"), blank=True)

    cover_image = models.ImageField(_("تصویر کاور"), upload_to="projects/covers/", validators=[validate_image_file])

    city = models.CharField(_("شهر"), max_length=100, blank=True)
    location = models.CharField(_("محل دقیق"), max_length=255, blank=True)
    year = models.PositiveIntegerField(_("سال اجرا"), null=True, blank=True)
    client = models.CharField(_("کارفرما"), max_length=255, blank=True)

    category = models.ForeignKey(
        ProjectCategory, on_delete=models.PROTECT, related_name="projects", verbose_name=_("دسته‌بندی"),
    )

    featured = models.BooleanField(_("پروژه ویژه (نمایش در صفحه اصلی)"), default=False)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("پروژه")
        verbose_name_plural = _("پروژه‌ها")
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["featured", "published"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:detail", kwargs={"slug": self.slug})


class ProjectImage(models.Model):
    class Stage(models.TextChoices):
        DESIGN = "design", _("طراحی")
        BUILD = "build", _("ساخت")
        INSTALL = "install", _("نصب و اجرا")
        RESULT = "result", _("نتیجه‌ی نهایی")

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images", verbose_name=_("پروژه"))
    image = models.ImageField(_("تصویر"), upload_to="projects/gallery/", validators=[validate_image_file])
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    caption = models.CharField(_("زیرنویس"), max_length=300, blank=True)
    alt_text = models.CharField(_("متن جایگزین (Alt)"), max_length=200, blank=True)
    stage = models.CharField(_("مرحله"), max_length=10, choices=Stage.choices, default=Stage.RESULT,
                             help_text=_("عکس در کدام مرحله‌ی پروژه گرفته شده؟ صفحه‌ی پروژه بر همین اساس چیده می‌شود."))
    display_order = models.PositiveIntegerField(_("ترتیب نمایش"), default=0)
    active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("تصویر پروژه")
        verbose_name_plural = _("تصاویر پروژه")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or f"{self.project.title} — image {self.pk}"


class ProjectVideo(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="videos", verbose_name=_("پروژه"))
    video = models.FileField(_("فایل ویدیو"), upload_to="projects/videos/", validators=[validate_video_file])
    poster = models.ImageField(_("پوستر"), upload_to="projects/videos/posters/", validators=[validate_image_file])
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    description = models.TextField(_("توضیح"), blank=True)
    caption = models.CharField(_("زیرنویس"), max_length=300, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب نمایش"), default=0)
    active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("ویدیوی پروژه")
        verbose_name_plural = _("ویدیوهای پروژه")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or f"{self.project.title} — video {self.pk}"
