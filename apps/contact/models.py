from django.db import models
from django.utils.translation import gettext_lazy as _


class RequestStatus(models.TextChoices):
    NEW = "new", _("جدید")
    CONTACTED = "contacted", _("تماس گرفته شده")
    IN_PROGRESS = "in_progress", _("در حال بررسی")
    COMPLETED = "completed", _("تکمیل‌شده")
    ARCHIVED = "archived", _("بایگانی‌شده")


class ConsultationRequest(models.Model):
    name = models.CharField(_("نام"), max_length=150)
    phone = models.CharField(_("تلفن"), max_length=32)
    email = models.EmailField(_("ایمیل"), blank=True)
    city = models.CharField(_("شهر"), max_length=100, blank=True)
    project_type = models.CharField(_("نوع پروژه"), max_length=150, blank=True)
    message = models.TextField(_("توضیحات"), blank=True)
    status = models.CharField(_("وضعیت"), max_length=20, choices=RequestStatus.choices, default=RequestStatus.NEW)
    created_at = models.DateTimeField(_("تاریخ ثبت"), auto_now_add=True)

    class Meta:
        verbose_name = _("درخواست مشاوره")
        verbose_name_plural = _("درخواست‌های مشاوره")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.get_status_display()}"


class ContactMessage(models.Model):
    name = models.CharField(_("نام"), max_length=150)
    phone = models.CharField(_("تلفن"), max_length=32, blank=True)
    email = models.EmailField(_("ایمیل"), blank=True)
    message = models.TextField(_("پیام"))
    status = models.CharField(_("وضعیت"), max_length=20, choices=RequestStatus.choices, default=RequestStatus.NEW)
    created_at = models.DateTimeField(_("تاریخ ثبت"), auto_now_add=True)

    class Meta:
        verbose_name = _("پیام تماس")
        verbose_name_plural = _("پیام‌های تماس")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.created_at:%Y-%m-%d}"
