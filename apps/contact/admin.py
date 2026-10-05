from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site

from .models import ConsultationRequest, ContactMessage


@admin.register(ConsultationRequest, site=partonoor_admin_site)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "city", "project_type", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "city", "project_type")
    search_fields = ("name", "phone", "email", "message")
    readonly_fields = ("name", "phone", "email", "city", "project_type", "message", "created_at")


@admin.register(ContactMessage, site=partonoor_admin_site)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status",)
    search_fields = ("name", "phone", "email", "message")
    readonly_fields = ("name", "phone", "email", "message", "created_at")
