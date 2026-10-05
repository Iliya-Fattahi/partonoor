"""SEO regression tests: every public page type has unique title/description, correct canonical/robots, valid JSON-LD."""
import json
import re

from django.core.management import call_command
from django.test import TestCase, override_settings

H = re.compile


def meta(html, name):
    m = re.search(r'<meta (?:name|property)="%s" content="([^"]*)"' % re.escape(name), html)
    return m.group(1) if m else None


@override_settings(SITE_URL="https://example-site.test")
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_real_media", verbosity=0)

    def urls(self):
        from apps.articles.models import Article
        from apps.gallery.views import public_categories
        from apps.projects.models import Project
        from apps.services.models import Service
        out = ["/", "/gallery/", "/projects/", "/products/", "/services/", "/articles/", "/about/", "/contact/"]
        out += [c.url for c in public_categories()]
        out += [p.get_absolute_url() for p in Project.objects.filter(published=True)]
        out += [s.get_absolute_url() for s in Service.objects.filter(published=True)]
        out += [a.get_absolute_url() for a in Article.objects.filter(published=True)]
        out += ["/products/risheh/"]
        return out

    def test_every_page_has_title_description_canonical_h1_and_unique_title(self):
        titles, descs = set(), set()
        for u in self.urls():
            r = self.client.get(u)
            self.assertEqual(r.status_code, 200, u)
            html = r.content.decode()
            t = re.search(r"<title>(.*?)</title>", html).group(1)
            self.assertNotIn(t, titles, f"duplicate title {u}")
            titles.add(t)
            d = meta(html, "description")
            self.assertTrue(d and 60 <= len(d) <= 165, f"description length {u}: {len(d or '')}")
            self.assertNotIn(d, descs, f"duplicate description {u}")
            descs.add(d)
            self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1, f"h1 count {u}")
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
            self.assertTrue(canon.startswith("https://example-site.test/"), canon)
            self.assertNotIn("?", canon)
            self.assertEqual(meta(html, "og:url"), canon)
            self.assertTrue(meta(html, "og:image").startswith("https://example-site.test/"))
            self.assertEqual(meta(html, "twitter:card"), "summary_large_image")

    def test_json_ld_is_valid_and_urls_absolute(self):
        for u in self.urls():
            html = self.client.get(u).content.decode()
            for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S):
                data = json.loads(blob)
                text = json.dumps(data, ensure_ascii=False)
                self.assertNotRegex(text, r'"(?:url|item|contentUrl|logo)": "/', u)

    def test_article_has_article_schema_with_real_author_dates_and_tags(self):
        from apps.articles.models import Article
        a = Article.objects.first()
        html = self.client.get(a.get_absolute_url()).content.decode()
        blobs = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S)]
        art = next(b for b in blobs if b.get("@type") == "Article")
        self.assertEqual(art["author"]["@type"], "Person")
        self.assertIn("datePublished", art)
        self.assertIn("dateModified", art)
        self.assertTrue(art["image"][0].startswith("https://"))
        self.assertTrue(a.tags.count() >= 3)
        self.assertIn('rel="tag"', html)
        self.assertIn("BreadcrumbList", json.dumps(blobs))

    def test_filtered_and_search_pages_are_noindex_with_clean_canonical(self):
        for u, canon in (("/articles/?tag=" + __import__("apps.articles.models", fromlist=["Tag"]).Tag.objects.first().slug, "/articles/"),
                         ("/articles/?q=نور", "/articles/"), ("/search/?q=نور", "/search/")):
            html = self.client.get(u).content.decode()
            self.assertIn("noindex", meta(html, "robots"), u)
            self.assertIn(f'href="https://example-site.test{canon}"', html)

    def test_sitemap_lists_only_indexable_canonical_urls(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        locs = re.findall(r"<loc>(.*?)</loc>", xml)
        self.assertTrue(all(l.startswith("https://example-site.test/") for l in locs))
        for bad in ("/admin", "/search", "?", "/tag"):
            self.assertFalse(any(bad in l for l in locs), bad)
        from apps.gallery.views import public_categories
        for c in public_categories():
            self.assertIn("https://example-site.test" + c.url, locs)
        self.assertEqual(len(locs), len(set(locs)))

    def test_robots_txt(self):
        txt = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /admin/", txt)
        self.assertIn("Sitemap: https://example-site.test/sitemap.xml", txt)
        self.assertNotIn("Disallow: /\n", txt)

    def test_error_pages_are_noindex(self):
        r = self.client.get("/definitely-missing/")
        self.assertEqual(r.status_code, 404)
        self.assertIn("noindex", r.content.decode())

    def test_images_have_alt_and_dimensions_on_key_pages(self):
        for u in ("/", "/projects/haft-khan-rostam/", "/gallery/", "/articles/"):
            html = self.client.get(u).content.decode()
            for img in re.findall(r"<img\b[^>]*>", html):
                if 'class="brand' in img:
                    continue
                self.assertIn("alt=", img, (u, img[:80]))
                self.assertIn("width=", img, (u, img[:80]))

    def test_haft_khan_alt_texts_are_unique(self):
        from apps.projects.models import Project
        p = Project.objects.get(slug="haft-khan-rostam")
        alts = list(p.images.values_list("alt_text", flat=True))
        self.assertEqual(len(alts), len(set(alts)))
        self.assertTrue(all(alts))
