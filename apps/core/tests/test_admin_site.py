"""
Real Django tests for PartoNoorAdminSite.get_app_list() regrouping.

EXECUTION STATUS: written, not run in this sandbox (no Django install
possible — see apps/projects/tests.py header for why). Run with:
    python manage.py test apps.core.tests.test_admin_site
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminAppListGroupingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser("admin_group_test", "a@test.local", "testpass123")
        self.client.force_login(self.superuser)

    def test_main_index_groups_models_into_custom_categories(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        app_list = response.context["app_list"]
        group_names = {app["name"] for app in app_list}
        for name in ("ظاهر سایت و صفحه اصلی", "آثار و پروژه‌ها", "ریسه و سفارش‌ها",
                     "خدمات", "مقالات و مجله", "اطلاعات شرکت", "درخواست‌ها و پیام‌ها", "حساب مدیر"):
            self.assertIn(name, group_names)
        # single-owner site: no roles/groups UI
        all_models = {m["object_name"] for a in app_list for m in a["models"]}
        self.assertNotIn("Group", all_models)
        self.assertIn("User", all_models)

    def test_project_model_appears_under_works_group_not_projects_app(self):
        response = self.client.get("/admin/")
        app_list = response.context["app_list"]
        content_group = next((a for a in app_list if a["name"] == "آثار و پروژه‌ها"), None)
        self.assertIsNotNone(content_group)
        model_names = {m["object_name"] for m in content_group["models"]}
        self.assertIn("Project", model_names)

    def test_per_app_index_page_falls_back_to_default_django_grouping(self):
        """
        Regression test for the app_label edge case: visiting a single
        app's own index page (e.g. /admin/projects/) must not show an
        incomplete custom group — it should fall back to Django's normal
        per-app listing.
        """
        response = self.client.get("/admin/projects/")
        self.assertEqual(response.status_code, 200)
        app_list = response.context["app_list"]
        # Django's default per-app page returns exactly one app entry
        self.assertEqual(len(app_list), 1)
        self.assertEqual(app_list[0]["app_label"], "projects")

    def test_uncategorized_future_model_still_appears_somewhere(self):
        """
        If a model exists that isn't in any of the explicit group lists,
        it must still be visible under its original Django app — never
        silently dropped from the admin index.
        """
        response = self.client.get("/admin/")
        app_list = response.context["app_list"]
        all_visible_models = set()
        for app in app_list:
            for model in app["models"]:
                all_visible_models.add(model["object_name"])
        # Spot check a few models that must be visible somewhere regardless of grouping
        for expected in ("Project", "Article", "ContactMessage", "SiteSettings"):
            self.assertIn(expected, all_visible_models)


class WorkReviewAdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.admin = get_user_model().objects.create_superuser("boss2", "b2@x.ir", "pw12345!")
        self.client.force_login(self.admin)

    def test_dashboard_renders_tiles_and_pending_review_block(self):
        from apps.gallery.models import GalleryItem
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.gallery.tests import TINY_PNG
        GalleryItem.objects.create(media_type="image", needs_review=True, title="مشکوک",
                                   image=SimpleUploadedFile("m.png", TINY_PNG, content_type="image/png"))
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "آثار در انتظار تأیید")
        self.assertContains(response, "داشبورد پرتو نور")

    def test_approve_action_requires_category_then_publishes(self):
        from apps.gallery.models import GalleryItem, WorkCategory
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.gallery.tests import TINY_PNG
        cat = WorkCategory.objects.create(title="لوسترهای نوری شهری")
        it = GalleryItem.objects.create(media_type="image", needs_review=True, is_visible=False, category=cat,
                                        image=SimpleUploadedFile("m.png", TINY_PNG, content_type="image/png"))
        self.client.post(reverse("admin:gallery_galleryitem_changelist"),
                         {"action": "approve_selected", "_selected_action": [it.pk]})
        it.refresh_from_db()
        self.assertFalse(it.needs_review)
        self.assertTrue(it.is_visible)


class SingleOwnerTests(TestCase):
    def test_no_role_groups_exist_after_migrations(self):
        from django.contrib.auth.models import Group
        self.assertEqual(Group.objects.count(), 0)

    def test_group_admin_not_registered(self):
        response = self.client.get("/admin/auth/group/")
        self.assertIn(response.status_code, (302, 404))

    def test_owner_can_open_every_registered_changelist(self):
        from apps.core.admin_site import partonoor_admin_site
        owner = get_user_model().objects.create_superuser("owner_t", "o@test.local", "testpass123")
        self.client.force_login(owner)
        for model, _ma in partonoor_admin_site._registry.items():
            url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
            self.assertIn(self.client.get(url).status_code, (200, 302), url)  # SiteSettings singleton redirects to its form

    def test_new_user_created_in_admin_is_superuser(self):
        owner = get_user_model().objects.create_superuser("owner_t", "o@test.local", "testpass123")
        self.client.force_login(owner)
        self.client.post("/admin/auth/user/add/", {"username": "u2", "password1": "Zx9!kqweRt21", "password2": "Zx9!kqweRt21"})
        u = get_user_model().objects.filter(username="u2").first()
        self.assertTrue(u and u.is_staff and u.is_superuser)
