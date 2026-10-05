"""
Real Django regression tests for core page rendering, requested explicitly
in the Phase "CORE / FOUNDATION" review: Homepage response, critical
URLs, SAFE-comment regression, structured data validity, and search.

Kept in a separate file (tests_pages.py) from tests.py (signal/validator
tests) purely for readability — Django's test runner discovers both
automatically as long as they're named test*.py or referenced by the
default test label `apps.core`. To be explicit and safe across Django
test-discovery configurations, also import them into tests.py's namespace
is NOT done here — instead this file is run directly via:
    python manage.py test apps.core.tests_pages

EXECUTION STATUS: written, not executed in this sandbox (no Django
install possible — see apps/projects/tests.py header for why).
"""
import json
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import HomepageSection
from apps.core.structured_data import organization_json_ld


class HomepageResponseTests(TestCase):
    def test_homepage_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_homepage_is_graceful_when_no_sections_are_visible(self):
        """Fresh-install state: every HomepageSection seeded with
        is_visible=False. Must not 500, must not show fake content."""
        HomepageSection.objects.update(is_visible=False)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<script>alert", response.content)  # sanity: no stray broken markup

    def test_staff_only_empty_homepage_notice_is_staff_only(self):
        """The empty-homepage admin notice must never appear to anonymous visitors."""
        HomepageSection.objects.update(is_visible=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "این پیام فقط به مدیران سایت نمایش داده می‌شود")

    def test_staff_only_empty_homepage_notice_shows_for_staff(self):
        User = get_user_model()
        staff_user = User.objects.create_user("staff_test", "staff@test.local", "testpass123", is_staff=True)
        self.client.force_login(staff_user)
        HomepageSection.objects.update(is_visible=False)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "این پیام فقط به مدیران سایت نمایش داده می‌شود")


class CriticalURLsTests(TestCase):
    """Every top-level public URL must at least resolve and respond
    without a server error — a broad but real smoke test."""

    def test_all_critical_urls_respond_without_500(self):
        urls = [
            reverse("home"),
            reverse("projects:list"),
            reverse("services:list"),
            reverse("products:list"),
            reverse("articles:list"),
            reverse("gallery:index"),
            reverse("contact:index"),
            reverse("company:about"),
            reverse("company:workshop"),
            reverse("search"),
            "/sitemap.xml",
            "/robots.txt",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertLess(response.status_code, 500, f"{url} returned a server error")


class SafeCommentRegressionTests(TestCase):
    """
    Regression test for the reported production bug: a Django {# #}
    template comment leaked into rendered HTML, and — because it was a
    MULTI-LINE comment containing the literal substrings '<script>' and
    '</' in its own explanatory prose — the browser then parsed fragments
    of the comment's own text as real markup. Every {# #} comment in this
    codebase is now single-line (see scripts/check_templates.py's
    check_multiline_comments for the static guard); this test additionally
    confirms none of that comment TEXT is present in real rendered pages.
    """

    def test_safe_comment_text_never_appears_in_rendered_homepage(self):
        HomepageSection.objects.filter(section_type="hero").update(is_visible=True, published=True)
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("SAFE:", content)
        self.assertNotIn("organization_json_ld is built", content)

    def test_safe_comment_text_never_appears_on_any_public_page(self):
        urls = [
            reverse("home"), reverse("projects:list"), reverse("services:list"),
            reverse("products:list"), reverse("articles:list"), reverse("gallery:index"),
            reverse("company:about"), reverse("contact:index"),
        ]
        for url in urls:
            with self.subTest(url=url):
                content = self.client.get(url).content.decode("utf-8")
                self.assertNotIn("SAFE:", content, f"leaked template comment text found on {url}")


class StructuredDataValidityTests(TestCase):
    def test_organization_json_ld_is_valid_json(self):
        from apps.core.models import SiteSettings

        settings_obj = SiteSettings.load()
        raw = organization_json_ld(settings_obj)
        parsed = json.loads(raw)  # raises if invalid — the test itself IS the assertion
        types = {n["@type"] for n in parsed["@graph"]}
        self.assertEqual(types, {"Organization", "WebSite"})

    def test_organization_json_ld_survives_special_characters_in_company_name(self):
        """A company name containing a double quote or </script> must not
        break the JSON or allow script injection into the page."""
        from apps.core.models import SiteSettings

        settings_obj = SiteSettings.load()
        settings_obj.company_name_fa = 'پرتو نور "ویژه" </script><script>alert(1)</script>'
        settings_obj.save()

        raw = organization_json_ld(settings_obj)
        parsed = json.loads(raw)  # must still be valid JSON despite the quote/script content
        self.assertNotIn("</script>", raw, "raw JSON-LD string must never contain a literal </script>")

    def test_homepage_json_ld_script_tag_is_well_formed_in_rendered_html(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL,
        )
        self.assertIsNotNone(match, "organization JSON-LD script tag not found on homepage")
        json.loads(match.group(1))  # must parse as valid JSON


class SearchTests(TestCase):
    def test_search_with_no_query_returns_200(self):
        response = self.client.get(reverse("search"))
        self.assertEqual(response.status_code, 200)

    def test_search_empty_state_is_in_persian(self):
        response = self.client.get(reverse("search"), {"q": "no-such-thing-xyz"})
        self.assertContains(response, "پیدا نشد")

    def test_search_results_are_paginated_per_category(self):
        response = self.client.get(reverse("search"), {"q": "a"})
        self.assertEqual(response.status_code, 200)
        for key in ("projects", "services", "articles", "products"):
            self.assertIn(key, response.context["results"])

    def test_search_query_is_not_vulnerable_to_sql_wildcard_injection(self):
        """icontains is parameterized by the ORM — a query containing SQL
        wildcard characters must not raise or behave unexpectedly."""
        response = self.client.get(reverse("search"), {"q": "%' OR '1'='1"})
        self.assertEqual(response.status_code, 200)
