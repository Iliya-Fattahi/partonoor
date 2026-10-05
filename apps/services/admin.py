from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site

from .models import Service, ServiceImage


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1


@admin.register(Service, site=partonoor_admin_site)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "published")
    list_editable = ("display_order", "published")
    search_fields = ("title", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ServiceImageInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "main_image", "short_description", "full_description")}),
        ("نمایش", {"fields": ("published", "display_order")}),
        ("سئو", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
    )
