from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site
from django.utils.html import format_html

from .models import Project, ProjectCategory, ProjectImage, ProjectVideo


@admin.register(ProjectCategory, site=partonoor_admin_site)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "published")
    list_editable = ("display_order", "published")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    fields = ("preview", "image", "stage", "title", "caption", "alt_text", "display_order", "active")
    readonly_fields = ("preview",)

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;" />', obj.image.url)
        return "—"


class ProjectVideoInline(admin.TabularInline):
    model = ProjectVideo
    extra = 0
    fields = ("poster_preview", "video", "poster", "title", "caption", "display_order", "active")
    readonly_fields = ("poster_preview",)

    @admin.display(description="پوستر")
    def poster_preview(self, obj):
        if obj.pk and obj.poster:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;" />', obj.poster.url)
        return "—"


@admin.register(Project, site=partonoor_admin_site)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "city", "year", "featured", "published", "display_order", "cover_preview")
    list_editable = ("featured", "published", "display_order")
    list_filter = ("category", "featured", "published", "city")
    search_fields = ("title", "city", "client", "location")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProjectImageInline, ProjectVideoInline]
    autocomplete_fields = ["category"]

    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "cover_image", "short_description")}),
        ("داستان پروژه", {"fields": ("full_description", "design_concept", "manufacturing_notes", "execution_notes")}),
        ("اطلاعات پروژه", {"fields": ("city", "location", "year", "client")}),
        ("نمایش", {"fields": ("featured", "published", "display_order")}),
        ("سئو", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
    )

    @admin.display(description="کاور")
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.cover_image.url)
        return "—"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images", "videos")


# search_fields already defined on ProjectAdmin above enables autocomplete from GalleryItemAdmin
