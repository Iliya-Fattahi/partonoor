from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_site import partonoor_admin_site

from .models import Gallery, GalleryItem, WorkCategory


class GalleryItemInline(admin.TabularInline):
    model = GalleryItem
    extra = 1
    fk_name = "gallery"


@admin.register(Gallery, site=partonoor_admin_site)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "published")
    list_editable = ("display_order", "published")
    inlines = [GalleryItemInline]


@admin.register(WorkCategory, site=partonoor_admin_site)
class WorkCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "work_count", "display_order", "published")
    list_editable = ("display_order", "published")
    fields = ("title", "description", "display_order", "published", "seo_title", "seo_description")

    @admin.display(description="تعداد آثار")
    def work_count(self, obj):
        return obj.items.count()


@admin.register(GalleryItem, site=partonoor_admin_site)
class GalleryItemAdmin(admin.ModelAdmin):
    """مدیریت آثار: عکس/ویدیو، دسته‌بندی، عنوان و وضعیت نمایش — ساده و بدون گزینه‌ی اضافی."""

    list_display = ("preview", "__str__", "category", "needs_review", "is_visible", "display_order")
    list_display_links = ("preview", "__str__")
    list_editable = ("category", "needs_review", "is_visible", "display_order")
    list_filter = ("category", "needs_review", "is_visible", "media_type")
    search_fields = ("title", "caption")
    list_per_page = 40
    actions = ["approve_selected", "hide_selected"]
    autocomplete_fields = ["project"]
    fieldsets = (
        ("اثر", {"fields": ("media_type", "image", "video", "video_poster", "title", "caption", "category")}),
        ("نمایش", {"fields": ("is_visible", "needs_review", "display_order")}),
        ("تنظیمات بیشتر", {"classes": ("collapse",), "fields": ("alt_text", "project", "gallery")}),
    )

    @admin.action(description="تأیید دسته‌بندی و نمایش در سایت")
    def approve_selected(self, request, queryset):
        missing = queryset.filter(category__isnull=True).count()
        ok = queryset.filter(category__isnull=False)
        updated = ok.update(needs_review=False, is_visible=True)
        if missing:
            self.message_user(request, f"{missing} اثر دسته‌بندی ندارد؛ ابتدا دسته را انتخاب کنید.", level="warning")
        self.message_user(request, f"{updated} اثر تأیید و منتشر شد.")

    @admin.action(description="مخفی کردن از سایت")
    def hide_selected(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_visible=False)} اثر مخفی شد.")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        src = obj.image.url if obj.image else (obj.video_poster.url if obj.video_poster else "")
        return format_html('<img src="{}" style="height:56px;width:84px;object-fit:cover;border-radius:6px">', src) if src else "—"
