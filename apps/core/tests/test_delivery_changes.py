from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.core.models import HomepageSection, SiteSettings


class ContactInfoTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_client_contact_details_are_present_after_migrate(self):
        s = SiteSettings.load()
        self.assertEqual(s.phone, "09156249754")
        self.assertIn("partonoor.co", s.instagram_url)
        self.assertEqual(s.whatsapp_link, "https://wa.me/989156249754")
        self.assertEqual(s.telegram_link, "https://t.me/+989156249754")

    def test_links_follow_toggles_and_number(self):
        s = SiteSettings.load()
        s.show_whatsapp = False
        s.phone = "۰۹۱۵۶۲۴۹۷۵۴"
        s.save()
        self.assertEqual(s.whatsapp_link, "")
        self.assertEqual(s.telegram_link, "https://t.me/+989156249754")
        s.phone = ""
        self.assertEqual(s.telegram_link, "")

    def test_footer_and_contact_page_show_number_and_no_removed_fields(self):
        for url in ("/", "/contact/"):
            r = self.client.get(url)
            self.assertContains(r, "09156249754")
            self.assertContains(r, "wa.me/989156249754")
            self.assertContains(r, "instagram.com/partonoor.co")
            self.assertNotContains(r, "نشانی")
            self.assertNotContains(r, "mailto:")

    def test_removed_contact_fields_are_gone_from_admin_form(self):
        User = get_user_model()
        User.objects.create_superuser("boss", "b@example.org", "pw-123456-xyz")
        self.client.login(username="boss", password="pw-123456-xyz")
        r = self.client.get("/admin/core/sitesettings/1/change/")
        self.assertEqual(r.status_code, 200)
        for gone in ("id_address", "id_email", "id_map_embed_url", "id_linkedin_url", "id_aparat_url", "id_mobile"):
            self.assertNotContains(r, gone)
        self.assertContains(r, "id_phone")
        self.assertContains(r, "id_maintenance_mode")

    def test_settings_form_saves_without_logo_upload(self):
        User = get_user_model()
        User.objects.create_superuser("boss", "b@example.org", "pw-123456-xyz")
        self.client.login(username="boss", password="pw-123456-xyz")
        s = SiteSettings.load()
        data = {"company_name_fa": "پرتو نور", "company_name_en": "", "slogan": s.slogan, "phone": "09150000000",
                "show_whatsapp": "on", "show_telegram": "on", "instagram_url": s.instagram_url, "footer_text": "", "copyright_text": "",
                "default_seo_title": "", "default_seo_description": "", "maintenance_title": "x", "maintenance_message": "y"}
        r = self.client.post("/admin/core/sitesettings/1/change/", data)
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["adminform"].form.errors)
        self.assertEqual(SiteSettings.load().phone, "09150000000")


class MaintenanceTests(TestCase):
    def setUp(self):
        cache.clear()
        s = SiteSettings.load()
        s.maintenance_mode = True
        s.maintenance_title = "به‌زودی برمی‌گردیم"
        s.save()
        cache.clear()

    def test_visitors_get_503_branded_noindex_page(self):
        for url in ("/", "/gallery/", "/contact/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 503)
            self.assertContains(r, "به‌زودی برمی‌گردیم", status_code=503)
            self.assertContains(r, "09156249754", status_code=503)
            self.assertEqual(r["Retry-After"], "3600")
            self.assertIn("noindex", r["X-Robots-Tag"])

    def test_admin_login_and_staff_are_not_blocked(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)
        User = get_user_model()
        User.objects.create_superuser("boss", "b@example.org", "pw-123456-xyz")
        self.client.login(username="boss", password="pw-123456-xyz")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_turning_it_off_restores_site(self):
        s = SiteSettings.load()
        s.maintenance_mode = False
        s.save()
        self.assertEqual(self.client.get("/").status_code, 200)


class HomepageEditableTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_kicker_and_overrides_come_from_section_fields(self):
        HomepageSection.objects.create(section_type="brand_intro", title="عنوان تازه", subtitle="متن تازه", kicker="برچسب تازه", display_order=1)
        HomepageSection.objects.create(section_type="gallery", title="آثار تازه", kicker="گالری تازه", cta_label="همه‌ی کارها", display_order=2)
        html = self.client.get("/").content.decode()
        for text in ("عنوان تازه", "متن تازه", "برچسب تازه", "آثار تازه", "گالری تازه"):
            self.assertIn(text, html)

    def test_admin_help_text_shown_for_section(self):
        User = get_user_model()
        User.objects.create_superuser("boss", "b@example.org", "pw-123456-xyz")
        self.client.login(username="boss", password="pw-123456-xyz")
        sec = HomepageSection.objects.create(section_type="hero", title="t", display_order=0)
        r = self.client.get(f"/admin/core/homepagesection/{sec.pk}/change/")
        self.assertContains(r, "بخش بالای صفحه")
