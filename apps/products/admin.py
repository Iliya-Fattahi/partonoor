from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site

from .models import Product, ProductFeature, ProductImage, ProductOrder, ProductVideo


class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 0


@admin.register(Product, site=partonoor_admin_site)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "display_order")
    list_editable = ("published", "display_order")
    search_fields = ("title", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductFeatureInline, ProductImageInline, ProductVideoInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "main_image", "short_description", "full_description")}),
        ("سفارش", {"fields": ("order_cta_label",), "description": "این محصول قابلیت خرید آنلاین ندارد — فقط تماس برای سفارش."}),
        ("نمایش", {"fields": ("published", "display_order")}),
        ("سئو", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
    )


@admin.register(ProductOrder, site=partonoor_admin_site)
class ProductOrderAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "city", "quantity", "model_type", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "created_at")
    search_fields = ("name", "phone", "city", "company")
    date_hierarchy = "created_at"
    readonly_fields = ("product", "name", "company", "phone", "city", "quantity", "model_type", "usage", "message", "created_at")
    fields = readonly_fields + ("status", "admin_note")

    def has_add_permission(self, request):
        return False
