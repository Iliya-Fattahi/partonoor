from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderedPublishable
from apps.core.validators import validate_image_file, validate_video_file


class TeamMember(OrderedPublishable):
    name = models.CharField(_("نام"), max_length=150)
    role = models.CharField(_("سمت"), max_length=150)
    photo = models.ImageField(_("عکس"), upload_to="team/", validators=[validate_image_file])
    biography = models.TextField(_("بیوگرافی"), blank=True)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("عضو تیم")
        verbose_name_plural = _("اعضای تیم")

    def __str__(self):
        return self.name


class AboutSection(models.Model):
    """Free-form CMS blocks for the About page — client edits text/media, dev never touches templates."""

    class BlockType(models.TextChoices):
        IDENTITY = "identity", _("هویت شرکت")
        PROCESS = "process", _("فرآیند کار")
        CAPABILITY = "capability", _("توانمندی‌ها")

    block_type = models.CharField(_("نوع بخش"), max_length=20, choices=BlockType.choices)
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    content = models.TextField(_("متن"), blank=True)
    image = models.ImageField(_("تصویر"), upload_to="about/", blank=True, null=True, validators=[validate_image_file])
    video = models.FileField(_("ویدیو"), upload_to="about/videos/", blank=True, null=True, validators=[validate_video_file])
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)
    published = models.BooleanField(_("منتشر شده"), default=True)

    class Meta:
        verbose_name = _("بخش درباره ما")
        verbose_name_plural = _("بخش‌های درباره ما")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or self.get_block_type_display()


class WorkshopSection(models.Model):
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    content = models.TextField(_("متن"), blank=True)
    image = models.ImageField(_("تصویر"), upload_to="workshop/", blank=True, null=True, validators=[validate_image_file])
    video = models.FileField(_("ویدیو"), upload_to="workshop/videos/", blank=True, null=True, validators=[validate_video_file])
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)
    published = models.BooleanField(_("منتشر شده"), default=True)

    class Meta:
        verbose_name = _("بخش کارگاه")
        verbose_name_plural = _("بخش‌های کارگاه")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or f"Workshop block {self.pk}"
