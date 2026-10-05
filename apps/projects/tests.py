"""
Real Django tests for the projects app.

EXECUTION STATUS: written and reviewed for correctness, but NOT executed —
this sandbox has no PyPI/network access to install Django (verified: pip
install django -> 403 from pypi.org). Run with:
    python manage.py test apps.projects
in a real environment. See README.md troubleshooting section.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectCategory

# 1x1 transparent PNG — smallest possible valid image for upload tests.
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_test_image(name="test.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class ProjectModelTests(TestCase):
    def setUp(self):
        self.category = ProjectCategory.objects.create(title="نورپردازی شهری")

    def test_slug_auto_generated_from_title(self):
        project = Project.objects.create(
            title="پروژه تست", short_description="کوتاه", full_description="کامل",
            cover_image=make_test_image(), category=self.category,
        )
        self.assertTrue(project.slug)
        self.assertIn("پروژه", project.slug)  # allow_unicode=True slugify keeps Persian

    def test_get_absolute_url(self):
        project = Project.objects.create(
            title="یک پروژه", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category,
        )
        self.assertEqual(project.get_absolute_url(), reverse("projects:detail", kwargs={"slug": project.slug}))


class ProjectListViewTests(TestCase):
    def setUp(self):
        self.category = ProjectCategory.objects.create(title="لایت آرت")
        self.published = Project.objects.create(
            title="پروژه منتشرشده", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category, published=True,
        )
        self.unpublished = Project.objects.create(
            title="پروژه منتشرنشده", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category, published=False,
        )

    def test_list_returns_200(self):
        response = self.client.get(reverse("projects:list"))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_only_published_projects(self):
        response = self.client.get(reverse("projects:list"))
        titles = [p.title for p in response.context["page_obj"]]
        self.assertIn("پروژه منتشرشده", titles)
        self.assertNotIn("پروژه منتشرنشده", titles)

    def test_list_filters_by_category(self):
        other_category = ProjectCategory.objects.create(title="پروژه‌های سفارشی")
        Project.objects.create(
            title="پروژه دسته دیگر", short_description="s", full_description="f",
            cover_image=make_test_image(), category=other_category, published=True,
        )
        response = self.client.get(reverse("projects:list"), {"category": self.category.slug})
        titles = [p.title for p in response.context["page_obj"]]
        self.assertIn("پروژه منتشرشده", titles)
        self.assertNotIn("پروژه دسته دیگر", titles)

    def test_pagination_object_present(self):
        response = self.client.get(reverse("projects:list"))
        self.assertIn("page_obj", response.context)
        self.assertTrue(hasattr(response.context["page_obj"], "has_other_pages"))


class ProjectDetailViewTests(TestCase):
    def setUp(self):
        self.category = ProjectCategory.objects.create(title="المان‌های نوری")
        self.project = Project.objects.create(
            title="پروژه دیده‌بان", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category, published=True,
            seo_title="عنوان سئوی سفارشی",
        )

    def test_detail_returns_200_for_published(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_detail_returns_404_for_unpublished(self):
        self.project.published = False
        self.project.save()
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_detail_returns_404_for_invalid_slug(self):
        response = self.client.get(reverse("projects:detail", kwargs={"slug": "does-not-exist"}))
        self.assertEqual(response.status_code, 404)

    def test_featured_flag_does_not_affect_visibility(self):
        """featured controls homepage placement, not whether the detail page is reachable."""
        self.project.featured = False
        self.project.save()
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_seo_title_rendered_in_page_title(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertContains(response, "عنوان سئوی سفارشی")

    def test_related_projects_exclude_self(self):
        Project.objects.create(
            title="پروژه مرتبط", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category, published=True,
        )
        response = self.client.get(self.project.get_absolute_url())
        related_ids = [p.pk for p in response.context["related_projects"]]
        self.assertNotIn(self.project.pk, related_ids)


class ProjectBreadcrumbTests(TestCase):
    """
    Regression test for a real bug found during Phase 1 review: the view
    computed breadcrumb_items for the JSON-LD but never passed it into
    the template context, so the *visible* HTML breadcrumb silently never
    rendered (only the invisible JSON-LD did).
    """

    def setUp(self):
        self.category = ProjectCategory.objects.create(title="تست بردکرامب")
        self.project = Project.objects.create(
            title="پروژه بردکرامب", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category, published=True,
        )

    def test_breadcrumb_items_present_in_context(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertIn("breadcrumb_items", response.context)
        self.assertTrue(len(response.context["breadcrumb_items"]) >= 2)

    def test_breadcrumb_visible_in_rendered_html(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertContains(response, 'class="breadcrumbs"')
        self.assertContains(response, "پروژه بردکرامب")

    def test_breadcrumb_projects_link_uses_reverse_not_hardcoded_path(self):
        from django.urls import reverse

        response = self.client.get(self.project.get_absolute_url())
        items = response.context["breadcrumb_items"]
        projects_link = next(i["url"] for i in items if i["name"] == "پروژه‌ها")
        self.assertIn(reverse("projects:list"), projects_link)
