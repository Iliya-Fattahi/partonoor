"""
Tests for the real-content seeder. NOT EXECUTED in the authoring sandbox.
Run: python manage.py test apps.core.tests.test_seed_real_media
"""
from django.core.management import call_command
from django.test import TestCase

from apps.articles.models import Article
from apps.gallery.models import GalleryItem, WorkCategory
from apps.products.models import Product
from apps.projects.models import Project, ProjectImage

CLIENT_CATEGORIES = [
    "المان‌های نوری زمینی و مناسبتی", "المان‌های نوری داستانی", "لوسترهای نوری شهری",
    "ریسه‌های نوری عرض خیابانی", "نورپردازی دینامیک", "محصول اختصاصی ریسه نوری", "کاتالوگ",
]


class SeedRealMediaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_real_media", verbosity=0)

    def test_categories_match_the_client_sheet_exactly_and_in_order(self):
        self.assertEqual(list(WorkCategory.objects.values_list("title", flat=True)), CLIENT_CATEGORIES)

    def test_works_are_split_across_categories_and_doubtful_ones_wait_for_review(self):
        self.assertGreater(GalleryItem.objects.filter(needs_review=False).count(), 20)
        self.assertGreater(GalleryItem.objects.filter(needs_review=True).count(), 0)
        self.assertEqual(GalleryItem.objects.filter(needs_review=False, category__isnull=True).count(), 0)

    def test_haft_khan_is_a_staged_case_study_with_its_own_staged_photos(self):
        p = Project.objects.get(slug="haft-khan-rostam")
        self.assertTrue(p.featured)
        stages = set(p.images.values_list("stage", flat=True))
        self.assertTrue({"design", "build", "install", "result"} <= stages)
        # Works in the story category point back to this case study (Works → Project link).
        self.assertTrue(GalleryItem.objects.filter(project=p).exists())

    def test_product_and_articles_seeded(self):
        self.assertEqual(Product.objects.get(slug="risheh").features.count(), 6)
        self.assertEqual(Article.objects.count(), 2)
        for a in Article.objects.all():
            self.assertIn("<h2", a.content)
            self.assertNotIn("<img src=\"article", a.content)

    def test_seeder_is_idempotent(self):
        before = (GalleryItem.objects.count(), ProjectImage.objects.count(), Article.objects.count())
        call_command("seed_real_media", verbosity=0)
        self.assertEqual(before, (GalleryItem.objects.count(), ProjectImage.objects.count(), Article.objects.count()))

    def test_public_pages_render_after_seed(self):
        for url in ("/", "/gallery/", "/projects/haft-khan-rostam/", "/products/risheh/", "/services/", "/articles/", "/about/", "/contact/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_homepage_section_order_is_the_storytelling_order(self):
        from apps.core.models import HomepageSection
        order = list(HomepageSection.objects.filter(is_visible=True).order_by("display_order").values_list("section_type", flat=True))
        want = ["hero", "brand_intro", "differentiator", "featured_projects", "gallery", "services", "product_highlight", "workshop", "company_video", "cta"]
        self.assertEqual([t for t in order if t in want], want)

    def test_story_works_link_to_haft_khan_project_and_back(self):
        p = Project.objects.get(slug="haft-khan-rostam")
        self.assertGreater(GalleryItem.objects.filter(project=p).count(), 0)
        r = self.client.get(p.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "/gallery/")
