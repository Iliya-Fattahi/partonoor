from django.core.cache import cache
from django.test import TestCase

from apps.core.models import SiteSettings


class FinalPassTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_admin_login_is_noindex_and_branded_without_english_fallback(self):
        r = self.client.get("/admin/login/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("noindex", r["X-Robots-Tag"])
        self.assertContains(r, 'name="robots" content="noindex')
        self.assertNotContains(r, "PARTO NOOR")

    def test_permissions_policy_header(self):
        self.assertIn("camera=()", self.client.get("/")["Permissions-Policy"])

    def test_english_name_is_optional(self):
        self.assertEqual(SiteSettings.load().company_name_en, "")
        self.assertNotContains(self.client.get("/"), "PARTO NOOR")
