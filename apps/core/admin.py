from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site
from django.utils.html import format_html

from .models import HomepageSection, Navigation, NavigationItem, ProcessStep, SiteSettings, Statistic


@admin.register(SiteSettings, site=partonoor_admin_site)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton — the client always lands on the same one editable page."""

    fieldsets = (
        ("شناسه شرکت", {"fields": ("company_name_fa", "company_name_en", "slogan")}),
        ("برند و لوگو", {"fields": (
            "logo_full", "logo_symbol", "logo_light", "logo_dark", "favicon_ico", "favicon_svg",
        )}),
        ("اطلاعات تماس و شبکه‌های اجتماعی", {"fields": ("phone", "show_whatsapp", "show_telegram", "instagram_url")}),
        ("فوتر", {"fields": ("footer_text", "copyright_text")}),
        ("سئوی پیش‌فرض", {"fields": ("default_seo_title", "default_seo_description", "default_og_image")}),
        ("صفحه‌ی تعمیرات", {"fields": ("maintenance_mode", "maintenance_title", "maintenance_message")}),
    )

    def has_add_permission(self, request):
        # Singleton: block adding a second settings row from the admin UI.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Skip the list page entirely — jump straight to the single editable object.
        obj = SiteSettings.load()
        from django.shortcuts import redirect
        return redirect("admin:core_sitesettings_change", obj.pk)


class NavigationItemInline(admin.TabularInline):
    model = NavigationItem
    fk_name = "navigation"
    extra = 1
    fields = ("title", "url", "parent", "is_external", "open_in_new_tab", "display_order", "active")


@admin.register(Navigation, site=partonoor_admin_site)
class NavigationAdmin(admin.ModelAdmin):
    list_display = ("slot",)
    inlines = [NavigationItemInline]


@admin.register(Statistic, site=partonoor_admin_site)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "display_order", "published")
    list_editable = ("display_order", "published")
    ordering = ("display_order",)


@admin.register(ProcessStep, site=partonoor_admin_site)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "display_order", "published")
    list_editable = ("display_order", "published")
    ordering = ("display_order",)


@admin.register(HomepageSection, site=partonoor_admin_site)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("section_type_label", "title", "is_visible", "display_order", "preview")
    list_editable = ("display_order", "is_visible")
    ordering = ("display_order",)

    fieldsets = (
        (None, {"fields": ("section_help", "section_type", "kicker", "title", "subtitle", "is_visible", "display_order")}),
        ("رسانه", {"fields": ("image", "video", "video_poster")}),
        ("دکمه", {"fields": ("cta_label", "cta_url")}),
    )
    readonly_fields = ("section_help",)

    HELP = {
        "hero": "بخش بالای صفحه: عنوان، توضیح، تصویر یا ویدیوی پس‌زمینه و دکمه از همین‌جا تغییر می‌کند.",
        "brand_intro": "معرفی کوتاه شرکت: برچسب، عنوان، متن و عکس کنار آن را اینجا بنویسید.",
        "differentiator": "فرایند از طراحی تا اجرا: عنوان و توضیح از همین‌جا؛ خود مراحل از «مراحل کار» در منو تغییر می‌کنند.",
        "featured_projects": "پروژه‌ی ویژه (هفت‌خان رستم): اگر عنوان، توضیح یا تصویر بنویسید جای متن و عکس خود پروژه می‌نشیند؛ خالی بماند از صفحه‌ی پروژه خوانده می‌شود.",
        "gallery": "آثار: عنوان و توضیح بالای بخش؛ عکس دسته‌ها از «آثار» ← «تصاویر آثار» تغییر می‌کند.",
        "services": "خدمات: عنوان و توضیح بالای بخش؛ خود خدمات از «خدمات» تغییر می‌کنند.",
        "product_highlight": "ریسه: اگر متن یا تصویر بنویسید جای متن و عکس خود محصول می‌نشیند؛ خالی بماند از صفحه‌ی محصول خوانده می‌شود.",
        "workshop": "کارگاه: اگر متن یا تصویر بنویسید جای اطلاعات «کارگاه» می‌نشیند؛ خالی بماند از بخش «کارگاه» خوانده می‌شود.",
        "company_video": "ویدیوی معرفی: فایل ویدیو، تصویر پوستر، عنوان و توضیح کوتاه.",
        "cta": "دعوت به مشاوره در انتهای صفحه: عنوان، توضیح و متن دکمه.",
        "statistics": "آمار: ارقام از «آمار» در منو تغییر می‌کنند.",
        "team": "تیم: افراد از «تیم» تغییر می‌کنند.",
    }

    @admin.display(description="راهنما")
    def section_help(self, obj):
        text = self.HELP.get(getattr(obj, "section_type", ""), "")
        return text or "نوع بخش را انتخاب کنید و فیلدهای مورد نیاز را پر کنید؛ فیلدهای خالی با متن پیش‌فرض سایت پر می‌شوند."

    @admin.display(description="نوع بخش")
    def section_type_label(self, obj):
        return obj.get_section_type_display()

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.image.url)
        return "—"
