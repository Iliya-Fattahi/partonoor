"""
Custom AdminSite so the landing page is a real dashboard (spec section 33)
instead of the default flat model list. Wired up in config/urls.py.

IMPORTANT (bug fixed): every app's admin.py must register its ModelAdmins
on THIS site object (via @admin.register(Model, site=partonoor_admin_site)),
never via the bare @admin.register(Model) decorator — that decorator always
targets django.contrib.admin.site, the global default site, which is a
*different* registry from this one. Using the bare decorator anywhere is
exactly how partonoor_admin_site._registry ends up empty while
django.contrib.admin.site._registry is populated.

The site's `name` is deliberately "admin" (not "partonoor_admin") so every
existing `reverse("admin:...")` / `{% url "admin:..." %}` call in the
codebase (dashboard quick actions, any future admin links) keeps resolving
correctly — AdminSite uses `self.name` as the URL instance namespace.
"""
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import reverse


class PartoNoorAdminSite(AdminSite):
    site_header = "پنل مدیریت پرتو نور"
    site_title = "پرتو نور"
    index_title = "داشبورد مدیریت محتوا"

    def get_app_list(self, request, app_label=None):
        """
        Regroups the flat, one-group-per-Django-app admin index into
        logical categories a non-technical client actually understands
        (spec section 4: "مدیریت سایت / محتوا / ارتباط / تنظیمات"). This
        is a presentation-layer override only — no model, migration, or
        permission change. Permission filtering still happens exactly as
        Django does it by default (via the super() call below); this only
        changes which heading a model's Add/Change link appears under.

        Only applied to the main index (app_label=None). If Django is
        building a single per-app index page (app_label set — used by
        Django 5.0's AdminSite.get_app_list(request, app_label) for a
        specific app's own listing), super() only returns that one app's
        models, so this custom cross-app grouping would show incomplete
        groups. Falling back to Django's own behavior in that case is
        correct and avoids that edge case entirely.

        Any model not explicitly placed in a group below still appears
        under its normal Django app — so a future model nobody remembered
        to categorize here is never silently hidden, just uncategorized.
        """
        original_app_list = super().get_app_list(request, app_label)

        if app_label is not None:
            return original_app_list

        all_models = {}
        for app in original_app_list:
            for model in app["models"]:
                all_models[model["object_name"]] = model

        groups = [
            ("آثار و پروژه‌ها", ["GalleryItem", "WorkCategory", "Project", "ProjectCategory"]),
            ("ریسه و سفارش‌ها", ["Product", "ProductOrder"]),
            ("مقالات و مجله", ["Article", "ArticleCategory", "Tag"]),
            ("خدمات", ["Service"]),
            ("درخواست‌ها و پیام‌ها", ["ConsultationRequest", "ContactMessage"]),
            ("ظاهر سایت و صفحه اصلی", ["HomepageSection", "ProcessStep", "Statistic", "Navigation", "NavigationItem", "AboutSection", "WorkshopSection", "TeamMember", "Gallery"]),
            ("اطلاعات شرکت", ["SiteSettings"]),
            ("حساب مدیر", ["User"]),
        ]

        grouped_app_list = []
        used_model_names = set()
        for group_name, model_names in groups:
            group_models = [all_models[name] for name in model_names if name in all_models]
            if group_models:
                used_model_names.update(m["object_name"] for m in group_models)
                grouped_app_list.append({
                    "name": group_name,
                    "app_label": group_name,
                    "app_url": "#",
                    "has_module_perms": True,
                    "models": group_models,
                })

        for app in original_app_list:
            leftover_models = [m for m in app["models"] if m["object_name"] not in used_model_names]
            if leftover_models:
                grouped_app_list.append({**app, "models": leftover_models})

        return grouped_app_list

    def index(self, request, extra_context=None):
        from apps.projects.models import Project
        from apps.articles.models import Article
        from apps.services.models import Service
        from apps.products.models import Product
        from apps.gallery.models import GalleryItem
        from apps.contact.models import ConsultationRequest, ContactMessage
        from apps.products.models import ProductOrder

        context = {
            "stats": {
                "projects_total": Project.objects.count(),
                "projects_published": Project.objects.filter(published=True).count(),
                "projects_featured": Project.objects.filter(featured=True).count(),
                "articles_total": Article.objects.count(),
                "articles_published": Article.objects.filter(published=True).count(),
                "services_total": Service.objects.count(),
                "products_total": Product.objects.count(),
                "gallery_items": GalleryItem.objects.count(),
                "consultations_new": ConsultationRequest.objects.filter(status="new").count(),
                "messages_new": ContactMessage.objects.filter(status="new").count(),
                "orders_new": ProductOrder.objects.filter(status="new").count(),
                "review_pending": GalleryItem.objects.filter(needs_review=True).count(),
            },
            "recent_orders": ProductOrder.objects.order_by("-created_at")[:5],
            "pending_works": GalleryItem.objects.filter(needs_review=True).select_related("category")[:8],
            "recent_projects": Project.objects.order_by("-created_at")[:5],
            "recent_articles": Article.objects.order_by("-created_at")[:5],
            "recent_consultations": ConsultationRequest.objects.order_by("-created_at")[:5],
            "recent_messages": ContactMessage.objects.order_by("-created_at")[:5],
            "tiles": [
                {"icon": "🖼", "title": "آثار", "hint": "افزودن و مرتب‌سازی عکس‌های آثار", "url": reverse("admin:gallery_galleryitem_changelist"), "add": reverse("admin:gallery_galleryitem_add")},
                {"icon": "🗂", "title": "دسته‌بندی آثار", "hint": "المان‌های داستانی، لوسترها، ...", "url": reverse("admin:gallery_workcategory_changelist")},
                {"icon": "⭐", "title": "پروژه‌های ویژه", "hint": "هفت‌خان رستم و سایر پروژه‌ها", "url": reverse("admin:projects_project_changelist"), "add": reverse("admin:projects_project_add")},
                {"icon": "💡", "title": "ریسه", "hint": "متن، مزیت‌ها و عکس‌های ریسه", "url": reverse("admin:products_product_changelist")},
                {"icon": "🧾", "title": "سفارش‌های ریسه", "hint": "سفارش‌های ثبت‌شده از سایت", "url": reverse("admin:products_productorder_changelist"), "badge": "orders_new"},
                {"icon": "📝", "title": "مقالات", "hint": "نوشتن و ویرایش مقاله", "url": reverse("admin:articles_article_changelist"), "add": reverse("admin:articles_article_add")},
                {"icon": "🛠", "title": "خدمات", "hint": "خدمات و راهکارها", "url": reverse("admin:services_service_changelist")},
                {"icon": "📩", "title": "درخواست‌های مشاوره", "hint": "تماس بگیرید و وضعیت را ثبت کنید", "url": reverse("admin:contact_consultationrequest_changelist"), "badge": "consultations_new"},
                {"icon": "✉", "title": "پیام‌های تماس", "hint": "پیام‌های فرم تماس", "url": reverse("admin:contact_contactmessage_changelist"), "badge": "messages_new"},
                {"icon": "🎨", "title": "ظاهر سایت", "hint": "بخش‌های صفحه اصلی، ویدیو و متن‌ها", "url": reverse("admin:core_homepagesection_changelist")},
                {"icon": "🏢", "title": "درباره شرکت", "hint": "فلسفه، تیم و کارگاه", "url": reverse("admin:company_aboutsection_changelist")},
                {"icon": "⚙", "title": "اطلاعات شرکت", "hint": "لوگو، تلفن، ایمیل، آدرس، شبکه‌ها", "url": reverse("admin:core_sitesettings_changelist")},
            ],
        }
        context.update(extra_context or {})
        return super().index(request, context)


# name="admin" is intentional — see module docstring above.
partonoor_admin_site = PartoNoorAdminSite(name="admin")

# One site, one manager (a superuser). There is deliberately NO Group / role /
# permission management: the single admin account has full access. We keep the
# User model registered only so the owner can change their own password/e-mail.
class OwnerUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("اطلاعات", {"fields": ("first_name", "last_name", "email")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2")}),
    )
    list_display = ("username", "email", "last_login")
    list_filter = ()

    def save_model(self, request, obj, form, change):
        # Any account created from the panel is a full manager: there are no partial roles.
        if not change:
            obj.is_staff = True
            obj.is_superuser = True
        super().save_model(request, obj, form, change)


partonoor_admin_site.register(User, OwnerUserAdmin)
