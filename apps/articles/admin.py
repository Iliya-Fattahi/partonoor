from django import forms
from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site

from apps.core.widgets import QuillEditorWidget
from .models import Article, ArticleCategory, Tag


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = "__all__"
        widgets = {"content": QuillEditorWidget}


@admin.register(ArticleCategory, site=partonoor_admin_site)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order")
    list_editable = ("display_order",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


@admin.register(Tag, site=partonoor_admin_site)
class TagAdmin(admin.ModelAdmin):
    list_display = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


@admin.register(Article, site=partonoor_admin_site)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm
    list_display = ("title", "category", "author", "published", "published_at")
    list_editable = ("published",)
    list_filter = ("published", "category", "tags")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["category", "tags"]
    filter_horizontal = ("tags",)
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "tags", "author_name", "cover_image", "excerpt", "content")}),
        ("انتشار", {"fields": ("published", "published_at")}),
        ("سئو", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
