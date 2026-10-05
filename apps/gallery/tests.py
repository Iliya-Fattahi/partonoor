"""
Tests for the works gallery (آثار): categories, filtering, review flag, empty states.
NOT EXECUTED in the authoring sandbox (Django could not be installed there). Run:
    python manage.py test apps.gallery
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import GalleryItem, WorkCategory

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def img(name="g.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


def work(category, name, **kw):
    kw.setdefault("is_visible", True)
    return GalleryItem.objects.create(media_type="image", image=img(name), category=category, title=name, **kw)


class GalleryViewTests(TestCase):
    def setUp(self):
        self.story = WorkCategory.objects.create(title="المان‌های نوری داستانی", display_order=1)
        self.luster = WorkCategory.objects.create(title="لوسترهای نوری شهری", display_order=2)

    def test_empty_gallery_returns_200_with_empty_state(self):
        response = self.client.get(reverse("gallery:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هنوز اثری منتشر نشده است")

    def _all_items(self, response):
        return [it for g in response.context["groups"] for it in g["items"]]

    def test_only_visible_categorised_and_approved_items_are_public(self):
        ok = work(self.story, "ok.png")
        hidden = work(self.story, "hidden.png", is_visible=False)
        pending = work(self.story, "pending.png", needs_review=True)
        no_cat = work(None, "nocat.png")
        items = self._all_items(self.client.get(reverse("gallery:index")))
        self.assertIn(ok, items)
        for bad in (hidden, pending, no_cat):
            self.assertNotIn(bad, items)

    def test_unpublished_category_hides_its_works_and_its_page(self):
        item = work(self.story, "a.png")
        self.story.published = False
        self.story.save()
        self.assertNotIn(item, self._all_items(self.client.get(reverse("gallery:index"))))
        self.assertEqual(self.client.get(f"/gallery/{self.story.slug}/").status_code, 404)

    def test_category_page_follows_display_order_and_only_has_its_items(self):
        b = work(self.luster, "b.png", display_order=1)
        a2 = work(self.story, "a2.png", display_order=2)
        a1 = work(self.story, "a1.png", display_order=1)
        r = self.client.get(reverse("gallery:category", kwargs={"slug": self.story.slug}))
        self.assertEqual(list(r.context["items"]), [a1, a2])
        self.assertNotIn(b, r.context["items"])

    def test_categories_context_has_counts_and_skips_empty_categories(self):
        work(self.story, "a.png")
        cats = self.client.get(reverse("gallery:index")).context["categories"]
        self.assertEqual([c.title for c in cats], [self.story.title])
        self.assertEqual(cats[0].count, 1)

    def test_legacy_query_url_redirects_permanently_to_category_page(self):
        work(self.story, "a.png")
        r = self.client.get(reverse("gallery:index") + f"?category={self.story.slug}")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], reverse("gallery:category", kwargs={"slug": self.story.slug}))

    def test_each_category_page_has_its_own_title_description_and_canonical(self):
        work(self.story, "a.png"); work(self.luster, "b.png")
        seen = set()
        for c in (self.story, self.luster):
            html = self.client.get(reverse("gallery:category", kwargs={"slug": c.slug})).content.decode()
            self.assertIn(c.title, html)
            self.assertIn(f'<link rel="canonical" href="http://', html.replace("https://", "http://"))
            self.assertIn(f"/gallery/{c.slug}/", html)
            import re
            seen.add(re.search(r"<title>(.*?)</title>", html).group(1))
        self.assertEqual(len(seen), 2)

    def test_gallery_container_is_optional(self):
        item = work(self.story, "standalone.png")
        self.assertIsNone(item.gallery)
        self.assertIn(item, self._all_items(self.client.get(reverse("gallery:index"))))
