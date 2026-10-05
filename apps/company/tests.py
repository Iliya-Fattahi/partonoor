"""
Real Django tests for apps.company (About/Workshop/Team). EXECUTION STATUS:
written, not run in this sandbox (see apps/projects/tests.py header).
Run with: python manage.py test apps.company
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import AboutSection, TeamMember, WorkshopSection

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_test_image(name="c.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class AboutPageTests(TestCase):
    def test_about_returns_200_when_empty(self):
        """Spec requirement: graceful when no content exists yet."""
        response = self.client.get(reverse("company:about"))
        self.assertEqual(response.status_code, 200)

    def test_about_shows_only_published_sections(self):
        AboutSection.objects.create(block_type="identity", title="منتشر", published=True)
        AboutSection.objects.create(block_type="process", title="منتشرنشده", published=False)
        response = self.client.get(reverse("company:about"))
        titles = [s.title for s in response.context["sections"]]
        self.assertIn("منتشر", titles)
        self.assertNotIn("منتشرنشده", titles)

    def test_team_member_visibility_respects_published_flag(self):
        TeamMember.objects.create(name="نمایان", role="طراح", photo=make_test_image("a.png"), published=True)
        TeamMember.objects.create(name="پنهان", role="طراح", photo=make_test_image("b.png"), published=False)
        response = self.client.get(reverse("company:about"))
        names = [m.name for m in response.context["team"]]
        self.assertIn("نمایان", names)
        self.assertNotIn("پنهان", names)


class WorkshopPageTests(TestCase):
    def test_workshop_returns_200_when_empty(self):
        response = self.client.get(reverse("company:workshop"))
        self.assertEqual(response.status_code, 200)

    def test_workshop_shows_only_published_blocks(self):
        WorkshopSection.objects.create(title="منتشر", published=True)
        WorkshopSection.objects.create(title="پنهان", published=False)
        response = self.client.get(reverse("company:workshop"))
        titles = [b.title for b in response.context["blocks"]]
        self.assertIn("منتشر", titles)
        self.assertNotIn("پنهان", titles)
